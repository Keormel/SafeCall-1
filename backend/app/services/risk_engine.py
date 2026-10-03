"""Rule-based risk scoring. `score_number` is a pure function; `recalculate_number` wires it to the DB."""

from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Campaign, Device, Number, Report, RiskLevel, utcnow

LOW_MAX = 29
MEDIUM_MAX = 59
MIN_REPORTERS_FOR_HIGH = 3
MAX_REPUTATION = 2.0

REPORTERS_MAX_POINTS = 40
SIMILARITY_MAX_POINTS = 20
CAMPAIGN_MAX_POINTS = 30


@dataclass(frozen=True)
class ReportSignal:
    device_id: str
    category: str
    actions: tuple[str, ...] = ()
    reputation: float = 1.0


@dataclass(frozen=True)
class RiskResult:
    score: int
    level: RiskLevel
    unique_reporters: int
    breakdown: dict[str, int] = field(default_factory=dict)


def reporters_points(effective_reporters: float) -> int:
    """0 -> 0; 1-2 -> 10; 3-5 -> 20; 6-10 -> 30; >10 -> 40 (on reputation-weighted count)."""
    if effective_reporters <= 0:
        return 0
    if effective_reporters < 3:
        return 10
    if effective_reporters < 6:
        return 20
    if effective_reporters < 11:
        return 30
    return REPORTERS_MAX_POINTS


def similarity_points(signals: list[ReportSignal]) -> int:
    """Share (by weight) of reports with the same category + actions, scaled to 0..20. Needs >= 2 reports."""
    weighted = [s for s in signals if s.reputation > 0]
    if len(weighted) < 2:
        return 0
    buckets: Counter[tuple[str, tuple[str, ...]]] = Counter()
    for s in weighted:
        buckets[(s.category, tuple(sorted(set(s.actions))))] += s.reputation
    total = sum(buckets.values())
    if total <= 0:
        return 0
    return round(SIMILARITY_MAX_POINTS * max(buckets.values()) / total)


def campaign_points(campaign_risk_score: float | None) -> int:
    if campaign_risk_score is None:
        return 0
    clamped = min(max(campaign_risk_score, 0.0), 100.0)
    return round(CAMPAIGN_MAX_POINTS * clamped / 100)


def level_for_score(score: int) -> RiskLevel:
    if score <= LOW_MAX:
        return RiskLevel.LOW
    if score <= MEDIUM_MAX:
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH


def score_number(signals: list[ReportSignal], campaign_risk_score: float | None = None) -> RiskResult:
    # One vote per device: keep the latest signal of each reporter.
    per_device: dict[str, ReportSignal] = {}
    for s in signals:
        per_device[s.device_id] = s
    votes = [
        ReportSignal(s.device_id, s.category, s.actions, min(max(s.reputation, 0.0), MAX_REPUTATION))
        for s in per_device.values()
    ]
    trusted = [v for v in votes if v.reputation > 0]
    unique_reporters = len(trusted)

    if not trusted and campaign_risk_score is None:
        return RiskResult(0, RiskLevel.UNKNOWN, 0, {"reporters": 0, "similarity": 0, "campaign": 0})

    breakdown = {
        "reporters": reporters_points(sum(v.reputation for v in trusted)),
        "similarity": similarity_points(trusted),
        "campaign": campaign_points(campaign_risk_score),
    }
    score = min(sum(breakdown.values()), 100)
    level = level_for_score(score)

    # Anti-abuse: a couple of reports can never make a number HIGH.
    if unique_reporters < MIN_REPORTERS_FOR_HIGH and level == RiskLevel.HIGH:
        level = RiskLevel.MEDIUM
        score = MEDIUM_MAX
    return RiskResult(score, level, unique_reporters, breakdown)


async def load_signals(session: AsyncSession, number_id: int) -> list[ReportSignal]:
    rows = await session.execute(
        select(Report.device_id, Report.category, Report.actions, Device.reputation)
        .join(Device, Device.id == Report.device_id)
        .where(Report.number_id == number_id)
        .order_by(Report.created_at, Report.id)
    )
    return [ReportSignal(str(d), c, tuple(a or ()), float(r)) for d, c, a, r in rows.all()]


async def recalculate_number(session: AsyncSession, number: Number) -> bool:
    """Recompute counters and risk; bump updated_at only when sync-visible fields change."""
    signals = await load_signals(session, number.id)
    campaign_risk: float | None = None
    if number.campaign_id is not None:
        campaign = await session.get(Campaign, number.campaign_id)
        campaign_risk = float(campaign.risk_score) if campaign else None

    result = score_number(signals, campaign_risk)
    number.reports_count = len(signals)
    number.unique_reporters_count = len({s.device_id for s in signals})

    changed = number.risk_score != result.score or number.risk_level != result.level.value
    if changed:
        number.risk_score = result.score
        number.risk_level = result.level.value
        number.updated_at = utcnow()
    return changed
