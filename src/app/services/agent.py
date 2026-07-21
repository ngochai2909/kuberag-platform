from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from langchain.agents.middleware.model_call_limit import ModelCallLimitExceededError
from langchain.agents.middleware.tool_call_limit import ToolCallLimitExceededError
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from app.core.config import Settings
from app.core.errors import (
    AgentEmptyResponseError,
    AgentExecutionError,
    AgentLimitError,
    AgentTimeoutError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AgentReply:
    response: str
    thread_id: UUID


class AgentService(Protocol):
    async def chat(self, message: str, thread_id: UUID, request_id: str) -> AgentReply: ...


class AgentRunner(Protocol):
    async def ainvoke(
        self,
        input: dict[str, Any],
        config: RunnableConfig,
    ) -> dict[str, Any]: ...


class LangGraphAgentService:
    def __init__(self, runner: AgentRunner, settings: Settings) -> None:
        self._runner = runner
        self._settings = settings

    async def chat(self, message: str, thread_id: UUID, request_id: str) -> AgentReply:
        config: RunnableConfig = {
            "configurable": {"thread_id": str(thread_id)},
            "recursion_limit": self._settings.agent_recursion_limit,
            "tags": [self._settings.app_env.value, "chat"],
            "metadata": {
                "request_id": request_id,
                "app_version": self._settings.app_version,
            },
        }

        try:
            async with asyncio.timeout(self._settings.agent_timeout_seconds):
                result = await self._runner.ainvoke(
                    {"messages": [HumanMessage(content=message)]},
                    config=config,
                )
        except TimeoutError as exc:
            raise AgentTimeoutError from exc
        except (ModelCallLimitExceededError, ToolCallLimitExceededError) as exc:
            raise AgentLimitError from exc
        except Exception as exc:
            logger.exception(
                "agent_execution_failed",
                extra={"request_id": request_id, "thread_id": str(thread_id)},
            )
            raise AgentExecutionError from exc

        response = _last_assistant_text(result.get("messages"))
        if not response:
            raise AgentEmptyResponseError
        return AgentReply(response=response, thread_id=thread_id)


def _last_assistant_text(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""

    for message in reversed(messages):
        if isinstance(message, AIMessage):
            text = _content_to_text(message.content)
            if text:
                return text
    return ""


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
            continue
        if not isinstance(block, Mapping):
            continue
        if block.get("type") not in {"text", "output_text"}:
            continue
        text = block.get("text")
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(part.strip() for part in parts if part.strip())
