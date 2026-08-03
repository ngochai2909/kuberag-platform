"""Persistence contracts for documents, chunks, and ingestion runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from ingestion.chunking import TextChunk
from ingestion.models import SourceDocument

UpsertAction = Literal["inserted", "updated", "skipped"]
RunStatus = Literal["running", "completed", "failed"]


@dataclass(frozen=True, slots=True)
class StoredDocument:
    id: UUID
    source: str
    external_id: str
    title: str
    url: str
    published_at: datetime | None
    content: str
    checksum: str
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class StoredChunk:
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    metadata: dict[str, Any]
    embedding: list[float] | None = None


@dataclass(frozen=True, slots=True)
class UpsertResult:
    action: UpsertAction
    document_id: UUID
    chunk_count: int
    source: str
    external_id: str
    checksum: str


@dataclass
class IngestionCounters:
    fetched_count: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0

    def apply(self, result: UpsertResult) -> None:
        self.fetched_count += 1
        if result.action == "inserted":
            self.inserted_count += 1
        elif result.action == "updated":
            self.updated_count += 1
        else:
            self.skipped_count += 1

    def record_failure(self) -> None:
        self.fetched_count += 1
        self.failed_count += 1

    @property
    def total_documents(self) -> int:
        return self.inserted_count + self.updated_count + self.skipped_count


@dataclass(frozen=True, slots=True)
class IngestionRunRecord:
    id: UUID
    flow_name: str
    source_scope: str
    status: RunStatus
    watermark_from: datetime | None
    watermark_to: datetime | None
    counters: IngestionCounters
    error_summary: str | None
    started_at: datetime
    finished_at: datetime | None
    prefect_flow_run_id: UUID | None = None


class DocumentStore(Protocol):
    """Provider-independent persistence used by the upsert service."""

    def get_document(self, source: str, external_id: str) -> StoredDocument | None:
        """Return the current document identity row, if any."""

    def count_documents(self) -> int:
        """Return the number of stored documents."""

    def count_chunks(self) -> int:
        """Return the number of stored chunks."""

    def list_chunks(self, document_id: UUID) -> list[StoredChunk]:
        """Return chunks for one document ordered by chunk_index."""

    def insert_document(
        self,
        document: SourceDocument,
        chunks: list[TextChunk],
        *,
        embeddings: list[list[float]] | None = None,
    ) -> StoredDocument:
        """Insert a new document and its chunks."""

    def update_document(
        self,
        document_id: UUID,
        document: SourceDocument,
        chunks: list[TextChunk],
        *,
        embeddings: list[list[float]] | None = None,
    ) -> StoredDocument:
        """Replace document fields and all chunks for a changed checksum."""

    def start_ingestion_run(
        self,
        *,
        flow_name: str,
        source_scope: str,
        watermark_from: datetime | None = None,
        watermark_to: datetime | None = None,
        prefect_flow_run_id: UUID | None = None,
    ) -> IngestionRunRecord:
        """Create a running ingestion_runs row."""

    def finish_ingestion_run(
        self,
        run_id: UUID,
        *,
        status: RunStatus,
        counters: IngestionCounters,
        error_summary: str | None = None,
        watermark_to: datetime | None = None,
    ) -> IngestionRunRecord:
        """Complete an ingestion run with counters and final status."""

    def get_ingestion_run(self, run_id: UUID) -> IngestionRunRecord | None:
        """Load one ingestion run by id."""


@dataclass
class InMemoryDocumentStore:
    """Deterministic offline store for upsert/idempotency unit tests."""

    documents: dict[tuple[str, str], StoredDocument] = field(default_factory=dict)
    chunks_by_document: dict[UUID, list[StoredChunk]] = field(default_factory=dict)
    runs: dict[UUID, IngestionRunRecord] = field(default_factory=dict)

    def get_document(self, source: str, external_id: str) -> StoredDocument | None:
        return self.documents.get((source, external_id))

    def count_documents(self) -> int:
        return len(self.documents)

    def count_chunks(self) -> int:
        return sum(len(chunks) for chunks in self.chunks_by_document.values())

    def list_chunks(self, document_id: UUID) -> list[StoredChunk]:
        return list(self.chunks_by_document.get(document_id, []))

    def insert_document(
        self,
        document: SourceDocument,
        chunks: list[TextChunk],
        *,
        embeddings: list[list[float]] | None = None,
    ) -> StoredDocument:
        key = (document.source, document.external_id)
        if key in self.documents:
            msg = f"document already exists for {key}"
            raise ValueError(msg)
        stored = StoredDocument(
            id=uuid4(),
            source=document.source,
            external_id=document.external_id,
            title=document.title,
            url=document.url,
            published_at=document.published_at,
            content=document.text,
            checksum=document.checksum,
            metadata=dict(document.metadata),
        )
        self.documents[key] = stored
        self.chunks_by_document[stored.id] = _chunks_for(
            stored.id,
            chunks,
            embeddings=embeddings,
        )
        return stored

    def update_document(
        self,
        document_id: UUID,
        document: SourceDocument,
        chunks: list[TextChunk],
        *,
        embeddings: list[list[float]] | None = None,
    ) -> StoredDocument:
        key = (document.source, document.external_id)
        existing = self.documents.get(key)
        if existing is None or existing.id != document_id:
            msg = f"document {document_id} not found for update"
            raise ValueError(msg)
        stored = StoredDocument(
            id=document_id,
            source=document.source,
            external_id=document.external_id,
            title=document.title,
            url=document.url,
            published_at=document.published_at,
            content=document.text,
            checksum=document.checksum,
            metadata=dict(document.metadata),
        )
        self.documents[key] = stored
        self.chunks_by_document[document_id] = _chunks_for(
            document_id,
            chunks,
            embeddings=embeddings,
        )
        return stored

    def start_ingestion_run(
        self,
        *,
        flow_name: str,
        source_scope: str,
        watermark_from: datetime | None = None,
        watermark_to: datetime | None = None,
        prefect_flow_run_id: UUID | None = None,
    ) -> IngestionRunRecord:
        record = IngestionRunRecord(
            id=uuid4(),
            flow_name=flow_name,
            source_scope=source_scope,
            status="running",
            watermark_from=watermark_from,
            watermark_to=watermark_to,
            counters=IngestionCounters(),
            error_summary=None,
            started_at=datetime.now(UTC),
            finished_at=None,
            prefect_flow_run_id=prefect_flow_run_id,
        )
        self.runs[record.id] = record
        return record

    def finish_ingestion_run(
        self,
        run_id: UUID,
        *,
        status: RunStatus,
        counters: IngestionCounters,
        error_summary: str | None = None,
        watermark_to: datetime | None = None,
    ) -> IngestionRunRecord:
        existing = self.runs.get(run_id)
        if existing is None:
            msg = f"ingestion run {run_id} not found"
            raise ValueError(msg)
        if status == "running":
            msg = "finish_ingestion_run requires completed or failed status"
            raise ValueError(msg)
        finished = IngestionRunRecord(
            id=existing.id,
            flow_name=existing.flow_name,
            source_scope=existing.source_scope,
            status=status,
            watermark_from=existing.watermark_from,
            watermark_to=watermark_to if watermark_to is not None else existing.watermark_to,
            counters=IngestionCounters(
                fetched_count=counters.fetched_count,
                inserted_count=counters.inserted_count,
                updated_count=counters.updated_count,
                skipped_count=counters.skipped_count,
                failed_count=counters.failed_count,
            ),
            error_summary=error_summary,
            started_at=existing.started_at,
            finished_at=datetime.now(UTC),
            prefect_flow_run_id=existing.prefect_flow_run_id,
        )
        self.runs[run_id] = finished
        return finished

    def get_ingestion_run(self, run_id: UUID) -> IngestionRunRecord | None:
        return self.runs.get(run_id)


def _chunks_for(
    document_id: UUID,
    chunks: list[TextChunk],
    *,
    embeddings: list[list[float]] | None = None,
) -> list[StoredChunk]:
    if embeddings is not None and len(embeddings) != len(chunks):
        msg = "embeddings length must match chunks length"
        raise ValueError(msg)
    stored: list[StoredChunk] = []
    for index, chunk in enumerate(chunks):
        metadata = dict(chunk.metadata)
        embedding = embeddings[index] if embeddings is not None else None
        if embedding is not None:
            metadata.setdefault("embedding_dimensions", len(embedding))
        stored.append(
            StoredChunk(
                id=uuid4(),
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                metadata=metadata,
                embedding=list(embedding) if embedding is not None else None,
            )
        )
    return stored
