from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.router import api_router, root_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import add_request_context
from app.services.rag import RagService

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    rag_service: RagService | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "application_started",
            extra={
                "environment": resolved_settings.app_env.value,
                "version": resolved_settings.app_version,
                "rag_configured": rag_service is not None,
            },
        )
        yield
        logger.info("application_stopped")

    docs_url = "/docs" if resolved_settings.docs_enabled else None
    openapi_url = "/openapi.json" if resolved_settings.docs_enabled else None
    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description="KubeRAG retrieval-augmented generation API",
        docs_url=docs_url,
        redoc_url=None,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.rag_service = rag_service

    if resolved_settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_origin_list,
            allow_credentials=resolved_settings.cors_allow_credentials,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Trace-ID"],
            expose_headers=["X-Request-ID", "X-Trace-ID"],
        )

    app.middleware("http")(add_request_context)
    register_exception_handlers(app)
    app.include_router(root_router)
    app.include_router(api_router)
    return app


app = create_app()
