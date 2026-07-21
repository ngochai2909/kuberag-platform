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

    rag_timeout_seconds: float = Field(default=45.0, gt=0, le=600)
    rag_max_context_chars: int = Field(default=12000, ge=1000, le=100000)

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

        if self.app_env is Environment.PRODUCTION and not self.api_auth_enabled:
            raise ValueError("API authentication must be enabled in production")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
