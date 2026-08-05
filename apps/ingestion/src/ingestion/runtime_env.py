"""Build :class:`IngestionRuntime` from environment variables for cluster workers.

Laptop unit tests keep using explicit :func:`ingestion_runtime` injection.
Cluster workers bind HTTP, PostgreSQL, and embedder collaborators from env so
Prefect process runs can execute without a shell entrypoint script.
"""

from __future__ import annotations

import os
from typing import Literal

import psycopg

from ingestion.chunking import ChunkingConfig
from ingestion.embedding import EmbeddingProvider, FakeEmbeddingProvider
from ingestion.flows.ingest import IngestionRuntime
from ingestion.http import HttpxHttpClient, RetryingHttpClient
from ingestion.postgres_store import PostgresDocumentStore

EmbeddingMode = Literal["fake", "e5"]


def embedding_mode_from_env() -> EmbeddingMode:
    raw = os.environ.get("KUBERAG_EMBEDDING_MODE", "fake").strip().lower()
    if raw in {"fake", "e5"}:
        return raw  # type: ignore[return-value]
    msg = f"KUBERAG_EMBEDDING_MODE must be 'fake' or 'e5', got {raw!r}"
    raise ValueError(msg)


def build_embedder(mode: EmbeddingMode | None = None) -> EmbeddingProvider:
    selected = mode or embedding_mode_from_env()
    if selected == "fake":
        return FakeEmbeddingProvider()
    if selected == "e5":
        from ingestion.e5 import E5EmbeddingProvider

        cache = os.environ.get("KUBERAG_EMBEDDING_CACHE") or None
        local_only = os.environ.get("KUBERAG_EMBEDDING_LOCAL_ONLY", "").lower() in {
            "1",
            "true",
            "yes",
        }
        return E5EmbeddingProvider(cache_folder=cache, local_files_only=local_only)
    msg = f"unsupported embedding mode: {selected!r}"
    raise ValueError(msg)


def build_runtime_from_env() -> IngestionRuntime:
    """Construct runtime collaborators for in-cluster Prefect flow runs."""

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        msg = "DATABASE_URL is required to bind PostgresDocumentStore"
        raise RuntimeError(msg)

    timeout_seconds = float(os.environ.get("KUBERAG_HTTP_TIMEOUT_SECONDS", "30"))
    max_attempts = int(os.environ.get("KUBERAG_HTTP_MAX_ATTEMPTS", "3"))
    batch_size = int(os.environ.get("KUBERAG_EMBEDDING_BATCH_SIZE", "32"))
    max_chars = int(os.environ.get("KUBERAG_CHUNK_MAX_CHARS", "800"))
    overlap_chars = int(os.environ.get("KUBERAG_CHUNK_OVERLAP_CHARS", "150"))
    feed_urls = _vnexpress_feed_urls_from_env()

    http = RetryingHttpClient(
        HttpxHttpClient(timeout_seconds=timeout_seconds),
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
    )
    # Autocommit keeps reads from opening a long-lived implicit transaction.
    # PostgresDocumentStore wraps each mutation in an explicit transaction.
    connection = psycopg.connect(database_url, autocommit=True)
    store = PostgresDocumentStore(connection)
    return IngestionRuntime(
        http=http,
        store=store,
        embedder=build_embedder(),
        chunking=ChunkingConfig(max_chars=max_chars, overlap_chars=overlap_chars),
        vnexpress_feed_urls=feed_urls,
        embedding_batch_size=batch_size,
    )


def _vnexpress_feed_urls_from_env() -> list[str]:
    from ingestion.adapters.vnexpress import DEFAULT_FEED_URLS

    raw = os.environ.get("KUBERAG_VNEXPRESS_FEED_URLS", "").strip()
    if not raw:
        return list(DEFAULT_FEED_URLS)
    urls = [part.strip() for part in raw.split(",") if part.strip()]
    if not urls:
        msg = "KUBERAG_VNEXPRESS_FEED_URLS is set but empty after parsing"
        raise ValueError(msg)
    return urls
