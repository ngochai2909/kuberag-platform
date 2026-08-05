"""Daily ingestion Prefect flow: fetch → normalize → dedup → chunk → embed → upsert.

The flow is dependency-injected through :class:`IngestionRuntime` so unit tests
can run offline with fake HTTP, fake embeddings, and an in-memory store.
Prefect server/worker deployment and the real e5 model remain later cluster
checkpoints.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from prefect import flow, task

from ingestion.adapters.vnexpress import DEFAULT_FEED_URLS, VnExpressAdapter
from ingestion.chunking import ChunkingConfig
from ingestion.embedding import EmbeddingProvider
from ingestion.http import HttpClient
from ingestion.models import SourceDocument
from ingestion.store import DocumentStore, IngestionCounters, IngestionRunRecord
from ingestion.telemetry import (
    configure_ingestion_telemetry,
    get_tracer,
    log_event,
    record_flow_result,
    shutdown_ingestion_telemetry,
)
from ingestion.upsert import start_ingestion_run

DAILY_INGEST_FLOW_NAME = "kuberag-daily-ingest"
# 03:00 UTC is 10:00 Asia/Ho_Chi_Minh (Vietnam, UTC+7).
DAILY_INGEST_CRON = "0 3 * * *"
DAILY_INGEST_TIMEZONE = "UTC"

SourceName = Literal["vnexpress"]

_RUNTIME: IngestionRuntime | None = None


@dataclass(slots=True)
class IngestionRuntime:
    """Injectable collaborators for one ingestion flow execution."""

    http: HttpClient
    store: DocumentStore
    embedder: EmbeddingProvider | None = None
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    vnexpress_feed_urls: list[str] = field(default_factory=lambda: list(DEFAULT_FEED_URLS))
    embedding_batch_size: int = 32


@dataclass(frozen=True, slots=True)
class IngestionFlowResult:
    """Business summary returned by the daily ingest flow."""

    flow_name: str
    status: Literal["completed", "failed"]
    sources: list[str]
    document_count: int
    counters: IngestionCounters
    run_id: UUID
    started_at: datetime
    finished_at: datetime | None
    error_summary: str | None = None


@contextmanager
def ingestion_runtime(runtime: IngestionRuntime) -> Iterator[IngestionRuntime]:
    """Bind collaborators for the current process while a flow runs."""

    global _RUNTIME
    previous = _RUNTIME
    _RUNTIME = runtime
    try:
        yield runtime
    finally:
        _RUNTIME = previous


def get_ingestion_runtime() -> IngestionRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        # Cluster workers bind collaborators from env; unit tests inject explicitly.
        from ingestion.runtime_env import build_runtime_from_env

        _RUNTIME = build_runtime_from_env()
    return _RUNTIME


def deployment_schedule() -> dict[str, str]:
    """Declarative daily schedule for later Prefect deployment registration.

    ING-005 cluster evidence still requires inspecting the deployed schedule in
    Prefect UI/API after server/worker exist. This helper keeps the cron choice
    versioned in Git until then.
    """

    return {
        "flow_name": DAILY_INGEST_FLOW_NAME,
        "cron": DAILY_INGEST_CRON,
        "timezone": DAILY_INGEST_TIMEZONE,
    }


@task(name="fetch-vnexpress", retries=2, retry_delay_seconds=1)
def fetch_vnexpress_documents(
    *,
    feed_url: str | None = None,
    feed_urls: list[str] | None = None,
) -> list[SourceDocument]:
    runtime = get_ingestion_runtime()
    if feed_url:
        urls = [feed_url]
    elif feed_urls is not None:
        urls = feed_urls
    else:
        urls = list(runtime.vnexpress_feed_urls)
    adapter = VnExpressAdapter(runtime.http)
    with get_tracer().start_as_current_span("ingestion.fetch"):
        return adapter.fetch_documents_from_feeds(urls)


@task(name="upsert-documents", retries=1, retry_delay_seconds=1)
def upsert_documents(
    documents: list[SourceDocument],
    *,
    source_scope: str,
) -> IngestionRunRecord:
    runtime = get_ingestion_runtime()
    session = start_ingestion_run(
        runtime.store,
        flow_name=DAILY_INGEST_FLOW_NAME,
        source_scope=source_scope,
        chunking=runtime.chunking,
        embedder=runtime.embedder,
        embedding_batch_size=runtime.embedding_batch_size,
    )
    with get_tracer().start_as_current_span("ingestion.upsert"):
        for document in documents:
            try:
                session.upsert_document(document)
            except Exception as exc:
                session.record_failure(exc)
    return session.complete(watermark_to=datetime.now(UTC))


@flow(name=DAILY_INGEST_FLOW_NAME, log_prints=False)
def daily_ingest_flow(
    sources: list[SourceName] | None = None,
    *,
    vnexpress_feed_url: str | None = None,
) -> IngestionFlowResult:
    """Run the deterministic ingestion pipeline for configured sources.

    ``vnexpress_feed_url`` is an operator-only override used by the isolated
    failure-test Job (forces a single feed URL). Normal runs use the multi-feed
    catalog on :class:`IngestionRuntime`.
    """

    configure_ingestion_telemetry()
    started_monotonic = datetime.now(UTC)
    selected: list[SourceName] = list(sources) if sources else ["vnexpress"]
    documents: list[SourceDocument] = []
    log_event(
        "ingestion_started", flow_name=DAILY_INGEST_FLOW_NAME, source_scope=",".join(selected)
    )

    try:
        if "vnexpress" in selected:
            documents.extend(fetch_vnexpress_documents(feed_url=vnexpress_feed_url))

        categories = sorted(
            {
                str(document.metadata.get("category"))
                for document in documents
                if isinstance(document.metadata.get("category"), str)
            }
        )
        source_scope = (
            f"vnexpress:{','.join(categories)}" if categories else ",".join(selected)
        )
        run = upsert_documents(documents, source_scope=source_scope)
        status: Literal["completed", "failed"] = (
            "failed" if run.status != "completed" else "completed"
        )
        duration_seconds = (datetime.now(UTC) - started_monotonic).total_seconds()
        record_flow_result(
            status=status,
            document_count=len(documents),
            duration_seconds=duration_seconds,
        )
        log_event(
            "ingestion_completed",
            flow_name=DAILY_INGEST_FLOW_NAME,
            status=status,
            document_count=len(documents),
            duration_ms=round(duration_seconds * 1000, 2),
        )
        return IngestionFlowResult(
            flow_name=DAILY_INGEST_FLOW_NAME,
            status=status,
            sources=list(selected),
            document_count=len(documents),
            counters=run.counters,
            run_id=run.id,
            started_at=run.started_at,
            finished_at=run.finished_at,
            error_summary=run.error_summary,
        )
    except Exception:
        duration_seconds = (datetime.now(UTC) - started_monotonic).total_seconds()
        record_flow_result(
            status="failed", document_count=len(documents), duration_seconds=duration_seconds
        )
        log_event(
            "ingestion_failed",
            flow_name=DAILY_INGEST_FLOW_NAME,
            duration_ms=round(duration_seconds * 1000, 2),
        )
        raise
    finally:
        # Short-lived Prefect processes must flush OTLP batches before exit.
        shutdown_ingestion_telemetry()


def flow_pipeline_steps() -> list[str]:
    """Stable step names for contract/documentation tests."""

    return [
        "fetch",
        "normalize",
        "deduplicate",
        "chunk",
        "embed",
        "upsert",
    ]


# Prefect may wrap returns; keep a plain helper for typing-focused callers.
def summarize_flow_result(result: IngestionFlowResult) -> dict[str, Any]:
    return {
        "flow_name": result.flow_name,
        "status": result.status,
        "sources": result.sources,
        "document_count": result.document_count,
        "fetched_count": result.counters.fetched_count,
        "inserted_count": result.counters.inserted_count,
        "updated_count": result.counters.updated_count,
        "skipped_count": result.counters.skipped_count,
        "failed_count": result.counters.failed_count,
        "run_id": str(result.run_id),
        "error_summary": result.error_summary,
    }
