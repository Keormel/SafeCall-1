"""SQL injection attempts in every input that reaches a query."""

import pytest
from sqlalchemy import func, inspect, select

from app import db
from app.models import Number, Report
from tests.conftest import admin_headers, auth_headers
from tests.factories import API, api_report, reported_number

PAYLOADS = [
    "'; DROP TABLE numbers;--",
    "' OR '1'='1",
    "1; DELETE FROM reports",
    "+37369123456' UNION SELECT * FROM devices--",
    "\" OR 1=1 --",
    "%27%20OR%201%3D1",
]


async def _tables_intact(session, numbers_expected: int):
    async with db.engine.connect() as conn:
        tables = await conn.run_sync(lambda c: inspect(c).get_table_names())
    assert {"numbers", "reports", "devices", "campaigns", "feedback"} <= set(tables)
    assert await session.scalar(select(func.count(Number.id))) == numbers_expected


@pytest.mark.parametrize("payload", PAYLOADS)
async def test_injection_in_phone_is_rejected(client, session, payload):
    await reported_number(session, 2)
    headers = await auth_headers(client)
    for endpoint, body in [
        ("check-number", {"phone": payload}),
        ("report", {"phone": payload, "category": "BANK", "actions": []}),
        ("feedback", {"phone": payload, "was_correct": False}),
    ]:
        resp = await client.post(f"{API}/{endpoint}", json=body, headers=headers)
        assert resp.status_code == 422, (endpoint, resp.status_code)
    await _tables_intact(session, 1)


@pytest.mark.parametrize("payload", PAYLOADS)
async def test_injection_in_query_params_is_rejected(client, session, payload):
    await reported_number(session, 2)
    headers = await auth_headers(client)
    assert (await client.get(f"{API}/sync", params={"since": payload}, headers=headers)).status_code == 422
    assert (await client.get(f"{API}/sync", params={"cursor": payload}, headers=headers)).status_code == 400
    assert (await client.get(f"{API}/numbers", params={"risk_level": payload}, headers=headers)).status_code == 422
    assert (await client.get(f"{API}/numbers", params={"campaign_id": payload}, headers=headers)).status_code == 422
    admin = await admin_headers(client)
    assert (await client.get(f"{API}/admin/reports", params={"phone": payload}, headers=admin)).status_code == 422
    assert (await client.get(f"{API}/admin/reports", params={"category": payload}, headers=admin)).status_code == 422
    await _tables_intact(session, 1)


async def test_crafted_cursor_cannot_inject(client, session):
    import base64

    await reported_number(session, 1)
    evil = base64.urlsafe_b64encode(b"2026-01-01T00:00:00|1 OR 1=1").decode()
    resp = await client.get(f"{API}/sync", params={"cursor": evil}, headers=await auth_headers(client))
    assert resp.status_code == 400


async def test_injection_in_free_text_is_inert(client, session):
    """free_text is never stored or interpolated into SQL; the report is accepted and tables survive."""
    resp = await api_report(client, await auth_headers(client), "+37369123456", free_text=PAYLOADS[0])
    assert resp.status_code == 200
    await _tables_intact(session, 1)
    assert await session.scalar(select(func.count(Report.id))) == 1


@pytest.mark.parametrize("payload", ["%2B37369123456'%20OR%20'1'='1", "..%2F..%2Fetc%2Fpasswd"])
async def test_injection_in_admin_path_param(client, session, payload):
    await reported_number(session, 1)
    resp = await client.post(f"{API}/admin/numbers/{payload}/remove", headers=await admin_headers(client))
    assert resp.status_code in {404, 422}
    await _tables_intact(session, 1)
