from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request, Response, status

from app.core.config import Settings
from app.models.chat import AgentStatusResponse, HealthResponse
from app.services.agent import AgentService

router = APIRouter(tags=["health"])


def _settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def _agent_is_ready(request: Request) -> bool:
    return cast(AgentService | None, request.app.state.agent_service) is not None


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
    ready = _agent_is_ready(request)
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ok" if ready else "not_ready",
        version=_settings(request).app_version,
        checks={"agent": ready},
    )


@router.get("/api/v1/status", response_model=AgentStatusResponse)
async def agent_status(request: Request) -> AgentStatusResponse:
    settings = _settings(request)
    return AgentStatusResponse(
        status="ready" if _agent_is_ready(request) else "not_configured",
        memory="in_memory" if settings.agent_memory_enabled else "disabled",
    )
