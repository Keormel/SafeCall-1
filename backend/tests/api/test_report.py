"""POST /report."""

import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.models import Number, Report
from tests.conftest import auth_headers
from tests.factories import API, api_check, api_report

PHONE = "+37369123456"


async def test_valid_report_is_accepted_and_creates_the_number(client, session):
    resp = await api_report(client, await auth_headers(client), PHONE)
    assert resp.status_code == 200 and resp.json() == {"status": "accepted"}
    number = await session.scalar(select(Number).where(Number.phone == PHONE))
    assert number is not None and number.reports_count == 1


async def test_same_device_same_day_is_rejected(client, session):
    """Rule 5: one device, one report per number per day — otherwise one person inflates risk."""
    headers = await auth_headers(client)
    assert (await api_report(client, headers, PHONE)).status_code == 200
    dup = await api_report(client, headers, "069 123 456", category="POLICE", actions=("THREAT",))
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "DUPLICATE_REPORT"
    assert await session.scalar(select(func.count(Report.id))) == 1


async def test_same_device_next_day_is_accepted_but_counts_as_one_reporter(client, clock):
    headers = await auth_headers(client)
    assert (await api_report(client, headers, PHONE)).status_code == 200
    clock.tick(timedelta(days=1))
    assert (await api_report(client, headers, PHONE)).status_code == 200
    data = await api_check(client, headers, PHONE)
    assert data["reports_count"] == 2
    assert data["risk_level"] == "LOW"  # still a single reporter


async def test_day_boundary_is_utc_midnight(client, clock):
    clock.move_to("2099-06-15 23:59:00")
    headers = await auth_headers(client)
    assert (await api_report(client, headers, PHONE)).status_code == 200
    clock.move_to("2099-06-16 00:00:30")
    assert (await api_report(client, headers, PHONE)).status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        {"phone": PHONE, "category": "ALIENS", "actions": []},
        {"phone": PHONE, "category": "BANK", "actions": ["MIND_CONTROL"]},
        {"phone": PHONE, "category": "bank", "actions": []},
        {"phone": PHONE, "actions": []},
        {"category": "BANK", "actions": []},
        {"phone": PHONE, "category": "BANK", "actions": "OTP"},
        {"phone": PHONE, "category": "BANK", "actions": ["OTP"] * 8},
    ],
    ids=["unknown-category", "unknown-action", "lowercase-category", "no-category", "no-phone", "actions-not-list", "too-many-actions"],
)
async def test_bad_report_bodies_are_422(client, body):
    resp = await client.post(f"{API}/report", json=body, headers=await auth_headers(client))
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_free_text_length_boundaries(client):
    ok = await api_report(client, await auth_headers(client), PHONE, free_text="я" * 1000)
    assert ok.status_code == 200
    too_long = await api_report(client, await auth_headers(client), "+37369123457", free_text="я" * 1001)
    assert too_long.status_code == 422


async def test_huge_free_text_is_rejected_cheaply(client):
    resp = await api_report(client, await auth_headers(client), PHONE, free_text="x" * 1_000_000)
    assert resp.status_code == 422


async def test_invalid_phone_is_422_and_creates_nothing(client, session):
    resp = await api_report(client, await auth_headers(client), "123")
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "INVALID_PHONE"
    assert await session.scalar(select(func.count(Number.id))) == 0


async def test_one_number_in_many_formats_is_one_row(client, session):
    """Rule 9: storing E.164 only means every format lands on the same record."""
    for fmt in ["+373 69 123 456", "069123456", "0037369123456", "(069) 123-456", "37369123456"]:
        assert (await api_report(client, await auth_headers(client), fmt)).status_code == 200
    assert await session.scalar(select(func.count(Number.id))) == 1
    number = await session.scalar(select(Number))
    assert number.phone == PHONE and number.unique_reporters_count == 5


async def test_duplicate_actions_are_stored_once(client, session):
    await api_report(client, await auth_headers(client), PHONE, actions=("OTP", "OTP", "URGENCY"))
    report = await session.scalar(select(Report))
    assert report.actions == ["OTP", "URGENCY"]


async def test_twenty_parallel_reports_on_one_new_number(client, session):
    """Race: 20 devices report the same brand-new number at once. Counters must equal the stored rows."""
    headers = [await auth_headers(client) for _ in range(20)]
    responses = await asyncio.gather(*(api_report(client, h, PHONE) for h in headers))
    statuses = sorted(r.status_code for r in responses)
    assert all(code == 200 for code in statuses), statuses

    numbers = (await session.scalars(select(Number))).all()
    assert len(numbers) == 1
    stored = await session.scalar(select(func.count(Report.id)))
    assert stored == 20
    assert numbers[0].reports_count == stored
    assert numbers[0].unique_reporters_count == 20


async def test_report_requires_auth(client):
    resp = await client.post(f"{API}/report", json={"phone": PHONE, "category": "BANK", "actions": []})
    assert resp.status_code == 401
