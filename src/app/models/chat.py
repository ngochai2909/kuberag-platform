from __future__ import annotations

from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ChatRequest(StrictModel):
    message: str = Field(min_length=1, max_length=5000)
    thread_id: UUID = Field(default_factory=uuid4)


class ChatResponse(StrictModel):
    response: str
    thread_id: UUID
    request_id: str


class ErrorDetail(StrictModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(StrictModel):
    error: ErrorDetail


class HealthResponse(StrictModel):
    status: Literal["ok", "not_ready"]
    version: str
    checks: dict[str, bool] = Field(default_factory=dict)


class AgentStatusResponse(StrictModel):
    status: Literal["ready", "not_configured"]
    memory: Literal["in_memory", "disabled"]
