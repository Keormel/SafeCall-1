"""GET /sync: the only way the offline database on the phone learns anything."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import Number, RiskLevel
from tests.conftest import admin_headers, auth_headers
from tests.factories import API, api_report, make_number, reported_number


async def _get(client, headers, **params):
    resp = await client.get(f"{API}/sync", params=params, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _all_pages(client, headers, **params):
    items, cursor, first_server_time = [], None, None
    while True:
        page = await _get(client, headers, **params, **({"cursor": cursor} if cursor else {}))
        first_server_time = first_server_time or page["server_time"]
        items.extend(page["items"])
        if not page["has_more"]:
            return items, first_server_time
        cursor = page["next_cursor"]


async def test_snapshot_pagination_loses_and_duplicates_nothing(client, session):
    expected = {(await reported_number(session, 1)).phone for _ in range(50)}
    items, _ = await _all_pages(client, await auth_headers(client), limit=7)
    phones = [i["phone"] for i in items]
    assert len(phones) == len(set(phones)) == 50
    assert set(phones) == expected


async def test_snapshot_never_ships_numbers_without_data(client, session):
    """Rule 1 on the phone: an UNKNOWN row in the local DB would be indistinguishable from data."""
    await make_number(session, "+37369000001")  # exists, never reported
    await reported_number(session, 1)
    await session.commit()
    items, _ = await _all_pages(client, await auth_headers(client))
    assert "+37369000001" not in {i["phone"] for i in items}
    assert all(i["risk_level"] != "UNKNOWN" and i["removed"] is False for i in items)


async def test_delta_contains_only_changes(client, session, clock):
    old = await reported_number(session, 1)
    headers = await auth_headers(client)
    clock.tick(timedelta(minutes=1))  # rows from the last 10 s before a snapshot are re-sent by design
    since = (await _get(client, headers))["server_time"]
    clock.tick(timedelta(minutes=5))  # beyond the 10 s safety margin
    await api_report(client, headers, "+37369777777")
    items, _ = await _all_pages(client, headers, since=since)
    phones = {i["phone"] for i in items}
    assert "+37369777777" in phones
    assert old.phone not in phones


async def test_empty_delta(client, session, clock):
    await reported_number(session, 1)
    headers = await auth_headers(client)
    clock.tick(timedelta(minutes=1))
    since = (await _get(client, headers))["server_time"]
    clock.tick(timedelta(minutes=5))
    page = await _get(client, headers, since=since)
    assert page["items"] == [] and page["has_more"] is False and page["full_snapshot"] is False


async def test_since_in_the_future_is_empty(client, session):
    await reported_number(session, 3)
    page = await _get(client, await auth_headers(client), since="2999-01-01T00:00:00Z")
    assert page["items"] == []


@pytest.mark.parametrize("since", ["yesterday", "2026-13-45", "1' OR '1'='1", ""])
async def test_invalid_since_is_422(client, since):
    resp = await client.get(f"{API}/sync", params={"since": since}, headers=await auth_headers(client))
    assert resp.status_code == 422


@pytest.mark.parametrize("limit", [0, -1, "many"])
async def test_invalid_limit_is_422(client, limit):
    resp = await client.get(f"{API}/sync", params={"limit": limit}, headers=await auth_headers(client))
    assert resp.status_code == 422


async def test_huge_limit_is_capped(client, session):
    for _ in range(3):
        await reported_number(session, 1)
    page = await _get(client, await auth_headers(client), limit=10**9)
    assert len(page["items"]) == 3


async def test_rows_changed_just_before_a_snapshot_are_resent_once(client, session, clock):
    """The 10 s safety margin re-sends recent rows instead of losing ones committed in parallel."""
    number = await reported_number(session, 1)
    headers = await auth_headers(client)
    since = (await _get(client, headers))["server_time"]
    clock.tick(timedelta(minutes=5))
    assert [i["phone"] for i in (await _get(client, headers, since=since))["items"]] == [number.phone]


async def test_server_time_is_monotonic(client, clock):
    headers = await auth_headers(client)
    times = []
    for _ in range(5):
        times.append((await _get(client, headers))["server_time"])
        clock.tick(timedelta(seconds=1))
    assert times == sorted(times) and len(set(times)) == 5


async def test_removed_and_downgraded_numbers_come_as_removed(client, session, clock):
    moderated = await reported_number(session, 11)
    headers = await auth_headers(client)
    since = (await _get(client, headers))["server_time"]
    clock.tick(timedelta(minutes=5))
    resp = await client.post(f"{API}/admin/numbers/{moderated.phone}/remove", headers=await admin_headers(client))
    assert resp.status_code == 200
    items = {i["phone"]: i for i in (await _all_pages(client, headers, since=since))[0]}
    assert items[moderated.phone]["removed"] is True
    assert items[moderated.phone]["risk_score"] == 0 and items[moderated.phone]["campaign_type"] is None


async def _server_state(session) -> dict[str, tuple]:
    session.expire_all()
    rows = (await session.scalars(select(Number))).all()
    return {
        n.phone: (n.risk_level, n.risk_score)
        for n in rows
        if not n.is_removed and n.risk_level != RiskLevel.UNKNOWN.value
    }


async def test_snapshot_plus_all_deltas_equals_server_state(client, session, clock):
    """End to end: a phone that applies the snapshot and then every delta holds exactly the server's data."""
    local: dict[str, tuple] = {}

    def apply(items):
        for item in items:
            if item["removed"]:
                local.pop(item["phone"], None)
            else:
                local[item["phone"]] = (item["risk_level"], item["risk_score"])

    devices = [await auth_headers(client) for _ in range(12)]
    for i in range(6):
        await api_report(client, devices[i], f"+3736900000{i}")
    items, since = await _all_pages(client, devices[0], limit=4)
    apply(items)

    for round_ in range(4):
        clock.tick(timedelta(minutes=10))
        for i, headers in enumerate(devices):
            await api_report(client, headers, f"+3736900000{(i + round_) % 8}")
        if round_ == 2:
            await client.post(f"{API}/admin/numbers/+37369000001/remove", headers=await admin_headers(client))
        clock.tick(timedelta(minutes=10))
        items, since = await _all_pages(client, devices[0], since=since, limit=3)
        apply(items)
        assert local == await _server_state(session), f"diverged after round {round_}"


async def test_bad_cursor_is_400(client):
    resp = await client.get(f"{API}/sync", params={"cursor": "not-base64!"}, headers=await auth_headers(client))
    assert resp.status_code == 400 and resp.json()["error"]["code"] == "INVALID_CURSOR"


async def test_sync_requires_auth(client):
    assert (await client.get(f"{API}/sync")).status_code == 401
