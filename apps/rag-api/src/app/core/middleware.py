from __future__ import annotations

import logging
import re
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response
from opentelemetry import propagate
from opentelemetry.trace import SpanKind

from app.core.metrics import record_http_request
from app.core.telemetry import current_trace_id, get_tracer

logger = logging.getLogger(__name__)
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_TRACE_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
_TRACEPARENT_PATTERN = re.compile(r"^00-([a-f0-9]{32})-[a-f0-9]{16}-[a-f0-9]{2}$")


def resolve_request_id(candidate: str | None) -> str:
    if candidate and _REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return str(uuid4())


def resolve_trace_id(*, traceparent: str | None, candidate: str | None) -> str:
    if traceparent:
        match = _TRACEPARENT_PATTERN.fullmatch(traceparent)
        if match:
            return match.group(1)
    if candidate and _TRACE_ID_PATTERN.fullmatch(candidate):
        return candidate
    return uuid4().hex


async def add_request_context(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = resolve_request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = request_id
    started_at = time.perf_counter()
    parent_context = propagate.extract(request.headers)
    route = _metric_route(request.url.path)

    with get_tracer(__name__).start_as_current_span(
        "http.request",
        context=parent_context,
        kind=SpanKind.SERVER,
    ) as span:
        span.set_attribute("http.request.method", request.method)
        span.set_attribute("url.path", route)
        trace_id = current_trace_id() or resolve_trace_id(
            traceparent=request.headers.get("traceparent"),
            candidate=request.headers.get("X-Trace-ID"),
        )
        request.state.trace_id = trace_id
        try:
            response = await call_next(request)
        except Exception:
            duration_seconds = time.perf_counter() - started_at
            span.set_attribute("http.response.status_code", 500)
            record_http_request(
                method=request.method,
                route=route,
                status_code=500,
                duration_seconds=duration_seconds,
            )
            logger.error(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "method": request.method,
                    "route": route,
                    "status_code": 500,
                    "duration_ms": round(duration_seconds * 1000, 2),
                },
            )
            raise

        duration_seconds = time.perf_counter() - started_at
        span.set_attribute("http.response.status_code", response.status_code)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        record_http_request(
            method=request.method,
            route=route,
            status_code=response.status_code,
            duration_seconds=duration_seconds,
        )
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "trace_id": trace_id,
                "method": request.method,
                "route": route,
                "status_code": response.status_code,
                "duration_ms": round(duration_seconds * 1000, 2),
            },
        )
        return response


def _metric_route(path: str) -> str:
    """Keep Prometheus labels bounded; never use an arbitrary user path."""

    known_routes = {
        "/api/v1/query",
        "/api/v1/status",
        "/health",
        "/health/live",
        "/health/ready",
        "/metrics",
    }
    return path if path in known_routes else "unmatched"
