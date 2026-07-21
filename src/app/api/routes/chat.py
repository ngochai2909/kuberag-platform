from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    AgentServiceDependency,
    RequestIdDependency,
    require_api_key,
)
from app.models.chat import ChatRequest, ChatResponse, ErrorResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    dependencies=[Depends(require_api_key)],
    responses={
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def chat(
    payload: ChatRequest,
    service: AgentServiceDependency,
    request_id: RequestIdDependency,
) -> ChatResponse:
    reply = await service.chat(
        message=payload.message,
        thread_id=payload.thread_id,
        request_id=request_id,
    )
    return ChatResponse(
        response=reply.response,
        thread_id=reply.thread_id,
        request_id=request_id,
    )
