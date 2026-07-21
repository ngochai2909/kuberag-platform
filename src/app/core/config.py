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


ReasoningEffort = Literal["none", "low", "medium", "high", "xhigh", "max"]


class Settings(BaseSettings):
    """Validated application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Agent Source Base"
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

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5.6-luna"
    openai_use_responses_api: bool = True
    openai_reasoning_effort: ReasoningEffort | None = "low"
    openai_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    openai_max_retries: int = Field(default=2, ge=0, le=10)

    agent_timeout_seconds: float = Field(default=45.0, gt=0, le=600)
    agent_model_call_limit: int = Field(default=8, ge=1, le=50)
    agent_tool_call_limit: int = Field(default=6, ge=1, le=50)
    agent_recursion_limit: int = Field(default=24, ge=4, le=200)
    agent_memory_enabled: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def agent_configured(self) -> bool:
        return self.openai_api_key is not None

    @model_validator(mode="after")
    def validate_security_settings(self) -> Self:
        if self.cors_allow_credentials and "*" in self.cors_origin_list:
            raise ValueError("CORS wildcard origins cannot be used with credentials")

        if self.api_auth_enabled:
            if self.app_api_key is None:
                raise ValueError("APP_API_KEY is required when API authentication is enabled")
            if len(self.app_api_key.get_secret_value()) < 32:
                raise ValueError("APP_API_KEY must contain at least 32 characters")

        if self.app_env is Environment.PRODUCTION:
            if not self.api_auth_enabled:
                raise ValueError("API authentication must be enabled in production")
            if self.openai_api_key is None:
                raise ValueError("OPENAI_API_KEY is required in production")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
