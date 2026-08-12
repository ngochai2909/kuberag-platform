from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.dependencies import (
    get_rag_service,
    get_request_id,
    get_trace_id,
    require_api_key,
)
from app.models.rag import ErrorResponse, QueryRequest, QueryResponse, SourceReference

router = APIRouter(prefix="/query", tags=["rag"])


@router.post(
    "",
    response_model=QueryResponse,
    responses={
        401: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def query(
    payload: QueryRequest,
    request: Request,
) -> QueryResponse:
    await require_api_key(request)
    service = get_rag_service(request)
    request_id = get_request_id(request)
    trace_id = get_trace_id(request)
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
