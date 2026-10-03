"""Mass-reporting and whitewashing attempts."""

import random

import pytest

from app.models import RiskLevel
from tests.conftest import auth_headers
from tests.factories import API, api_check, api_report

BANK_HOTLINE = "+37322225555"  # stands for a legitimate bank number
SCHEMES = [
    ("BANK", ["OTP"]), ("POLICE", ["THREAT"]), ("DELIVERY", ["CARD_DATA"]), ("RELATIVE", ["TRANSFER"]),
    ("INVESTMENT", ["TRANSFER", "URGENCY"]), ("OTHER", []), ("BANK", ["INSTALL_APP"]), ("POLICE", ["TRANSFER", "THREAT"]),
    ("DELIVERY", ["OTP"]), ("RELATIVE", ["URGENCY"]), ("OTHER", ["SUSPICIOUS_TRANSACTION"]), ("BANK", ["CARD_DATA", "URGENCY"]),
]


async def test_fifty_uncoordinated_devices_do_not_make_a_number_high(client):
    """Random, dissimilar complaints (no shared scheme) are not evidence of fraud.

    Remaining risk: 50 reporters still give 40 points + some similarity → MEDIUM. A real bank
    number can be painted 'suspicious' by a crowd. Mitigation: an allowlist of verified
    organization numbers and device attestation (Play Integrity).
    """
    rng = random.Random(7)
    for _ in range(50):
        category, actions = rng.choice(SCHEMES)
        await api_report(client, await auth_headers(client), BANK_HOTLINE, category=category, actions=tuple(actions))
    level = (await api_check(client, await auth_headers(client), BANK_HOTLINE))["risk_level"]
    assert level != RiskLevel.HIGH.value


@pytest.mark.xfail(
    strict=True,
    reason="RISK/BUG: 50 coordinated fresh device_ids sending the same scheme push a legitimate number to HIGH. "
    "device_id is free to mint (30/min per IP) and there is no allowlist of verified organization numbers "
    "or device attestation. Needs Play Integrity + an allowlist before production.",
)
async def test_fifty_coordinated_fresh_devices_cannot_brand_a_bank_number_high(client):
    for _ in range(50):
        await api_report(client, await auth_headers(client), BANK_HOTLINE, category="BANK", actions=("OTP",))
    assert (await api_check(client, await auth_headers(client), BANK_HOTLINE))["risk_level"] != "HIGH"


async def test_one_device_reporting_daily_stays_a_single_reporter(client, clock):
    from datetime import timedelta

    headers = await auth_headers(client)
    for _ in range(30):
        assert (await api_report(client, headers, "+37369123456")).status_code == 200
        clock.tick(timedelta(days=1))
    data = await api_check(client, headers, "+37369123456")
    assert data["reports_count"] == 30 and data["risk_level"] == "LOW"


@pytest.mark.xfail(
    strict=True,
    reason="BUG: five fresh device_ids sending 'false alarm' feedback zero the reporters' reputation and drop "
    "a scam number from MEDIUM to UNKNOWN. Feedback needs agreement of several independent voters and must "
    "ignore feedback on a number the voter reported itself.",
)
async def test_feedback_cannot_whitewash_a_scam_number(client):
    scam = "+37369111222"
    for _ in range(2):
        await api_report(client, await auth_headers(client), scam)
    assert (await api_check(client, await auth_headers(client), scam))["risk_level"] == "MEDIUM"
    for _ in range(5):
        await client.post(f"{API}/feedback", json={"phone": scam, "was_correct": False}, headers=await auth_headers(client))
    assert (await api_check(client, await auth_headers(client), scam))["risk_level"] == "MEDIUM"
