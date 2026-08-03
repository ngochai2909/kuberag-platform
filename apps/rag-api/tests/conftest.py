from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import Environment, Settings
from app.main import create_app
from app.services.rag import RagReply, RagSource

TEST_API_KEY = "test-api-key-that-is-at-least-32-characters"


class FakeRagService:
    def __init__(self, answer: str = "Mocked RAG answer") -> None:
        self.answer = answer
        self.error: Exception | None = None
        self.calls: list[tuple[str, int, str, str]] = []

    async def query(
        self,
        *,
        question: str,
        top_k: int,
        request_id: str,
        trace_id: str,
    ) -> RagReply:
        self.calls.append((question, top_k, request_id, trace_id))
        if self.error is not None:
            raise self.error
        return RagReply(
            answer=self.answer,
            sources=(
                RagSource(
                    title="KubeRAG source",
                    url="https://example.com/source",
                    source="fixture",
                    score=0.91,
                    thumbnail_url="https://example.com/source-thumbnail.jpg",
                ),
            ),
            request_id=request_id,
            trace_id=trace_id,
            retrieval_ms=12.5,
            generation_ms=34.5,
            total_ms=47.0,
        )


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env=Environment.TEST,
        cors_origins="",
    )


@pytest.fixture
def fake_rag() -> FakeRagService:
    return FakeRagService()


@pytest_asyncio.fixture
async def client(
    test_settings: Settings,
    fake_rag: FakeRagService,
) -> AsyncIterator[AsyncClient]:
    app = create_app(settings=test_settings, rag_service=fake_rag)
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest_asyncio.fixture
async def unavailable_client(test_settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings=test_settings, rag_service=None)
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest_asyncio.fixture
async def authenticated_client() -> AsyncIterator[AsyncClient]:
    settings = Settings(
        _env_file=None,
        app_env=Environment.TEST,
        cors_origins="",
        api_auth_enabled=True,
        app_api_key=TEST_API_KEY,
    )
    app = create_app(settings=settings, rag_service=FakeRagService())
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
