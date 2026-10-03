import uuid

from sqlalchemy import select

from app.models import Report
from tests.conftest import auth_headers

API = "/api/v1"


async def report(client, headers, phone="+37369123456", category="BANK", actions=("OTP", "URGENCY"), **extra):
    return await client.post(
        f"{API}/report", json={"phone": phone, "category": category, "actions": list(actions), **extra}, headers=headers
    )


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_auth_required(client):
    resp = await client.post(f"{API}/check-number", json={"phone": "+37369123456"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


async def test_auth_is_idempotent(client):
    device_id = uuid.uuid4()
    await auth_headers(client, device_id)
    await auth_headers(client, device_id)


async def test_check_unknown_number(client):
    headers = await auth_headers(client)
    resp = await client.post(f"{API}/check-number", json={"phone": "069 123 456"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {
        "phone": "+37369123456",
        "risk_level": "UNKNOWN",
        "risk_score": 0,
        "campaign_id": None,
        "campaign_type": None,
        "reports_count": 0,
    }


async def test_check_invalid_number(client):
    headers = await auth_headers(client)
    resp = await client.post(f"{API}/check-number", json={"phone": "12345"}, headers=headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_PHONE"


async def test_report_then_check(client):
    h1, h2 = await auth_headers(client), await auth_headers(client)
    assert (await report(client, h1)).json() == {"status": "accepted"}
    data = (await client.post(f"{API}/check-number", json={"phone": "+37369123456"}, headers=h1)).json()
    assert data["risk_level"] == "LOW"
    assert data["reports_count"] == 1

    await report(client, h2)
    data = (await client.post(f"{API}/check-number", json={"phone": "+37369123456"}, headers=h1)).json()
    assert data["risk_level"] == "MEDIUM"
    assert data["reports_count"] == 2


async def test_duplicate_report_same_device_same_day(client, session):
    headers = await auth_headers(client)
    assert (await report(client, headers)).status_code == 200
    dup = await report(client, headers, category="POLICE", actions=["THREAT"])
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "DUPLICATE_REPORT"
    assert len((await session.scalars(select(Report))).all()) == 1


async def test_report_validation_errors(client):
    headers = await auth_headers(client)
    resp = await report(client, headers, category="ALIENS")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
    resp = await report(client, headers, actions=["MIND_CONTROL"])
    assert resp.status_code == 422


async def test_free_text_not_stored(client, session):
    headers = await auth_headers(client)
    resp = await report(client, headers, free_text="Мне звонил Иван из банка, номер карты 4111")
    assert resp.status_code == 200
    stored = (await session.scalars(select(Report))).one()
    assert stored.free_text_hash and len(stored.free_text_hash) == 64
    assert "Иван" not in repr(stored.__dict__)


async def test_sync_full_and_delta(client):
    h1, h2, h3 = [await auth_headers(client) for _ in range(3)]
    await report(client, h1, phone="+37369000001")
    await report(client, h1, phone="+37368000002")
    # Checked but never reported -> must not be shipped.
    await client.post(f"{API}/check-number", json={"phone": "+37379000003"}, headers=h1)

    full = (await client.get(f"{API}/sync", headers=h1)).json()
    assert full["full_snapshot"] is True
    assert {i["phone"] for i in full["items"]} == {"+37369000001", "+37368000002"}
    assert all(i["removed"] is False for i in full["items"])
    assert full["has_more"] is False

    # Pagination
    page1 = (await client.get(f"{API}/sync", params={"limit": 1}, headers=h1)).json()
    assert page1["has_more"] is True and len(page1["items"]) == 1
    page2 = (
        await client.get(f"{API}/sync", params={"limit": 1, "cursor": page1["next_cursor"]}, headers=h1)
    ).json()
    assert page2["has_more"] is False
    assert {page1["items"][0]["phone"], page2["items"][0]["phone"]} == {"+37369000001", "+37368000002"}

    # Delta: a new report changes +37369000001's level; a fresh number appears.
    since = full["server_time"]
    await report(client, h2, phone="+37369000001")
    await report(client, h3, phone="+37360000004")
    delta = (await client.get(f"{API}/sync", params={"since": since}, headers=h1)).json()
    assert delta["full_snapshot"] is False
    by_phone = {i["phone"]: i for i in delta["items"]}
    assert by_phone["+37369000001"]["risk_level"] == "MEDIUM"
    assert "+37360000004" in by_phone


async def test_sync_reports_removed_numbers(client):
    headers = await auth_headers(client)
    await report(client, headers, phone="+37369000001")
    since = (await client.get(f"{API}/sync", headers=headers)).json()["server_time"]

    resp = await client.post(
        f"{API}/admin/numbers/+37369000001/remove", headers={"X-Admin-Key": "test-admin-key"}
    )
    assert resp.status_code == 200

    delta = (await client.get(f"{API}/sync", params={"since": since}, headers=headers)).json()
    item = next(i for i in delta["items"] if i["phone"] == "+37369000001")
    assert item["removed"] is True
    full = (await client.get(f"{API}/sync", headers=headers)).json()
    assert full["items"] == []


async def test_sync_bad_cursor(client):
    headers = await auth_headers(client)
    resp = await client.get(f"{API}/sync", params={"cursor": "!!!"}, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_CURSOR"


async def test_feedback(client):
    headers = await auth_headers(client)
    resp = await client.post(f"{API}/feedback", json={"phone": "+37369000001", "was_correct": True}, headers=headers)
    assert resp.status_code == 404
    await report(client, headers, phone="+37369000001")
    resp = await client.post(f"{API}/feedback", json={"phone": "+37369000001", "was_correct": True}, headers=headers)
    assert resp.json() == {"status": "accepted"}


async def test_campaign_flow_and_listing(client):
    devices = [await auth_headers(client) for _ in range(8)]
    for i, phone in enumerate(["+37369100001", "+37369100002", "+37369100003"]):
        for h in devices[i * 2 : i * 2 + 2]:
            await report(client, h, phone=phone)

    campaigns = (await client.get(f"{API}/campaigns", headers=devices[0])).json()
    assert campaigns["total"] == 1
    cid = campaigns["items"][0]["id"]

    detail = (await client.get(f"{API}/campaigns/{cid}", headers=devices[0])).json()
    assert len(detail["numbers"]) == 3
    assert detail["type"] == "BANK"

    # Demo scenario: unknown -> 1 report (LOW) -> 2nd similar report -> joins campaign, MEDIUM.
    new = "+37378999999"
    check = lambda: client.post(f"{API}/check-number", json={"phone": new}, headers=devices[0])  # noqa: E731
    assert (await check()).json()["risk_level"] == "UNKNOWN"
    await report(client, devices[6], phone=new)
    assert (await check()).json()["risk_level"] == "LOW"
    await report(client, devices[7], phone=new)
    data = (await check()).json()
    assert data["risk_level"] == "MEDIUM"
    assert data["campaign_id"] == cid
    assert data["campaign_type"] == "BANK"

    numbers = (await client.get(f"{API}/numbers", params={"campaign_id": cid}, headers=devices[0])).json()
    assert numbers["total"] == 4
    medium = (await client.get(f"{API}/numbers", params={"risk_level": "MEDIUM"}, headers=devices[0])).json()
    assert all(n["risk_level"] == "MEDIUM" for n in medium["items"])

    assert (await client.get(f"{API}/campaigns/9999", headers=devices[0])).status_code == 404


async def test_admin_stats(client):
    headers = await auth_headers(client)
    await report(client, headers)
    assert (await client.get(f"{API}/admin/stats")).status_code == 403
    assert (await client.get(f"{API}/admin/stats", headers={"X-Admin-Key": "nope"})).status_code == 403
    stats = (await client.get(f"{API}/admin/stats", headers={"X-Admin-Key": "test-admin-key"})).json()
    assert stats["numbers_count"] == 1
    assert stats["reports_count"] == 1
    assert stats["campaigns_count"] == 0
    assert stats["by_risk_level"]["LOW"] == 1

    recalc = await client.post(f"{API}/admin/recalculate", headers={"X-Admin-Key": "test-admin-key"})
    assert recalc.status_code == 200


async def test_report_rate_limit_per_device(client):
    from app.limiter import limiter

    limiter.reset()
    limiter.enabled = True
    try:
        headers = await auth_headers(client)
        other = await auth_headers(client)
        for i in range(10):
            assert (await report(client, headers, phone=f"+3736900{i:04d}")).status_code == 200
        limited = await report(client, headers, phone="+37369009999")
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "RATE_LIMITED"
        # Another device is not affected.
        assert (await report(client, other, phone="+37369009999")).status_code == 200
    finally:
        limiter.enabled = False
        limiter.reset()


def test_openapi_operation_ids_are_short_and_unique():
    from app.main import app

    ids = [op["operationId"] for ops in app.openapi()["paths"].values() for op in ops.values()]
    assert len(ids) == len(set(ids))
    assert set(ids) == {
        "auth_device",
        "check_number",
        "list_numbers",
        "create_report",
        "sync_numbers",
        "list_campaigns",
        "get_campaign",
        "create_feedback",
        "get_stats",
        "recalculate",
        "remove_number",
        "restore_number",
        "health",
    }
