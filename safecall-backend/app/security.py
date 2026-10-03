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


def create_access_token(device_id: uuid.UUID) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.jwt_expire_days * 24 * 3600
    now = datetime.now(UTC)
    payload = {"sub": str(device_id), "iat": now, "exp": now + timedelta(seconds=expires_in), "typ": "device"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), expires_in


def decode_device_id(token: str) -> uuid.UUID | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
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


async def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    if not x_admin_key or not secrets.compare_digest(x_admin_key, get_settings().admin_api_key):
        raise AppError("FORBIDDEN", "Invalid admin key", 403)
