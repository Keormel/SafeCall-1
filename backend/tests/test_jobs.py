import asyncio
import uuid

import fakeredis
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import select

from app.jobs import create_scheduler, recalculate_all, recalculate_incremental, run_exclusive
from app.models import Campaign, CampaignNumber, Device, Feedback, Number, RiskLevel
from app.services.campaign_engine import maintain_campaigns, plan_merges
from app.services.report_service import submit_report

BANK = frozenset({"BANK", "OTP", "URGENCY"})


# --- pure merge planner

def test_plan_merges_keeps_biggest_then_oldest():
    campaigns = [(1, 3, BANK), (2, 5, BANK | {"CARD_DATA"}), (3, 4, frozenset({"POLICE", "THREAT"}))]
    assert plan_merges(campaigns) == {1: 2}
    assert plan_merges([(1, 3, BANK), (2, 3, BANK)]) == {2: 1}
    assert plan_merges([(1, 3, BANK), (2, 3, frozenset({"POLICE"}))]) == {}


# --- campaign maintenance in the DB

async def _devices(session, n):
    devices = [Device(id=uuid.uuid4()) for _ in range(n)]
    session.add_all(devices)
    await session.commit()
    return devices


async def _campaign_with_numbers(session, devices, phones, actions=("OTP", "URGENCY")):
    for i, phone in enumerate(phones):
        for dev in devices[i * 2 : i * 2 + 2]:
            await submit_report(session, dev, phone, "BANK", list(actions))


async def test_duplicate_campaigns_are_merged(session):
    devices = await _devices(session, 12)
    await _campaign_with_numbers(session, devices, ["+37369100001", "+37369100002", "+37369100003"])
    keeper = (await session.scalars(select(Campaign))).one()
    # Simulate a twin campaign created in parallel for the same scheme.
    twin = Campaign(name="twin", type="BANK", fingerprint=sorted(BANK))
    session.add(twin)
    await session.flush()
    stray = Number(phone="+37368200001", campaign_id=twin.id, reports_count=2)
    session.add(stray)
    await session.flush()
    session.add(CampaignNumber(campaign_id=twin.id, number_id=stray.id, similarity_score=1.0))
    await session.commit()

    result = await maintain_campaigns(session)
    await session.commit()
    assert result.merged == 1
    campaigns = (await session.scalars(select(Campaign))).all()
    assert [c.id for c in campaigns] == [keeper.id]
    assert campaigns[0].numbers_count == 4
    links = (await session.scalars(select(CampaignNumber))).all()
    assert {link.campaign_id for link in links} == {keeper.id}


async def test_removed_numbers_leave_and_small_campaign_dissolves(session):
    devices = await _devices(session, 6)
    phones = ["+37369100001", "+37369100002", "+37369100003"]
    await _campaign_with_numbers(session, devices, phones)
    numbers = (await session.scalars(select(Number).order_by(Number.id))).all()
    numbers[0].is_removed = True
    await session.commit()

    first = await maintain_campaigns(session)
    await session.commit()
    assert first.detached == 1 and first.dissolved == 0
    assert numbers[0].campaign_id is None
    assert (await session.scalars(select(Campaign))).one().numbers_count == 2

    numbers[1].is_removed = True
    await session.commit()
    second = await maintain_campaigns(session)
    await session.commit()
    assert second.dissolved == 1
    assert (await session.scalars(select(Campaign))).all() == []
    assert all(n.campaign_id is None for n in (await session.scalars(select(Number))).all())
    assert (await session.scalars(select(CampaignNumber))).all() == []


# --- jobs

async def test_incremental_rescores_numbers_of_reweighted_devices(session):
    devices = await _devices(session, 4)
    for dev in devices[:2]:
        await submit_report(session, dev, "+37369100001", "BANK", ["OTP"])
    number = (await session.scalars(select(Number))).one()
    assert number.risk_level == RiskLevel.MEDIUM.value

    # Reporters' credibility collapses after many "false alarm" feedbacks; only the job applies it.
    for voter in await _devices(session, 5):
        session.add(Feedback(device_id=voter.id, number_id=number.id, was_correct=False))
    await session.commit()

    changed, _ = await recalculate_incremental(session)
    await session.refresh(number)
    assert changed >= 1
    assert number.risk_level != RiskLevel.MEDIUM.value


async def test_full_and_incremental_agree(session):
    devices = await _devices(session, 8)
    await _campaign_with_numbers(session, devices, ["+37369100001", "+37369100002", "+37369100003"])
    await recalculate_all(session)
    snapshot = {(n.phone, n.risk_level, n.risk_score, n.campaign_id) for n in (await session.scalars(select(Number))).all()}
    changed, created = await recalculate_incremental(session)
    assert (changed, created) == (0, 0)
    again = {(n.phone, n.risk_level, n.risk_score, n.campaign_id) for n in (await session.scalars(select(Number))).all()}
    assert again == snapshot


def test_scheduler_has_incremental_and_daily_full_job():
    jobs = {job.id: job for job in create_scheduler().get_jobs()}
    assert set(jobs) == {"recalculate_incremental", "recalculate_all"}
    assert "hour='3'" in str(jobs["recalculate_all"].trigger)


# --- one runner across workers

async def test_only_one_worker_runs_the_job():
    redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    started, release = asyncio.Event(), asyncio.Event()
    runs = []

    async def slow_job():
        runs.append("run")
        started.set()
        await release.wait()

    first = asyncio.create_task(run_exclusive("recalc", 60, slow_job, redis=redis))
    await started.wait()
    assert await run_exclusive("recalc", 60, slow_job, redis=redis) is False  # second worker skips
    release.set()
    assert await first is True
    assert runs == ["run"]
    # Lock released: the next tick runs again.
    release.set()
    assert await run_exclusive("recalc", 60, slow_job, redis=redis) is True
    assert await redis.get("safecall:lock:recalc") is None


async def test_job_still_runs_when_redis_is_down():
    class DownRedis:
        async def set(self, *a, **kw):
            raise RedisConnectionError("down")

    runs = []

    async def job():
        runs.append(1)

    assert await run_exclusive("recalc", 60, job, redis=DownRedis()) is True
    assert runs == [1]
