import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.errors import AppError
from app.models import Device, utcnow

bearer = HTTPBearer(auto_error=False)
LAST_SEEN_RESOLUTION = timedelta(minutes=5)


def _encode(sub: str, typ: str, expires_in: int) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": sub, "iat": now, "exp": now + timedelta(seconds=expires_in), "typ": typ}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def create_access_token(device_id: uuid.UUID) -> tuple[str, int]:
    expires_in = get_settings().jwt_expire_days * 24 * 3600
    return _encode(str(device_id), "device", expires_in), expires_in


def create_admin_token() -> tuple[str, int]:
    expires_in = get_settings().admin_token_expire_hours * 3600
    return _encode("admin", "admin", expires_in), expires_in


def decode_device_id(token: str) -> uuid.UUID | None:
    payload = _decode(token)
    if not payload or payload.get("typ") != "device":
        return None
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        return None


async def get_current_device(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> Device:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("UNAUTHORIZED", "Missing bearer token", 401)
    device_id = decode_device_id(credentials.credentials)
    if device_id is None:
        raise AppError("UNAUTHORIZED", "Invalid or expired token", 401)
    device = await session.get(Device, device_id)
    if device is None:
        raise AppError("UNAUTHORIZED", "Unknown device, call /auth/device again", 401)
    now = utcnow()
    if now - device.last_seen > LAST_SEEN_RESOLUTION:
        device.last_seen = now
        await session.commit()
    request.state.device_id = str(device.id)
    return device


def verify_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    """Only used to obtain an admin JWT; every other admin endpoint takes the token."""
    if not x_admin_key or not secrets.compare_digest(x_admin_key, get_settings().admin_api_key):
        raise AppError("FORBIDDEN", "Invalid admin key", 403)


async def require_admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("UNAUTHORIZED", "Missing admin bearer token, get one at /admin/token", 401)
    payload = _decode(credentials.credentials)
    if payload is None:
        raise AppError("UNAUTHORIZED", "Invalid or expired token", 401)
    if payload.get("typ") != "admin":
        raise AppError("FORBIDDEN", "Admin token required", 403)
