import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.routing import APIRoute
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.errors import register_error_handlers
from app.jobs import create_scheduler
from app.limiter import limiter
from app.routers import admin, assistant, auth, campaigns, feedback, numbers, reports, sync
from app.schemas import HealthResponse

settings = get_settings()
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def operation_id(route: APIRoute) -> str:
    """operationId = endpoint function name.

    Generated clients then get `checkNumber`, not `checkNumberApiV1CheckNumberPost`.
    """
    return route.name


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    scheduler = create_scheduler() if settings.scheduler_enabled else None
    if scheduler:
        scheduler.start()
    try:
        yield
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Number-reputation backend for the SafeCall app. No audio or call content is collected.",
    lifespan=lifespan,
    generate_unique_id_function=operation_id,
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
# /sync snapshots are large, repetitive JSON: gzip typically shrinks them ~10x for mobile networks.
app.add_middleware(GZipMiddleware, minimum_size=settings.gzip_minimum_size)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)

API_PREFIX = "/api/v1"
for module in (auth, numbers, reports, sync, campaigns, feedback, assistant, admin):
    app.include_router(module.router, prefix=API_PREFIX)
app.include_router(admin.token_router, prefix=API_PREFIX)


@app.get("/health", response_model=HealthResponse, tags=["health"])
@limiter.exempt
async def health() -> HealthResponse:
    return HealthResponse()
