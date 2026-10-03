"""Admin endpoints: token exchange, stats equal the database, feed, activity."""

import pytest
from sqlalchemy import func, select

from app.models import Campaign, Device, Feedback, Number, Report
from tests.conftest import ADMIN_KEY, admin_headers, auth_headers
from tests.factories import API, reported_number


async def test_stats_equal_database_counts(client, session):
    for reporters in (1, 2, 11):
        await reported_number(session, reporters)
    stats = (await client.get(f"{API}/admin/stats", headers=await admin_headers(client))).json()
    assert stats["numbers_count"] == await session.scalar(select(func.count(Number.id)))
    assert stats["reports_count"] == await session.scalar(select(func.count(Report.id)))
    assert stats["campaigns_count"] == await session.scalar(select(func.count(Campaign.id)))
    assert stats["devices_count"] == await session.scalar(select(func.count(Device.id)))
    assert stats["feedback_count"] == await session.scalar(select(func.count(Feedback.id)))
    assert stats["by_risk_level"] == {"UNKNOWN": 0, "LOW": 1, "MEDIUM": 1, "HIGH": 1}


async def test_stats_without_token_is_401(client):
    assert (await client.get(f"{API}/admin/stats")).status_code == 401


async def test_bare_admin_key_is_not_enough(client):
    assert (await client.get(f"{API}/admin/stats", headers={"X-Admin-Key": ADMIN_KEY})).status_code == 401


@pytest.mark.parametrize("key", ["wrong", "", ADMIN_KEY + " ", ADMIN_KEY.upper()])
async def test_wrong_admin_key_gets_no_token(client, key):
    resp = await client.post(f"{API}/admin/token", headers={"X-Admin-Key": key})
    assert resp.status_code == 403
    assert ADMIN_KEY not in resp.text


async def test_device_token_cannot_use_admin(client):
    resp = await client.get(f"{API}/admin/stats", headers=await auth_headers(client))
    assert resp.status_code == 403


async def test_remove_unknown_number_is_404(client):
    resp = await client.post(f"{API}/admin/numbers/+37369999999/remove", headers=await admin_headers(client))
    assert resp.status_code == 404


async def test_remove_invalid_number_is_422(client):
    resp = await client.post(f"{API}/admin/numbers/not-a-phone/remove", headers=await admin_headers(client))
    assert resp.status_code == 422


@pytest.mark.parametrize("days", [0, 366, "x"])
async def test_activity_bad_days_is_422(client, days):
    resp = await client.get(f"{API}/admin/activity", params={"days": days}, headers=await admin_headers(client))
    assert resp.status_code == 422
