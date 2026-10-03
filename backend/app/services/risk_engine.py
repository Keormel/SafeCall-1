"""Rule-based risk scoring. `score_number` is a pure function; `recalculate_number` wires it to the DB."""

import uuid
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Campaign, Device, Feedback, Number, Report, RiskLevel, utcnow

LOW_MAX = 29
MEDIUM_MAX = 59
MIN_REPORTERS_FOR_HIGH = 3
MIN_REPUTATION = 0.0
MAX_REPUTATION = 2.0
FEEDBACK_CORRECT_DELTA = 0.1
FEEDBACK_INCORRECT_DELTA = 0.2

# A vote that has decayed below this weight no longer counts (≈ 1 year with the defaults).
MIN_VOTE_WEIGHT = 0.1
DEFAULT_GRACE_DAYS = 30
DEFAULT_HALF_LIFE_DAYS = 90

REPORTERS_MAX_POINTS = 40
SIMILARITY_MAX_POINTS = 20
CAMPAIGN_MAX_POINTS = 30


@dataclass(frozen=True)
class ReportSignal:
    device_id: str
    category: str
    actions: tuple[str, ...] = ()
    reputation: float = 1.0
    age_days: float = 0.0


@dataclass(frozen=True)
class RiskResult:
    score: int
    level: RiskLevel
    unique_reporters: int
    breakdown: dict[str, int] = field(default_factory=dict)


def decay_weight(
    age_days: float, grace_days: float = DEFAULT_GRACE_DAYS, half_life_days: float = DEFAULT_HALF_LIFE_DAYS
) -> float:
    """1.0 while fresh, then halves every `half_life_days`, so old complaints fade out."""
    if age_days <= grace_days:
        return 1.0
    return 0.5 ** ((age_days - grace_days) / half_life_days)


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


def score_number(
    signals: list[ReportSignal],
    campaign_risk_score: float | None = None,
    grace_days: float = DEFAULT_GRACE_DAYS,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> RiskResult:
    # One vote per device: keep the latest signal of each reporter.
    per_device: dict[str, ReportSignal] = {}
    for s in signals:
        per_device[s.device_id] = s
    # A vote's weight = device reputation (clamped) × how fresh the report is.
    votes = [
        ReportSignal(
            s.device_id,
            s.category,
            s.actions,
            min(max(s.reputation, 0.0), MAX_REPUTATION) * decay_weight(s.age_days, grace_days, half_life_days),
            s.age_days,
        )
        for s in per_device.values()
    ]
    trusted = [v for v in votes if v.reputation >= MIN_VOTE_WEIGHT]
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
        select(Report.device_id, Report.category, Report.actions, Device.reputation, Report.created_at)
        .join(Device, Device.id == Report.device_id)
        .where(Report.number_id == number_id)
        .order_by(Report.created_at, Report.id)
    )
    now = utcnow()
    return [
        ReportSignal(str(d), c, tuple(a or ()), float(r), (now - created).total_seconds() / 86400)
        for d, c, a, r, created in rows.all()
    ]


def _apply_result(number: Number, signals: list[ReportSignal], campaign_risk: float | None) -> bool:
    settings = get_settings()
    result = score_number(signals, campaign_risk, settings.report_grace_days, settings.report_half_life_days)
    number.reports_count = len(signals)
    number.unique_reporters_count = len({s.device_id for s in signals})
    changed = number.risk_score != result.score or number.risk_level != result.level.value
    if changed:
        number.risk_score = result.score
        number.risk_level = result.level.value
        number.updated_at = utcnow()
    return changed


BATCH_SIZE = 500


