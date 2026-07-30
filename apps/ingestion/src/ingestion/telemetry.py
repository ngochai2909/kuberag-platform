"""Small OTLP telemetry setup for Prefect flow processes.

The worker process is short-lived per flow run, so ingestion metrics are pushed
to the Collector with OTLP and exposed there for Prometheus to scrape. Payloads
are deliberately excluded from logs, span names, and metric attributes.
"""

from __future__ import annotations

import logging
import os

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


def configure_ingestion_telemetry() -> None:
    """Enable OTLP only in the cluster deployment; local tests remain offline."""

    global _configured, _tracer, _meter, _run_counter, _document_counter, _duration_histogram
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
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True, timeout=2))
    )
    trace.set_tracer_provider(trace_provider)
    _tracer = trace.get_tracer("kuberag.ingestion")

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=endpoint, insecure=True, timeout=2),
        export_interval_millis=5_000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
    _meter = metrics.get_meter("kuberag.ingestion")
    _run_counter = _meter.create_counter("kuberag.ingestion.runs")
    _document_counter = _meter.create_counter("kuberag.ingestion.documents")
    _duration_histogram = _meter.create_histogram("kuberag.ingestion.duration")

    log_provider = LoggerProvider(resource=resource)
    log_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint, insecure=True, timeout=2))
    )
    set_logger_provider(log_provider)
    root_logger = logging.getLogger()
    root_logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=log_provider))
    _configured = True


def get_tracer() -> trace.Tracer:
    return _tracer


def record_flow_result(*, status: str, document_count: int, duration_seconds: float) -> None:
    attributes = {"status": status}
    _run_counter.add(1, attributes)
    _document_counter.add(document_count, attributes)
    _duration_histogram.record(duration_seconds, attributes)


def log_event(event: str, **attributes: object) -> None:
    _logger.info(event, extra={"event": event, **attributes})


def _enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}
