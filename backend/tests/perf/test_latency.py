"""Latency on a realistic database size (100 000 numbers). SQLite here; the CI Postgres job runs the same test."""

import statistics
import time
from datetime import timedelta

import pytest
from sqlalchemy import insert

from app import db
from app.models import Number, utcnow
from tests.conftest import auth_headers
from tests.factories import API

N = 100_000
LEVELS = ["LOW", "MEDIUM", "HIGH"]


@pytest.fixture
async def big_db():
    old = utcnow() - timedelta(days=1)
    rows = [
        {
            "phone": f"+37369{i:06d}",
            "risk_score": (i * 7) % 100,
            "risk_level": LEVELS[i % 3],
            "reports_count": 1 + i % 5,
            "unique_reporters_count": 1 + i % 5,
            "is_removed": False,
            "created_at": old,
            "updated_at": old,
        }
        for i in range(N)
    ]
    async with db.engine.begin() as conn:
        for start in range(0, N, 10_000):
            await conn.execute(insert(Number), rows[start : start + 10_000])
    return N


def p95(samples: list[float]) -> float:
    return statistics.quantiles(samples, n=20)[18]


async def test_check_number_p95_under_200ms(client, big_db):
    headers = await auth_headers(client)
    samples = []
    for i in range(300):
        started = time.perf_counter()
        resp = await client.post(f"{API}/check-number", json={"phone": f"+37369{(i * 331) % N:06d}"}, headers=headers)
        samples.append(time.perf_counter() - started)
        assert resp.status_code == 200
    assert p95(samples) < 0.200, f"p95 = {p95(samples) * 1000:.0f} ms"


async def test_sync_delta_under_500ms(client, big_db):
    headers = await auth_headers(client)
    since = (utcnow() - timedelta(hours=1)).isoformat()
    # A few fresh changes on top of 100k untouched rows.
    async with db.engine.begin() as conn:
        await conn.execute(
            Number.__table__.update().where(Number.id <= 50).values(updated_at=utcnow(), risk_level="HIGH")
        )
    samples = []
    for _ in range(20):
        started = time.perf_counter()
        resp = await client.get(f"{API}/sync", params={"since": since}, headers=headers)
        samples.append(time.perf_counter() - started)
        assert resp.status_code == 200 and len(resp.json()["items"]) == 50
    assert max(samples) < 0.500, f"max = {max(samples) * 1000:.0f} ms"


async def test_full_snapshot_page_under_1s(client, big_db):
    headers = await auth_headers(client)
    started = time.perf_counter()
    resp = await client.get(f"{API}/sync", params={"limit": 5000}, headers=headers)
    elapsed = time.perf_counter() - started
    assert resp.status_code == 200 and len(resp.json()["items"]) == 5000
    assert elapsed < 1.0, f"{elapsed * 1000:.0f} ms for a 5000-row page"
