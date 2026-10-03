from fastapi import APIRouter, Depends, Request

from app.config import get_settings
from app.limiter import limiter
from app.models import Device
from app.schemas import ChatReply, ChatRequest, ErrorResponse
from app.security import get_current_device
from app.services import assistant

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post(
    "/chat",
    response_model=ChatReply,
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {"model": ErrorResponse, "description": "Assistant unavailable (no key, Gemini down or blocked)"},
    },
)
@limiter.limit(get_settings().rate_limit_assistant)
async def chat(request: Request, body: ChatRequest, _: Device = Depends(get_current_device)) -> ChatReply:
    """Plain-language anti-fraud advice. The app sends the whole dialogue each time; nothing is stored or logged."""
    messages = [assistant.Message(m.role, m.content) for m in body.messages]
    return ChatReply(reply=await assistant.chat(messages))
