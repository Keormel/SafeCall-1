"""slowapi limits per device, and that they reset with time."""

from datetime import timedelta

from tests.conftest import auth_headers
from tests.factories import API, api_report


async def test_report_limit_10_per_hour_then_resets(client, clock, limiter_on):
    headers = await auth_headers(client)
    for i in range(10):
        assert (await api_report(client, headers, f"+3736900{i:04d}")).status_code == 200
    blocked = await api_report(client, headers, "+37369009999")
    assert blocked.status_code == 429 and blocked.json()["error"]["code"] == "RATE_LIMITED"
    clock.tick(timedelta(hours=1, seconds=1))
    assert (await api_report(client, headers, "+37369009999")).status_code == 200


async def test_check_limit_60_per_minute_then_resets(client, clock, limiter_on):
    headers = await auth_headers(client)
    body = {"phone": "+37369123456"}
    for _ in range(60):
        assert (await client.post(f"{API}/check-number", json=body, headers=headers)).status_code == 200
    assert (await client.post(f"{API}/check-number", json=body, headers=headers)).status_code == 429
    clock.tick(timedelta(seconds=61))
    assert (await client.post(f"{API}/check-number", json=body, headers=headers)).status_code == 200


async def test_assistant_limit_20_per_hour(client, clock, limiter_on, monkeypatch):
    from app.config import get_settings
    from app.services import gemini

    class Models:
        async def generate_content(self, **kw):
            return type("R", (), {"text": "ok"})()

    monkeypatch.setattr(get_settings(), "gemini_api_key", "k")
    monkeypatch.setattr(gemini, "get_client", lambda key=None: type("C", (), {"aio": type("A", (), {"models": Models()})()})())
    headers = await auth_headers(client)
    body = {"messages": [{"role": "user", "content": "?"}]}
    for _ in range(20):
        assert (await client.post(f"{API}/assistant/chat", json=body, headers=headers)).status_code == 200
    assert (await client.post(f"{API}/assistant/chat", json=body, headers=headers)).status_code == 429
    clock.tick(timedelta(hours=1, seconds=1))
    assert (await client.post(f"{API}/assistant/chat", json=body, headers=headers)).status_code == 200


async def test_limits_are_per_device(client, limiter_on):
    a, b = await auth_headers(client), await auth_headers(client)
    for i in range(10):
        await api_report(client, a, f"+3736900{i:04d}")
    assert (await api_report(client, a, "+37369009999")).status_code == 429
    assert (await api_report(client, b, "+37369009999")).status_code == 200


async def test_new_device_ids_are_throttled_per_ip(client, limiter_on):
    """Minting device ids is the cheapest abuse path; /auth/device allows 30 per minute per IP."""
    import uuid

    codes = [(await client.post(f"{API}/auth/device", json={"device_id": str(uuid.uuid4())})).status_code for _ in range(31)]
    assert codes[:30] == [200] * 30 and codes[30] == 429
