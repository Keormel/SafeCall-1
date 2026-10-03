from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import get_settings
from app.security import decode_device_id


def device_or_ip_key(request: Request) -> str:
    """Rate-limit per device (from the JWT); fall back to client IP for anonymous calls."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        device_id = decode_device_id(auth[7:].strip())
        if device_id is not None:
            return f"device:{device_id}"
    return f"ip:{get_remote_address(request)}"


_settings = get_settings()
limiter = Limiter(
    key_func=device_or_ip_key,
    enabled=_settings.rate_limit_enabled,
    default_limits=[_settings.rate_limit_default],
    headers_enabled=False,
)
