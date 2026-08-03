"""Offline unit tests for E5EmbeddingProvider (mocked SentenceTransformer)."""

from __future__ import annotations

from typing import Any

import pytest

from ingestion.e5 import E5EmbeddingProvider
from ingestion.embedding import EMBEDDING_DIMENSIONS, PLANNED_EMBEDDING_MODEL_ID


class _FakeSentenceTransformer:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def encode(
        self,
        texts: list[str],
        *,
        batch_size: int,
        normalize_embeddings: bool,
        show_progress_bar: bool,
        convert_to_numpy: bool,
    ) -> list[list[float]]:
        self.calls.append(
            {
                "texts": list(texts),
                "batch_size": batch_size,
                "normalize_embeddings": normalize_embeddings,
                "show_progress_bar": show_progress_bar,
                "convert_to_numpy": convert_to_numpy,
            }
        )
        vectors: list[list[float]] = []
        for index, _text in enumerate(texts):
            values = [0.0] * EMBEDDING_DIMENSIONS
            values[index % EMBEDDING_DIMENSIONS] = 1.0
            vectors.append(values)
        return vectors


def test_e5_prefixes_and_dimensions() -> None:
    fake_model = _FakeSentenceTransformer()
    provider = E5EmbeddingProvider()
    provider._model = fake_model

    docs = provider.embed_documents(["a", "b"], batch_size=2)
    query = provider.embed_query("q")

    assert provider.model_id == PLANNED_EMBEDDING_MODEL_ID
    assert len(docs) == 2
    assert len(docs[0]) == EMBEDDING_DIMENSIONS
    assert len(query) == EMBEDDING_DIMENSIONS
    assert fake_model.calls[0]["texts"] == ["passage: a", "passage: b"]
    assert fake_model.calls[1]["texts"] == ["query: q"]


def test_e5_missing_sentence_transformers(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    orig_import = builtins.__import__

    def _fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "sentence_transformers":
            raise ImportError("missing")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    provider = E5EmbeddingProvider()
    with pytest.raises(RuntimeError, match="sentence-transformers"):
        provider.embed_query("hello")
