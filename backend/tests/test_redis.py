"""Shared state across API workers: fingerprint cache and rate limits in Redis."""

import fakeredis
import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from redis.exceptions import ConnectionError as RedisConnectionError
from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware

from app.errors import register_error_handlers
from app.services import fingerprint
from app.services.fingerprint import FingerprintCache, LLMResult, build_fingerprint


@pytest.fixture
def shared_redis():
    return fakeredis.FakeAsyncRedis(decode_responses=True)


def worker_cache(redis) -> FingerprintCache:
    cache = FingerprintCache(max_size=16, redis_url=None, ttl_seconds=60)
    cache.redis = redis
    return cache


async def test_cache_is_shared_between_workers(shared_redis):
    worker_a, worker_b = worker_cache(shared_redis), worker_cache(shared_redis)
    await worker_a.set("k", LLMResult("BANK", ("OTP", "URGENCY")))

    assert await worker_b.get("k") == LLMResult("BANK", ("OTP", "URGENCY"))
    assert len(worker_b.local) == 1  # warmed into the local layer
    assert 0 < await shared_redis.ttl(FingerprintCache.KEY_PREFIX + "k") <= 60


async def test_second_worker_does_not_call_llm_again(shared_redis, monkeypatch):
    calls = []

    async def classifier(text):
        calls.append(text)
        return LLMResult("POLICE", ("THREAT",))

    monkeypatch.setattr(fingerprint, "_cache", worker_cache(shared_redis))
    first = await build_fingerprint("OTHER", [], "Звонили из полиции, угрожали делом", classifier)
    monkeypatch.setattr(fingerprint, "_cache", worker_cache(shared_redis))  # another process
    second = await build_fingerprint("OTHER", [], "Звонили из полиции, угрожали делом", classifier)

    assert first == second == ["POLICE", "THREAT"]
    assert len(calls) == 1


async def test_cache_survives_redis_outage(monkeypatch):
    class DownRedis:
        async def get(self, *a, **kw):
            raise RedisConnectionError("down")

        async def set(self, *a, **kw):
            raise RedisConnectionError("down")

    cache = worker_cache(DownRedis())
    assert await cache.get("k") is None
    await cache.set("k", LLMResult("BANK", ("OTP",)))
    assert await cache.get("k") == LLMResult("BANK", ("OTP",))  # local layer still works

    async def classifier(text):
        return LLMResult("BANK", ("OTP",))

    monkeypatch.setattr(fingerprint, "_cache", worker_cache(DownRedis()))
    assert await build_fingerprint("OTHER", [], "text", classifier) == ["BANK", "OTP"]


async def test_rate_limit_falls_back_to_memory_when_redis_is_down():
    # Nothing listens on this port: slowapi must keep limiting in memory instead of failing requests.
    limiter = Limiter(
        key_func=lambda request: "device:x",
        storage_uri="redis://127.0.0.1:6399/0",
        in_memory_fallback_enabled=True,
    )
    app = FastAPI()
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    register_error_handlers(app)

    @app.get("/ping")
    @limiter.limit("2/minute")
    async def ping(request: Request) -> dict:
        return {"ok": True}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        codes = [(await client.get("/ping")).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


@pytest.fixture
def redis_server():
    """A real Redis-protocol server on localhost (fakeredis), so redis:// URLs are exercised end to end."""
    import threading

    from fakeredis import TcpFakeServer

    server = TcpFakeServer(("127.0.0.1", 0), server_type="redis")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"redis://{host}:{port}/0"
    server.shutdown()
    server.server_close()


async def test_rate_limit_is_shared_between_workers_via_redis(redis_server):
    def make_worker() -> FastAPI:
        limiter = Limiter(key_func=lambda request: "device:x", storage_uri=redis_server, key_prefix="safecall")
        app = FastAPI()
        app.state.limiter = limiter
        app.add_middleware(SlowAPIMiddleware)
        register_error_handlers(app)

        @app.get("/ping")
        @limiter.limit("3/minute")
        async def ping(request: Request) -> dict:
            return {"ok": True}

        return app

    worker_a, worker_b = make_worker(), make_worker()
    codes = []
    for app in (worker_a, worker_b, worker_a, worker_b):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            codes.append((await client.get("/ping")).status_code)
    # 3/minute in total, not per worker.
    assert codes == [200, 200, 200, 429]


async def test_fingerprint_cache_over_redis_url(redis_server):
    worker_a = FingerprintCache(max_size=16, redis_url=redis_server, ttl_seconds=60)
    worker_b = FingerprintCache(max_size=16, redis_url=redis_server, ttl_seconds=60)
    await worker_a.set("k", LLMResult("DELIVERY", ("CARD_DATA",)))
    assert await worker_b.get("k") == LLMResult("DELIVERY", ("CARD_DATA",))
    await worker_a.redis.aclose()
    await worker_b.redis.aclose()
