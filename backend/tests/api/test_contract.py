"""Contract: real responses validate against the published OpenAPI schema (what the Dart client is generated from)."""

import jsonschema
import pytest

from app.main import app
from app.services import gemini
from app.services.report_service import submit_report
from tests.conftest import admin_headers, auth_headers
from tests.factories import API, make_devices, phone, reported_number

SPEC = app.openapi()


def _validate(path: str, method: str, status: int, body) -> None:
    schema = SPEC["paths"][path][method]["responses"][str(status)]["content"]["application/json"]["schema"]
    # Resolve "#/components/..." refs against the whole document.
    jsonschema.validate(body, {**schema, "components": SPEC["components"]})


@pytest.fixture
async def world(session):
    devices = await make_devices(session, 6)
    await session.commit()
    for i, p in enumerate([phone(), phone(), phone()]):
        for dev in devices[i * 2 : i * 2 + 2]:
            await submit_report(session, dev, p, "BANK", ["OTP", "URGENCY"])
    await reported_number(session, 1)


async def test_device_endpoints_match_schema(client, world, monkeypatch):
    h = await auth_headers(client)
    calls = [
        ("/api/v1/check-number", "post", {"json": {"phone": "+37369000123"}}),
        ("/api/v1/numbers", "get", {}),
        ("/api/v1/sync", "get", {"params": {"limit": 2}}),
        ("/api/v1/sync", "get", {"params": {"since": "2020-01-01T00:00:00Z"}}),
        ("/api/v1/campaigns", "get", {}),
        ("/api/v1/campaigns/{campaign_id}", "get", {}),
        ("/api/v1/report", "post", {"json": {"phone": "+37369000124", "category": "OTHER", "actions": []}}),
    ]
    for path, method, kwargs in calls:
        resp = await client.request(method.upper(), path.replace("{campaign_id}", "1"), headers=h, **kwargs)
        assert resp.status_code == 200, (path, resp.text)
        _validate(path, method, 200, resp.json())


async def test_sync_page_with_cursor_and_removed_matches_schema(client, world):
    from sqlalchemy import update

    from app import db
    from app.models import Number

    async with db.SessionLocal() as s:
        await s.execute(update(Number).values(is_removed=True).where(Number.id == 1))
        await s.commit()
    headers = await auth_headers(client)
    params = {"since": "2020-01-01T00:00:00Z", "limit": 1}
    saw_cursor = saw_removed = False
    while True:
        page = (await client.get(f"{API}/sync", params=params, headers=headers)).json()
        _validate("/api/v1/sync", "get", 200, page)
        saw_removed |= any(i["removed"] for i in page["items"])
        if not page["has_more"]:
            break
        saw_cursor = True
        params["cursor"] = page["next_cursor"]
    assert saw_cursor and saw_removed


async def test_admin_endpoints_match_schema(client, world):
    h = await admin_headers(client)
    for path in ("/api/v1/admin/stats", "/api/v1/admin/reports", "/api/v1/admin/activity"):
        resp = await client.get(path, headers=h)
        _validate(path, "get", 200, resp.json())


async def test_error_responses_match_schema(client):
    resp = await client.post(f"{API}/check-number", json={"phone": "+37369000123"})
    _validate("/api/v1/check-number", "post", 401, resp.json())


async def test_assistant_matches_schema(client, monkeypatch):
    from app.config import get_settings

    class Models:
        async def generate_content(self, **kw):
            return type("R", (), {"text": "Положите трубку."})()

    monkeypatch.setattr(get_settings(), "gemini_api_key", "k")
    monkeypatch.setattr(gemini, "get_client", lambda key=None: type("C", (), {"aio": type("A", (), {"models": Models()})()})())
    resp = await client.post(f"{API}/assistant/chat", json={"messages": [{"role": "user", "content": "?"}]}, headers=await auth_headers(client))
    _validate("/api/v1/assistant/chat", "post", 200, resp.json())
