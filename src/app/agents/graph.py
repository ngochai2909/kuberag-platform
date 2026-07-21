from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.prompts import SYSTEM_PROMPT
from app.agents.tools.registry import executable_tools
from app.core.config import Settings


def create_openai_model(settings: Settings) -> ChatOpenAI:
    if settings.openai_api_key is None:
        raise ValueError("OPENAI_API_KEY is required to construct the model")

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key.get_secret_value(),
        timeout=settings.openai_timeout_seconds,
        max_retries=settings.openai_max_retries,
        use_responses_api=settings.openai_use_responses_api,
        reasoning_effort=settings.openai_reasoning_effort,
    )


def build_agent(
    settings: Settings,
    *,
    model: BaseChatModel | None = None,
    tools: Sequence[BaseTool] | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> Any:
    """Build the bounded single-agent loop used by the service layer."""

    selected_model = model or create_openai_model(settings)
    selected_tools = list(tools) if tools is not None else executable_tools()
    selected_checkpointer = checkpointer
    if selected_checkpointer is None and settings.agent_memory_enabled:
        selected_checkpointer = InMemorySaver()

    middleware: list[Any] = [
        ModelCallLimitMiddleware(
            run_limit=settings.agent_model_call_limit,
            exit_behavior="error",
        ),
        ToolCallLimitMiddleware(
            run_limit=settings.agent_tool_call_limit,
            exit_behavior="error",
        ),
    ]
    return create_agent(
        model=selected_model,
        tools=selected_tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=middleware,
        checkpointer=selected_checkpointer,
        name="application_assistant",
    )
