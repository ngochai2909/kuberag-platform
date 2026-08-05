"""Production composition root for the deterministic RAG request path."""

from __future__ import annotations

from app.core.config import Settings
from app.providers.catalog import CatalogService, PostgresDocumentCatalog
from app.providers.llama_cpp import LlamaCppGenerator
from app.providers.retrieval import PostgresRetriever, PostgresVectorStore
from app.services.rag import RagPipelineService, RagService
from ingestion.e5 import E5EmbeddingProvider


def build_rag_service(settings: Settings) -> RagService | None:
    """Bind infrastructure adapters only when the real RAG runtime is enabled.

    Unit tests and the skeleton API stay offline by leaving
    ``RAG_RUNTIME_ENABLED`` disabled. The deployed API creates its E5 provider
    lazily; model weights load only on the first query from the read-only PVC.
    """

    if not settings.rag_runtime_enabled:
        return None
    if settings.database_url is None:
        msg = "DATABASE_URL is required when the RAG runtime is enabled"
        raise RuntimeError(msg)

    embedder = E5EmbeddingProvider(
        cache_folder=settings.rag_embedding_cache,
        local_files_only=settings.rag_embedding_local_only,
    )
    store = PostgresVectorStore(
        database_url=settings.database_url.get_secret_value(),
        connect_timeout_seconds=settings.rag_database_connect_timeout_seconds,
    )
    retriever = PostgresRetriever(embedder=embedder, store=store)
    generator = LlamaCppGenerator(
        base_url=settings.llama_cpp_base_url,
        model=settings.llama_cpp_model,
        timeout_seconds=settings.rag_timeout_seconds,
        max_tokens=settings.llama_cpp_max_tokens,
        temperature=settings.llama_cpp_temperature,
    )
    return RagPipelineService(retriever=retriever, generator=generator, settings=settings)


def build_catalog_service(settings: Settings) -> CatalogService | None:
    """Bind the browse catalog when the RAG runtime (and database) are enabled."""

    if not settings.rag_runtime_enabled:
        return None
    if settings.database_url is None:
        msg = "DATABASE_URL is required when the RAG runtime is enabled"
        raise RuntimeError(msg)

    catalog = PostgresDocumentCatalog(
        database_url=settings.database_url.get_secret_value(),
        connect_timeout_seconds=settings.rag_database_connect_timeout_seconds,
    )
    return CatalogService(catalog)
