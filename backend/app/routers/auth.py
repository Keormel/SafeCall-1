from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.limiter import limiter
from app.models import Device, utcnow
from app.schemas import DeviceAuthRequest, ErrorResponse, TokenResponse
from app.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/device", response_model=TokenResponse, responses={422: {"model": ErrorResponse}})
@limiter.limit("30/minute")
async def auth_device(
    request: Request, body: DeviceAuthRequest, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    """Register (or re-register) an app install by its random UUID and issue a JWT. No PII involved."""
    device = await session.get(Device, body.device_id)
    if device is None:
        session.add(Device(id=body.device_id))
    else:
        device.last_seen = utcnow()
    await session.commit()
    token, expires_in = create_access_token(body.device_id)
    return TokenResponse(access_token=token, expires_in=expires_in)