async def recalculate_numbers(session: AsyncSession, numbers: list[Number]) -> int:
    """Batched `recalculate_number`: two queries per 500 numbers instead of two per number."""
    campaign_risk = dict((await session.execute(select(Campaign.id, Campaign.risk_score))).all())
    now = utcnow()
    changed = 0
    for start in range(0, len(numbers), BATCH_SIZE):
        chunk = numbers[start : start + BATCH_SIZE]
        signals: dict[int, list[ReportSignal]] = {n.id: [] for n in chunk}
        rows = await session.execute(
            select(Report.number_id, Report.device_id, Report.category, Report.actions, Device.reputation, Report.created_at)
            .join(Device, Device.id == Report.device_id)
            .where(Report.number_id.in_(list(signals)))
            .order_by(Report.created_at, Report.id)
        )
        for nid, d, c, a, r, created in rows.all():
            signals[nid].append(ReportSignal(str(d), c, tuple(a or ()), float(r), (now - created).total_seconds() / 86400))
        for number in chunk:
            risk = campaign_risk.get(number.campaign_id) if number.campaign_id is not None else None
            changed += _apply_result(number, signals[number.id], float(risk) if risk is not None else None)
    return changed


async def recalculate_number(session: AsyncSession, number: Number) -> bool:
    """Recompute counters and risk; bump updated_at only when sync-visible fields change."""
    signals = await load_signals(session, number.id)
    campaign_risk: float | None = None
    if number.campaign_id is not None:
        campaign = await session.get(Campaign, number.campaign_id)
        campaign_risk = float(campaign.risk_score) if campaign else None

    return _apply_result(number, signals, campaign_risk)


async def apply_feedback_to_reporters(
    session: AsyncSession,
    number_id: int,
    was_correct: bool,
    feedback_device_reputation: float = 1.0,
    revert_was_correct: bool | None = None,
) -> list[Device]:
    """Adjust reputation of devices that reported this number based on user feedback.

    - Confirmed correct warning -> +0.1 reputation (up to 2.0).
    - False positive warning -> -0.2 reputation (down to 0.0).
    - Feedback from banned devices (reputation <= 0) is ignored.
    """
    if feedback_device_reputation <= 0.0:
        return []

    if revert_was_correct is not None:
        prev_delta = FEEDBACK_CORRECT_DELTA if revert_was_correct else -FEEDBACK_INCORRECT_DELTA
        new_delta = FEEDBACK_CORRECT_DELTA if was_correct else -FEEDBACK_INCORRECT_DELTA
        delta = new_delta - prev_delta
    else:
        delta = FEEDBACK_CORRECT_DELTA if was_correct else -FEEDBACK_INCORRECT_DELTA

    if delta == 0.0:
        return []

    reporter_ids = (
        await session.scalars(
            select(Report.device_id).where(Report.number_id == number_id).distinct()
        )
    ).all()

    updated: list[Device] = []
    for rep_id in reporter_ids:
        rep_device = await session.get(Device, rep_id)
        if rep_device is not None:
            new_rep = round(min(max(rep_device.reputation + delta, MIN_REPUTATION), MAX_REPUTATION), 2)
            if rep_device.reputation != new_rep:
                rep_device.reputation = new_rep
                updated.append(rep_device)
    return updated


async def recalculate_device_reputations(session: AsyncSession) -> int:
    """Recalculate reputation for all devices based on accumulated feedback on their reported numbers."""
    stmt = (
        select(
            Report.device_id,
            Feedback.was_correct,
            func.count(func.distinct(Feedback.id)),
        )
        .join(Feedback, Feedback.number_id == Report.number_id)
        .join(Device, Device.id == Feedback.device_id)
        .where(Device.reputation > 0)
        .group_by(Report.device_id, Feedback.was_correct)
    )
    rows = (await session.execute(stmt)).all()

    deltas: dict[uuid.UUID, float] = {}
    for dev_id, was_correct, count in rows:
        d = count * FEEDBACK_CORRECT_DELTA if was_correct else -count * FEEDBACK_INCORRECT_DELTA
        deltas[dev_id] = deltas.get(dev_id, 0.0) + d

    devices = (await session.scalars(select(Device))).all()
    changed = 0
    for dev in devices:
        new_rep = round(min(max(1.0 + deltas.get(dev.id, 0.0), MIN_REPUTATION), MAX_REPUTATION), 2)
        if dev.reputation != new_rep:
            dev.reputation = new_rep
            changed += 1
    return changed
