from __future__ import annotations

import pytest

from ingestion import telemetry


class _FakeProvider:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def force_flush(self, *, timeout_millis: int) -> None:
        self.calls.append(f"flush:{timeout_millis}")

    def shutdown(self) -> None:
        self.calls.append("shutdown")


def test_shutdown_is_noop_when_telemetry_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KUBERAG_OTEL_ENABLED", raising=False)
    telemetry._configured = False
    telemetry.configure_ingestion_telemetry()
    assert telemetry._configured is False
    telemetry.shutdown_ingestion_telemetry()
    assert telemetry._configured is False


def test_shutdown_force_flushes_all_configured_exporters(monkeypatch: pytest.MonkeyPatch) -> None:
    providers = [_FakeProvider(), _FakeProvider(), _FakeProvider()]
    monkeypatch.setattr(telemetry, "_configured", True)
    monkeypatch.setattr(telemetry, "_trace_provider", providers[0])
    monkeypatch.setattr(telemetry, "_meter_provider", providers[1])
    monkeypatch.setattr(telemetry, "_log_provider", providers[2])

    telemetry.shutdown_ingestion_telemetry()

    assert [provider.calls for provider in providers] == [
        ["flush:5000", "shutdown"],
        ["flush:5000", "shutdown"],
        ["flush:5000", "shutdown"],
    ]
    assert telemetry._configured is False
    assert telemetry._trace_provider is None
    assert telemetry._meter_provider is None
    assert telemetry._log_provider is None
