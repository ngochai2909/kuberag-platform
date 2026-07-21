from __future__ import annotations

import secrets
from typing import Annotated, cast

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings
from app.core.errors import AgentUnavailableError, AuthenticationError
from app.services.agent import AgentService

_bearer_scheme = HTTPBearer(auto_error=False)


def get_settings_from_request(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_request_id(request: Request) -> str:
    return cast(str, request.state.request_id)


def get_agent_service(request: Request) -> AgentService:
    service = cast(AgentService | None, request.app.state.agent_service)
    if service is None:
        raise AgentUnavailableError
    return service


async def require_api_key(
    settings: Annotated[Settings, Depends(get_settings_from_request)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(_bearer_scheme),
    ],
) -> None:
    if not settings.api_auth_enabled:
        return

    if credentials is None or settings.app_api_key is None:
        raise AuthenticationError

    supplied = credentials.credentials.encode()
    expected = settings.app_api_key.get_secret_value().encode()
    if not secrets.compare_digest(supplied, expected):
        raise AuthenticationError


AgentServiceDependency = Annotated[AgentService, Depends(get_agent_service)]
RequestIdDependency = Annotated[str, Depends(get_request_id)]
