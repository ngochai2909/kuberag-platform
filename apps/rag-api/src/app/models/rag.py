from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class QueryRequest(StrictModel):
    question: str = Field(min_length=1, max_length=5000)
    top_k: int = Field(default=3, ge=1, le=20)


class SourceReference(StrictModel):
    title: str = Field(min_length=1, max_length=500)
    url: HttpUrl
    source: str = Field(min_length=1, max_length=100)
    score: float = Field(ge=0, le=1)
    thumbnail_url: HttpUrl | None = None


class QueryResponse(StrictModel):
    answer: str
    sources: list[SourceReference]
    request_id: str
    trace_id: str
    retrieval_ms: float = Field(ge=0)
    generation_ms: float = Field(ge=0)
    total_ms: float = Field(ge=0)


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


class RagStatusResponse(StrictModel):
    status: Literal["ready", "not_configured"]
