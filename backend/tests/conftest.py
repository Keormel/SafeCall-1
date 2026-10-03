"""Shared fixtures.

- Every test gets an empty database (SQLite file by default; TEST_DATABASE_URL runs the suite on Postgres).
- Gemini is never called for real: any attempt fails the test unless the test installs a fake.
- Network is disabled by pytest-socket (see pyproject.toml); only loopback is allowed.
- Time is controllable through the `clock` fixture (freezegun).
"""

import os
import tempfile
import uuid
from collections.abc import Iterator
from pathlib import Path

_db_dir = tempfile.mkdtemp(prefix="safecall-test-")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite+aiosqlite:///{_db_dir}/test.db"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["GEMINI_API_KEY"] = ""
os.environ["REDIS_URL"] = ""
os.environ["ADMIN_API_KEY"] = "test-admin-key"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["APP_ENV"] = "test"

import pytest  # noqa: E402
from freezegun import freeze_time  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app import db  # noqa: E402
from app.db import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.services import fingerprint, gemini  # noqa: E402

TESTS_DIR = Path(__file__).parent
ADMIN_KEY = "test-admin-key"
FROZEN_NOW = "2099-06-15 12:00:00"

_MARKER_BY_DIR = {"unit": "unit", "api": "api", "security": "security", "perf": "perf", "e2e": "e2e"}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark tests by folder, so `pytest -m "unit or api"` is the fast set."""
    for item in items:
        folder = Path(str(item.fspath)).relative_to(TESTS_DIR).parts[0]
        if folder in _MARKER_BY_DIR:
            item.add_marker(_MARKER_BY_DIR[folder])


@pytest.fixture(scope="session", autouse=True)
async def warm_routes():
    """FastAPI parses endpoint signatures lazily, on the first request to each route. If that first
    request happens under freezegun, `datetime` annotations resolve to its fake class and parsing
    breaks. One throwaway request per route, before any test, avoids that."""
    from app import models  # noqa: F401

    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://w") as c:
        for path, ops in app.openapi()["paths"].items():
            url = path.replace("{campaign_id}", "1").replace("{phone}", "%2B37369000000")
            for method in ops:
                await c.request(method.upper(), url)


@pytest.fixture(autouse=True)
async def reset_db():
    from app import models  # noqa: F401

    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    fingerprint.clear_cache()
    yield


@pytest.fixture(autouse=True)
def no_real_gemini(monkeypatch):
    """External boundary: a test that reaches the real Gemini client fails loudly."""

    def forbidden():
        raise AssertionError("Real Gemini client requested in a test; use the fake_gemini fixture")

    gemini.reset_state()
    monkeypatch.setattr(gemini, "get_client", lambda key=None: forbidden())


class FakeGemini:
    """Stands in for Gemini at the client boundary (app.services.gemini.get_client).

    `text` is returned for every call unless `responder(kwargs)` is set; `errors` are raised in order,
    one per call, before falling back to the text. `calls` records each request with the key used.
    """

    def __init__(self) -> None:
        self.text: str | None = "Положите трубку и сами позвоните в банк по номеру на карте."
        self.finish_reason: str = "STOP"
        self.responder = None
        self.errors: list[Exception] = []
        self.calls: list[dict] = []

    def client_for(self, key=None):
        fake = self

        class Models:
            async def get(self, model):
                fake.calls.append({"get": model, "key": key})
                return type("ModelInfo", (), {"name": model, "output_token_limit": 65536})()

            async def generate_content(self, **kwargs):
                fake.calls.append({**kwargs, "key": key})
                if fake.errors:
                    raise fake.errors.pop(0)
                text = fake.responder(kwargs) if fake.responder else fake.text
                candidate = type("Candidate", (), {"finish_reason": fake.finish_reason})()
                return type("Response", (), {"text": text, "candidates": [candidate]})()

        return type("Client", (), {"aio": type("Aio", (), {"models": Models()})()})()


@pytest.fixture
def fake_gemini(monkeypatch):
    from app.config import get_settings

    fake = FakeGemini()
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    monkeypatch.setattr(gemini, "get_client", fake.client_for)
    return fake


@pytest.fixture
async def session():
    async with db.SessionLocal() as s:
        yield s


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def raw_client():
    """Client that receives 500 responses instead of re-raising server exceptions."""
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as c:
        yield c


@pytest.fixture
def clock() -> Iterator:
    """Frozen, movable time starting at FROZEN_NOW: `clock.tick(timedelta(days=1))`, `clock.move_to(...)`."""
    # Routes are pre-parsed by `warm_routes`, so FastAPI never meets freezegun's fake datetime class.
    # The frozen date is in the far future on purpose: freezegun gives *real* time to background threads
    # (limits' memory storage expires keys from a timer thread), so a frozen "now" earlier than the real
    # clock would make that thread wipe every rate-limit counter immediately.
    with freeze_time(FROZEN_NOW, real_asyncio=True) as frozen:
        yield frozen


@pytest.fixture
def limiter_on():
    """Enable slowapi for one test (it is off for the rest of the suite)."""
    from app.limiter import limiter

    limiter.reset()
    limiter.enabled = True
    yield limiter
    limiter.enabled = False
    limiter.reset()


async def auth_headers(client: AsyncClient, device_id: uuid.UUID | None = None) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/device", json={"device_id": str(device_id or uuid.uuid4())})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def admin_headers(client: AsyncClient) -> dict[str, str]:
    resp = await client.post("/api/v1/admin/token", headers={"X-Admin-Key": ADMIN_KEY})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
