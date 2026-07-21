from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.graph import build_agent
from app.api.errors import register_exception_handlers
from app.api.router import api_router, root_router
from app.core.config import Environment, Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import add_request_context
from app.services.agent import AgentRunner, AgentService, LangGraphAgentService

logger = logging.getLogger(__name__)


class _AutoAgent:
    pass


_AUTO_AGENT = _AutoAgent()


def _create_default_agent_service(settings: Settings) -> AgentService | None:
    if not settings.agent_configured:
        return None
    runner = cast(AgentRunner, build_agent(settings))
    return LangGraphAgentService(runner=runner, settings=settings)


def create_app(
    settings: Settings | None = None,
    agent_service: AgentService | None | _AutoAgent = _AUTO_AGENT,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    resolved_service = (
        _create_default_agent_service(resolved_settings)
        if isinstance(agent_service, _AutoAgent)
        else agent_service
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "application_started",
            extra={
                "environment": resolved_settings.app_env.value,
                "version": resolved_settings.app_version,
                "agent_configured": resolved_service is not None,
            },
        )
        if (
            resolved_settings.app_env is Environment.PRODUCTION
            and resolved_settings.agent_memory_enabled
        ):
            logger.warning("in_memory_checkpointing_enabled_in_production")
        yield
        logger.info("application_stopped")

    docs_url = "/docs" if resolved_settings.docs_enabled else None
    openapi_url = "/openapi.json" if resolved_settings.docs_enabled else None
    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description="Bounded, tool-using agent API",
        docs_url=docs_url,
        redoc_url=None,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.agent_service = resolved_service

    if resolved_settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_origin_list,
            allow_credentials=resolved_settings.cors_allow_credentials,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
        )

    app.middleware("http")(add_request_context)
    register_exception_handlers(app)
    app.include_router(root_router)
    app.include_router(api_router)
    return app


app = create_app()
