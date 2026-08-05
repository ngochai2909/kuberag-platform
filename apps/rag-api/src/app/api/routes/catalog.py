"""Browse endpoints for the Tin UI: categories + document metadata cards."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import CatalogServiceDependency, require_api_key
from app.models.catalog import (
    CategoriesResponse,
    CategoryCount,
    DocumentsResponse,
    DocumentSummary,
)
from app.models.rag import ErrorResponse

router = APIRouter(tags=["catalog"])


@router.get(
    "/categories",
    response_model=CategoriesResponse,
    dependencies=[Depends(require_api_key)],
    responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def list_categories(service: CatalogServiceDependency) -> CategoriesResponse:
    records = await service.list_categories()
    return CategoriesResponse(
        categories=[
            CategoryCount(category=record.category, count=record.count) for record in records
        ]
    )


@router.get(
    "/documents",
    response_model=DocumentsResponse,
    dependencies=[Depends(require_api_key)],
    responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def list_documents(
    service: CatalogServiceDependency,
    category: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=24, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> DocumentsResponse:
    page = await service.list_documents(category=category, limit=limit, offset=offset)
    return DocumentsResponse(
        documents=[
            DocumentSummary.model_validate(
                {
                    "id": document.id,
                    "title": document.title,
                    "url": document.url,
                    "source": document.source,
                    "published_at": document.published_at,
                    "category": document.category,
                    "summary": document.summary,
                    "image_url": document.image_url,
                }
            )
            for document in page.documents
        ],
        limit=page.limit,
        offset=page.offset,
        total=page.total,
    )
