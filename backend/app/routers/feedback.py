from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.errors import AppError
from app.limiter import limiter
from app.models import Campaign, Device, Feedback, Report
from app.schemas import ErrorResponse, FeedbackAccepted, FeedbackRequest
from app.security import get_current_device
from app.services import campaign_engine, report_service, risk_engine
from app.services.report_service import get_number, normalize_or_400

router = APIRouter(tags=["feedback"])


@router.post(
    "/feedback",
    response_model=FeedbackAccepted,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse, "description": "A device cannot review its own report"},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
@limiter.limit(get_settings().rate_limit_feedback)
async def create_feedback(
    request: Request,
    body: FeedbackRequest,
    device: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
) -> FeedbackAccepted:
    """Was the warning shown for this number correct? Adjusts reporter device reputations and number risk score."""
    phone = normalize_or_400(body.phone)
    number = await get_number(session, phone)
    if number is None:
        raise AppError("NOT_FOUND", "No data for this number", 404)

    own_report = await session.scalar(
        select(Report.id).where(
            Report.device_id == device.id,
            Report.number_id == number.id,
        )
    )
    if own_report is not None:
        raise AppError("SELF_FEEDBACK", "A device cannot review its own report", 409)

    existing = await session.scalar(
        select(Feedback).where(
            Feedback.device_id == device.id,
            Feedback.number_id == number.id,
        )
    )

    revert_was_correct: bool | None = None
    if existing is None:
        session.add(Feedback(device_id=device.id, number_id=number.id, was_correct=body.was_correct))
    elif existing.was_correct != body.was_correct:
        revert_was_correct = existing.was_correct
        existing.was_correct = body.was_correct
    else:
        # Same feedback already recorded from this device; idempotent
        return FeedbackAccepted()

    updated = await risk_engine.apply_feedback_to_reporters(
        session,
        number.id,
        was_correct=body.was_correct,
        feedback_device_reputation=device.reputation,
        revert_was_correct=revert_was_correct,
    )

    if updated:
        await risk_engine.recalculate_number(session, number)
        if number.campaign_id is not None:
            campaign = await session.get(Campaign, number.campaign_id)
            if campaign is not None:
                await campaign_engine.refresh_campaign(session, campaign)
                await report_service.recalculate_campaign_numbers(session, campaign.id)

    await session.commit()
    return FeedbackAccepted()
