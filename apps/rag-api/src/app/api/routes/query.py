from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    RagServiceDependency,
    RequestIdDependency,
    TraceIdDependency,
    require_api_key,
)
from app.models.rag import ErrorResponse, QueryRequest, QueryResponse, SourceReference

router = APIRouter(prefix="/query", tags=["rag"])


@router.post(
    "",
    response_model=QueryResponse,
    dependencies=[Depends(require_api_key)],
    responses={
        401: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def query(
    payload: QueryRequest,
    service: RagServiceDependency,
    request_id: RequestIdDependency,
    trace_id: TraceIdDependency,
) -> QueryResponse:
    reply = await service.query(
        question=payload.question,
        top_k=payload.top_k,
        request_id=request_id,
        trace_id=trace_id,
    )
    return QueryResponse(
        answer=reply.answer,
        sources=[
            SourceReference(
                title=source.title,
                url=source.url,
                source=source.source,
                score=source.score,
                thumbnail_url=source.thumbnail_url,
            )
            for source in reply.sources
        ],
        request_id=reply.request_id,
        trace_id=reply.trace_id,
        retrieval_ms=reply.retrieval_ms,
        generation_ms=reply.generation_ms,
        total_ms=reply.total_ms,
    )
