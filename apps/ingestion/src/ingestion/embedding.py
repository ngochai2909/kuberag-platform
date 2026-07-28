"""Embedding provider interface and offline fake.

The planned production model is ``intfloat/multilingual-e5-small`` (384-dim).
Unit tests and local ``make check`` use :class:`FakeEmbeddingProvider` only.
The real model is downloaded later inside the cluster ingestion workload, not
during laptop pytest runs.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from ingestion.chunking import TextChunk

# Planned production embedding size for multilingual-e5-small.
EMBEDDING_DIMENSIONS = 384
PLANNED_EMBEDDING_MODEL_ID = "intfloat/multilingual-e5-small"
FAKE_EMBEDDING_MODEL_ID = "fake/hashing-e5-dim384"

_WHITESPACE_RE = re.compile(r"\s+")


class EmbeddingProvider(Protocol):
    """Provider-independent embedding API used by ingestion and later RAG."""

    @property
    def dimensions(self) -> int:
        """Vector width written to ``chunks.embedding``."""

    @property
    def model_id(self) -> str:
        """Stable model identifier recorded in chunk metadata."""

    def embed_documents(
        self,
        texts: Sequence[str],
        *,
        batch_size: int = 32,
    ) -> list[list[float]]:
        """Embed passage/document texts (E5 ``passage:`` semantics when real)."""

    def embed_query(self, text: str) -> list[float]:
        """Embed one retrieval query (E5 ``query:`` semantics when real)."""


@dataclass(frozen=True, slots=True)
class FakeEmbeddingProvider:
    """Deterministic offline embedder for unit tests and CI.

    Vectors are derived from SHA-256 digests and L2-normalized. They are not
    semantically meaningful; they only prove batching, dimension, and upsert
    wiring without downloading a model.
    """

    dimensions: int = EMBEDDING_DIMENSIONS
    model_id: str = FAKE_EMBEDDING_MODEL_ID

    def __post_init__(self) -> None:
        if self.dimensions < 8:
            msg = "dimensions must be >= 8"
            raise ValueError(msg)

    def embed_documents(
        self,
        texts: Sequence[str],
        *,
        batch_size: int = 32,
    ) -> list[list[float]]:
        if batch_size < 1:
            msg = "batch_size must be >= 1"
            raise ValueError(msg)
        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            vectors.extend(self._embed_one(text, prefix="passage") for text in batch)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text, prefix="query")

    def _embed_one(self, text: str, *, prefix: str) -> list[float]:
        normalized = _WHITESPACE_RE.sub(" ", text).strip().lower()
        seed = f"{prefix}:{normalized}".encode()
        values: list[float] = []
        counter = 0
        while len(values) < self.dimensions:
            digest = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            for index in range(0, len(digest), 4):
                if len(values) >= self.dimensions:
                    break
                raw = int.from_bytes(digest[index : index + 4], "big")
                # Map to (-1, 1) for a dense-looking unit vector.
                values.append((raw / 0xFFFFFFFF) * 2.0 - 1.0)
            counter += 1
        return _l2_normalize(values)


def embed_chunks(
    chunks: Sequence[TextChunk],
    provider: EmbeddingProvider,
    *,
    batch_size: int = 32,
) -> list[list[float]]:
    """Embed chunk contents in batches and return aligned vectors."""

    texts = [chunk.content for chunk in chunks]
    vectors = provider.embed_documents(texts, batch_size=batch_size)
    if len(vectors) != len(chunks):
        msg = "embedding provider returned a mismatched vector count"
        raise ValueError(msg)
    for vector in vectors:
        if len(vector) != provider.dimensions:
            msg = (
                f"embedding width {len(vector)} does not match "
                f"provider dimensions {provider.dimensions}"
            )
            raise ValueError(msg)
    return vectors


def _l2_normalize(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0.0:
        return values
    return [value / norm for value in values]
