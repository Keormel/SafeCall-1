import uuid

import pytest
from sqlalchemy import select

from app.models import Campaign, Device, Number, RiskLevel
from app.services.campaign_engine import (
    best_campaign_match,
    cluster_numbers,
    campaign_name,
    dominant_fingerprint,
    is_campaign_eligible,
    jaccard,
)
from app.services.report_service import submit_report

BANK_OTP = frozenset({"BANK", "OTP", "URGENCY"})


def test_jaccard():
    assert jaccard({"A", "B"}, {"A", "B"}) == 1.0
    assert jaccard({"A", "B"}, {"C"}) == 0.0
    assert jaccard({"A", "B", "C"}, {"A", "B"}) == pytest.approx(2 / 3)
    assert jaccard(set(), set()) == 0.0


def test_match_requires_two_independent_reporters():
    campaigns = [(1, BANK_OTP)]
    one = [("d1", BANK_OTP)]
    assert best_campaign_match(one, campaigns) is None
    same_device_twice = [("d1", BANK_OTP), ("d1", BANK_OTP)]
    assert best_campaign_match(same_device_twice, campaigns) is None
    two = [("d1", BANK_OTP), ("d2", frozenset({"BANK", "OTP", "URGENCY", "CARD_DATA"}))]
    match = best_campaign_match(two, campaigns)
    assert match is not None
    assert match.campaign_id == 1
    assert match.supporting_reporters == 2


def test_match_ignores_dissimilar_reports():
    reports = [("d1", frozenset({"BANK", "OTP"})), ("d2", frozenset({"POLICE", "THREAT"}))]
    assert best_campaign_match(reports, [(1, BANK_OTP)]) is None


def test_dominant_fingerprint():
    assert dominant_fingerprint([("d1", BANK_OTP)]) is None
    assert dominant_fingerprint([("d1", BANK_OTP), ("d2", BANK_OTP), ("d3", frozenset({"POLICE"}))]) == BANK_OTP


def test_other_without_actions_is_not_campaign_eligible():
    generic = frozenset({"OTHER"})
    assert not is_campaign_eligible(generic)
    assert is_campaign_eligible(frozenset({"OTHER", "URGENCY"}))
    assert dominant_fingerprint([("d1", generic), ("d2", generic)]) is None
    assert cluster_numbers([(1, generic), (2, generic), (3, generic)]) == []
    assert best_campaign_match(
        [("d1", generic), ("d2", generic)],
        [(1, generic)],
    ) is None


def test_cluster_needs_three_numbers():
    two = [(1, BANK_OTP), (2, BANK_OTP)]
    assert cluster_numbers(two) == []
    three = two + [(3, frozenset({"BANK", "OTP", "URGENCY", "TRANSFER"})), (4, frozenset({"POLICE", "THREAT"}))]
    clusters = cluster_numbers(three)
    assert len(clusters) == 1
    assert {nid for nid, _ in clusters[0].members} == {1, 2, 3}
    assert clusters[0].fingerprint == BANK_OTP


def test_campaign_name():
    assert campaign_name(["BANK", "OTP"]) == "Bank impersonation + OTP"
    assert campaign_name(["POLICE"]) == "Police impersonation"


async def _devices(session, n):
    devices = [Device(id=uuid.uuid4()) for _ in range(n)]
    session.add_all(devices)
    await session.commit()
    return devices


async def test_campaign_created_from_three_similar_numbers(session):
    devices = await _devices(session, 6)
    phones = ["+37369100001", "+37369100002", "+37369100003"]
    for i, phone in enumerate(phones):
        for dev in devices[i * 2 : i * 2 + 2]:
            await submit_report(session, dev, phone, "BANK", ["OTP", "URGENCY"])

    campaigns = (await session.scalars(select(Campaign))).all()
    assert len(campaigns) == 1
    campaign = campaigns[0]
    assert campaign.type == "BANK"
    assert set(campaign.fingerprint) == BANK_OTP
    assert campaign.numbers_count == 3
    numbers = (await session.scalars(select(Number))).all()
    assert all(n.campaign_id == campaign.id for n in numbers)


async def test_new_number_joins_existing_campaign_only_after_two_reports(session):
    devices = await _devices(session, 8)
    for i, phone in enumerate(["+37369100001", "+37369100002", "+37369100003"]):
        for dev in devices[i * 2 : i * 2 + 2]:
            await submit_report(session, dev, phone, "BANK", ["OTP", "URGENCY"])
    campaign = (await session.scalars(select(Campaign))).one()

    new_phone = "+37368555555"
    number = await submit_report(session, devices[6], new_phone, "BANK", ["OTP", "URGENCY"])
    assert number.campaign_id is None
    assert number.risk_level == RiskLevel.LOW.value

    number = await submit_report(session, devices[7], new_phone, "BANK", ["OTP", "URGENCY"])
    assert number.campaign_id == campaign.id
    assert number.risk_level == RiskLevel.MEDIUM.value  # capped: only 2 reporters

    await session.refresh(campaign)
    assert campaign.numbers_count == 4
