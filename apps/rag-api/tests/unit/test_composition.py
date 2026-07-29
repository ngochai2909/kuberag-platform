from __future__ import annotations

from app.core.config import Settings
from app.services.composition import build_rag_service
from app.services.rag import RagPipelineService


def test_disabled_runtime_does_not_bind_providers() -> None:
    service = build_rag_service(Settings(_env_file=None))

    assert service is None


def test_enabled_runtime_binds_the_self_hosted_provider_chain() -> None:
    settings = Settings(
        _env_file=None,
        rag_runtime_enabled=True,
        database_url="postgresql://kuberag:placeholder@kuberag-pg-rw.data.svc:5432/kuberag",
        rag_embedding_cache="/models",
        llama_cpp_base_url="http://kuberag-llm.rag.svc.cluster.local:8080",
    )

    service = build_rag_service(settings)

    assert isinstance(service, RagPipelineService)
