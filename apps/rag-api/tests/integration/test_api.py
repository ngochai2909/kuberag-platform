from __future__ import annotations

import re

import pytest
from httpx import AsyncClient

from app.core.errors import RagExecutionError
from tests.conftest import TEST_API_KEY, FakeRagService

_TRACE_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


@pytest.mark.asyncio
async def test_liveness_and_legacy_health_alias(client: AsyncClient) -> None:
    for path in ("/health", "/health/live"):
        response = await client.get(path)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.headers["X-Request-ID"]
        assert _TRACE_ID_PATTERN.fullmatch(response.headers["X-Trace-ID"])


@pytest.mark.asyncio
async def test_readiness_reflects_rag_configuration(
    client: AsyncClient,
    unavailable_client: AsyncClient,
) -> None:
    ready = await client.get("/health/ready")
    not_ready = await unavailable_client.get("/health/ready")

    assert ready.status_code == 200
    assert ready.json()["checks"] == {"rag": True}
    assert not_ready.status_code == 503
    assert not_ready.json()["status"] == "not_ready"
    assert not_ready.json()["checks"] == {"rag": False}


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_prometheus_text(client: AsyncClient) -> None:
    response = await client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert 'kuberag_api_info{version="0.1.0"} 1' in response.text


@pytest.mark.asyncio
async def test_rag_status_is_truthful(
    client: AsyncClient,
    unavailable_client: AsyncClient,
) -> None:
    ready = await client.get("/api/v1/status")
    unavailable = await unavailable_client.get("/api/v1/status")

    assert ready.json() == {"status": "ready"}
    assert unavailable.json() == {"status": "not_configured"}


@pytest.mark.asyncio
async def test_query_returns_answer_sources_ids_and_timings(
    client: AsyncClient,
    fake_rag: FakeRagService,
) -> None:
    response = await client.post(
        "/api/v1/query",
        headers={"X-Request-ID": "request-123", "X-Trace-ID": "a" * 32},
        json={"question": "  What is KubeRAG?  ", "top_k": 3},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Mocked RAG answer",
        "sources": [
            {
                "title": "KubeRAG source",
                "url": "https://example.com/source",
                "source": "fixture",
                "score": 0.91,
            }
        ],
        "request_id": "request-123",
        "trace_id": "a" * 32,
        "retrieval_ms": 12.5,
        "generation_ms": 34.5,
        "total_ms": 47.0,
    }
    assert "analysis" not in response.json()
    assert fake_rag.calls == [("What is KubeRAG?", 3, "request-123", "a" * 32)]


@pytest.mark.asyncio
async def test_query_generates_request_and_trace_ids(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/query",
        headers={"X-Request-ID": "invalid request id with spaces"},
        json={"question": "hello"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == response.json()["request_id"]
    assert response.headers["X-Trace-ID"] == response.json()["trace_id"]
    assert _TRACE_ID_PATTERN.fullmatch(response.json()["trace_id"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"question": ""},
        {"question": "   "},
        {"question": "ok", "top_k": 0},
        {"question": "ok", "top_k": 21},
        {"question": "ok", "unexpected": True},
    ],
)
async def test_query_validation_uses_safe_error_shape(
    client: AsyncClient,
    payload: dict[str, object],
) -> None:
    response = await client.post("/api/v1/query", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request_validation_error"
    assert response.json()["error"]["message"] == "The request payload is invalid."
    assert "input" not in response.text


@pytest.mark.asyncio
async def test_unconfigured_rag_returns_503(unavailable_client: AsyncClient) -> None:
    response = await unavailable_client.post("/api/v1/query", json={"question": "hello"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "rag_unavailable"


@pytest.mark.asyncio
async def test_known_rag_error_does_not_leak_details(
    client: AsyncClient,
    fake_rag: FakeRagService,
) -> None:
    fake_rag.error = RagExecutionError()
    response = await client.post("/api/v1/query", json={"question": "hello"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "rag_execution_failed"
    assert response.json()["error"]["message"] == RagExecutionError.public_message


@pytest.mark.asyncio
async def test_unexpected_error_is_generic(
    client: AsyncClient,
    fake_rag: FakeRagService,
) -> None:
    fake_rag.error = RuntimeError("provider-secret-must-not-leak")
    response = await client.post("/api/v1/query", json={"question": "hello"})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_server_error"
    assert "provider-secret" not in response.text


@pytest.mark.asyncio
async def test_authentication_is_enforced(authenticated_client: AsyncClient) -> None:
    missing = await authenticated_client.post("/api/v1/query", json={"question": "hello"})
    invalid = await authenticated_client.post(
        "/api/v1/query",
        headers={"Authorization": "Bearer wrong"},
        json={"question": "hello"},
    )
    valid = await authenticated_client.post(
        "/api/v1/query",
        headers={"Authorization": f"Bearer {TEST_API_KEY}"},
        json={"question": "hello"},
    )

    assert missing.status_code == 401
    assert missing.headers["WWW-Authenticate"] == "Bearer"
    assert invalid.status_code == 401
    assert valid.status_code == 200
