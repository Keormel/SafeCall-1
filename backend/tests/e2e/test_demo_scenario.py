"""The defense demo, step by step, through the public API (same code as scripts/demo_e2e.py)."""

import pytest

from scripts.demo_e2e import DEMO_PHONE, run_demo
from scripts.seed import seed
from tests.conftest import ADMIN_KEY, admin_headers, auth_headers
from tests.factories import API, api_check, api_report


@pytest.fixture
async def seeded():
    await seed(reset_first=True, seed_value=42)


async def test_demo_passes_every_step(client, seeded):
    result = await run_demo(client, ADMIN_KEY, log=lambda _: None)
    assert result["demo"]["risk_level"] == "MEDIUM"
    assert result["sync_item"]["campaign_type"] == "BANK"


async def test_third_matching_reporter_makes_the_demo_number_high(client, seeded):
    """Rule 4 caps only while there are fewer than 3 reporters; the third lifts the cap."""
    await run_demo(client, ADMIN_KEY, log=lambda _: None)
    await api_report(client, await auth_headers(client), DEMO_PHONE, category="BANK", actions=("OTP", "URGENCY"))
    assert (await api_check(client, await auth_headers(client), DEMO_PHONE))["risk_level"] == "HIGH"


@pytest.mark.xfail(
    strict=True,
    reason="SPEC CONTRADICTION: the brief's demo sends 3 reports 'BANK + OTP + SUSPICIOUS_TRANSACTION' and expects "
    "(a) a link to 'Bank impersonation + OTP' and (b) MEDIUM 'because of anti-abuse'. But (a) the campaign "
    "fingerprint is {BANK, OTP, URGENCY}: Jaccard = 2/4 = 0.5 < 0.7, so rule 6 forbids the link; and (b) rule 4 "
    "caps only while reporters < 3, so 3 matching reporters plus a campaign give HIGH. scripts/demo_e2e.py uses "
    "2 reports with the campaign's own scheme instead.",
)
async def test_demo_as_written_in_the_brief(client, seeded):
    campaigns = (await client.get(f"{API}/campaigns", headers=await auth_headers(client))).json()["items"]
    bank = next(c for c in campaigns if c["name"].startswith("Bank impersonation + OTP"))
    for _ in range(3):
        await api_report(
            client, await auth_headers(client), DEMO_PHONE, category="BANK", actions=("OTP", "SUSPICIOUS_TRANSACTION")
        )
    await client.post(f"{API}/admin/recalculate", headers=await admin_headers(client))
    data = await api_check(client, await auth_headers(client), DEMO_PHONE)
    assert data["campaign_id"] == bank["id"]
    assert data["risk_level"] == "MEDIUM"

