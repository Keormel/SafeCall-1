"""Periodic full recalculation of campaigns and number risk."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import db
from app.config import get_settings
from app.models import Campaign, Number
from app.services import campaign_engine, risk_engine

logger = logging.getLogger(__name__)


async def recalculate_all(session: AsyncSession) -> tuple[int, int]:
    """Returns (numbers whose risk changed, campaigns created)."""
    # 1. Counters first: campaign matching relies on reports_count.
    numbers = (await session.scalars(select(Number))).all()
    for number in numbers:
        await risk_engine.recalculate_number(session, number)
    await session.flush()

    # 2. Attach numbers to known campaigns / create new ones.
    created = await campaign_engine.discover_campaigns(session)

    # 3. Campaign stats feed into number risk, so refresh them before the final pass.
    for campaign in (await session.scalars(select(Campaign))).all():
        await campaign_engine.refresh_campaign(session, campaign)
    await session.flush()

    changed = 0
    for number in numbers:
        changed += await risk_engine.recalculate_number(session, number)
    await session.commit()
    return changed, len(created)


async def recalculate_job() -> None:
    try:
        async with db.SessionLocal() as session:
            changed, created = await recalculate_all(session)
        logger.info("Recalculation done: %s numbers changed, %s campaigns created", changed, created)
    except Exception:
        logger.exception("Recalculation job failed")


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        recalculate_job,
        "interval",
        minutes=get_settings().recalc_interval_minutes,
        id="recalculate_all",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
