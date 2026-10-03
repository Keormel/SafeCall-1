"""N+1 detection: the number of SQL statements per request must not grow with the data size."""

import contextlib

import pytest
from sqlalchemy import event, inspect, select

from app import db
from app.db import Base
from app.models import Campaign, Number
from app.services.report_service import submit_report
from tests.conftest import admin_headers, auth_headers
from tests.factories import API, api_report, make_devices, phone, reported_number


@contextlib.contextmanager
def count_queries():
    counter = {"n": 0}

    def before(*_):
        counter["n"] += 1

    event.listen(db.engine.sync_engine, "before_cursor_execute", before)
    try:
        yield counter
    finally:
        event.remove(db.engine.sync_engine, "before_cursor_execute", before)


async def _campaign(session, size: int):
    devices = await make_devices(session, size * 2)
    await session.commit()
    for i in range(size):
        p = phone()
        for dev in devices[i * 2 : i * 2 + 2]:
            await submit_report(session, dev, p, "BANK", ["OTP", "URGENCY"])
    return (await session.scalars(select(Campaign))).one()


async def _wipe() -> None:
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def _measure(client, request) -> int:
    with count_queries() as c:
        resp = await request()
    assert resp.status_code == 200, resp.text
    return c["n"]


@pytest.mark.parametrize(
    "endpoint",
    ["numbers", "sync", "campaign", "admin_reports", "check"],
)
async def test_read_endpoints_use_constant_queries(client, session, endpoint):
    async def run(size: int) -> int:
        campaign = await _campaign(session, size)
        for _ in range(size):
            await reported_number(session, 1)
        device, admin = await auth_headers(client), await admin_headers(client)
        calls = {
            "numbers": lambda: client.get(f"{API}/numbers", params={"limit": 500}, headers=device),
            "sync": lambda: client.get(f"{API}/sync", headers=device),
            "campaign": lambda: client.get(f"{API}/campaigns/{campaign.id}", headers=device),
            "admin_reports": lambda: client.get(f"{API}/admin/reports", params={"limit": 500}, headers=admin),
            "check": lambda: client.post(f"{API}/check-number", json={"phone": "+37369000001"}, headers=device),
        }
        return await _measure(client, calls[endpoint])

    small = await run(3)
    await _wipe()
    large = await run(25)
    assert large == small, f"{endpoint}: {small} queries with small data, {large} with 8x more"


@pytest.mark.xfail(
    strict=True,
    reason="BUG (N+1): a report on a number that belongs to a campaign rescores every campaign member one by "
    "one (2 queries each) inside the request. With a 1000-number campaign one report runs ~2000 queries. "
    "Fix: use risk_engine.recalculate_numbers (batched) in report_service.recalculate_campaign_numbers.",
)
async def test_report_into_a_campaign_uses_constant_queries(client, session):
    async def queries_for_report(size: int) -> int:
        await _wipe()
        campaign = await _campaign(session, size)
        target = (await session.scalars(select(Number).where(Number.campaign_id == campaign.id))).first()
        headers = await auth_headers(client)
        with count_queries() as c:
            resp = await api_report(client, headers, target.phone)
        assert resp.status_code == 200
        return c["n"]

    assert await queries_for_report(25) == await queries_for_report(3)


async def test_indexes_exist_for_hot_lookups():
    async with db.engine.connect() as conn:
        def collect(c):
            insp = inspect(c)
            idx = {
                t: {tuple(i["column_names"]) for i in insp.get_indexes(t)}
                | {tuple(u["column_names"]) for u in insp.get_unique_constraints(t)}
                for t in ("numbers", "reports", "campaigns", "feedback")
            }
            return idx

        indexes = await conn.run_sync(collect)
    assert ("phone",) in indexes["numbers"], "check-number looks numbers up by phone"
    assert ("updated_at",) in indexes["numbers"], "sync deltas filter by updated_at"
    assert ("risk_level",) in indexes["numbers"]
    assert ("campaign_id",) in indexes["numbers"]
    assert ("number_id",) in indexes["reports"]
    assert ("number_id", "device_id", "report_day") in indexes["reports"], "rule 5 is enforced by a unique key"
    assert ("updated_at",) in indexes["campaigns"]
