from __future__ import annotations

import secrets
from typing import cast

from fastapi import Request

from app.core.config import Settings
from app.core.errors import AuthenticationError, RagUnavailableError
from app.providers.catalog import CatalogService
from app.services.rag import RagService


def get_settings_from_request(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_request_id(request: Request) -> str:
    return cast(str, request.state.request_id)


def get_trace_id(request: Request) -> str:
    return cast(str, request.state.trace_id)


def get_rag_service(request: Request) -> RagService:
    service = cast(RagService | None, request.app.state.rag_service)
    if service is None:
        raise RagUnavailableError
    return service


def get_catalog_service(request: Request) -> CatalogService:
    service = cast(CatalogService | None, request.app.state.catalog_service)
    if service is None:
        raise RagUnavailableError
    return service


async def require_api_key(
    request: Request,
) -> None:
    settings = get_settings_from_request(request)
    if not settings.api_auth_enabled:
        return

    scheme, _, supplied_token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not supplied_token or settings.app_api_key is None:
        raise AuthenticationError

    supplied = supplied_token.encode()
    expected = settings.app_api_key.get_secret_value().encode()
    if not secrets.compare_digest(supplied, expected):
        raise AuthenticationError
