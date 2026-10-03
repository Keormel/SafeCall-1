"""Campaign Engine rules (rule 6) and data invariants."""

import random

import pytest
from sqlalchemy import func, select

from app.jobs import recalculate_all, recalculate_incremental
from app.models import Campaign, CampaignNumber, Device, Number, Report
from app.services.campaign_engine import (
    best_campaign_match,
    cluster_numbers,
    jaccard,
    maintain_campaigns,
)
from app.services.report_service import submit_report
from tests.factories import make_devices, phone

# |A|=8, |B|=9, 7 shared → 7/10 = 0.70 exactly.
A70 = frozenset({"BANK", "OTP", "URGENCY", "CARD_DATA", "TRANSFER", "THREAT", "INSTALL_APP", "SUSPICIOUS_TRANSACTION"})
B70 = frozenset({"BANK", "OTP", "URGENCY", "CARD_DATA", "TRANSFER", "THREAT", "INSTALL_APP", "POLICE", "DELIVERY"})
# |A|=|B|=11, 9 shared → 9/13 ≈ 0.692.
ALL = A70 | B70 | {"RELATIVE", "INVESTMENT", "OTHER"}
A69 = frozenset(sorted(ALL)[:11])
B69 = frozenset(sorted(ALL)[2:])


def test_threshold_fixtures_are_what_they_claim():
    assert jaccard(A70, B70) == pytest.approx(0.70)
    assert jaccard(A69, B69) == pytest.approx(9 / 13)


def test_join_at_exactly_0_70():
    """Rule 6: similarity >= 0.7 joins; the boundary itself counts."""
    reports = [("d1", A70), ("d2", A70)]
    assert best_campaign_match(reports, [(1, B70)]) is not None


def test_no_join_at_0_69():
    reports = [("d1", A69), ("d2", A69)]
    assert best_campaign_match(reports, [(1, B69)]) is None


def test_join_needs_two_independent_devices():
    """Rule 6: one device reporting twice is not independent evidence."""
    fp = frozenset({"BANK", "OTP"})
    assert best_campaign_match([("d1", fp)], [(1, fp)]) is None
    assert best_campaign_match([("d1", fp), ("d1", fp)], [(1, fp)]) is None
    assert best_campaign_match([("d1", fp), ("d2", fp)], [(1, fp)]) is not None


def test_two_similar_numbers_do_not_make_a_campaign():
    fp = frozenset({"BANK", "OTP"})
    assert cluster_numbers([(1, fp), (2, fp)]) == []


def test_exactly_three_similar_numbers_make_a_campaign():
    fp = frozenset({"BANK", "OTP"})
    clusters = cluster_numbers([(1, fp), (2, fp), (3, fp)])
    assert len(clusters) == 1 and {n for n, _ in clusters[0].members} == {1, 2, 3}


async def _campaign_from_api_flow(session, actions=("OTP", "URGENCY"), category="BANK"):
    devices = await make_devices(session, 6)
    await session.commit()
    phones = [phone(), phone(), phone()]
    for i, p in enumerate(phones):
        for dev in devices[i * 2 : i * 2 + 2]:
            await submit_report(session, dev, p, category, list(actions))
    return phones


async def test_two_reported_numbers_create_no_campaign(session):
    devices = await make_devices(session, 4)
    await session.commit()
    for i, p in enumerate([phone(), phone()]):
        for dev in devices[i * 2 : i * 2 + 2]:
            await submit_report(session, dev, p, "BANK", ["OTP"])
    assert await session.scalar(select(func.count(Campaign.id))) == 0


async def test_recalculation_is_idempotent(session):
    """Running the jobs again must not create duplicate campaigns or move numbers."""
    await _campaign_from_api_flow(session)
    await recalculate_all(session)
    before = (await session.scalars(select(Campaign.id))).all()
    for _ in range(3):
        await recalculate_all(session)
        await recalculate_incremental(session)
    assert (await session.scalars(select(Campaign.id))).all() == before


async def _assert_invariants(session):
    numbers = (await session.scalars(select(Number))).all()
    links = (await session.scalars(select(CampaignNumber))).all()
    by_number: dict[int, list[int]] = {}
    for link in links:
        by_number.setdefault(link.number_id, []).append(link.campaign_id)
    for number in numbers:
        # A number is in at most one campaign, and its link agrees with numbers.campaign_id.
        assert len(by_number.get(number.id, [])) <= 1, number.phone
        assert by_number.get(number.id, [None])[0] == number.campaign_id, number.phone
        assert number.reports_count == await session.scalar(
            select(func.count(Report.id)).where(Report.number_id == number.id)
        )
    for campaign in (await session.scalars(select(Campaign))).all():
        members = [n for n in numbers if n.campaign_id == campaign.id]
        assert campaign.numbers_count == len(members), campaign.id
        assert campaign.reports_count == sum(n.reports_count for n in members), campaign.id


@pytest.mark.parametrize("seed", range(5))
async def test_counters_match_data_after_random_operations(session, seed):
    """Campaign counters drive the risk score; they must equal the real data after any operation mix."""
    rng = random.Random(seed)
    device_ids = [d.id for d in await make_devices(session, 25)]
    await session.commit()
    pool = [phone() for _ in range(8)]
    schemes = [("BANK", ["OTP", "URGENCY"]), ("POLICE", ["THREAT", "TRANSFER"]), ("DELIVERY", ["CARD_DATA"])]
    for _ in range(60):
        op = rng.random()
        if op < 0.75:
            category, actions = rng.choice(schemes)
            try:
                # A duplicate rolls the session back, so look the device up fresh each time.
                device = await session.get(Device, rng.choice(device_ids))
                await submit_report(session, device, rng.choice(pool), category, actions)
            except Exception as exc:  # same device + number + day is rejected by design
                assert getattr(exc, "code", "") == "DUPLICATE_REPORT"
        elif op < 0.85:
            numbers = (await session.scalars(select(Number))).all()
            if numbers:
                rng.choice(numbers).is_removed = True
                await session.commit()
        elif op < 0.95:
            await maintain_campaigns(session)
            await session.commit()
        else:
            await recalculate_all(session)
        await _assert_invariants(session)


@pytest.mark.xfail(
    strict=True,
    reason="BUG: reports with category OTHER and no actions have fingerprint ['OTHER']; three such numbers "
    "form a 'Phone scam' campaign (risk 70) and every member gains +21 points without any shared scheme. "
    "Fix: ignore fingerprints without action tags in matching and clustering.",
)
async def test_other_without_actions_never_forms_a_campaign(session):
    await _campaign_from_api_flow(session, actions=(), category="OTHER")
    assert await session.scalar(select(func.count(Campaign.id))) == 0
