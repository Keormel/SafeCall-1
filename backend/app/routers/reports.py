from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.limiter import limiter
from app.models import Device
from app.schemas import ErrorResponse, ReportAccepted, ReportRequest
from app.security import get_current_device
from app.services.report_service import submit_report

router = APIRouter(tags=["reports"])


@router.post(
    "/report",
    response_model=ReportAccepted,
    responses={
        401: {"model": ErrorResponse},
        409: {"model": ErrorResponse, "description": "Same device already reported this number today"},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
@limiter.limit(get_settings().rate_limit_report)
async def create_report(
    request: Request,
    body: ReportRequest,
    device: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
) -> ReportAccepted:
    await submit_report(
        session,
        device,
        body.phone,
        body.category.value,
        [a.value for a in body.actions],
        body.free_text,
    )
    return ReportAccepted()
