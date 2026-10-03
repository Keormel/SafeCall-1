from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.jobs import recalculate_all
from app.models import Campaign, Device, Feedback, Number, Report, RiskLevel, utcnow
from app.schemas import AdminStats, ErrorResponse, RecalculateResult, RemoveNumberResult
from app.security import require_admin
from app.services.report_service import get_number, normalize_or_400

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
    responses={403: {"model": ErrorResponse}},
)


@router.get("/stats", response_model=AdminStats)
async def stats(session: AsyncSession = Depends(get_session)) -> AdminStats:
    by_level = {level: 0 for level in RiskLevel}
    rows = await session.execute(select(Number.risk_level, func.count(Number.id)).group_by(Number.risk_level))
    for level, count in rows.all():
        by_level[RiskLevel(level)] = count
    return AdminStats(
        numbers_count=await session.scalar(select(func.count(Number.id))) or 0,
        reports_count=await session.scalar(select(func.count(Report.id))) or 0,
        campaigns_count=await session.scalar(select(func.count(Campaign.id))) or 0,
        devices_count=await session.scalar(select(func.count(Device.id))) or 0,
        feedback_count=await session.scalar(select(func.count(Feedback.id))) or 0,
        by_risk_level=by_level,
    )


@router.post("/recalculate", response_model=RecalculateResult)
async def recalculate(session: AsyncSession = Depends(get_session)) -> RecalculateResult:
    """Run the periodic risk/campaign recalculation now (handy during a demo)."""
    changed, created = await recalculate_all(session)
    return RecalculateResult(numbers_changed=changed, campaigns_created=created)


@router.post("/numbers/{phone}/remove", response_model=RemoveNumberResult, responses={404: {"model": ErrorResponse}})
async def remove_number(phone: str, session: AsyncSession = Depends(get_session)) -> RemoveNumberResult:
    """Moderation: mark a number as a false positive. Clients delete it on next /sync."""
    number = await get_number(session, normalize_or_400(phone))
    if number is None:
        raise AppError("NOT_FOUND", "Number not found", 404)
    return await _set_removed(session, number, True)


@router.post("/numbers/{phone}/restore", response_model=RemoveNumberResult, responses={404: {"model": ErrorResponse}})
async def restore_number(phone: str, session: AsyncSession = Depends(get_session)) -> RemoveNumberResult:
    number = await get_number(session, normalize_or_400(phone))
    if number is None:
        raise AppError("NOT_FOUND", "Number not found", 404)
    return await _set_removed(session, number, False)


async def _set_removed(session: AsyncSession, number: Number, removed: bool) -> RemoveNumberResult:
    if number.is_removed != removed:
        number.is_removed = removed
        number.updated_at = utcnow()
        await session.commit()
    return RemoveNumberResult(phone=number.phone, removed=number.is_removed)
