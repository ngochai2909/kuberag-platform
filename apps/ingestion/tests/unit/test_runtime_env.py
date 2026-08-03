"""Unit tests for cluster runtime env helpers (offline, no database)."""

from __future__ import annotations

import pytest

from ingestion.embedding import FAKE_EMBEDDING_MODEL_ID
from ingestion.runtime_env import build_embedder, embedding_mode_from_env


def test_embedding_mode_defaults_to_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KUBERAG_EMBEDDING_MODE", raising=False)
    assert embedding_mode_from_env() == "fake"


def test_embedding_mode_rejects_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KUBERAG_EMBEDDING_MODE", "openai")
    with pytest.raises(ValueError, match="KUBERAG_EMBEDDING_MODE"):
        embedding_mode_from_env()


def test_build_embedder_fake() -> None:
    embedder = build_embedder("fake")
    assert embedder.model_id == FAKE_EMBEDDING_MODEL_ID
    assert len(embedder.embed_query("xin chao")) == 384


def test_build_embedder_e5_lazy(monkeypatch: pytest.MonkeyPatch) -> None:
    from ingestion.e5 import E5EmbeddingProvider

    embedder = build_embedder("e5")
    assert isinstance(embedder, E5EmbeddingProvider)
    assert embedder.model_id == "intfloat/multilingual-e5-small"
