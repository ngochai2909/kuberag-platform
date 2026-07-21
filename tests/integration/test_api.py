from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.core.errors import AgentExecutionError
from tests.conftest import TEST_API_KEY, FakeAgentService


@pytest.mark.asyncio
async def test_liveness_and_legacy_health_alias(client: AsyncClient) -> None:
    for path in ("/health", "/health/live"):
        response = await client.get(path)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_readiness_reflects_agent_configuration(
    client: AsyncClient,
    unavailable_client: AsyncClient,
) -> None:
    ready = await client.get("/health/ready")
    not_ready = await unavailable_client.get("/health/ready")

    assert ready.status_code == 200
    assert ready.json()["checks"] == {"agent": True}
    assert not_ready.status_code == 503
    assert not_ready.json()["status"] == "not_ready"
    assert not_ready.json()["checks"] == {"agent": False}


@pytest.mark.asyncio
async def test_agent_status_is_truthful(
    client: AsyncClient,
    unavailable_client: AsyncClient,
) -> None:
    ready = await client.get("/api/v1/status")
    unavailable = await unavailable_client.get("/api/v1/status")

    assert ready.json() == {"status": "ready", "memory": "disabled"}
    assert unavailable.json() == {"status": "not_configured", "memory": "disabled"}


@pytest.mark.asyncio
async def test_chat_returns_public_response_and_thread_id(
    client: AsyncClient,
    fake_agent: FakeAgentService,
) -> None:
    thread_id = uuid4()
    response = await client.post(
        "/api/v1/chat",
        headers={"X-Request-ID": "request-123"},
        json={"message": "  hello  ", "thread_id": str(thread_id)},
    )

    assert response.status_code == 200
    assert response.json() == {
        "response": "Mocked agent response",
        "thread_id": str(thread_id),
        "request_id": "request-123",
    }
    assert "analysis" not in response.json()
    assert fake_agent.calls == [("hello", thread_id, "request-123")]


@pytest.mark.asyncio
async def test_chat_generates_thread_and_request_ids(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/chat",
        headers={"X-Request-ID": "invalid request id with spaces"},
        json={"message": "hello"},
    )

    assert response.status_code == 200
    UUID(response.json()["thread_id"])
    UUID(response.json()["request_id"])
    assert response.headers["X-Request-ID"] == response.json()["request_id"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"message": ""},
        {"message": "   "},
        {"message": "ok", "unexpected": True},
    ],
)
async def test_chat_validation_uses_safe_error_shape(
    client: AsyncClient,
    payload: dict[str, object],
) -> None:
    response = await client.post("/api/v1/chat", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request_validation_error"
    assert response.json()["error"]["message"] == "The request payload is invalid."
    assert "input" not in response.text


@pytest.mark.asyncio
async def test_unconfigured_agent_returns_503(unavailable_client: AsyncClient) -> None:
    response = await unavailable_client.post("/api/v1/chat", json={"message": "hello"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "agent_unavailable"


@pytest.mark.asyncio
async def test_known_agent_error_does_not_leak_details(
    client: AsyncClient,
    fake_agent: FakeAgentService,
) -> None:
    fake_agent.error = AgentExecutionError()
    response = await client.post("/api/v1/chat", json={"message": "hello"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "agent_execution_failed"
    assert response.json()["error"]["message"] == AgentExecutionError.public_message


@pytest.mark.asyncio
async def test_unexpected_error_is_generic(
    client: AsyncClient,
    fake_agent: FakeAgentService,
) -> None:
    fake_agent.error = RuntimeError("provider-secret-must-not-leak")
    response = await client.post("/api/v1/chat", json={"message": "hello"})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_server_error"
    assert "provider-secret" not in response.text


@pytest.mark.asyncio
async def test_authentication_is_enforced(authenticated_client: AsyncClient) -> None:
    missing = await authenticated_client.post("/api/v1/chat", json={"message": "hello"})
    invalid = await authenticated_client.post(
        "/api/v1/chat",
        headers={"Authorization": "Bearer wrong"},
        json={"message": "hello"},
    )
    valid = await authenticated_client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={"message": "hello"},
    )

    assert missing.status_code == 401
    assert missing.headers["WWW-Authenticate"] == "Bearer"
    assert invalid.status_code == 401
    assert valid.status_code == 200
