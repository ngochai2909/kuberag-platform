"""PostgreSQL-backed document/chunk/ingestion_run store."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from ingestion.chunking import TextChunk
from ingestion.models import SourceDocument
from ingestion.store import (
    IngestionCounters,
    IngestionRunRecord,
    RunStatus,
    StoredChunk,
    StoredDocument,
)


class PostgresDocumentStore:
    """Persist upserts through CloudNativePG using the Alembic schema."""

    def __init__(self, connection: Connection[Any]) -> None:
        self._connection = connection

    def get_document(self, source: str, external_id: str) -> StoredDocument | None:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, source, external_id, title, url, published_at,
                       content, checksum, metadata
                FROM documents
                WHERE source = %s AND external_id = %s
                """,
                (source, external_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return _document_from_row(row)

    def count_documents(self) -> int:
        with self._connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM documents")
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    def count_chunks(self) -> int:
        with self._connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM chunks")
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    def list_chunks(self, document_id: UUID) -> list[StoredChunk]:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, document_id, chunk_index, content, metadata
                FROM chunks
                WHERE document_id = %s
                ORDER BY chunk_index
                """,
                (document_id,),
            )
            rows = cursor.fetchall()
        return [
            StoredChunk(
                id=row["id"],
                document_id=row["document_id"],
                chunk_index=row["chunk_index"],
                content=row["content"],
                metadata=dict(row["metadata"] or {}),
                embedding=None,
            )
            for row in rows
        ]

    def insert_document(
        self,
        document: SourceDocument,
        chunks: list[TextChunk],
        *,
        embeddings: list[list[float]] | None = None,
    ) -> StoredDocument:
        with self._connection.transaction():  # noqa: SIM117 - explicit transaction boundary
            with self._connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    INSERT INTO documents (
                        source, external_id, title, url, published_at,
                        content, checksum, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, source, external_id, title, url, published_at,
                              content, checksum, metadata
                    """,
                    (
                        document.source,
                        document.external_id,
                        document.title,
                        document.url,
                        document.published_at,
                        document.text,
                        document.checksum,
                        Jsonb(document.metadata),
                    ),
                )
                row = cursor.fetchone()
                assert row is not None
                stored = _document_from_row(row)
                _insert_chunks(cursor, stored.id, chunks, embeddings=embeddings)
        return stored

    def update_document(
        self,
        document_id: UUID,
        document: SourceDocument,
        chunks: list[TextChunk],
        *,
        embeddings: list[list[float]] | None = None,
    ) -> StoredDocument:
        with self._connection.transaction():  # noqa: SIM117 - explicit transaction boundary
            with self._connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    UPDATE documents
                    SET title = %s,
                        url = %s,
                        published_at = %s,
                        content = %s,
                        checksum = %s,
                        metadata = %s,
                        updated_at = now()
                    WHERE id = %s
                    RETURNING id, source, external_id, title, url, published_at,
                              content, checksum, metadata
                    """,
                    (
                        document.title,
                        document.url,
                        document.published_at,
                        document.text,
                        document.checksum,
                        Jsonb(document.metadata),
                        document_id,
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    msg = f"document {document_id} not found for update"
                    raise ValueError(msg)
                cursor.execute("DELETE FROM chunks WHERE document_id = %s", (document_id,))
                _insert_chunks(cursor, document_id, chunks, embeddings=embeddings)
                return _document_from_row(row)

    def start_ingestion_run(
        self,
        *,
        flow_name: str,
        source_scope: str,
        watermark_from: datetime | None = None,
        watermark_to: datetime | None = None,
        prefect_flow_run_id: UUID | None = None,
    ) -> IngestionRunRecord:
        with self._connection.transaction():  # noqa: SIM117 - explicit transaction boundary
            with self._connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    INSERT INTO ingestion_runs (
                        prefect_flow_run_id, flow_name, source_scope, status,
                        watermark_from, watermark_to
                    )
                    VALUES (%s, %s, %s, 'running', %s, %s)
                    RETURNING id, prefect_flow_run_id, flow_name, source_scope, status,
                              watermark_from, watermark_to, fetched_count, inserted_count,
                              updated_count, skipped_count, failed_count, error_summary,
                              started_at, finished_at
                    """,
                    (
                        prefect_flow_run_id,
                        flow_name,
                        source_scope,
                        watermark_from,
                        watermark_to,
                    ),
                )
                row = cursor.fetchone()
                assert row is not None
                return _run_from_row(row)

    def finish_ingestion_run(
        self,
        run_id: UUID,
        *,
        status: RunStatus,
        counters: IngestionCounters,
        error_summary: str | None = None,
        watermark_to: datetime | None = None,
    ) -> IngestionRunRecord:
        if status == "running":
            msg = "finish_ingestion_run requires completed or failed status"
            raise ValueError(msg)
        with self._connection.transaction():  # noqa: SIM117 - explicit transaction boundary
            with self._connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    UPDATE ingestion_runs
                    SET status = %s,
                        fetched_count = %s,
                        inserted_count = %s,
                        updated_count = %s,
                        skipped_count = %s,
                        failed_count = %s,
                        error_summary = %s,
                        watermark_to = COALESCE(%s, watermark_to),
                        finished_at = %s
                    WHERE id = %s
                    RETURNING id, prefect_flow_run_id, flow_name, source_scope, status,
                              watermark_from, watermark_to, fetched_count, inserted_count,
                              updated_count, skipped_count, failed_count, error_summary,
                              started_at, finished_at
                    """,
                    (
                        status,
                        counters.fetched_count,
                        counters.inserted_count,
                        counters.updated_count,
                        counters.skipped_count,
                        counters.failed_count,
                        error_summary,
                        watermark_to,
                        datetime.now(UTC),
                        run_id,
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    msg = f"ingestion run {run_id} not found"
                    raise ValueError(msg)
                return _run_from_row(row)

    def get_ingestion_run(self, run_id: UUID) -> IngestionRunRecord | None:
        with self._connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT id, prefect_flow_run_id, flow_name, source_scope, status,
                       watermark_from, watermark_to, fetched_count, inserted_count,
                       updated_count, skipped_count, failed_count, error_summary,
                       started_at, finished_at
                FROM ingestion_runs
                WHERE id = %s
                """,
                (run_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return _run_from_row(row)


def _insert_chunks(
    cursor: Any,
    document_id: UUID,
    chunks: list[TextChunk],
    *,
    embeddings: list[list[float]] | None = None,
) -> None:
    if embeddings is not None and len(embeddings) != len(chunks):
        msg = "embeddings length must match chunks length"
        raise ValueError(msg)
    for index, chunk in enumerate(chunks):
        metadata = dict(chunk.metadata)
        embedding = embeddings[index] if embeddings is not None else None
        if embedding is not None:
            metadata.setdefault("embedding_dimensions", len(embedding))
            cursor.execute(
                """
                INSERT INTO chunks (document_id, chunk_index, content, embedding, metadata)
                VALUES (%s, %s, %s, %s::vector, %s)
                """,
                (
                    document_id,
                    chunk.chunk_index,
                    chunk.content,
                    _vector_literal(embedding),
                    Jsonb(metadata),
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO chunks (document_id, chunk_index, content, metadata)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    document_id,
                    chunk.chunk_index,
                    chunk.content,
                    Jsonb(metadata),
                ),
            )


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def _document_from_row(row: dict[str, Any]) -> StoredDocument:
    return StoredDocument(
        id=row["id"],
        source=row["source"],
        external_id=row["external_id"],
        title=row["title"],
        url=row["url"],
        published_at=row["published_at"],
        content=row["content"],
        checksum=row["checksum"],
        metadata=dict(row["metadata"] or {}),
    )


def _run_from_row(row: dict[str, Any]) -> IngestionRunRecord:
    return IngestionRunRecord(
        id=row["id"],
        flow_name=row["flow_name"],
        source_scope=row["source_scope"],
        status=row["status"],
        watermark_from=row["watermark_from"],
        watermark_to=row["watermark_to"],
        counters=IngestionCounters(
            fetched_count=row["fetched_count"],
            inserted_count=row["inserted_count"],
            updated_count=row["updated_count"],
            skipped_count=row["skipped_count"],
            failed_count=row["failed_count"],
        ),
        error_summary=row["error_summary"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        prefect_flow_run_id=row["prefect_flow_run_id"],
    )
