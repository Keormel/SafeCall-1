"""Groups numbers into fraud campaigns by fingerprint similarity (Jaccard over tag sets)."""

import logging
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Campaign, CampaignNumber, Number, Report, utcnow
from app.services.fingerprint import ACTION_TAGS, CATEGORY_TAGS, Action, Category

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.7
MIN_INDEPENDENT_REPORTS = 2
MIN_NUMBERS_FOR_CAMPAIGN = 3
MIN_NUMBERS_TO_KEEP = 2  # below this a campaign is dissolved
# Arbitrary app-wide key for pg_advisory_xact_lock: serializes campaign creation/merging.
CAMPAIGN_LOCK_KEY = 7_303_211
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


def is_campaign_eligible(fingerprint: Iterable[str]) -> bool:
    """Generic "other" complaints need at least one concrete action to form a pattern."""
    tags = set(fingerprint)
    return not (Category.OTHER.value in tags and not ACTION_TAGS.intersection(tags))


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
        if not is_campaign_eligible(campaign_fp):
            continue
        sims_by_device: dict[str, float] = {}
        for device_id, fp in reports:
            if not is_campaign_eligible(fp):
                continue
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
    for candidate in {fp for _, fp in reports if fp and is_campaign_eligible(fp)}:
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
    candidates = [(nid, fp) for nid, fp in candidates if is_campaign_eligible(fp)]
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


def plan_merges(
    campaigns: list[tuple[int, int, frozenset[str]]], threshold: float = SIMILARITY_THRESHOLD
) -> dict[int, int]:
    """(id, numbers_count, fingerprint) → {absorbed_id: keeper_id} for campaigns describing one scheme.

    The bigger campaign (then the older one) survives, so ids clients already saw stay stable.
    """
    ordered = sorted(campaigns, key=lambda c: (-c[1], c[0]))
    merges: dict[int, int] = {}
    for i, (keeper_id, _, keeper_fp) in enumerate(ordered):
        if keeper_id in merges:
            continue
        for other_id, _, other_fp in ordered[i + 1 :]:
            if other_id not in merges and jaccard(keeper_fp, other_fp) >= threshold:
                merges[other_id] = keeper_id
    return merges


# ---------------------------------------------------------------- DB layer


async def lock_campaigns(session: AsyncSession) -> None:
    """Serialize campaign creation/merging between concurrent requests and the job.

    Postgres: a transaction-scoped advisory lock, released on commit/rollback. Once acquired, later
    statements see campaigns committed by whoever held it, so two simultaneous reports cannot create
    two copies of one campaign. SQLite (tests/dev) serializes writers by itself.
    """
    conn = await session.connection()
    if conn.dialect.name == "postgresql":
        await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": CAMPAIGN_LOCK_KEY})


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


async def _fingerprints_by_number(session: AsyncSession, number_ids: list[int]) -> dict[int, ReportFingerprints]:
    """All report fingerprints for many numbers in one query (instead of one query per number)."""
    out: dict[int, ReportFingerprints] = {nid: [] for nid in number_ids}
    if not number_ids:
        return out
    rows = await session.execute(
        select(Report.number_id, Report.device_id, Report.fingerprint).where(Report.number_id.in_(number_ids))
    )
    for nid, device_id, fp in rows.all():
        out[nid].append((str(device_id), frozenset(fp or ())))
    return out


