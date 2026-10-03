"""POST /check-number."""

from datetime import timedelta

import pytest

from app.models import utcnow
from app.services.risk_engine import recalculate_number
from tests.conftest import auth_headers
from tests.factories import API, api_check, make_devices, make_number, make_report, reported_number


async def test_unknown_number_never_returns_low(client):
    """Rule 1: a number without data is UNKNOWN — showing LOW would read as 'checked and fine'."""
    data = await api_check(client, await auth_headers(client), "+37369555555")
    assert data == {
        "phone": "+37369555555",
        "risk_level": "UNKNOWN",
        "risk_score": 0,
        "campaign_id": None,
        "campaign_type": None,
        "reports_count": 0,
    }


async def test_checking_does_not_create_data(client, session):
    """A lookup must not turn an unknown number into a known one."""
    headers = await auth_headers(client)
    await api_check(client, headers, "+37369555555")
    await api_check(client, headers, "+37369555555")
    assert (await api_check(client, headers, "+37369555555"))["risk_level"] == "UNKNOWN"


@pytest.mark.parametrize(("reporters", "level"), [(1, "LOW"), (2, "MEDIUM"), (11, "HIGH")])
async def test_levels_from_real_data(client, session, reporters, level):
    number = await reported_number(session, reporters)
    data = await api_check(client, await auth_headers(client), number.phone)
    assert data["risk_level"] == level
    assert data["reports_count"] == reporters


@pytest.mark.parametrize("fmt", ["+373 69 123 456", "069123456", "0037369123456", "(069) 123-456", "37369123456"])
async def test_any_format_finds_the_same_number(client, session, fmt):
    number = await make_number(session, "+37369123456")
    for device in await make_devices(session, 2):
        await make_report(session, number, device)
    await recalculate_number(session, number)
    await session.commit()
    data = await api_check(client, await auth_headers(client), fmt)
    assert data["phone"] == "+37369123456" and data["risk_level"] == "MEDIUM"


@pytest.mark.parametrize("bad", ["abc", "123", "", "+3736912345678901", "069123456'; DROP TABLE numbers;--"])
async def test_invalid_number_is_422(client, bad):
    resp = await client.post(f"{API}/check-number", json={"phone": bad}, headers=await auth_headers(client))
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] in {"INVALID_PHONE", "VALIDATION_ERROR"}


async def test_removed_number_reads_as_unknown(client, session):
    number = await reported_number(session, 11)
    number.is_removed = True
    await session.commit()
    assert (await api_check(client, await auth_headers(client), number.phone))["risk_level"] == "UNKNOWN"


async def test_fully_decayed_number_reads_as_unknown(client, session):
    """Old complaints fade out; after ~a year without new ones the number is UNKNOWN again."""
    from app.jobs import recalculate_all

    number = await make_number(session)
    for device in await make_devices(session, 11):
        await make_report(session, number, device, created_at=utcnow() - timedelta(days=500))
    await session.commit()
    await recalculate_all(session)
    assert (await api_check(client, await auth_headers(client), number.phone))["risk_level"] == "UNKNOWN"


async def test_missing_phone_field_is_422(client):
    resp = await client.post(f"{API}/check-number", json={}, headers=await auth_headers(client))
    assert resp.status_code == 422
