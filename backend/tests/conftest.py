import os
import tempfile
import uuid

_db_dir = tempfile.mkdtemp(prefix="safecall-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_dir}/test.db"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["GEMINI_API_KEY"] = ""
os.environ["ADMIN_API_KEY"] = "test-admin-key"
os.environ["JWT_SECRET"] = "test-secret"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app import db  # noqa: E402
from app.db import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.services import fingerprint  # noqa: E402


@pytest.fixture(autouse=True)
async def reset_db():
    from app import models  # noqa: F401

    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    fingerprint.clear_cache()
    yield


@pytest.fixture
async def session():
    async with db.SessionLocal() as s:
        yield s


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def auth_headers(client: AsyncClient, device_id: uuid.UUID | None = None) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/device", json={"device_id": str(device_id or uuid.uuid4())})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
