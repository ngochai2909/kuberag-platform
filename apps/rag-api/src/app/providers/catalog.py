"""Document catalog for the Tin browse UI (metadata only).

Never selects or returns ``documents.content`` — browse cards open the
canonical source URL instead of re-hosting article bodies.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.core.telemetry import get_tracer


@dataclass(frozen=True, slots=True)
class CategoryRecord:
    category: str
    count: int


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    id: UUID
    title: str
    url: str
    source: str
    published_at: datetime | None
    category: str | None
    summary: str | None
    image_url: str | None


@dataclass(frozen=True, slots=True)
class DocumentPage:
    documents: tuple[DocumentRecord, ...]
    total: int
    limit: int
    offset: int


class DocumentCatalog(Protocol):
    """Synchronous catalog boundary that can be faked in unit tests."""

    def list_categories(self) -> Sequence[CategoryRecord]: ...

    def list_documents(
        self,
        *,
        category: str | None,
        limit: int,
        offset: int,
    ) -> DocumentPage: ...


class PostgresDocumentCatalog:
    """Read document metadata from PostgreSQL for the browse UI."""

    def __init__(self, *, database_url: str, connect_timeout_seconds: int = 5) -> None:
        if not database_url.strip():
            msg = "database_url must not be empty"
            raise ValueError(msg)
        if connect_timeout_seconds < 1:
            msg = "connect_timeout_seconds must be >= 1"
            raise ValueError(msg)
        self._database_url = database_url
        self._connect_timeout_seconds = connect_timeout_seconds

    def list_categories(self) -> list[CategoryRecord]:
        with (
            psycopg.connect(
                self._database_url,
                autocommit=True,
                connect_timeout=self._connect_timeout_seconds,
            ) as connection,
            connection.cursor(row_factory=dict_row) as cursor,
        ):
            cursor.execute(
                """
                SELECT
                    metadata->>'category' AS category,
                    COUNT(*)::int AS count
                FROM documents
                WHERE metadata ? 'category'
                  AND NULLIF(BTRIM(metadata->>'category'), '') IS NOT NULL
                GROUP BY metadata->>'category'
                ORDER BY
                  CASE metadata->>'category'
                    WHEN 'tin-moi-nhat' THEN 0
                    WHEN 'tin-noi-bat' THEN 1
                    WHEN 'thoi-su' THEN 2
                    WHEN 'the-gioi' THEN 3
                    WHEN 'kinh-doanh' THEN 4
                    WHEN 'bat-dong-san' THEN 5
                    WHEN 'khoa-hoc-cong-nghe' THEN 6
                    WHEN 'giai-tri' THEN 7
                    WHEN 'the-thao' THEN 8
                    WHEN 'phap-luat' THEN 9
                    WHEN 'giao-duc' THEN 10
                    WHEN 'suc-khoe' THEN 11
                    WHEN 'doi-song' THEN 12
                    WHEN 'du-lich' THEN 13
                    WHEN 'oto-xe-may' THEN 14
                    WHEN 'y-kien' THEN 15
                    WHEN 'tam-su' THEN 16
                    WHEN 'cuoi' THEN 17
                    WHEN 'tin-xem-nhieu' THEN 18
                    ELSE 100
                  END,
                  metadata->>'category' ASC
                """
            )
            rows = cursor.fetchall()
        return [
            CategoryRecord(category=str(row["category"]), count=int(row["count"])) for row in rows
        ]

    def list_documents(
        self,
        *,
        category: str | None,
        limit: int,
        offset: int,
    ) -> DocumentPage:
        if limit < 1 or limit > 50:
            msg = "limit must be between 1 and 50"
            raise ValueError(msg)
        if offset < 0:
            msg = "offset must be >= 0"
            raise ValueError(msg)

        filters = []
        params: list[Any] = []
        if category is not None:
            filters.append("metadata->>'category' = %s")
            params.append(category)
        where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

        with (
            psycopg.connect(
                self._database_url,
                autocommit=True,
                connect_timeout=self._connect_timeout_seconds,
            ) as connection,
            connection.cursor(row_factory=dict_row) as cursor,
        ):
            cursor.execute(
                f"SELECT COUNT(*)::int AS total FROM documents {where_sql}",
                params,
            )
            total_row = cursor.fetchone()
            if total_row is None:
                total = 0
            else:
                total = int(total_row["total"])

            cursor.execute(
                f"""
                SELECT
                    id,
                    title,
                    url,
                    source,
                    published_at,
                    metadata
                FROM documents
                {where_sql}
                ORDER BY published_at DESC NULLS LAST, updated_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                [*params, limit, offset],
            )
            rows = cursor.fetchall()

        documents = tuple(_row_to_document(row) for row in rows)
        return DocumentPage(documents=documents, total=total, limit=limit, offset=offset)


class CatalogService:
    """Async wrapper that keeps psycopg off FastAPI's event loop."""

    def __init__(self, catalog: DocumentCatalog) -> None:
        self._catalog = catalog

    async def list_categories(self) -> list[CategoryRecord]:
        with get_tracer(__name__).start_as_current_span("catalog.list_categories"):
            records = await asyncio.to_thread(self._catalog.list_categories)
        return list(records)

    async def list_documents(
        self,
        *,
        category: str | None,
        limit: int,
        offset: int,
    ) -> DocumentPage:
        with get_tracer(__name__).start_as_current_span("catalog.list_documents"):
            return await asyncio.to_thread(
                self._catalog.list_documents,
                category=category,
                limit=limit,
                offset=offset,
            )


def _row_to_document(row: dict[str, Any]) -> DocumentRecord:
    metadata = row.get("metadata")
    category = None
    summary = None
    image_url = None
    if isinstance(metadata, dict):
        raw_category = metadata.get("category")
        if isinstance(raw_category, str) and raw_category.strip():
            category = raw_category.strip()
        raw_summary = metadata.get("summary")
        if isinstance(raw_summary, str) and raw_summary.strip():
            summary = raw_summary.strip()
        raw_image = metadata.get("image_url")
        if isinstance(raw_image, str) and raw_image.strip():
            image_url = raw_image.strip()

    return DocumentRecord(
        id=row["id"] if isinstance(row["id"], UUID) else UUID(str(row["id"])),
        title=str(row["title"]),
        url=str(row["url"]),
        source=str(row["source"]),
        published_at=row["published_at"] if isinstance(row["published_at"], datetime) else None,
        category=category,
        summary=summary,
        image_url=image_url,
    )
