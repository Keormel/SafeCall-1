"""Edge paths of the engines that the scenario tests do not reach."""

from sqlalchemy import select

from app.jobs import recalculate_all
from app.models import Campaign, CampaignNumber, Number
from app.services.campaign_engine import CAMPAIGN_LOCK_KEY, assign_number, detach_number, lock_campaigns
from app.services.fingerprint import LLMResult, LRUCache
from app.services.phone import mask_phone
from app.services.report_service import submit_report
from tests.factories import make_devices, make_number, phone


def test_mask_handles_empty_and_short_values():
    assert mask_phone(None) == "<empty>"
    assert mask_phone("") == "<empty>"
    assert mask_phone("112") == "***"


def test_lru_cache_evicts_least_recently_used():
    cache = LRUCache(max_size=2)
    cache.set("a", LLMResult("BANK", ()))
    cache.set("b", LLMResult("POLICE", ()))
    cache.get("a")  # "a" is now the most recent
    cache.set("c", LLMResult("OTHER", ()))
    assert cache.get("b") is None
    assert cache.get("a") is not None and cache.get("c") is not None
    assert len(cache) == 2


async def test_advisory_lock_is_taken_on_postgres():
    """The race guard only exists on Postgres; check the exact statement it sends."""
    executed = []

    class Conn:
        dialect = type("D", (), {"name": "postgresql"})()

    class FakeSession:
        async def connection(self):
            return Conn()

        async def execute(self, statement, params):
            executed.append((str(statement), params))

    await lock_campaigns(FakeSession())
    assert executed == [("SELECT pg_advisory_xact_lock(:key)", {"key": CAMPAIGN_LOCK_KEY})]


async def test_relinking_to_the_same_campaign_updates_similarity_only(session):
    number = await make_number(session)
    campaign = Campaign(name="c", type="BANK", fingerprint=["BANK"])
    session.add(campaign)
    await session.flush()
    await assign_number(session, number, campaign.id, 0.7)
    stamp = number.updated_at
    await assign_number(session, number, campaign.id, 0.9)
    links = (await session.scalars(select(CampaignNumber))).all()
    assert len(links) == 1 and links[0].similarity_score == 0.9
    assert number.updated_at == stamp  # nothing sync-visible changed


async def test_detaching_a_free_number_is_a_no_op(session):
    number = await make_number(session)
    stamp = number.updated_at
    await detach_number(session, number)
    assert number.campaign_id is None and number.updated_at == stamp


async def test_restored_number_rejoins_its_campaign(session):
    """Moderation mistake undone: the number must go back to the campaign on the next job run."""
    devices = await make_devices(session, 6)
    await session.commit()
    phones = [phone(), phone(), phone()]
    for i, p in enumerate(phones):
        for dev in devices[i * 2 : i * 2 + 2]:
            await submit_report(session, dev, p, "BANK", ["OTP", "URGENCY"])
    campaign = (await session.scalars(select(Campaign))).one()
    first = await session.scalar(select(Number).where(Number.phone == phones[0]))

    first.is_removed = True
    await session.commit()
    await recalculate_all(session)
    assert first.campaign_id is None

    first.is_removed = False
    await session.commit()
    await recalculate_all(session)
    assert first.campaign_id == campaign.id
    await session.refresh(campaign)
    assert campaign.numbers_count == 3
