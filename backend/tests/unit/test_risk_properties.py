"""Property-based checks of the Risk Engine (Hypothesis, fixed seed via derandomize)."""

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.models import RiskLevel
from app.services.fingerprint import Action, Category
from app.services.risk_engine import ReportSignal, score_number

CATEGORIES = [c.value for c in Category]
ACTIONS = [a.value for a in Action]

signal = st.builds(
    ReportSignal,
    device_id=st.text(alphabet="abcdef0123456789", min_size=1, max_size=6),
    category=st.sampled_from(CATEGORIES),
    actions=st.lists(st.sampled_from(ACTIONS), max_size=3, unique=True).map(tuple),
    reputation=st.floats(min_value=0, max_value=3, allow_nan=False),
    age_days=st.floats(min_value=0, max_value=800, allow_nan=False),
)
campaign = st.one_of(st.none(), st.floats(min_value=-50, max_value=200, allow_nan=False))
COMMON = settings(max_examples=300, derandomize=True, suppress_health_check=[HealthCheck.too_slow], deadline=None)


@COMMON
@given(st.lists(signal, max_size=40), campaign)
def test_score_is_always_0_to_100_and_level_matches(signals, campaign_risk):
    """Clients and thresholds assume 0..100; a score outside it breaks the level mapping."""
    result = score_number(signals, campaign_risk)
    assert 0 <= result.score <= 100
    if result.level != RiskLevel.UNKNOWN:
        expected = RiskLevel.LOW if result.score <= 29 else RiskLevel.MEDIUM if result.score <= 59 else RiskLevel.HIGH
        assert result.level == expected


@COMMON
@given(st.lists(signal, max_size=40), campaign)
def test_score_is_deterministic(signals, campaign_risk):
    """The same data must always give the same verdict (sync deltas depend on it)."""
    assert score_number(signals, campaign_risk) == score_number(list(signals), campaign_risk)


@COMMON
@given(st.lists(signal, max_size=40), campaign)
def test_fewer_than_three_reporters_never_high(signals, campaign_risk):
    """Rule 4: one or two people (or one person with many reports) cannot brand a number dangerous."""
    devices = {s.device_id for s in signals}
    if len(devices) < 3:
        assert score_number(signals, campaign_risk).level != RiskLevel.HIGH


@COMMON
@given(st.integers(min_value=1, max_value=1000))
def test_many_reports_from_two_devices_never_high(n):
    """Rule 4 under spam: 1000 reports from 2 devices still count as 2 reporters."""
    spam = [ReportSignal(f"dev-{i % 2}", "BANK", ("OTP",)) for i in range(n)]
    assert score_number(spam, campaign_risk_score=100).level != RiskLevel.HIGH


dead_signal = st.builds(
    ReportSignal,
    device_id=st.text(alphabet="abcdef", min_size=1, max_size=4),
    category=st.sampled_from(CATEGORIES),
    actions=st.lists(st.sampled_from(ACTIONS), max_size=3, unique=True).map(tuple),
    reputation=st.one_of(st.just(0.0), st.floats(min_value=0.5, max_value=2)),
    age_days=st.floats(min_value=0, max_value=800),
).filter(lambda s: s.reputation == 0.0 or s.age_days >= 500)  # 2.0 x 0.5^(470/90) < 0.1


@COMMON
@given(st.lists(dead_signal, max_size=30))
def test_no_usable_reports_and_no_campaign_is_unknown_never_low(signals):
    """Rule 1: banned devices and fully decayed reports are not data. Such a number is UNKNOWN, never LOW."""
    result = score_number(signals, None)
    assert result.level == RiskLevel.UNKNOWN
    assert result.score == 0


@COMMON
@given(
    st.lists(signal, min_size=0, max_size=20),
    st.sampled_from(CATEGORIES),
    st.lists(st.sampled_from(ACTIONS), max_size=3, unique=True).map(tuple),
    campaign,
)
@pytest.mark.xfail(
    strict=True,
    reason="BUG: a new, dissimilar unique report lowers the similarity share, so risk can go DOWN "
    "(3 identical reports = 40, add a 4th different one = 35). Rule: more independent reports never "
    "reduce risk. Fix: never let similarity points drop below their value before the new report, or "
    "score similarity on the dominant cluster size instead of its share.",
)
def test_new_unique_report_never_lowers_risk(signals, category, actions, campaign_risk):
    before = score_number(signals, campaign_risk)
    newcomer = ReportSignal("brand-new-device", category, actions, 1.0, 0.0)
    after = score_number([*signals, newcomer], campaign_risk)
    assert after.score >= before.score


def test_monotonicity_counterexample_is_concrete():
    """The minimal case behind the xfail above, spelled out (documents the bug, passes today)."""
    same = [ReportSignal(f"d{i}", "BANK", ("OTP",)) for i in range(3)]
    assert score_number(same).score == 40
    assert score_number([*same, ReportSignal("d4", "POLICE", ("THREAT",))]).score == 35
