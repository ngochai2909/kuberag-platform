from __future__ import annotations

from collections.abc import Sequence

import pytest

from app.providers.retrieval import PostgresRetriever, VectorSearchResult, VectorSearchStore
from app.services.rag import Retriever
from ingestion.embedding import EMBEDDING_DIMENSIONS, EmbeddingProvider


class StaticEmbeddingProvider:
    dimensions = EMBEDDING_DIMENSIONS
    model_id = "fixture/static-e5"

    def __init__(self, vector: list[float] | None = None) -> None:
        self.vector = vector or [1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 1)
        self.queries: list[str] = []

    def embed_documents(self, texts: Sequence[str], *, batch_size: int = 32) -> list[list[float]]:
        del batch_size
        return [self.vector for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return self.vector


class FakeVectorStore:
    def __init__(self, results: list[VectorSearchResult]) -> None:
        self.results = results
        self.calls: list[tuple[list[float], int]] = []

    def search(self, *, embedding: Sequence[float], top_k: int) -> list[VectorSearchResult]:
        self.calls.append((list(embedding), top_k))
        return self.results[:top_k]


@pytest.mark.asyncio
async def test_postgres_retriever_embeds_question_and_maps_vector_results() -> None:
    embedder = StaticEmbeddingProvider()
    store = FakeVectorStore(
        [
            VectorSearchResult(
                title="VnExpress technology",
                url="https://vnexpress.net/technology.html",
                source="vnexpress",
                content="A retrieved source chunk.",
                score=0.91,
                metadata={"chunk_index": 0},
                thumbnail_url="https://example.com/vnexpress-thumbnail.jpg",
            )
        ]
    )
    retriever = PostgresRetriever(embedder=embedder, store=store)

    chunks = await retriever.retrieve(
        question="AI co tac dong gi?",
        top_k=1,
        request_id="request-1",
    )

    assert embedder.queries == ["AI co tac dong gi?"]
    assert store.calls == [(embedder.vector, 1)]
    assert chunks[0].title == "VnExpress technology"
    assert chunks[0].url == "https://vnexpress.net/technology.html"
    assert chunks[0].metadata == {"chunk_index": 0}
    assert chunks[0].thumbnail_url == "https://example.com/vnexpress-thumbnail.jpg"


@pytest.mark.asyncio
async def test_postgres_retriever_rejects_an_invalid_embedding_width() -> None:
    embedder = StaticEmbeddingProvider(vector=[1.0, 0.0])
    store = FakeVectorStore([])
    retriever = PostgresRetriever(embedder=embedder, store=store)

    with pytest.raises(ValueError, match="embedding width"):
        await retriever.retrieve(question="q", top_k=1, request_id="request-1")

    assert store.calls == []


def test_fakes_and_retriever_satisfy_provider_interfaces() -> None:
    embedder: EmbeddingProvider = StaticEmbeddingProvider()
    store: VectorSearchStore = FakeVectorStore([])
    retriever: Retriever = PostgresRetriever(embedder=embedder, store=store)

    assert retriever is not None
