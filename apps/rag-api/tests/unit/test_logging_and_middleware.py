from __future__ import annotations

import json
import logging
import sys
from uuid import UUID

from app.core.logging import JsonFormatter
from app.core.middleware import resolve_request_id, resolve_trace_id


def test_json_formatter_emits_structured_context_and_exception() -> None:
    formatter = JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=10,
            msg="failed",
            args=(),
            exc_info=sys.exc_info(),
        )
    record.request_id = "request-1"
    record.trace_id = "a" * 32
    record.non_json = object()

    payload = json.loads(formatter.format(record))

    assert payload["message"] == "failed"
    assert payload["request_id"] == "request-1"
    assert payload["trace_id"] == "a" * 32
    assert payload["non_json"].startswith("<object object")
    assert "ValueError: boom" in payload["exception"]


def test_request_id_validation() -> None:
    assert resolve_request_id("valid.request-1") == "valid.request-1"
    assert resolve_request_id("not valid") != "not valid"
    UUID(resolve_request_id(None))


def test_trace_id_resolution() -> None:
    assert resolve_trace_id(traceparent=None, candidate="a" * 32) == "a" * 32
    assert (
        resolve_trace_id(
            traceparent=f"00-{'b' * 32}-{'c' * 16}-01",
            candidate="a" * 32,
        )
        == "b" * 32
    )
    assert resolve_trace_id(traceparent="invalid", candidate="not-hex") != "not-hex"
