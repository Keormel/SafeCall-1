"""scripts/seed.py prepares the demo data."""

import pytest
from sqlalchemy import func, select

from app.models import Campaign, Number, RiskLevel
from scripts.seed import seed


async def _counts(session):
    session.expire_all()
    return (
        await session.scalar(select(func.count(Number.id))),
        await session.scalar(select(func.count(Campaign.id))),
    )


async def test_seed_creates_numbers_and_three_campaigns(session):
    await seed(reset_first=True, seed_value=42)
    numbers, campaigns = await _counts(session)
    assert 85 <= numbers <= 100  # ~100: 90 stored + 10 printed unknowns
    assert campaigns == 3
    for campaign in (await session.scalars(select(Campaign))).all():
        assert 3 <= campaign.numbers_count <= 5, campaign.name
    names = {c.name for c in (await session.scalars(select(Campaign))).all()}
    assert any(n.startswith("Bank impersonation + OTP") for n in names)
    assert any(n.startswith("Police impersonation") and "TRANSFER" in n for n in names)
    assert any(n.startswith("Fake delivery") and "CARD_DATA" in n for n in names)
    levels = {lvl for (lvl,) in (await session.execute(select(Number.risk_level))).all()}
    assert {RiskLevel.LOW.value, RiskLevel.MEDIUM.value, RiskLevel.HIGH.value} <= levels


async def test_seed_does_not_duplicate_on_rerun(session):
    await seed(reset_first=True, seed_value=42)
    before = await _counts(session)
    with pytest.raises(SystemExit):
        await seed(reset_first=False, seed_value=42)
    assert await _counts(session) == before


async def test_seed_with_reset_is_reproducible(session):
    await seed(reset_first=True, seed_value=42)
    first = sorted((await session.scalars(select(Number.phone))).all())
    await seed(reset_first=True, seed_value=42)
    session.expire_all()
    assert sorted((await session.scalars(select(Number.phone))).all()) == first
