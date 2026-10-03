import pytest

from app.models import RiskLevel
from app.services.risk_engine import (
    ReportSignal,
    campaign_points,
    level_for_score,
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
