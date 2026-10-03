from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.jobs import recalculate_all
from app.models import Campaign, Device, Feedback, Number, Report, RiskLevel, utcnow
from app.limiter import limiter
from app.schemas import (
    ActivityDay,
    ActivityResponse,
    AdminReportList,
    AdminReportOut,
    AdminStats,
    ErrorResponse,
    RecalculateResult,
    RemoveNumberResult,
    TokenResponse,
)
from app.services.fingerprint import Category
from app.security import create_admin_token, require_admin, verify_admin_key
from app.services.report_service import get_number, normalize_or_400

token_router = APIRouter(prefix="/admin", tags=["admin"])

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)


@token_router.post(
    "/token",
    response_model=TokenResponse,
    dependencies=[Depends(verify_admin_key)],
    responses={403: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
@limiter.limit("10/minute")
async def admin_token(request: Request) -> TokenResponse:
    """Exchange the admin key (header `X-Admin-Key`) for a short-lived admin JWT."""
    token, expires_in = create_admin_token()
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/stats", response_model=AdminStats)
async def get_stats(session: AsyncSession = Depends(get_session)) -> AdminStats:
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


@router.get("/reports", response_model=AdminReportList)
async def list_reports(
    category: Category | None = None,
    phone: str | None = Query(None, description="Any format; normalized to E.164"),
    campaign_id: int | None = None,
    since: datetime | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> AdminReportList:
    """Complaints feed for the dashboard, newest first."""
    conditions = []
    if category is not None:
        conditions.append(Report.category == category.value)
    if phone:
        conditions.append(Number.phone == normalize_or_400(phone))
    if campaign_id is not None:
        conditions.append(Number.campaign_id == campaign_id)
    if since is not None:
        conditions.append(Report.created_at >= since)

    base = select(Report, Number).join(Number, Number.id == Report.number_id).where(*conditions)
    total = await session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = await session.execute(base.order_by(Report.created_at.desc(), Report.id.desc()).limit(limit).offset(offset))
    items = [
        AdminReportOut(
            id=r.id,
            phone=n.phone,
            category=r.category,
            actions=r.actions or [],
            fingerprint=r.fingerprint or [],
            has_free_text=r.free_text_hash is not None,
            risk_level=RiskLevel(n.risk_level),
            campaign_id=n.campaign_id,
            created_at=r.created_at,
        )
        for r, n in rows.all()
    ]
    return AdminReportList(items=items, total=total, limit=limit, offset=offset)


@router.get("/activity", response_model=ActivityResponse)
async def activity(
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> ActivityResponse:
    """Daily reports, reporters and new numbers for the dashboard chart (UTC days)."""
    today = utcnow().date()
    first = today - timedelta(days=days - 1)

    per_day = await session.execute(
        select(Report.report_day, func.count(Report.id), func.count(func.distinct(Report.device_id)))
        .where(Report.report_day >= first)
        .group_by(Report.report_day)
    )
    reports = {d: (n, devices) for d, n, devices in per_day.all()}

    created = await session.scalars(
        select(Number.created_at).where(Number.created_at >= datetime.combine(first, datetime.min.time()))
    )
    new_numbers: dict = {}
    for ts in created.all():
        new_numbers[ts.date()] = new_numbers.get(ts.date(), 0) + 1

    out = []
    for i in range(days):
        d = first + timedelta(days=i)
        n, devices = reports.get(d, (0, 0))
        out.append(ActivityDay(date=d, reports=n, reporters=devices, new_numbers=new_numbers.get(d, 0)))
    return ActivityResponse(days=out)


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
