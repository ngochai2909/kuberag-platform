from __future__ import annotations

import math

import pytest

from ingestion.chunking import ChunkingConfig, TextChunk, chunk_document
from ingestion.embedding import (
    EMBEDDING_DIMENSIONS,
    FAKE_EMBEDDING_MODEL_ID,
    FakeEmbeddingProvider,
    embed_chunks,
)
from ingestion.models import SourceDocument, document_checksum
from ingestion.store import InMemoryDocumentStore
from ingestion.upsert import DocumentUpserter


def test_fake_embed_documents_is_batched_and_normalized() -> None:
    provider = FakeEmbeddingProvider()
    texts = [f"passage number {index}" for index in range(5)]
    vectors = provider.embed_documents(texts, batch_size=2)
    assert len(vectors) == 5
    assert provider.dimensions == EMBEDDING_DIMENSIONS
    assert provider.model_id == FAKE_EMBEDDING_MODEL_ID
    for vector in vectors:
        assert len(vector) == EMBEDDING_DIMENSIONS
        norm = math.sqrt(sum(value * value for value in vector))
        assert norm == pytest.approx(1.0, rel=1e-5)


def test_fake_query_and_passage_prefixes_differ() -> None:
    provider = FakeEmbeddingProvider()
    text = "robot kho tự hành"
    query = provider.embed_query(text)
    passage = provider.embed_documents([text])[0]
    assert query != passage


def test_fake_embeddings_are_deterministic() -> None:
    provider = FakeEmbeddingProvider()
    first = provider.embed_documents(["same text"])[0]
    second = provider.embed_documents(["same text"])[0]
    assert first == second


def test_embed_chunks_aligns_with_chunk_order() -> None:
    chunks = [
        TextChunk(chunk_index=0, content="first chunk", metadata={"max_chars": 100}),
        TextChunk(chunk_index=1, content="second chunk", metadata={"max_chars": 100}),
    ]
    vectors = embed_chunks(chunks, FakeEmbeddingProvider(), batch_size=1)
    assert len(vectors) == 2
    assert vectors[0] != vectors[1]


def test_upsert_with_fake_embedder_stores_vectors() -> None:
    store = InMemoryDocumentStore()
    provider = FakeEmbeddingProvider()
    upserter = DocumentUpserter(
        store,
        chunking=ChunkingConfig(max_chars=200, overlap_chars=40),
        embedder=provider,
        embedding_batch_size=2,
    )
    title = "Demo embed"
    text = "Câu một về embedding. Câu hai về pgvector và retrieval."
    document = SourceDocument(
        source="vnexpress",
        external_id="https://vnexpress.net/embed-demo.html",
        title=title,
        url="https://vnexpress.net/embed-demo.html",
        text=text,
        checksum=document_checksum(title=title, text=text),
        metadata={},
    )
    result = upserter.upsert(document)
    assert result.action == "inserted"
    stored_chunks = store.list_chunks(result.document_id)
    assert stored_chunks
    for chunk in stored_chunks:
        assert chunk.embedding is not None
        assert len(chunk.embedding) == EMBEDDING_DIMENSIONS
        assert chunk.metadata["embedding_model"] == FAKE_EMBEDDING_MODEL_ID
        assert chunk.metadata["embedding_dimensions"] == EMBEDDING_DIMENSIONS


def test_skip_does_not_reembed() -> None:
    store = InMemoryDocumentStore()
    provider = FakeEmbeddingProvider()
    upserter = DocumentUpserter(
        store,
        chunking=ChunkingConfig(max_chars=200, overlap_chars=40),
        embedder=provider,
    )
    title = "Skip embed"
    text = "Nội dung không đổi giữa hai lần upsert."
    document = SourceDocument(
        source="vnexpress",
        external_id="https://vnexpress.net/skip-embed.html",
        title=title,
        url="https://vnexpress.net/skip-embed.html",
        text=text,
        checksum=document_checksum(title=title, text=text),
        metadata={},
    )
    first = upserter.upsert(document)
    before = store.list_chunks(first.document_id)[0].embedding
    second = upserter.upsert(document)
    assert second.action == "skipped"
    after = store.list_chunks(first.document_id)[0].embedding
    assert before == after


def test_invalid_batch_size_rejected() -> None:
    with pytest.raises(ValueError, match="batch_size"):
        FakeEmbeddingProvider().embed_documents(["x"], batch_size=0)


def test_chunk_document_plus_fake_batch_smoke() -> None:
    # Offline stand-in for ING-010 batch wiring (no model download).
    text = " ".join(f"Mệnh đề kỹ thuật số {index}." for index in range(12))
    chunks = chunk_document(
        SourceDocument(
            source="fixture",
            external_id="batch-smoke",
            title="Batch",
            url="https://example.invalid/batch",
            text=text,
            checksum=document_checksum(title="Batch", text=text),
            metadata={},
        ),
        config=ChunkingConfig(max_chars=120, overlap_chars=20),
    )
    vectors = embed_chunks(chunks, FakeEmbeddingProvider(), batch_size=3)
    assert len(chunks) >= 2
    assert len(vectors) == len(chunks)
