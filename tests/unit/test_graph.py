from __future__ import annotations

from typing import Any

import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from app.agents.graph import build_agent, create_openai_model
from app.core.config import Environment, Settings


class RecordingChatModel(BaseChatModel):
    calls: list[list[BaseMessage]] = Field(default_factory=list, exclude=True)

    @property
    def _llm_type(self) -> str:
        return "recording-chat-model"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        del stop, run_manager, kwargs
        self.calls.append(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="done"))])


def _settings(*, memory: bool) -> Settings:
    return Settings(
        _env_file=None,
        app_env=Environment.TEST,
        agent_memory_enabled=memory,
    )


@pytest.mark.asyncio
async def test_built_agent_runs_without_external_provider() -> None:
    model = RecordingChatModel()
    agent = build_agent(_settings(memory=False), model=model, tools=[])

    result = await agent.ainvoke({"messages": [HumanMessage(content="hello")]})

    assert result["messages"][-1].content == "done"
    assert len(model.calls) == 1


@pytest.mark.asyncio
async def test_built_agent_retains_thread_memory() -> None:
    model = RecordingChatModel()
    agent = build_agent(_settings(memory=True), model=model, tools=[])
    config = {"configurable": {"thread_id": "thread-1"}}

    await agent.ainvoke({"messages": [HumanMessage(content="first")]}, config=config)
    await agent.ainvoke({"messages": [HumanMessage(content="second")]}, config=config)

    human_messages = [
        message.content for message in model.calls[-1] if isinstance(message, HumanMessage)
    ]
    assert human_messages == ["first", "second"]


def test_openai_model_requires_api_key() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        create_openai_model(_settings(memory=False))
