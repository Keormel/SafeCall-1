from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.config import settings
from app.schemas import AdminMeResponse


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
)


def create_admin_token(
    username: str,
    role: str,
) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.admin_access_token_expire_minutes,
    )

    payload = {
        "sub": username,
        "role": role,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.admin_jwt_secret,
        algorithm=settings.admin_jwt_algorithm,
    )


def get_current_admin(
    token: str = Depends(oauth2_scheme),
) -> AdminMeResponse:
    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Токен недействителен или истёк",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.admin_jwt_secret,
            algorithms=[settings.admin_jwt_algorithm],
        )
        username = payload.get("sub")
        role = payload.get("role")
    except JWTError:
        raise auth_error

    if not username or role not in {
        "viewer",
        "operator",
        "admin",
        "main_admin",
    }:
        raise auth_error

    return AdminMeResponse(
        id=0,
        username=username,
        role=role,
    )


def require_roles(*roles: str):
    def checker(
        admin: AdminMeResponse = Depends(get_current_admin),
    ) -> AdminMeResponse:
        if admin.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для этого действия",
            )
        return admin

    return checker
