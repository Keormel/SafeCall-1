"""Background recalculation of reputations, campaigns and number risk.

Two jobs:
- incremental, every RECALC_INTERVAL_MINUTES: only numbers touched by changed reputations or campaigns;
- full, once a day: every number, so report ageing (decay) moves risk levels down over time.

With several API workers each one runs a scheduler; a Redis lock makes sure a job runs in one of them.
"""

import logging
import uuid
from collections.abc import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import db
from app.config import get_settings
from app.models import Campaign, Device, Number, Report
from app.services import campaign_engine, risk_engine

logger = logging.getLogger(__name__)


async def _refresh_campaigns(session: AsyncSession) -> None:
    for campaign in (await session.scalars(select(Campaign))).all():
        await campaign_engine.refresh_campaign(session, campaign)
    await session.flush()


async def recalculate_all(session: AsyncSession) -> tuple[int, int]:
    """Full pass. Returns (numbers whose risk changed, campaigns created)."""
    # 0. Sync device reputations with accumulated feedback.
    await risk_engine.recalculate_device_reputations(session)
    await session.flush()

    # 1. Counters first: campaign matching relies on reports_count.
    numbers = list((await session.scalars(select(Number))).all())
    await risk_engine.recalculate_numbers(session, numbers)
    await session.flush()

    # 2. Attach numbers to known campaigns / create new ones, then merge or dissolve.
    created = await campaign_engine.discover_campaigns(session)
    await campaign_engine.maintain_campaigns(session)

    # 3. Campaign stats feed into number risk, so refresh them before the final pass.
    await _refresh_campaigns(session)
    changed = await risk_engine.recalculate_numbers(session, numbers)
    await session.commit()
    return changed, len(created)


async def recalculate_incremental(session: AsyncSession) -> tuple[int, int]:
    """Cheap pass: rescore only numbers whose inputs could have changed since the last run."""
    before = dict((await session.execute(select(Device.id, Device.reputation))).all())
    await risk_engine.recalculate_device_reputations(session)
    await session.flush()
    after = dict((await session.execute(select(Device.id, Device.reputation))).all())
    devices_changed = [d for d, rep in after.items() if before.get(d) != rep]

    created = await campaign_engine.discover_campaigns(session)
    maintenance = await campaign_engine.maintain_campaigns(session)
    await _refresh_campaigns(session)

    # Reports by re-weighted devices + every campaign member (campaign risk feeds their score)
    # + numbers that just lost their campaign (moderation, dissolve).
    conditions = [Number.campaign_id.is_not(None)]
    if devices_changed:
        conditions.append(Number.id.in_(select(Report.number_id).where(Report.device_id.in_(devices_changed))))
    if maintenance.released_number_ids:
        conditions.append(Number.id.in_(maintenance.released_number_ids))
    numbers = {n.id: n for n in (await session.scalars(select(Number).where(or_(*conditions)))).all()}

    changed = await risk_engine.recalculate_numbers(session, list(numbers.values()))
    await session.commit()
    logger.debug(
        "Incremental: %s devices re-weighted, %s numbers rescored, %s",
        len(devices_changed),
        len(numbers),
        maintenance,
    )
    return changed, len(created)


# ---------------------------------------------------------------- single-runner lock

_RELEASE = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"
_lock_client = None


def _redis():
    global _lock_client
    url = get_settings().redis_url
    if not url:
        return None
    if _lock_client is None:
        import redis.asyncio as aioredis

        _lock_client = aioredis.from_url(url, decode_responses=True, socket_timeout=2, socket_connect_timeout=2)
    return _lock_client


async def run_exclusive(name: str, ttl_seconds: int, fn: Callable[[], Awaitable[None]], redis=None) -> bool:
    """Run `fn` only if no other worker holds the lock. Returns False when skipped.

    No Redis configured → just run (single worker). Redis unreachable → run anyway: the jobs are
    idempotent and campaign creation is guarded by a database lock, so a duplicate run costs only CPU.
    """
    from redis.exceptions import RedisError

    client = redis if redis is not None else _redis()
    if client is None:
        await fn()
        return True
    key, token = f"safecall:lock:{name}", uuid.uuid4().hex
    try:
        acquired = await client.set(key, token, nx=True, ex=ttl_seconds)
    except RedisError as exc:
        logger.warning("Redis lock unavailable (%s), running %s anyway", type(exc).__name__, name)
        await fn()
        return True
    if not acquired:
        logger.debug("%s is running in another worker, skipping", name)
        return False
    try:
        await fn()
    finally:
        try:
            await client.eval(_RELEASE, 1, key, token)  # release only our own lock
        except RedisError:
            pass  # it expires by TTL
    return True


async def _job(name: str, recalc: Callable[[AsyncSession], Awaitable[tuple[int, int]]], ttl: int) -> None:
    async def body() -> None:
        async with db.SessionLocal() as session:
            changed, created = await recalc(session)
        logger.info("%s done: %s numbers changed, %s campaigns created", name, changed, created)

    try:
        await run_exclusive(name, ttl, body)
    except Exception:
        logger.exception("%s failed", name)


async def incremental_job() -> None:
    await _job("recalculate_incremental", recalculate_incremental, get_settings().recalc_interval_minutes * 60)


async def full_job() -> None:
    await _job("recalculate_all", recalculate_all, 3600)


def create_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        incremental_job,
        "interval",
        minutes=settings.recalc_interval_minutes,
        id="recalculate_incremental",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        full_job,
        "cron",
        hour=settings.full_recalc_hour_utc,
        minute=0,
        id="recalculate_all",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
