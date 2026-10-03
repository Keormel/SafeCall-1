"""Rule 8: no audio, names, contacts or complaint text are kept; logs carry masked numbers only."""

import logging
import re

import pytest
from sqlalchemy import inspect

from app import db
from app.main import app
from app.services import assistant
from tests.conftest import ADMIN_KEY, admin_headers, auth_headers
from tests.factories import API, api_report

PHONE = "+37369123456"
NATIONAL = "069123456"
SECRET_TEXT = "Звонил Ион Попеску, просил код 4821 и карту 4111111111111111"
CHAT_TEXT = "Я уже назвал код 9931, что делать?"


def _server_logs(caplog) -> str:
    # httpx's own "HTTP Request: ..." lines come from the *test client*, not from the server.
    return "\n".join(r.getMessage() + (r.exc_text or "") for r in caplog.records if not r.name.startswith("httpx"))


@pytest.fixture
def fake_llms(monkeypatch):
    from app.config import get_settings
    from app.services import fingerprint

    class Models:
        async def generate_content(self, **kw):
            text = '{"category": "BANK", "tags": ["OTP"]}' if isinstance(kw["contents"], str) else "Позвоните в банк."
            return type("R", (), {"text": text})()

    client = type("C", (), {"aio": type("A", (), {"models": Models()})()})()
    monkeypatch.setattr(get_settings(), "gemini_api_key", "k")
    monkeypatch.setattr(fingerprint, "_get_gemini_client", lambda: client)
    monkeypatch.setattr(assistant, "get_client", lambda: client)


async def test_full_flow_logs_hold_no_number_text_token_or_key(client, caplog, fake_llms):
    # Production runs at INFO; our own code is checked down to DEBUG. (Third-party drivers at DEBUG,
    # e.g. aiosqlite or DB_ECHO, print SQL parameters — see the risk list in tests/README.md.)
    caplog.set_level(logging.INFO)
    caplog.set_level(logging.DEBUG, logger="app")
    device = await auth_headers(client)
    token = device["Authorization"].split()[1]
    admin = await admin_headers(client)
    admin_token = admin["Authorization"].split()[1]

    await api_report(client, device, NATIONAL, free_text=SECRET_TEXT)
    await api_report(client, await auth_headers(client), PHONE)
    await api_report(client, device, PHONE)  # duplicate → 409 path
    await client.post(f"{API}/check-number", json={"phone": PHONE}, headers=device)
    await client.post(f"{API}/feedback", json={"phone": PHONE, "was_correct": True}, headers=device)
    await client.get(f"{API}/sync", headers=device)
    await client.post(f"{API}/assistant/chat", json={"messages": [{"role": "user", "content": CHAT_TEXT}]}, headers=device)
    await client.get(f"{API}/admin/stats", headers=admin)

    logs = _server_logs(caplog)
    assert "+3736*****56" in logs, "the masked form should be what gets logged"
    for secret in (PHONE, PHONE[1:], NATIONAL, "Попеску", "4111111111111111", "9931", token, admin_token, ADMIN_KEY):
        assert secret not in logs, f"leaked into logs: {secret[:12]}…"


async def test_database_has_no_column_for_complaint_or_chat_text():
    async with db.engine.connect() as conn:
        columns = await conn.run_sync(
            lambda c: {t: [col["name"] for col in inspect(c).get_columns(t)] for t in inspect(c).get_table_names()}
        )
    flat = {f"{t}.{c}" for t, cols in columns.items() for c in cols}
    suspicious = {c for c in flat if re.search(r"(text|message|content|comment|audio|name|contact)", c)}
    # Only the HMAC of the complaint and the campaign name (generated, not user text) are allowed.
    assert suspicious <= {"reports.free_text_hash", "campaigns.name"}, suspicious


async def test_admin_key_is_not_echoed_in_error_responses(client):
    resp = await client.post(f"{API}/admin/token", headers={"X-Admin-Key": "attacker-guess"})
    assert "attacker-guess" not in resp.text and ADMIN_KEY not in resp.text


@pytest.mark.xfail(
    strict=True,
    reason="BUG: SQLAlchemy puts bound parameters into exception text; the unhandled-error handler logs it, "
    "so a phone number reaches the logs in full. Fix: create_async_engine(..., hide_parameters=True).",
)
async def test_database_errors_do_not_carry_phone_numbers():
    from sqlalchemy import text

    async with db.engine.connect() as conn:
        try:
            await conn.execute(text("INSERT INTO no_such_table (phone) VALUES (:p)"), {"p": PHONE})
        except Exception as exc:
            assert PHONE not in str(exc)
            return
    pytest.fail("expected a database error")


@pytest.mark.xfail(
    strict=True,
    reason="BUG: admin endpoints take the phone in the URL (/admin/numbers/{phone}/remove, /admin/reports?phone=), "
    "and the uvicorn access log writes full URLs, so full numbers end up in server logs. Fix: move the phone "
    "into the request body (POST) or disable the access log for these routes.",
)
def test_no_endpoint_takes_a_phone_number_in_the_url():
    leaking = [
        f"{method.upper()} {path}"
        for path, ops in app.openapi()["paths"].items()
        for method, op in ops.items()
        for p in op.get("parameters", [])
        if p["name"] == "phone" and p["in"] in {"path", "query"}
    ]
    assert leaking == []
