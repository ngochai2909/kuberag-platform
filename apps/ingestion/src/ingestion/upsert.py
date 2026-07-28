"""Idempotent document/chunk upsert and ingestion_run recording."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

from ingestion.chunking import ChunkingConfig, TextChunk, chunk_document
from ingestion.embedding import EmbeddingProvider, embed_chunks
from ingestion.models import SourceDocument
from ingestion.store import (
    DocumentStore,
    IngestionCounters,
    IngestionRunRecord,
    UpsertResult,
)


@dataclass(slots=True)
class DocumentUpserter:
    """Upsert SourceDocument rows using checksum-based skip/update rules."""

    store: DocumentStore
    chunking: ChunkingConfig | None = None
    embedder: EmbeddingProvider | None = None
    embedding_batch_size: int = 32

    def upsert(
        self,
        document: SourceDocument,
        *,
        chunks: list[TextChunk] | None = None,
    ) -> UpsertResult:
        existing = self.store.get_document(document.source, document.external_id)
        if existing is not None and existing.checksum == document.checksum:
            return UpsertResult(
                action="skipped",
                document_id=existing.id,
                chunk_count=len(self.store.list_chunks(existing.id)),
                source=document.source,
                external_id=document.external_id,
                checksum=document.checksum,
            )

        prepared = chunks if chunks is not None else chunk_document(document, config=self.chunking)
        embeddings = self._embed(prepared)
        action: Literal["inserted", "updated"]
        if existing is None:
            stored = self.store.insert_document(
                document,
                prepared,
                embeddings=embeddings,
            )
            action = "inserted"
        else:
            stored = self.store.update_document(
                existing.id,
                document,
                prepared,
                embeddings=embeddings,
            )
            action = "updated"

        return UpsertResult(
            action=action,
            document_id=stored.id,
            chunk_count=len(prepared),
            source=document.source,
            external_id=document.external_id,
            checksum=document.checksum,
        )

    def upsert_many(self, documents: list[SourceDocument]) -> list[UpsertResult]:
        return [self.upsert(document) for document in documents]

    def _embed(self, chunks: list[TextChunk]) -> list[list[float]] | None:
        if self.embedder is None or not chunks:
            return None
        vectors = embed_chunks(
            chunks,
            self.embedder,
            batch_size=self.embedding_batch_size,
        )
        for chunk in chunks:
            chunk.metadata["embedding_model"] = self.embedder.model_id
            chunk.metadata["embedding_dimensions"] = self.embedder.dimensions
        return vectors


@dataclass(slots=True)
class IngestionRunSession:
    """Tracks one business ingestion run and its counters."""

    store: DocumentStore
    run: IngestionRunRecord
    counters: IngestionCounters
    upserter: DocumentUpserter
    _pending_errors: list[str] = field(default_factory=list, init=False, repr=False)

    def upsert_document(
        self,
        document: SourceDocument,
        *,
        chunks: list[TextChunk] | None = None,
    ) -> UpsertResult:
        result = self.upserter.upsert(document, chunks=chunks)
        self.counters.apply(result)
        return result

    def record_failure(self, error: Exception | str) -> None:
        self.counters.record_failure()
        self._pending_errors.append(sanitize_error_summary(error))

    def complete(self, *, watermark_to: datetime | None = None) -> IngestionRunRecord:
        error_summary = _join_errors(self._pending_errors)
        status: Literal["completed", "failed"] = (
            "failed" if self.counters.failed_count > 0 else "completed"
        )
        if status == "failed" and error_summary is None:
            error_summary = "one or more documents failed during upsert"
        return self.store.finish_ingestion_run(
            self.run.id,
            status=status,
            counters=self.counters,
            error_summary=error_summary,
            watermark_to=watermark_to,
        )

    def fail(
        self,
        error: Exception | str,
        *,
        watermark_to: datetime | None = None,
    ) -> IngestionRunRecord:
        self._pending_errors.append(sanitize_error_summary(error))
        return self.store.finish_ingestion_run(
            self.run.id,
            status="failed",
            counters=self.counters,
            error_summary=_join_errors(self._pending_errors),
            watermark_to=watermark_to,
        )


def start_ingestion_run(
    store: DocumentStore,
    *,
    flow_name: str,
    source_scope: str,
    watermark_from: datetime | None = None,
    watermark_to: datetime | None = None,
    prefect_flow_run_id: UUID | None = None,
    chunking: ChunkingConfig | None = None,
    embedder: EmbeddingProvider | None = None,
    embedding_batch_size: int = 32,
) -> IngestionRunSession:
    run = store.start_ingestion_run(
        flow_name=flow_name,
        source_scope=source_scope,
        watermark_from=watermark_from,
        watermark_to=watermark_to,
        prefect_flow_run_id=prefect_flow_run_id,
    )
    return IngestionRunSession(
        store=store,
        run=run,
        counters=IngestionCounters(),
        upserter=DocumentUpserter(
            store=store,
            chunking=chunking,
            embedder=embedder,
            embedding_batch_size=embedding_batch_size,
        ),
    )


def sanitize_error_summary(error: Exception | str, *, limit: int = 500) -> str:
    """Keep run errors bounded and free of raw document bodies."""

    text = f"{type(error).__name__}: {error}" if isinstance(error, Exception) else error
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 3]}..."


def run_idempotent_upsert(
    store: DocumentStore,
    documents: list[SourceDocument],
    *,
    flow_name: str,
    source_scope: str,
    chunking: ChunkingConfig | None = None,
    embedder: EmbeddingProvider | None = None,
    embedding_batch_size: int = 32,
) -> tuple[IngestionRunRecord, list[UpsertResult]]:
    """Upsert a batch and persist ingestion_run counters (Prefect-independent)."""

    session = start_ingestion_run(
        store,
        flow_name=flow_name,
        source_scope=source_scope,
        chunking=chunking,
        embedder=embedder,
        embedding_batch_size=embedding_batch_size,
    )
    results: list[UpsertResult] = []
    for document in documents:
        try:
            results.append(session.upsert_document(document))
        except Exception as exc:
            session.record_failure(exc)
    finished = session.complete()
    return finished, results


def _join_errors(errors: list[str]) -> str | None:
    if not errors:
        return None
    return sanitize_error_summary("; ".join(errors))
