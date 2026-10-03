from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.models import Device, Feedback
from app.schemas import ErrorResponse, FeedbackAccepted, FeedbackRequest
from app.security import get_current_device
from app.services.report_service import get_number, normalize_or_400

router = APIRouter(tags=["feedback"])


@router.post(
    "/feedback",
    response_model=FeedbackAccepted,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def create_feedback(
    body: FeedbackRequest,
    device: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
) -> FeedbackAccepted:
    """Was the warning shown for this number correct? Used to evaluate and tune scoring."""
    phone = normalize_or_400(body.phone)
    number = await get_number(session, phone)
    if number is None:
        raise AppError("NOT_FOUND", "No data for this number", 404)
    session.add(Feedback(device_id=device.id, number_id=number.id, was_correct=body.was_correct))
    await session.commit()
    return FeedbackAccepted()
