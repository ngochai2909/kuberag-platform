from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import PlainTextResponse

from app.core.config import Settings
from app.core.metrics import render_metrics
from app.models.rag import HealthResponse, RagStatusResponse
from app.services.rag import RagService

router = APIRouter(tags=["health"])


def _settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def _rag_is_ready(request: Request) -> bool:
    return cast(RagService | None, request.app.state.rag_service) is not None


@router.get("/health", response_model=HealthResponse, include_in_schema=False)
@router.get("/health/live", response_model=HealthResponse)
async def liveness(request: Request) -> HealthResponse:
    return HealthResponse(status="ok", version=_settings(request).app_version)


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse}},
)
async def readiness(request: Request, response: Response) -> HealthResponse:
    ready = _rag_is_ready(request)
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ok" if ready else "not_ready",
        version=_settings(request).app_version,
        checks={"rag": ready},
    )


@router.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
async def metrics(request: Request) -> PlainTextResponse:
    version = _settings(request).app_version
    body, media_type = render_metrics(version=version)
    return PlainTextResponse(
        content=body,
        media_type=media_type,
    )


@router.get("/api/v1/status", response_model=RagStatusResponse)
async def rag_status(request: Request) -> RagStatusResponse:
    return RagStatusResponse(status="ready" if _rag_is_ready(request) else "not_configured")
