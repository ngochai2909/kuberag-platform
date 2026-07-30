from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import ApplicationError, AuthenticationError
from app.models.rag import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unavailable")


def _trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", "unavailable")


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(code=code, message=message, request_id=request_id)
    ).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=body, headers=headers)


async def handle_application_error(request: Request, exc: ApplicationError) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, AuthenticationError) else None
    return _error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.public_message,
        request_id=_request_id(request),
        headers=headers,
    )


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.info(
        "request_validation_failed",
        extra={
            "request_id": _request_id(request),
            "trace_id": _trace_id(request),
            "path": request.url.path,
            "error_count": len(exc.errors()),
        },
    )
    return _error_response(
        status_code=422,
        code="request_validation_error",
        message="The request payload is invalid.",
        request_id=_request_id(request),
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Do not attach exception details: OTLP exports this record to Loki.
    logger.error(
        "unhandled_request_error",
        extra={
            "request_id": _request_id(request),
            "trace_id": _trace_id(request),
            "path": request.url.path,
        },
    )
    return _error_response(
        status_code=500,
        code="internal_server_error",
        message="An unexpected error occurred.",
        request_id=_request_id(request),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.exception_handler(ApplicationError)(handle_application_error)
    app.exception_handler(RequestValidationError)(handle_validation_error)
    app.exception_handler(Exception)(handle_unexpected_error)
