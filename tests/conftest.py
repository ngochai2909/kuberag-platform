from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import Environment, Settings
from app.main import create_app
from app.services.agent import AgentReply

TEST_API_KEY = "test-api-key-that-is-at-least-32-characters"


class FakeAgentService:
    def __init__(self, response: str = "Mocked agent response") -> None:
        self.response = response
        self.error: Exception | None = None
        self.calls: list[tuple[str, UUID, str]] = []

    async def chat(self, message: str, thread_id: UUID, request_id: str) -> AgentReply:
        self.calls.append((message, thread_id, request_id))
        if self.error is not None:
            raise self.error
        return AgentReply(response=self.response, thread_id=thread_id)


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env=Environment.TEST,
        cors_origins="",
        agent_memory_enabled=False,
    )


@pytest.fixture
def fake_agent() -> FakeAgentService:
    return FakeAgentService()


@pytest_asyncio.fixture
async def client(
    test_settings: Settings,
    fake_agent: FakeAgentService,
) -> AsyncIterator[AsyncClient]:
    app = create_app(settings=test_settings, agent_service=fake_agent)
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest_asyncio.fixture
async def unavailable_client(test_settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings=test_settings, agent_service=None)
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
        agent_memory_enabled=False,
    )
    app = create_app(settings=settings, agent_service=FakeAgentService())
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
