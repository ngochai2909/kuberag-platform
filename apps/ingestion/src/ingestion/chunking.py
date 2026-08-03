"""Sentence-aware text chunking for retrieval-friendly embeddings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pydantic import Field, model_validator

from ingestion.models import SourceDocument, StrictModel, normalize_whitespace

CHUNKING_VERSION = "sentence-overlap-v1"

# Sentence ends common in Vietnamese/English news text.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+")
_WORD_RE = re.compile(r"\S+\s*")


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    """Configurable chunk budget for the offline ingestion path.

    Sizing is character-based on purpose: the embedding tokenizer is not pinned
    yet, so unit tests stay deterministic and offline. Defaults stay under a
    typical 512-token small-embedding window after the title prefix is added.
    """

    max_chars: int = 800
    overlap_chars: int = 150
    include_title: bool = True
    version: str = CHUNKING_VERSION

    def __post_init__(self) -> None:
        if self.max_chars < 64:
            msg = "max_chars must be >= 64"
            raise ValueError(msg)
        if self.overlap_chars < 0:
            msg = "overlap_chars must be >= 0"
            raise ValueError(msg)
        if self.overlap_chars >= self.max_chars:
            msg = "overlap_chars must be smaller than max_chars"
            raise ValueError(msg)


class TextChunk(StrictModel):
    """One retrieval unit derived from a SourceDocument body."""

    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def content_within_configured_budget(self) -> TextChunk:
        max_chars = self.metadata.get("max_chars")
        if isinstance(max_chars, int) and len(self.content) > max_chars:
            msg = "chunk content exceeds configured max_chars"
            raise ValueError(msg)
        return self


def chunk_text(
    text: str,
    *,
    title: str | None = None,
    config: ChunkingConfig | None = None,
) -> list[TextChunk]:
    """Split normalized prose into overlapping, sentence-aware chunks."""

    cfg = config or ChunkingConfig()
    body = normalize_whitespace(text)
    if not body:
        return []

    title_prefix = ""
    if cfg.include_title and title:
        cleaned_title = normalize_whitespace(title)
        if cleaned_title:
            title_prefix = f"{cleaned_title}\n\n"

    body_budget = cfg.max_chars - len(title_prefix)
    if body_budget < 32:
        msg = "title prefix leaves insufficient room for chunk body"
        raise ValueError(msg)

    units = _expand_units(_split_sentences(body), max_chars=body_budget)
    windows = _window_units(units, max_chars=body_budget, overlap_chars=cfg.overlap_chars)

    chunks: list[TextChunk] = []
    for index, (segment, start, end) in enumerate(windows):
        chunks.append(
            TextChunk(
                chunk_index=index,
                content=f"{title_prefix}{segment}",
                metadata={
                    "chunking_version": cfg.version,
                    "max_chars": cfg.max_chars,
                    "overlap_chars": cfg.overlap_chars,
                    "char_start": start,
                    "char_end": end,
                    "title_prefixed": bool(title_prefix),
                    "body_chars": len(segment),
                },
            )
        )
    return chunks


def chunk_document(
    document: SourceDocument,
    *,
    config: ChunkingConfig | None = None,
) -> list[TextChunk]:
    """Chunk a normalized source document for later embedding/upsert."""

    return chunk_text(document.text, title=document.title, config=config)


def _split_sentences(text: str) -> list[tuple[str, int, int]]:
    pieces = [part.strip() for part in _SENTENCE_SPLIT_RE.split(text) if part.strip()]
    if not pieces:
        return [(text, 0, len(text))]

    spans: list[tuple[str, int, int]] = []
    cursor = 0
    for piece in pieces:
        start = text.find(piece, cursor)
        if start < 0:
            start = cursor
        end = start + len(piece)
        spans.append((piece, start, end))
        cursor = end
    return spans


def _expand_units(
    units: list[tuple[str, int, int]],
    *,
    max_chars: int,
) -> list[tuple[str, int, int]]:
    expanded: list[tuple[str, int, int]] = []
    for text, start, _end in units:
        if len(text) <= max_chars:
            expanded.append((text, start, start + len(text)))
            continue
        expanded.extend(_hard_split(text, start=start, max_chars=max_chars))
    return expanded


def _window_units(
    units: list[tuple[str, int, int]],
    *,
    max_chars: int,
    overlap_chars: int,
) -> list[tuple[str, int, int]]:
    if not units:
        return []

    windows: list[tuple[str, int, int]] = []
    start_idx = 0

    while start_idx < len(units):
        end_idx = start_idx
        size = 0
        while end_idx < len(units):
            piece_len = len(units[end_idx][0])
            next_size = piece_len if end_idx == start_idx else size + 1 + piece_len
            if end_idx > start_idx and next_size > max_chars:
                break
            size = next_size
            end_idx += 1

        selected = units[start_idx:end_idx]
        segment = " ".join(part for part, _s, _e in selected)
        # Guard against a pathological single oversized unit.
        if len(segment) > max_chars:
            segment = segment[:max_chars]
        windows.append((segment, selected[0][1], selected[-1][2]))

        if end_idx >= len(units):
            break

        if overlap_chars == 0:
            start_idx = end_idx
            continue

        # Walk backward from the end of this window until overlap budget is met.
        overlap_idx = end_idx - 1
        covered = 0
        while overlap_idx > start_idx and covered < overlap_chars:
            covered += len(units[overlap_idx][0])
            if covered >= overlap_chars:
                break
            covered += 1  # account for the joining space when another unit is included
            overlap_idx -= 1

        next_start = overlap_idx
        if next_start <= start_idx:
            next_start = start_idx + 1
        start_idx = next_start if next_start < end_idx else end_idx

    return windows


def _hard_split(text: str, *, start: int, max_chars: int) -> list[tuple[str, int, int]]:
    words = _WORD_RE.findall(text)
    if not words:
        return _split_by_chars(text, start=start, max_chars=max_chars)

    spans: list[tuple[str, int, int]] = []
    local_offset = 0
    buffer = ""
    buffer_start = start

    for word in words:
        candidate = f"{buffer}{word}"
        if buffer and len(candidate.rstrip()) > max_chars:
            piece = buffer.rstrip()
            spans.append((piece, buffer_start, buffer_start + len(piece)))
            local_offset += len(buffer)
            buffer = word
            buffer_start = start + local_offset
            if len(buffer.rstrip()) > max_chars:
                hard = _split_by_chars(buffer.rstrip(), start=buffer_start, max_chars=max_chars)
                spans.extend(hard)
                local_offset += len(buffer)
                buffer = ""
                buffer_start = start + local_offset
        else:
            buffer = candidate

    if buffer.strip():
        piece = buffer.rstrip()
        spans.append((piece, buffer_start, buffer_start + len(piece)))
    return spans


def _split_by_chars(text: str, *, start: int, max_chars: int) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    offset = 0
    while offset < len(text):
        piece = text[offset : offset + max_chars]
        spans.append((piece, start + offset, start + offset + len(piece)))
        offset += max_chars
    return spans
