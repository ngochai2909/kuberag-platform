from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from app.core import telemetry
from app.core.config import Environment, Settings


def test_disabled_api_telemetry_is_a_noop() -> None:
    settings = Settings(_env_file=None, app_env=Environment.TEST, otel_enabled=False)

    assert telemetry.configure_telemetry(settings) is None
    telemetry.configure_pyroscope(settings)


def test_current_trace_id_is_absent_without_an_active_span() -> None:
    assert telemetry.current_trace_id() is None


def test_enabled_api_telemetry_builds_exporters_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(_env_file=None, app_env=Environment.TEST, otel_enabled=True)
    configured: list[object] = []
    monkeypatch.setattr(telemetry, "_configured", False)
    monkeypatch.setattr(telemetry.trace, "set_tracer_provider", configured.append)
    monkeypatch.setattr(telemetry, "set_logger_provider", configured.append)

    handler = telemetry.configure_telemetry(settings)

    assert handler is not None
    assert len(configured) == 2


def test_pyroscope_configuration_uses_only_service_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setitem(
        sys.modules,
        "pyroscope",
        SimpleNamespace(configure=lambda **kwargs: calls.append(kwargs)),
    )
    settings = Settings(_env_file=None, app_env=Environment.TEST, pyroscope_enabled=True)

    telemetry.configure_pyroscope(settings)

    assert calls == [
        {
            "application_name": "kuberag-rag-api",
            "server_address": "http://kuberag-pyroscope.observability.svc.cluster.local:4040",
            "tags": {"environment": "test"},
        }
    ]
