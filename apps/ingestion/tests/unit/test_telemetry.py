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


class _FakeCounter:
    def __init__(self) -> None:
        self.calls: list[tuple[float, dict[str, str]]] = []

    def add(self, value: float, attributes: dict[str, str]) -> None:
        self.calls.append((value, attributes))


class _FakeHistogram:
    def __init__(self) -> None:
        self.calls: list[tuple[float, dict[str, str]]] = []

    def record(self, value: float, attributes: dict[str, str]) -> None:
        self.calls.append((value, attributes))


class _FakeGauge:
    def __init__(self) -> None:
        self.calls: list[tuple[float, dict[str, str]]] = []

    def set(self, value: float, attributes: dict[str, str]) -> None:
        self.calls.append((value, attributes))


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


def test_failed_flow_records_timestamp_gauge(monkeypatch: pytest.MonkeyPatch) -> None:
    run_counter = _FakeCounter()
    document_counter = _FakeCounter()
    duration_histogram = _FakeHistogram()
    failure_timestamp = _FakeGauge()
    monkeypatch.setattr(telemetry, "_run_counter", run_counter)
    monkeypatch.setattr(telemetry, "_document_counter", document_counter)
    monkeypatch.setattr(telemetry, "_duration_histogram", duration_histogram)
    monkeypatch.setattr(telemetry, "_last_failure_timestamp_gauge", failure_timestamp)
    monkeypatch.setattr(telemetry.time, "time", lambda: 1_785_752_900.0)

    telemetry.record_flow_result(status="failed", document_count=0, duration_seconds=2.5)

    assert run_counter.calls == [(1, {"status": "failed"})]
    assert document_counter.calls == [(0, {"status": "failed"})]
    assert duration_histogram.calls == [(2.5, {"status": "failed"})]
    assert failure_timestamp.calls == [(1_785_752_900.0, {"status": "failed"})]
