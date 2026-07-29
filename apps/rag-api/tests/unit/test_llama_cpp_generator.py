from __future__ import annotations

import json

import httpx
import pytest

from app.providers.llama_cpp import LlamaCppGenerator
from app.services.rag import Generator


def _client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler)


@pytest.mark.asyncio
async def test_llama_cpp_generator_sends_bounded_completion_request() -> None:
    observed: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["url"] = str(request.url)
        observed["headers"] = dict(request.headers)
        observed["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Grounded answer."}}]},
        )

    generator = LlamaCppGenerator(
        base_url="http://kuberag-llm.rag.svc.cluster.local:8080/",
        model="kuberag-qwen2.5-1.5b",
        timeout_seconds=10,
        max_tokens=128,
        temperature=0.2,
        client=_client(httpx.MockTransport(handler)),
    )

    answer = await generator.generate(prompt="bounded prompt", request_id="request-1")

    assert answer == "Grounded answer."
    assert observed["url"] == "http://kuberag-llm.rag.svc.cluster.local:8080/v1/chat/completions"
    headers = observed["headers"]
    assert isinstance(headers, dict)
    assert headers["x-request-id"] == "request-1"
    assert observed["payload"] == {
        "model": "kuberag-qwen2.5-1.5b",
        "messages": [{"role": "user", "content": "bounded prompt"}],
        "max_tokens": 128,
        "temperature": 0.2,
        "stream": False,
    }


@pytest.mark.asyncio
async def test_llama_cpp_generator_hides_upstream_response_details() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="upstream diagnostic that must not leak")

    generator = LlamaCppGenerator(
        base_url="http://llm.test",
        model="test-model",
        timeout_seconds=10,
        client=_client(httpx.MockTransport(handler)),
    )

    with pytest.raises(RuntimeError, match=r"llama\.cpp generation request failed") as exc_info:
        await generator.generate(prompt="prompt", request_id="request-1")

    assert "upstream diagnostic" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_llama_cpp_generator_rejects_invalid_completion_shape() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    generator = LlamaCppGenerator(
        base_url="http://llm.test",
        model="test-model",
        timeout_seconds=10,
        client=_client(httpx.MockTransport(handler)),
    )

    with pytest.raises(RuntimeError, match=r"llama\.cpp generation request failed"):
        await generator.generate(prompt="prompt", request_id="request-1")


def test_llama_cpp_generator_validates_configuration_and_satisfies_generator_protocol() -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        LlamaCppGenerator(base_url="http://llm.test", model="test-model", timeout_seconds=0)

    generator: Generator = LlamaCppGenerator(
        base_url="http://llm.test",
        model="test-model",
        timeout_seconds=10,
    )
    assert generator is not None
