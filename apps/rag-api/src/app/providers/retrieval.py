"""pgvector retrieval adapter for the deterministic RAG request path.

The API service depends on ``Retriever`` only. This module contains the
database-specific implementation and keeps its synchronous psycopg calls off
FastAPI's event loop.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import psycopg
from psycopg.rows import dict_row

from app.services.rag import RetrievedChunk
from ingestion.embedding import EmbeddingProvider


@dataclass(frozen=True, slots=True)
class VectorSearchResult:
    """One chunk returned by a vector store before RAG mapping."""

    title: str
    url: str
    source: str
    content: str
    score: float
    metadata: dict[str, object] = field(default_factory=dict)
    thumbnail_url: str | None = None


class VectorSearchStore(Protocol):
    """Synchronous vector-search boundary that can be faked in unit tests."""

    def search(
        self,
        *,
        embedding: Sequence[float],
        top_k: int,
    ) -> Sequence[VectorSearchResult]: ...


class PostgresVectorStore:
    """Search ``documents`` and ``chunks`` through PostgreSQL/pgvector."""

    def __init__(self, *, database_url: str, connect_timeout_seconds: int = 5) -> None:
        if not database_url.strip():
            msg = "database_url must not be empty"
            raise ValueError(msg)
        if connect_timeout_seconds < 1:
            msg = "connect_timeout_seconds must be >= 1"
            raise ValueError(msg)
        self._database_url = database_url
        self._connect_timeout_seconds = connect_timeout_seconds

    def search(
        self,
        *,
        embedding: Sequence[float],
        top_k: int,
    ) -> list[VectorSearchResult]:
        if top_k < 1:
            msg = "top_k must be >= 1"
            raise ValueError(msg)
        vector = _vector_literal(embedding)
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
                    documents.title,
                    documents.url,
                    documents.source,
                    documents.metadata AS document_metadata,
                    chunks.content,
                    chunks.metadata,
                    chunks.embedding <=> %s::vector AS cosine_distance
                FROM chunks
                INNER JOIN documents ON documents.id = chunks.document_id
                WHERE chunks.embedding IS NOT NULL
                ORDER BY chunks.embedding <=> %s::vector, chunks.id
                LIMIT %s
                """,
                (vector, vector, top_k),
            )
            rows = cursor.fetchall()

        return [_row_to_search_result(row) for row in rows]


class PostgresRetriever:
    """Embed a question and retrieve its nearest chunks from pgvector."""

    def __init__(
        self,
        *,
        embedder: EmbeddingProvider,
        store: VectorSearchStore,
    ) -> None:
        self._embedder = embedder
        self._store = store

    async def retrieve(
        self,
        *,
        question: str,
        top_k: int,
        request_id: str,
    ) -> list[RetrievedChunk]:
        del request_id
        if top_k < 1:
            msg = "top_k must be >= 1"
            raise ValueError(msg)

        embedding = await asyncio.to_thread(self._embedder.embed_query, question)
        if len(embedding) != self._embedder.dimensions:
            msg = (
                f"embedding width {len(embedding)} does not match "
                f"provider dimensions {self._embedder.dimensions}"
            )
            raise ValueError(msg)

        matches = await asyncio.to_thread(
            self._store.search,
            embedding=embedding,
            top_k=top_k,
        )
        return [
            RetrievedChunk(
                title=match.title,
                url=match.url,
                source=match.source,
                content=match.content,
                score=match.score,
                metadata=match.metadata,
                thumbnail_url=match.thumbnail_url,
            )
            for match in matches
        ]


def _row_to_search_result(row: dict[str, Any]) -> VectorSearchResult:
    metadata = row["metadata"]
    document_metadata = row["document_metadata"]
    image_url = document_metadata.get("image_url") if isinstance(document_metadata, dict) else None
    return VectorSearchResult(
        title=str(row["title"]),
        url=str(row["url"]),
        source=str(row["source"]),
        content=str(row["content"]),
        score=_score_from_cosine_distance(float(row["cosine_distance"])),
        metadata=dict(metadata) if isinstance(metadata, dict) else {},
        thumbnail_url=image_url if isinstance(image_url, str) and image_url else None,
    )


def _score_from_cosine_distance(distance: float) -> float:
    """Map pgvector cosine distance into the API's bounded similarity score."""

    return max(0.0, min(1.0, 1.0 - distance))


def _vector_literal(embedding: Sequence[float]) -> str:
    if not embedding:
        msg = "embedding must not be empty"
        raise ValueError(msg)
    values = [float(value) for value in embedding]
    if not all(math.isfinite(value) for value in values):
        msg = "embedding values must be finite"
        raise ValueError(msg)
    return "[" + ",".join(str(value) for value in values) + "]"
