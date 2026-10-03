"""Groups numbers into fraud campaigns by fingerprint similarity (Jaccard over tag sets)."""

import logging
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Campaign, CampaignNumber, Number, Report, utcnow
from app.services.fingerprint import ACTION_TAGS, CATEGORY_TAGS, Action, Category

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.7
MIN_INDEPENDENT_REPORTS = 2
MIN_NUMBERS_FOR_CAMPAIGN = 3
DANGEROUS_TAGS = frozenset({Action.OTP, Action.CARD_DATA, Action.TRANSFER, Action.INSTALL_APP})

CATEGORY_TITLES = {
    Category.BANK: "Bank impersonation",
    Category.POLICE: "Police impersonation",
    Category.DELIVERY: "Fake delivery",
    Category.RELATIVE: "Relative in trouble",
    Category.INVESTMENT: "Investment scam",
    Category.OTHER: "Phone scam",
}

# (device_id, fingerprint) for every report on a number
ReportFingerprints = list[tuple[str, frozenset[str]]]


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)


@dataclass(frozen=True)
class Match:
    campaign_id: int
    similarity: float
    supporting_reporters: int


def best_campaign_match(
    reports: ReportFingerprints,
    campaigns: list[tuple[int, frozenset[str]]],
    threshold: float = SIMILARITY_THRESHOLD,
) -> Match | None:
    """A number joins a campaign only if >= 2 independent reporters describe a similar scheme."""
    best: Match | None = None
    for campaign_id, campaign_fp in campaigns:
        sims_by_device: dict[str, float] = {}
        for device_id, fp in reports:
            sim = jaccard(fp, campaign_fp)
            if sim >= threshold:
                sims_by_device[device_id] = max(sim, sims_by_device.get(device_id, 0.0))
        if len(sims_by_device) < MIN_INDEPENDENT_REPORTS:
            continue
        candidate = Match(
            campaign_id,
            round(sum(sims_by_device.values()) / len(sims_by_device), 4),
            len(sims_by_device),
        )
        if best is None or (candidate.supporting_reporters, candidate.similarity) > (
            best.supporting_reporters,
            best.similarity,
        ):
            best = candidate
    return best


def dominant_fingerprint(
    reports: ReportFingerprints, threshold: float = SIMILARITY_THRESHOLD
) -> frozenset[str] | None:
    """Fingerprint backed by the most independent reporters, or None if fewer than 2 agree."""
    best_fp: frozenset[str] | None = None
    best_key: tuple[int, int, int] = (0, 0, 0)
    for candidate in {fp for _, fp in reports if fp}:
        supporters = {d for d, fp in reports if jaccard(fp, candidate) >= threshold}
        exact = sum(1 for _, fp in reports if fp == candidate)
        key = (len(supporters), exact, len(candidate))
        if key > best_key:
            best_fp, best_key = candidate, key
    if best_fp is None or best_key[0] < MIN_INDEPENDENT_REPORTS:
        return None
    return best_fp


def consensus_fingerprint(fingerprints: list[frozenset[str]]) -> frozenset[str]:
    """Tags present in at least half of the member fingerprints."""
    counts: dict[str, int] = {}
    for fp in fingerprints:
        for tag in fp:
            counts[tag] = counts.get(tag, 0) + 1
    need = len(fingerprints) / 2
    return frozenset(tag for tag, n in counts.items() if n >= need)


@dataclass(frozen=True)
class Cluster:
    fingerprint: frozenset[str]
    members: list[tuple[int, float]]  # (number_id, similarity to the cluster fingerprint)


def cluster_numbers(
    candidates: list[tuple[int, frozenset[str]]],
    threshold: float = SIMILARITY_THRESHOLD,
    min_size: int = MIN_NUMBERS_FOR_CAMPAIGN,
) -> list[Cluster]:
    """Greedy clustering of unassigned numbers; clusters smaller than `min_size` are discarded."""
    remaining = sorted(candidates, key=lambda c: (-len(c[1]), c[0]))
    clusters: list[Cluster] = []
    while remaining:
        _, seed_fp = remaining[0]
        group = [c for c in remaining if jaccard(c[1], seed_fp) >= threshold]
        if len(group) < min_size:
            remaining = remaining[1:]
            continue
        fp = consensus_fingerprint([g[1] for g in group]) or seed_fp
        members = [(nid, round(jaccard(nfp, fp), 4)) for nid, nfp in group]
        clusters.append(Cluster(fp, members))
        taken = {nid for nid, _ in group}
        remaining = [c for c in remaining if c[0] not in taken]
    return clusters