async def discover_campaigns(session: AsyncSession) -> list[Campaign]:
    """Match unassigned numbers to known campaigns, then cluster the rest into new campaigns."""
    await lock_campaigns(session)
    numbers = (
        await session.scalars(
            select(Number).where(
                Number.campaign_id.is_(None),
                Number.is_removed.is_(False),
                Number.reports_count >= MIN_INDEPENDENT_REPORTS,
            )
        )
    ).all()
    fingerprints = await _fingerprints_by_number(session, [n.id for n in numbers])
    known = await _campaign_fingerprints(session)

    candidates: list[tuple[int, frozenset[str]]] = []
    by_id: dict[int, Number] = {}
    touched: set[int] = set()
    for number in numbers:
        reports = fingerprints[number.id]
        match = best_campaign_match(reports, known)
        if match is not None:
            await assign_number(session, number, match.campaign_id, match.similarity)
            touched.add(match.campaign_id)
            continue
        fp = dominant_fingerprint(reports)
        if fp is not None:
            candidates.append((number.id, fp))
            by_id[number.id] = number
    for campaign_id in touched:
        campaign = await session.get(Campaign, campaign_id)
        if campaign is not None:
            await refresh_campaign(session, campaign)

    created: list[Campaign] = []
    for cluster in cluster_numbers(candidates):
        tags = sorted(cluster.fingerprint)
        campaign = Campaign(name=campaign_name(tags), type=campaign_type(tags), fingerprint=tags)
        session.add(campaign)
        await session.flush()
        for number_id, similarity in cluster.members:
            await assign_number(session, by_id[number_id], campaign.id, similarity)
        await refresh_campaign(session, campaign)
        created.append(campaign)
        logger.info("Created campaign #%s '%s' with %s numbers", campaign.id, campaign.name, len(cluster.members))
    return created


async def detach_number(session: AsyncSession, number: Number) -> None:
    if number.campaign_id is None:
        return
    await session.execute(
        delete(CampaignNumber).where(
            CampaignNumber.campaign_id == number.campaign_id, CampaignNumber.number_id == number.id
        )
    )
    number.campaign_id = None
    number.updated_at = utcnow()


@dataclass(frozen=True)
class MaintenanceResult:
    detached: int
    merged: int
    dissolved: int
    released_number_ids: frozenset[int] = frozenset()  # numbers left without a campaign


async def maintain_campaigns(session: AsyncSession) -> MaintenanceResult:
    """Keep campaigns honest: drop moderated numbers, merge duplicates, dissolve leftovers."""
    await lock_campaigns(session)

    # 1. Numbers removed by moderation leave their campaign.
    removed = (
        await session.scalars(select(Number).where(Number.campaign_id.is_not(None), Number.is_removed.is_(True)))
    ).all()
    released: set[int] = set()
    for number in removed:
        await detach_number(session, number)
        released.add(number.id)
    await session.flush()

    campaigns = (await session.scalars(select(Campaign))).all()
    for campaign in campaigns:
        await refresh_campaign(session, campaign)

    # 2. Campaigns that describe the same scheme (e.g. found in parallel) become one.
    merges = plan_merges([(c.id, c.numbers_count, frozenset(c.fingerprint or ())) for c in campaigns])
    by_id = {c.id: c for c in campaigns}
    for absorbed_id, keeper_id in merges.items():
        keeper_fp = frozenset(by_id[keeper_id].fingerprint or ())
        members = (await session.scalars(select(Number).where(Number.campaign_id == absorbed_id))).all()
        fingerprints = await _fingerprints_by_number(session, [n.id for n in members])
        for number in members:
            fp = dominant_fingerprint(fingerprints[number.id]) or frozenset()
            await detach_number(session, number)
            await assign_number(session, number, keeper_id, round(jaccard(fp, keeper_fp), 4))
        await session.delete(by_id[absorbed_id])
        logger.info("Merged campaign #%s into #%s", absorbed_id, keeper_id)
    await session.flush()

    # 3. A campaign left with fewer than 2 numbers is no longer a pattern.
    dissolved = 0
    for campaign in (await session.scalars(select(Campaign))).all():
        await refresh_campaign(session, campaign)
        if campaign.numbers_count >= MIN_NUMBERS_TO_KEEP:
            continue
        for number in (await session.scalars(select(Number).where(Number.campaign_id == campaign.id))).all():
            await detach_number(session, number)
            released.add(number.id)
        await session.execute(delete(CampaignNumber).where(CampaignNumber.campaign_id == campaign.id))
        await session.delete(campaign)
        dissolved += 1
        logger.info("Dissolved campaign #%s", campaign.id)
    await session.flush()
    return MaintenanceResult(
        detached=len(removed), merged=len(merges), dissolved=dissolved, released_number_ids=frozenset(released)
    )
