"""Shared document contract returned by every source adapter."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

_WHITESPACE_RE = re.compile(r"\s+")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SourceDocument(StrictModel):
    """Normalized source record before PostgreSQL upsert and chunking."""

    source: str = Field(min_length=1, max_length=64)
    external_id: str = Field(min_length=1, max_length=2048)
    title: str = Field(min_length=1, max_length=1000)
    url: str = Field(min_length=1, max_length=2048)
    published_at: datetime | None = None
    text: str = Field(min_length=1)
    checksum: str = Field(min_length=64, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("checksum")
    @classmethod
    def checksum_must_be_sha256_hex(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            msg = "checksum must be a lowercase sha256 hex digest"
            raise ValueError(msg)
        return value


def normalize_whitespace(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value).strip()


def document_checksum(*, title: str, text: str) -> str:
    """Checksum from normalized title and body, not raw RSS/HTML/JSON."""

    payload = f"{normalize_whitespace(title)}\n{normalize_whitespace(text)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