def campaign_type(fingerprint: Iterable[str]) -> str:
    cats = sorted(t for t in fingerprint if t in CATEGORY_TAGS)
    return cats[0] if cats else Category.OTHER.value


def campaign_name(fingerprint: Iterable[str]) -> str:
    fp = set(fingerprint)
    title = CATEGORY_TITLES[Category(campaign_type(fp))]
    actions = sorted(t for t in fp if t in ACTION_TAGS)
    return f"{title} + {', '.join(actions)}" if actions else title


def campaign_risk(numbers_count: int, reports_count: int, fingerprint: Iterable[str]) -> int:
    score = 40 + 8 * min(numbers_count, 5) + min(reports_count, 20)
    if DANGEROUS_TAGS & set(fingerprint):
        score += 10
    return min(score, 100)


# ---------------------------------------------------------------- DB layer


async def load_report_fingerprints(session: AsyncSession, number_id: int) -> ReportFingerprints:
    rows = await session.execute(
        select(Report.device_id, Report.fingerprint).where(Report.number_id == number_id)
    )
    return [(str(d), frozenset(fp or ())) for d, fp in rows.all()]


async def _campaign_fingerprints(session: AsyncSession) -> list[tuple[int, frozenset[str]]]:
    rows = await session.execute(select(Campaign.id, Campaign.fingerprint))
    return [(cid, frozenset(fp or ())) for cid, fp in rows.all()]


async def assign_number(session: AsyncSession, number: Number, campaign_id: int, similarity: float) -> None:
    link = await session.get(CampaignNumber, (campaign_id, number.id))
    if link is None:
        session.add(CampaignNumber(campaign_id=campaign_id, number_id=number.id, similarity_score=similarity))
    else:
        link.similarity_score = similarity
    if number.campaign_id != campaign_id:
        number.campaign_id = campaign_id
        number.updated_at = utcnow()
    await session.flush()


async def refresh_campaign(session: AsyncSession, campaign: Campaign) -> bool:
    numbers_count, reports_count = (
        await session.execute(
            select(func.count(Number.id), func.coalesce(func.sum(Number.reports_count), 0)).where(
                Number.campaign_id == campaign.id
            )
        )
    ).one()
    risk = campaign_risk(int(numbers_count), int(reports_count), campaign.fingerprint)
    changed = (campaign.numbers_count, campaign.reports_count, campaign.risk_score) != (
        numbers_count,
        reports_count,
        risk,
    )
    if changed:
        campaign.numbers_count = int(numbers_count)
        campaign.reports_count = int(reports_count)
        campaign.risk_score = risk
        campaign.updated_at = utcnow()
    return changed


async def match_number(session: AsyncSession, number: Number) -> Campaign | None:
    """Attach an unassigned number to the most similar existing campaign, if evidence allows."""
    if number.campaign_id is not None:
        return await session.get(Campaign, number.campaign_id)
    reports = await load_report_fingerprints(session, number.id)
    match = best_campaign_match(reports, await _campaign_fingerprints(session))
    if match is None:
        return None
    await assign_number(session, number, match.campaign_id, match.similarity)
    campaign = await session.get(Campaign, match.campaign_id)
    if campaign is not None:
        await refresh_campaign(session, campaign)
    return campaign


async def discover_campaigns(session: AsyncSession) -> list[Campaign]:
    """Match unassigned numbers to known campaigns, then cluster the rest into new campaigns."""
    numbers = (
        await session.scalars(
            select(Number).where(
                Number.campaign_id.is_(None),
                Number.is_removed.is_(False),
                Number.reports_count >= MIN_INDEPENDENT_REPORTS,
            )
        )
    ).all()

    candidates: list[tuple[int, frozenset[str]]] = []
    by_id: dict[int, Number] = {}
    for number in numbers:
        if await match_number(session, number) is not None:
            continue
        fp = dominant_fingerprint(await load_report_fingerprints(session, number.id))
        if fp is not None:
            candidates.append((number.id, fp))
            by_id[number.id] = number

    created: list[Campaign] = []
    for cluster in cluster_numbers(candidates):
        fp = sorted(cluster.fingerprint)
        campaign = Campaign(name=campaign_name(fp), type=campaign_type(fp), fingerprint=fp)
        session.add(campaign)
        await session.flush()
        for number_id, similarity in cluster.members:
            await assign_number(session, by_id[number_id], campaign.id, similarity)
        await refresh_campaign(session, campaign)
        created.append(campaign)
        logger.info("Created campaign #%s '%s' with %s numbers", campaign.id, campaign.name, len(cluster.members))
    return created
