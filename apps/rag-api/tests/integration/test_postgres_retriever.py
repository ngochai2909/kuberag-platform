from __future__ import annotations

import os
from collections.abc import Sequence
from uuid import uuid4

import psycopg
import pytest

from app.providers.retrieval import PostgresRetriever, PostgresVectorStore
from ingestion.embedding import EMBEDDING_DIMENSIONS

pytestmark = pytest.mark.db_integration


class StaticEmbeddingProvider:
    dimensions = EMBEDDING_DIMENSIONS
    model_id = "fixture/static-e5"

    def __init__(self, vector: list[float]) -> None:
        self._vector = vector

    def embed_documents(self, texts: Sequence[str], *, batch_size: int = 32) -> list[list[float]]:
        del batch_size
        return [self._vector for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        del text
        return self._vector


@pytest.mark.asyncio
async def test_postgres_retriever_returns_nearest_chunk_and_document_source() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for the database integration test")

    query_vector = [1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 1)
    far_vector = [0.0, 1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 2)
    external_id = f"rag-002-{uuid4()}"
    document_id = None

    try:
        with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO documents (source, external_id, title, url, content, checksum, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING id
                """,
                (
                    "fixture",
                    external_id,
                    "RAG-002 retrieval fixture",
                    "https://example.invalid/rag-002",
                    "Synthetic document used only by the PostgreSQL retrieval test.",
                    "b" * 64,
                    '{"image_url": "https://example.invalid/rag-002.jpg"}',
                ),
            )
            document_row = cursor.fetchone()
            assert document_row is not None
            document_id = document_row[0]
            cursor.executemany(
                """
                INSERT INTO chunks (document_id, chunk_index, content, embedding, metadata)
                VALUES (%s, %s, %s, %s::vector, %s::jsonb)
                """,
                [
                    (document_id, 0, "nearest chunk", _vector(query_vector), '{"fixture": true}'),
                    (document_id, 1, "farther chunk", _vector(far_vector), "{}"),
                ],
            )

        retriever = PostgresRetriever(
            embedder=StaticEmbeddingProvider(query_vector),
            store=PostgresVectorStore(database_url=database_url),
        )
        chunks = await retriever.retrieve(question="fixture question", top_k=1, request_id="test")

        assert [chunk.content for chunk in chunks] == ["nearest chunk"]
        assert chunks[0].title == "RAG-002 retrieval fixture"
        assert chunks[0].url == "https://example.invalid/rag-002"
        assert chunks[0].source == "fixture"
        assert chunks[0].score == pytest.approx(1.0)
        assert chunks[0].metadata == {"fixture": True}
        assert chunks[0].thumbnail_url == "https://example.invalid/rag-002.jpg"
    finally:
        if document_id is not None:
            with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
                cursor.execute("DELETE FROM documents WHERE id = %s", (document_id,))


def _vector(values: list[float]) -> str:
    return "[" + ",".join(str(value) for value in values) + "]"
