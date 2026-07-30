from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

_STANDARD_LOG_RECORD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__)


class JsonFormatter(logging.Formatter):
    """Small JSON formatter that avoids adding request bodies to logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_FIELDS and key not in {"message", "asctime"}:
                payload[key] = _json_safe(value)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return repr(value)
    return value


def configure_logging(level: str, *, telemetry_handler: logging.Handler | None = None) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    if telemetry_handler is not None:
        root_logger.addHandler(telemetry_handler)
    root_logger.setLevel(level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
