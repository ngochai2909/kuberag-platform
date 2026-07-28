"""Real multilingual-e5-small embedding provider for cluster/VM workloads.

Laptop unit tests must not import :mod:`sentence_transformers` or download
weights. This module lazy-imports the heavy stack only when an instance embeds.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from ingestion.embedding import EMBEDDING_DIMENSIONS, PLANNED_EMBEDDING_MODEL_ID

_PASSAGE_PREFIX = "passage: "
_QUERY_PREFIX = "query: "


@dataclass(slots=True)
class E5EmbeddingProvider:
    """CPU SentenceTransformer wrapper for ``intfloat/multilingual-e5-small``.

    E5 requires explicit ``query:`` / ``passage:`` prefixes. Vectors are
    L2-normalized to match typical pgvector cosine / inner-product retrieval.
    """

    model_id: str = PLANNED_EMBEDDING_MODEL_ID
    dimensions: int = EMBEDDING_DIMENSIONS
    cache_folder: str | None = None
    local_files_only: bool = False
    _model: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.dimensions != EMBEDDING_DIMENSIONS:
            msg = (
                f"multilingual-e5-small produces {EMBEDDING_DIMENSIONS}-dim "
                f"vectors; got dimensions={self.dimensions}"
            )
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
        prefixed = [f"{_PASSAGE_PREFIX}{text}" for text in texts]
        return self._encode(prefixed, batch_size=batch_size)

    def embed_query(self, text: str) -> list[float]:
        vectors = self._encode([f"{_QUERY_PREFIX}{text}"], batch_size=1)
        return vectors[0]

    def _encode(self, texts: list[str], *, batch_size: int) -> list[list[float]]:
        model = self._ensure_model()
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        if hasattr(vectors, "tolist"):
            raw_vectors = vectors.tolist()
        else:
            raw_vectors = [list(vector) for vector in vectors]
        result = [list(vector) for vector in raw_vectors]
        for vector in result:
            if len(vector) != self.dimensions:
                msg = (
                    f"embedding width {len(vector)} does not match "
                    f"expected {self.dimensions}"
                )
                raise ValueError(msg)
        return result

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            msg = (
                "sentence-transformers is required for KUBERAG_EMBEDDING_MODE=e5. "
                "Install the optional extra: uv sync --extra embedding"
            )
            raise RuntimeError(msg) from exc

        cache_folder = self.cache_folder or os.environ.get("KUBERAG_EMBEDDING_CACHE")
        kwargs: dict[str, Any] = {
            "local_files_only": self.local_files_only
            or os.environ.get("KUBERAG_EMBEDDING_LOCAL_ONLY", "").lower()
            in {"1", "true", "yes"},
        }
        if cache_folder:
            kwargs["cache_folder"] = cache_folder

        # Prefer an explicit local snapshot path when provided.
        model_path = os.environ.get("KUBERAG_EMBEDDING_MODEL_PATH", "").strip()
        model_name = model_path or self.model_id
        self._model = SentenceTransformer(model_name, **kwargs)
        return self._model
