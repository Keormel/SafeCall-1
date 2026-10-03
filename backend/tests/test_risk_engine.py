import uuid

import pytest

from app.models import Device, Feedback, Number, Report, RiskLevel
from app.services.risk_engine import (
    FEEDBACK_CORRECT_DELTA,
    FEEDBACK_INCORRECT_DELTA,
    MAX_REPUTATION,
    MIN_REPUTATION,
    ReportSignal,
    apply_feedback_to_reporters,
    campaign_points,
    level_for_score,
    recalculate_device_reputations,
    reporters_points,
    score_number,
    similarity_points,
)


def signals(n: int, category: str = "BANK", actions: tuple[str, ...] = ("OTP",), reputation: float = 1.0):
    return [ReportSignal(f"dev-{i}", category, actions, reputation) for i in range(n)]


def test_no_data_is_unknown():
    result = score_number([], None)
    assert result.level == RiskLevel.UNKNOWN
    assert result.score == 0


@pytest.mark.parametrize(
    ("count", "points"),
    [(0, 0), (1, 10), (2, 10), (3, 20), (5, 20), (6, 30), (10, 30), (11, 40), (50, 40)],
)
def test_reporters_points_bands(count, points):
    assert reporters_points(count) == points


@pytest.mark.parametrize(
    ("score", "level"),
    [(0, RiskLevel.LOW), (29, RiskLevel.LOW), (30, RiskLevel.MEDIUM), (59, RiskLevel.MEDIUM), (60, RiskLevel.HIGH), (100, RiskLevel.HIGH)],
)
def test_level_thresholds(score, level):
    assert level_for_score(score) == level


def test_single_report_is_low():
    result = score_number(signals(1))
    assert result.level == RiskLevel.LOW
    assert result.score == 10


def test_similarity_needs_two_reports_and_scales():
    assert similarity_points(signals(1)) == 0
    assert similarity_points(signals(4)) == 20
    mixed = signals(2) + [ReportSignal("x", "POLICE", ("THREAT",)), ReportSignal("y", "DELIVERY", ())]
    assert similarity_points(mixed) == 10


def test_campaign_points_proportional():
    assert campaign_points(None) == 0
    assert campaign_points(0) == 0
    assert campaign_points(50) == 15
    assert campaign_points(100) == 30
    assert campaign_points(250) == 30


def test_two_similar_reports_medium():
    result = score_number(signals(2))
    assert result.score == 30
    assert result.level == RiskLevel.MEDIUM


def test_many_similar_reports_high():
    result = score_number(signals(11))
    assert result.score == 60
    assert result.level == RiskLevel.HIGH


def test_anti_abuse_caps_at_medium_below_three_reporters():
    # 2 reporters + strong campaign would be 10 + 20 + 30 = 60 (HIGH) without the cap.
    result = score_number(signals(2), campaign_risk_score=100)
    assert result.unique_reporters == 2
    assert result.level == RiskLevel.MEDIUM
    assert result.score == 59


def test_three_reporters_in_campaign_can_be_high():
    result = score_number(signals(3), campaign_risk_score=100)
    assert result.score == 70
    assert result.level == RiskLevel.HIGH


def test_same_device_counts_once():
    spam = [ReportSignal("same", "BANK", ("OTP",)) for _ in range(20)]
    result = score_number(spam)
    assert result.unique_reporters == 1
    assert result.level == RiskLevel.LOW


def test_reputation_weights_reports():
    # 3 low-reputation devices count like 1.5 reporters -> 1-2 band.
    assert score_number(signals(3, reputation=0.5)).breakdown["reporters"] == 10
    # Banned devices (reputation 0) are ignored entirely.
    banned = score_number(signals(5, reputation=0.0))
    assert banned.level == RiskLevel.UNKNOWN
    # High-reputation devices count more (capped at 2x).
    assert score_number(signals(3, reputation=5.0)).breakdown["reporters"] == 30


def test_campaign_only_number_is_scored():
    result = score_number([], campaign_risk_score=80)
    assert result.level == RiskLevel.LOW
    assert result.score == 24


async def test_apply_feedback_to_reporters_unit(session):
    dev1 = Device(id=uuid.uuid4(), reputation=1.0)
    dev2 = Device(id=uuid.uuid4(), reputation=1.0)
    session.add_all([dev1, dev2])
    await session.commit()

    num = Number(phone="+37369999001", risk_level=RiskLevel.LOW.value, risk_score=10)
    session.add(num)
    await session.commit()

    from datetime import date
    r1 = Report(number_id=num.id, device_id=dev1.id, category="BANK", actions=["OTP"], report_day=date.today())
    r2 = Report(number_id=num.id, device_id=dev2.id, category="BANK", actions=["OTP"], report_day=date.today())
    session.add_all([r1, r2])
    await session.commit()

    # Positive feedback
    updated = await apply_feedback_to_reporters(session, num.id, was_correct=True)
    assert len(updated) == 2
    assert dev1.reputation == 1.1
    assert dev2.reputation == 1.1

    # Reversal to negative
    updated = await apply_feedback_to_reporters(session, num.id, was_correct=False, revert_was_correct=True)
    assert len(updated) == 2
    assert dev1.reputation == 0.8
    assert dev2.reputation == 0.8

    # Feedback from banned device is ignored
    updated = await apply_feedback_to_reporters(session, num.id, was_correct=True, feedback_device_reputation=0.0)
    assert updated == []
    assert dev1.reputation == 0.8


async def test_recalculate_device_reputations_unit(session):
    from datetime import date
    dev1 = Device(id=uuid.uuid4(), reputation=1.0)
    dev2 = Device(id=uuid.uuid4(), reputation=1.0)
    reviewer = Device(id=uuid.uuid4(), reputation=1.0)
    session.add_all([dev1, dev2, reviewer])
    await session.commit()

    num = Number(phone="+37369999002", risk_level=RiskLevel.LOW.value, risk_score=10)
    session.add(num)
    await session.commit()

    r1 = Report(number_id=num.id, device_id=dev1.id, category="BANK", actions=["OTP"], report_day=date.today())
    session.add(r1)
    fb1 = Feedback(device_id=reviewer.id, number_id=num.id, was_correct=True)
    session.add(fb1)
    await session.commit()

    changed = await recalculate_device_reputations(session)
    assert changed == 1
    assert dev1.reputation == 1.1
    assert dev2.reputation == 1.0
