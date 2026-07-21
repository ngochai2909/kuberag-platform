from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Environment, Settings


def test_default_development_settings_are_safe() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_env is Environment.DEVELOPMENT
    assert settings.agent_configured is False
    assert settings.api_auth_enabled is False
    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "http://localhost:5173",
    ]


def test_cors_origins_are_trimmed() -> None:
    settings = Settings(_env_file=None, cors_origins=" https://a.test, ,https://b.test ")

    assert settings.cors_origin_list == ["https://a.test", "https://b.test"]


def test_cors_wildcard_with_credentials_is_rejected() -> None:
    with pytest.raises(ValidationError, match="wildcard"):
        Settings(
            _env_file=None,
            cors_origins="*",
            cors_allow_credentials=True,
        )


@pytest.mark.parametrize(
    ("overrides", "expected_message"),
    [
        ({"api_auth_enabled": True}, "APP_API_KEY is required"),
        (
            {"api_auth_enabled": True, "app_api_key": "short"},
            "at least 32 characters",
        ),
        ({"app_env": Environment.PRODUCTION}, "authentication must be enabled"),
        (
            {
                "app_env": Environment.PRODUCTION,
                "api_auth_enabled": True,
                "app_api_key": "x" * 32,
            },
            "OPENAI_API_KEY is required",
        ),
    ],
)
def test_invalid_security_settings_are_rejected(
    overrides: dict[str, object],
    expected_message: str,
) -> None:
    with pytest.raises(ValidationError, match=expected_message):
        Settings.model_validate(overrides)


def test_valid_production_settings() -> None:
    settings = Settings(
        _env_file=None,
        app_env=Environment.PRODUCTION,
        api_auth_enabled=True,
        app_api_key="x" * 32,
        openai_api_key="test-openai-key",
    )

    assert settings.agent_configured is True
    assert settings.app_api_key is not None
    assert settings.app_api_key.get_secret_value() == "x" * 32
