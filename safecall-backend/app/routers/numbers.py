from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.limiter import limiter
from app.models import Campaign, Device, Number, RiskLevel
from app.schemas import CheckNumberRequest, CheckNumberResponse, ErrorResponse, NumberList, NumberOut
from app.security import get_current_device
from app.services.report_service import check_payload, normalize_or_400

router = APIRouter(tags=["numbers"])


@router.post(
    "/check-number",
    response_model=CheckNumberResponse,
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
@limiter.limit(get_settings().rate_limit_check)
async def check_number(
    request: Request,
    body: CheckNumberRequest,
    _: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
) -> CheckNumberResponse:
    """Online lookup (the app normally answers from its local DB). Numbers without data are UNKNOWN."""
    return await check_payload(session, normalize_or_400(body.phone))


@router.get("/numbers", response_model=NumberList, responses={401: {"model": ErrorResponse}})
async def list_numbers(
    risk_level: RiskLevel | None = None,
    campaign_id: int | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
) -> NumberList:
    conditions = [Number.is_removed.is_(False), Number.risk_level != RiskLevel.UNKNOWN.value]
    if risk_level is not None:
        conditions.append(Number.risk_level == risk_level.value)
    if campaign_id is not None:
        conditions.append(Number.campaign_id == campaign_id)

    total = await session.scalar(select(func.count(Number.id)).where(*conditions)) or 0
    rows = await session.execute(
        select(Number, Campaign.type)
        .outerjoin(Campaign, Campaign.id == Number.campaign_id)
        .where(*conditions)
        .order_by(Number.risk_score.desc(), Number.id)
        .limit(limit)
        .offset(offset)
    )
    items = [
        NumberOut.model_validate(number).model_copy(update={"campaign_type": ctype}) for number, ctype in rows.all()
    ]
    return NumberList(items=items, total=total, limit=limit, offset=offset)
