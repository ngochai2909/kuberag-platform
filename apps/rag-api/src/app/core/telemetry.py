"""OpenTelemetry traces/logs and direct Pyroscope setup for the API process."""

from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import Settings

logger = logging.getLogger(__name__)
_configured = False


def configure_telemetry(settings: Settings) -> logging.Handler | None:
    """Configure non-fatal OTLP export when the deployment explicitly enables it."""

    global _configured
    if not settings.otel_enabled or _configured:
        return None

    resource = Resource.create(
        {
            SERVICE_NAME: settings.otel_service_name,
            SERVICE_VERSION: settings.app_version,
            "deployment.environment.name": settings.app_env.value,
        }
    )
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                insecure=True,
                timeout=settings.otel_export_timeout_seconds,
            )
        )
    )
    trace.set_tracer_provider(trace_provider)

    log_provider = LoggerProvider(resource=resource)
    log_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                insecure=True,
                timeout=settings.otel_export_timeout_seconds,
            )
        )
    )
    set_logger_provider(log_provider)
    _configured = True
    return LoggingHandler(level=logging.INFO, logger_provider=log_provider)


def configure_pyroscope(settings: Settings) -> None:
    """Start in-process sampling only for the approved production-like deployment."""

    if not settings.pyroscope_enabled:
        return
    try:
        import pyroscope  # type: ignore[import-untyped]

        pyroscope.configure(
            application_name=settings.otel_service_name,
            server_address=settings.pyroscope_server_address,
            tags={"environment": settings.app_env.value},
        )
    except Exception:
        # Profiling must not prevent the API from serving a request.
        logger.warning("pyroscope_configuration_failed")


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)


def current_trace_id() -> str | None:
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return None
    return f"{context.trace_id:032x}"
