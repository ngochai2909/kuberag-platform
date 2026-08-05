"""Browse-catalog response models (metadata only; never full article text)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, HttpUrl

from app.models.rag import StrictModel


class CategoryCount(StrictModel):
    category: str = Field(min_length=1, max_length=100)
    count: int = Field(ge=0)


class CategoriesResponse(StrictModel):
    categories: list[CategoryCount]


class DocumentSummary(StrictModel):
    """One indexed article card for the Tin browse UI."""

    id: UUID
    title: str = Field(min_length=1, max_length=500)
    url: HttpUrl
    source: str = Field(min_length=1, max_length=100)
    published_at: datetime | None = None
    category: str | None = Field(default=None, max_length=100)
    summary: str | None = Field(default=None, max_length=4000)
    image_url: HttpUrl | None = None


class DocumentsResponse(StrictModel):
    documents: list[DocumentSummary]
    limit: int = Field(ge=1, le=50)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
