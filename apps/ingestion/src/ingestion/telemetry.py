"""Small OTLP telemetry setup for Prefect flow processes.

The worker process is short-lived per flow run, so ingestion metrics are pushed
to the Collector with OTLP and exposed there for Prometheus to scrape. Payloads
are deliberately excluded from logs, span names, and metric attributes.
"""

from __future__ import annotations

import logging
import os
import time

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_configured = False
_logger = logging.getLogger("kuberag.ingestion")
_tracer = trace.get_tracer("kuberag.ingestion")
_meter = metrics.get_meter("kuberag.ingestion")
_run_counter = _meter.create_counter("kuberag.ingestion.runs")
_document_counter = _meter.create_counter("kuberag.ingestion.documents")
_duration_histogram = _meter.create_histogram("kuberag.ingestion.duration")
_last_failure_timestamp_gauge = _meter.create_gauge(
    "kuberag.ingestion.last_failure_timestamp",
    unit="s",
)
_trace_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None
_log_provider: LoggerProvider | None = None


def configure_ingestion_telemetry() -> None:
    """Enable OTLP only in the cluster deployment; local tests remain offline."""

    global _configured, _tracer, _meter, _run_counter, _document_counter, _duration_histogram
    global _last_failure_timestamp_gauge
    global _trace_provider, _meter_provider, _log_provider
    if _configured or not _enabled("KUBERAG_OTEL_ENABLED"):
        return

    endpoint = os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "kuberag-otel-collector.observability.svc.cluster.local:4317",
    )
    resource = Resource.create(
        {
            SERVICE_NAME: "kuberag-ingestion",
            "deployment.environment.name": os.environ.get("APP_ENV", "production"),
        }
    )
    _trace_provider = TracerProvider(resource=resource)
    # Prefect flow processes exit quickly; keep the batch delay short so spans
    # are usually exported before shutdown_ingestion_telemetry() runs.
    _trace_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=endpoint, insecure=True, timeout=2),
            schedule_delay_millis=500,
        )
    )
    trace.set_tracer_provider(_trace_provider)
    _tracer = trace.get_tracer("kuberag.ingestion")

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=endpoint, insecure=True, timeout=2),
        export_interval_millis=1_000,
    )
    _meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(_meter_provider)
    _meter = metrics.get_meter("kuberag.ingestion")
    _run_counter = _meter.create_counter("kuberag.ingestion.runs")
    _document_counter = _meter.create_counter("kuberag.ingestion.documents")
    _duration_histogram = _meter.create_histogram("kuberag.ingestion.duration")
    _last_failure_timestamp_gauge = _meter.create_gauge(
        "kuberag.ingestion.last_failure_timestamp",
        unit="s",
    )

    _log_provider = LoggerProvider(resource=resource)
    _log_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(endpoint=endpoint, insecure=True, timeout=2),
            schedule_delay_millis=500,
        )
    )
    set_logger_provider(_log_provider)
    root_logger = logging.getLogger()
    root_logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=_log_provider))
    _configured = True


def shutdown_ingestion_telemetry() -> None:
    """Force-flush OTLP exporters so short-lived Prefect processes do not drop signals."""

    global _configured, _trace_provider, _meter_provider, _log_provider
    if not _configured:
        return

    for provider in (_trace_provider, _meter_provider, _log_provider):
        if provider is None:
            continue
        try:
            provider.force_flush(timeout_millis=5_000)
        except Exception:
            _logger.warning("ingestion_telemetry_force_flush_failed", exc_info=True)
        try:
            provider.shutdown()
        except Exception:
            _logger.warning("ingestion_telemetry_shutdown_failed", exc_info=True)

    _trace_provider = None
    _meter_provider = None
    _log_provider = None
    _configured = False


def get_tracer() -> trace.Tracer:
    return _tracer


def record_flow_result(*, status: str, document_count: int, duration_seconds: float) -> None:
    attributes = {"status": status}
    _run_counter.add(1, attributes)
    _document_counter.add(document_count, attributes)
    _duration_histogram.record(duration_seconds, attributes)
    if status == "failed":
        # A short-lived process first exports its counter at one, so PromQL
        # increase() cannot observe a 0 -> 1 transition. Keep a timestamp gauge
        # for an alert that reliably expires after its lookback window.
        _last_failure_timestamp_gauge.set(time.time(), attributes)


def log_event(event: str, **attributes: object) -> None:
    _logger.info(event, extra={"event": event, **attributes})


def _enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}
