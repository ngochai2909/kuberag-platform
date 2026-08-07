from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Validated application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "KubeRAG Platform"
    app_version: str = "0.1.0"
    app_env: Environment = Environment.DEVELOPMENT
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    docs_enabled: bool = True

    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    cors_allow_credentials: bool = False

    api_auth_enabled: bool = False
    app_api_key: SecretStr | None = None
    public_demo_mode: bool = False

    otel_enabled: bool = False
    otel_service_name: str = "kuberag-rag-api"
    otel_exporter_otlp_endpoint: str = "kuberag-otel-collector.observability.svc.cluster.local:4317"
    otel_export_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    pyroscope_enabled: bool = False
    pyroscope_server_address: str = "http://kuberag-pyroscope.observability.svc.cluster.local:4040"

    rag_timeout_seconds: float = Field(default=90.0, gt=0, le=600)
    rag_max_context_chars: int = Field(default=12000, ge=1000, le=100000)
    rag_runtime_enabled: bool = False
    database_url: SecretStr | None = None
    rag_embedding_cache: str = "/models"
    rag_embedding_local_only: bool = True
    rag_database_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)
    llama_cpp_base_url: str = "http://kuberag-llm.rag.svc.cluster.local:8080"
    llama_cpp_model: str = "kuberag-qwen2.5-1.5b"
    llama_cpp_max_tokens: int = Field(default=256, ge=1, le=1024)
    llama_cpp_temperature: float = Field(default=0.2, ge=0, le=2)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_security_settings(self) -> Self:
        if self.cors_allow_credentials and "*" in self.cors_origin_list:
            raise ValueError("CORS wildcard origins cannot be used with credentials")

        if self.api_auth_enabled:
            if self.app_api_key is None:
                raise ValueError("APP_API_KEY is required when API authentication is enabled")
            if len(self.app_api_key.get_secret_value()) < 32:
                raise ValueError("APP_API_KEY must contain at least 32 characters")

        if (
            self.app_env is Environment.PRODUCTION
            and not self.api_auth_enabled
            and not self.public_demo_mode
        ):
            raise ValueError(
                "API authentication must be enabled in production unless "
                "PUBLIC_DEMO_MODE is enabled"
            )

        if self.rag_runtime_enabled and self.database_url is None:
            raise ValueError("DATABASE_URL is required when RAG_RUNTIME_ENABLED is true")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
