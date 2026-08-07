from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from http_fakes import FakeHttpClient

from ingestion.adapters.vnexpress import DEFAULT_FEED_URL
from ingestion.chunking import ChunkingConfig
from ingestion.embedding import FakeEmbeddingProvider
from ingestion.flows.ingest import (
    DAILY_INGEST_CRON,
    DAILY_INGEST_FLOW_NAME,
    IngestionRuntime,
    daily_ingest_flow,
    deployment_schedule,
    flow_pipeline_steps,
    ingestion_runtime,
    summarize_flow_result,
)
from ingestion.http import HttpResponse
from ingestion.store import InMemoryDocumentStore

FIXTURES = Path(__file__).parent / "fixtures"

ARTICLE_1 = "https://vnexpress.net/robot-ho-tro-van-hanh-kho-1001.html"
ARTICLE_2 = "https://vnexpress.net/pin-the-ran-1002.html"


def load_fixture(*parts: str) -> str:
    return FIXTURES.joinpath(*parts).read_text(encoding="utf-8")


@dataclass
class SequentialProbeHttpClient(FakeHttpClient):
    """Fail the run unless article 1 is already stored before article 2 is fetched."""

    store: InMemoryDocumentStore | None = None
    saw_first_upserted_before_second_fetch: bool = field(default=False, init=False)

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        if url == ARTICLE_2 and self.store is not None:
            existing = self.store.get_document("vnexpress", ARTICLE_1)
            if existing is not None:
                self.saw_first_upserted_before_second_fetch = True
        return super().get(url, headers=headers, timeout=timeout)


def _runtime_with_fixtures() -> tuple[IngestionRuntime, InMemoryDocumentStore]:
    store = InMemoryDocumentStore()
    feed = load_fixture("vnexpress", "feed.xml")
    http = FakeHttpClient(
        {
            "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss": HttpResponse(200, feed),
            ARTICLE_1: HttpResponse(200, load_fixture("vnexpress", "article-1001.html")),
            ARTICLE_2: HttpResponse(200, load_fixture("vnexpress", "article-1002.html")),
        }
    )
    runtime = IngestionRuntime(
        http=http,
        store=store,
        embedder=FakeEmbeddingProvider(),
        chunking=ChunkingConfig(max_chars=220, overlap_chars=40),
        vnexpress_feed_urls=[DEFAULT_FEED_URL],
        embedding_batch_size=2,
    )
    return runtime, store


def test_deployment_schedule_is_daily_cron() -> None:
    schedule = deployment_schedule()
    assert schedule["flow_name"] == DAILY_INGEST_FLOW_NAME
    assert schedule["cron"] == DAILY_INGEST_CRON
    assert schedule["cron"].count(" ") == 4
    assert schedule["timezone"] == "UTC"


def test_pipeline_step_contract() -> None:
    assert flow_pipeline_steps() == [
        "catalog",
        "fetch",
        "normalize",
        "deduplicate",
        "chunk",
        "embed",
        "upsert",
    ]


def test_daily_ingest_flow_runs_offline_with_fakes() -> None:
    runtime, store = _runtime_with_fixtures()
    with ingestion_runtime(runtime):
        result = daily_ingest_flow()

    assert result.flow_name == DAILY_INGEST_FLOW_NAME
    assert result.status == "completed"
    assert result.sources == ["vnexpress"]
    assert result.document_count == 2
    assert result.counters.inserted_count == 2
    assert result.counters.failed_count == 0
    assert store.count_documents() == 2
    assert store.count_chunks() >= 2
    # Embeddings were produced for inserted chunks.
    embedded = [chunk for chunks in store.chunks_by_document.values() for chunk in chunks]
    assert embedded
    assert all(chunk.embedding is not None for chunk in embedded)

    summary = summarize_flow_result(result)
    assert summary["inserted_count"] == 2
    assert summary["status"] == "completed"


def test_daily_ingest_flow_is_idempotent_on_second_run() -> None:
    runtime, store = _runtime_with_fixtures()
    with ingestion_runtime(runtime):
        first = daily_ingest_flow()
        second = daily_ingest_flow()

    assert first.counters.inserted_count == 2
    assert second.counters.skipped_count == 2
    assert second.counters.inserted_count == 0
    assert store.count_documents() == 2


def test_daily_ingest_flow_accepts_vnexpress_source() -> None:
    runtime, store = _runtime_with_fixtures()
    with ingestion_runtime(runtime):
        result = daily_ingest_flow(sources=["vnexpress"])

    assert result.sources == ["vnexpress"]
    assert result.document_count == 2
    assert store.count_documents() == 2


def test_daily_ingest_flow_uses_operator_feed_override() -> None:
    runtime, store = _runtime_with_fixtures()
    http = cast(FakeHttpClient, runtime.http)
    override_url = "https://fixture.example.invalid/vnexpress.rss"
    http.responses[override_url] = http.responses.pop(
        "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss"
    )

    with ingestion_runtime(runtime):
        result = daily_ingest_flow(vnexpress_feed_url=override_url)

    assert result.status == "completed"
    assert result.document_count == 2
    assert http.calls[0][0] == override_url
    assert store.count_documents() == 2


def test_daily_ingest_upserts_each_article_before_fetching_the_next() -> None:
    store = InMemoryDocumentStore()
    feed = load_fixture("vnexpress", "feed.xml")
    http = SequentialProbeHttpClient(
        responses={
            "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss": HttpResponse(200, feed),
            ARTICLE_1: HttpResponse(200, load_fixture("vnexpress", "article-1001.html")),
            ARTICLE_2: HttpResponse(200, load_fixture("vnexpress", "article-1002.html")),
        },
        store=store,
    )
    runtime = IngestionRuntime(
        http=http,
        store=store,
        embedder=FakeEmbeddingProvider(),
        chunking=ChunkingConfig(max_chars=220, overlap_chars=40),
        vnexpress_feed_urls=[DEFAULT_FEED_URL],
        embedding_batch_size=2,
    )

    with ingestion_runtime(runtime):
        result = daily_ingest_flow()

    assert result.status == "completed"
    assert result.counters.inserted_count == 2
    assert http.saw_first_upserted_before_second_fetch
    assert [call[0] for call in http.calls] == [
        "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss",
        ARTICLE_1,
        ARTICLE_2,
    ]
