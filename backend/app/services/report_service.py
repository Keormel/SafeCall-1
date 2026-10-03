import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.models import Campaign, Device, Number, Report, RiskLevel, utcnow
from app.schemas import CheckNumberResponse
from app.services import campaign_engine, risk_engine
from app.services.fingerprint import Classifier, build_fingerprint, hash_free_text
from app.services.phone import InvalidPhoneError, mask_phone, normalize_phone

logger = logging.getLogger(__name__)


def normalize_or_400(raw: str) -> str:
    try:
        return normalize_phone(raw)
    except InvalidPhoneError as exc:
        raise AppError("INVALID_PHONE", str(exc), 422) from exc


async def get_number(session: AsyncSession, phone: str) -> Number | None:
    return await session.scalar(select(Number).where(Number.phone == phone))


async def get_or_create_number(session: AsyncSession, phone: str) -> Number:
    number = await get_number(session, phone)
    if number is not None:
        return number
    number = Number(phone=phone, risk_level=RiskLevel.UNKNOWN.value, risk_score=0)
    try:
        async with session.begin_nested():
            session.add(number)
    except IntegrityError:  # created concurrently by another request
        number = await get_number(session, phone)
        assert number is not None
    return number


async def campaign_type_for(session: AsyncSession, campaign_id: int | None) -> str | None:
    if campaign_id is None:
        return None
    return await session.scalar(select(Campaign.type).where(Campaign.id == campaign_id))


async def check_payload(session: AsyncSession, phone: str) -> CheckNumberResponse:
    """Lookup result for an E.164 number. Numbers without data are UNKNOWN, never 'safe'."""
    number = await get_number(session, phone)
    if number is None or number.is_removed or number.risk_level == RiskLevel.UNKNOWN.value:
        return CheckNumberResponse(phone=phone, risk_level=RiskLevel.UNKNOWN, risk_score=0, reports_count=0)
    return CheckNumberResponse(
        phone=phone,
        risk_level=RiskLevel(number.risk_level),
        risk_score=number.risk_score,
        campaign_id=number.campaign_id,
        campaign_type=await campaign_type_for(session, number.campaign_id),
        reports_count=number.reports_count,
    )


async def recalculate_campaign_numbers(session: AsyncSession, campaign_id: int) -> int:
    members = (await session.scalars(select(Number).where(Number.campaign_id == campaign_id))).all()
    changed = 0
    for member in members:
        changed += await risk_engine.recalculate_number(session, member)
    return changed


async def submit_report(
    session: AsyncSession,
    device: Device,
    raw_phone: str,
    category: str,
    actions: list[str],
    free_text: str | None = None,
    classifier: Classifier | None = None,
    now: datetime | None = None,
) -> Number:
    """Store a report, then rescore the number and try to tie it to a campaign. Commits."""
    now = now or utcnow()
    phone = normalize_or_400(raw_phone)
    number = await get_or_create_number(session, phone)

    duplicate = await session.scalar(
        select(Report.id).where(
            Report.number_id == number.id,
            Report.device_id == device.id,
            Report.report_day == now.date(),
        )
    )
    if duplicate is not None:
        await session.rollback()
        raise AppError("DUPLICATE_REPORT", "This device already reported this number today", 409)

    actions = sorted(set(actions))
    fingerprint = await build_fingerprint(category, actions, free_text, classifier)
    report = Report(
        number_id=number.id,
        device_id=device.id,
        category=category,
        actions=actions,
        fingerprint=fingerprint,
        free_text_hash=hash_free_text(free_text) if free_text and free_text.strip() else None,
        report_day=now.date(),
        created_at=now,
    )
    try:
        async with session.begin_nested():
            session.add(report)
    except IntegrityError as exc:
        await session.rollback()
        raise AppError("DUPLICATE_REPORT", "This device already reported this number today", 409) from exc

    await risk_engine.recalculate_number(session, number)  # refresh counters before matching
    touched: set[int] = set()
    campaign = await campaign_engine.match_number(session, number)
    if campaign is None and campaign_engine.dominant_fingerprint(
        await campaign_engine.load_report_fingerprints(session, number.id)
    ):
        # Only worth a clustering pass once this number itself has >= 2 agreeing reporters.
        touched.update(c.id for c in await campaign_engine.discover_campaigns(session))
        await session.refresh(number)
        if number.campaign_id is not None:
            campaign = await session.get(Campaign, number.campaign_id)
    if campaign is not None:
        await campaign_engine.refresh_campaign(session, campaign)
        touched.add(campaign.id)
    await risk_engine.recalculate_number(session, number)
    for campaign_id in touched:
        await recalculate_campaign_numbers(session, campaign_id)
    await session.commit()

    logger.info(
        "Report accepted for %s: fp=%s level=%s score=%s campaign=%s",
        mask_phone(phone),
        fingerprint,
        number.risk_level,
        number.risk_score,
        number.campaign_id,
    )
    return number
