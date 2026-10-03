from typing import Literal

from fastapi import APIRouter, Depends, Query, Request

from app.config import get_settings
from app.limiter import limiter
from app.models import Device
from app.schemas import ChatReply, ChatRequest, ErrorResponse, SuggestionButton, SuggestionsResponse
from app.security import get_current_device
from app.services import assistant

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post(
    "/chat",
    response_model=ChatReply,
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
@limiter.limit(get_settings().rate_limit_assistant)
async def chat(request: Request, body: ChatRequest, _: Device = Depends(get_current_device)) -> ChatReply:
    """Plain-language anti-fraud advice. The app sends the whole dialogue each time; nothing is stored or logged.

    A message equal to a ready-made button gets its vetted answer instantly. Free text goes to Gemini;
    if Gemini is unavailable the answer comes from the ready-made topics, so the user is never left
    without advice.
    """
    messages = [assistant.Message(m.role, m.content) for m in body.messages]
    result = await assistant.chat(messages)
    return ChatReply(reply=result.reply, source=result.source, suggestions=result.suggestions)


@router.get("/suggestions", response_model=SuggestionsResponse, responses={401: {"model": ErrorResponse}})
async def suggestions(
    lang: Literal["ru", "ro"] = Query("ru"), _: Device = Depends(get_current_device)
) -> SuggestionsResponse:
    """Ready-made phrases to show as buttons under the chat. Server-managed, so they change without an app release."""
    return SuggestionsResponse(
        language=lang,
        suggestions=[SuggestionButton(id=i, text=t) for i, t in assistant.suggestion_buttons(lang)],
    )
