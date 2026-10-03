"""POST /auth/device and JWT handling."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from tests.conftest import auth_headers
from tests.factories import API

CHECK = f"{API}/check-number"
BODY = {"phone": "+37369123456"}


async def test_valid_uuid_gets_a_working_token(client):
    resp = await client.post(f"{API}/auth/device", json={"device_id": str(uuid.uuid4())})
    assert resp.status_code == 200
    token = resp.json()
    assert token["token_type"] == "bearer" and token["expires_in"] == 30 * 24 * 3600
    ok = await client.post(CHECK, json=BODY, headers={"Authorization": f"Bearer {token['access_token']}"})
    assert ok.status_code == 200


@pytest.mark.parametrize("bad", ["not-a-uuid", "", "12345", None, 42, "00000000-0000-0000-0000-00000000000g"])
async def test_invalid_device_id_is_422(client, bad):
    resp = await client.post(f"{API}/auth/device", json={"device_id": bad})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_missing_body_is_422(client):
    assert (await client.post(f"{API}/auth/device")).status_code == 422


async def test_reissue_for_same_device_keeps_both_tokens_valid(client):
    device = uuid.uuid4()
    first, second = await auth_headers(client, device), await auth_headers(client, device)
    for headers in (first, second):
        assert (await client.post(CHECK, json=BODY, headers=headers)).status_code == 200


async def test_expired_token_is_401(client, clock):
    headers = await auth_headers(client)
    clock.tick(timedelta(days=31))
    resp = await client.post(CHECK, json=BODY, headers=headers)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def _token(secret: str, algorithm: str = "HS256", **claims) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(uuid.uuid4()), "iat": now, "exp": now + timedelta(days=1), "typ": "device", **claims}
    return jwt.encode(payload, secret, algorithm=algorithm)


@pytest.mark.parametrize(
    "token",
    [
        _token("someone-elses-secret"),
        "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxIiwidHlwIjoiZGV2aWNlIn0.",  # alg=none
        "garbage",
        "",
    ],
    ids=["forged-secret", "alg-none", "garbage", "empty"],
)
async def test_forged_or_broken_token_is_401(client, token):
    resp = await client.post(CHECK, json=BODY, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


async def test_valid_signature_for_unregistered_device_is_401(client):
    """A token is only good for a device that registered through /auth/device."""
    token = _token("test-secret")
    assert (await client.post(CHECK, json=BODY, headers={"Authorization": f"Bearer {token}"})).status_code == 401


@pytest.mark.parametrize("header", [{}, {"Authorization": "Basic dXNlcjpwYXNz"}, {"Authorization": "Bearer"}])
async def test_missing_or_wrong_scheme_is_401(client, header):
    assert (await client.post(CHECK, json=BODY, headers=header)).status_code == 401
