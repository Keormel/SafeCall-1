from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.config import settings
from app.schemas import AdminMeResponse, TokenResponse
from app.security import create_admin_token, get_current_admin


router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    valid_username = (
        form_data.username == settings.bootstrap_admin_username
    )

    valid_password = (
        form_data.password == settings.bootstrap_admin_password
    )

    if not valid_username or not valid_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    role = "main_admin"

    return TokenResponse(
        access_token=create_admin_token(
            username=form_data.username,
            role=role,
        ),
        role=role,
        username=form_data.username,
    )


@router.get("/me", response_model=AdminMeResponse)
def me(
    admin: AdminMeResponse = Depends(get_current_admin),
):
    return admin
