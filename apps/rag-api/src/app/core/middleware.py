from __future__ import annotations

import logging
import re
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response

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
    trace_id = resolve_trace_id(
        traceparent=request.headers.get("traceparent"),
        candidate=request.headers.get("X-Trace-ID"),
    )
    request.state.request_id = request_id
    request.state.trace_id = trace_id
    started_at = time.perf_counter()

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Trace-ID"] = trace_id

    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
        },
    )
    return response
