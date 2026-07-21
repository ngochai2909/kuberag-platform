from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

import pytest
from langchain.agents.middleware.model_call_limit import ModelCallLimitExceededError
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.core.config import Environment, Settings
from app.core.errors import (
    AgentEmptyResponseError,
    AgentExecutionError,
    AgentLimitError,
    AgentTimeoutError,
)
from app.services.agent import LangGraphAgentService, _content_to_text


class StubRunner:
    def __init__(
        self,
        *,
        result: dict[str, Any] | None = None,
        error: Exception | None = None,
        delay: float = 0,
    ) -> None:
        self.result = result or {"messages": [AIMessage(content="answer")]}
        self.error = error
        self.delay = delay
        self.input: dict[str, Any] | None = None
        self.config: RunnableConfig | None = None

    async def ainvoke(
        self,
        input: dict[str, Any],
        config: RunnableConfig,
    ) -> dict[str, Any]:
        self.input = input
        self.config = config
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.result


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": Environment.TEST,
        "agent_memory_enabled": False,
        **overrides,
    }
    return Settings.model_validate(values)


@pytest.mark.asyncio
async def test_service_invokes_runner_with_scoped_metadata() -> None:
    runner = StubRunner(result={"messages": [AIMessage(content=" final answer ")]})
    service = LangGraphAgentService(runner=runner, settings=_settings())
    thread_id = uuid4()

    reply = await service.chat("question", thread_id, "request-1")

    assert reply.response == "final answer"
    assert reply.thread_id == thread_id
    assert runner.config is not None
    assert runner.config["configurable"]["thread_id"] == str(thread_id)
    assert runner.config["metadata"] == {
        "request_id": "request-1",
        "app_version": "0.1.0",
    }
    assert runner.config["recursion_limit"] == 24


def test_content_extraction_ignores_non_text_blocks() -> None:
    content = [
        {"type": "reasoning", "text": "private"},
        {"type": "text", "text": "public"},
        {"type": "output_text", "text": "answer"},
        123,
    ]

    assert _content_to_text(content) == "public\nanswer"
    assert _content_to_text({"text": "not-a-list"}) == ""


@pytest.mark.asyncio
async def test_service_rejects_empty_agent_response() -> None:
    runner = StubRunner(result={"messages": [AIMessage(content="")]})
    service = LangGraphAgentService(runner=runner, settings=_settings())

    with pytest.raises(AgentEmptyResponseError):
        await service.chat("question", uuid4(), "request-1")


@pytest.mark.asyncio
async def test_service_maps_provider_failures() -> None:
    runner = StubRunner(error=RuntimeError("provider detail"))
    service = LangGraphAgentService(runner=runner, settings=_settings())

    with pytest.raises(AgentExecutionError):
        await service.chat("question", uuid4(), "request-1")


@pytest.mark.asyncio
async def test_service_enforces_timeout() -> None:
    runner = StubRunner(delay=0.05)
    service = LangGraphAgentService(
        runner=runner,
        settings=_settings(agent_timeout_seconds=0.01),
    )

    with pytest.raises(AgentTimeoutError):
        await service.chat("question", uuid4(), "request-1")


@pytest.mark.asyncio
async def test_service_maps_model_call_limit() -> None:
    limit_error = ModelCallLimitExceededError(
        thread_count=0,
        run_count=9,
        thread_limit=None,
        run_limit=8,
    )
    runner = StubRunner(error=limit_error)
    service = LangGraphAgentService(runner=runner, settings=_settings())

    with pytest.raises(AgentLimitError):
        await service.chat("question", uuid4(), "request-1")
