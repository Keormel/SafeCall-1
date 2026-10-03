"""Uniform error format and authentication across the whole API surface."""

import pytest

from app.main import app
from tests.conftest import auth_headers
from tests.factories import API

PUBLIC = {("/health", "get"), (f"{API}/auth/device", "post"), (f"{API}/admin/token", "post")}


def _routes():
    for path, ops in app.openapi()["paths"].items():
        for method in ops:
            yield path, method


def _url(path: str) -> str:
    return path.replace("{campaign_id}", "1").replace("{phone}", "%2B37369123456")


def _is_error_body(body) -> bool:
    return set(body) == {"error"} and set(body["error"]) == {"code", "message"} and all(
        isinstance(v, str) and v for v in body["error"].values()
    )


async def test_health_needs_no_token(client):
    resp = await client.get("/health")
    assert resp.status_code == 200 and resp.json() == {"status": "ok"}


@pytest.mark.parametrize(("path", "method"), [r for r in _routes() if r not in PUBLIC])
async def test_every_private_endpoint_requires_a_token(client, path, method):
    """A forgotten Depends(get_current_device) would open an endpoint to the internet."""
    resp = await client.request(method.upper(), _url(path), json={})
    assert resp.status_code == 401, f"{method.upper()} {path} answered {resp.status_code}"
    assert _is_error_body(resp.json())


async def test_404_uses_error_format(client):
    resp = await client.get(f"{API}/no-such-endpoint")
    assert resp.status_code == 404 and _is_error_body(resp.json())


async def test_405_uses_error_format(client):
    resp = await client.delete(f"{API}/check-number")
    assert resp.status_code == 405 and _is_error_body(resp.json())


async def test_422_uses_error_format(client):
    resp = await client.post(f"{API}/check-number", json={"phone": 1}, headers=await auth_headers(client))
    assert resp.status_code == 422 and _is_error_body(resp.json())


async def test_malformed_json_is_422_not_500(client):
    resp = await client.post(
        f"{API}/report", content=b"{not json", headers={**await auth_headers(client), "Content-Type": "application/json"}
    )
    assert resp.status_code == 422 and _is_error_body(resp.json())


async def test_500_uses_error_format_and_hides_internals(raw_client, monkeypatch):
    from app.routers import numbers

    async def explode(*args, **kwargs):
        raise RuntimeError("secret internal detail: postgres password=hunter2")

    monkeypatch.setattr(numbers, "check_payload", explode)
    resp = await raw_client.post(f"{API}/check-number", json={"phone": "+37369123456"}, headers=await auth_headers(raw_client))
    assert resp.status_code == 500
    assert resp.json() == {"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}
    assert "hunter2" not in resp.text


async def test_429_uses_error_format(client, limiter_on):
    headers = await auth_headers(client)
    for _ in range(60):
        await client.post(f"{API}/check-number", json={"phone": "+37369123456"}, headers=headers)
    resp = await client.post(f"{API}/check-number", json={"phone": "+37369123456"}, headers=headers)
    assert resp.status_code == 429 and _is_error_body(resp.json())
