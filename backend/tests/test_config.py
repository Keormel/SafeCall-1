import pytest
from pydantic import ValidationError

from app.config import Settings

STRONG = "x" * 40


def test_development_allows_placeholder_secrets():
    Settings(app_env="development", jwt_secret="change-me-in-production", admin_api_key="change-me-admin-key")


@pytest.mark.parametrize(
    ("jwt_secret", "admin_api_key", "bad"),
    [
        ("change-me-in-production", STRONG, "JWT_SECRET"),
        (STRONG, "change-me-admin-key", "ADMIN_API_KEY"),
        ("short", STRONG, "JWT_SECRET"),
    ],
)
def test_production_refuses_weak_secrets(jwt_secret, admin_api_key, bad):
    with pytest.raises(ValidationError, match=bad):
        Settings(app_env="production", jwt_secret=jwt_secret, admin_api_key=admin_api_key)


def test_production_accepts_strong_secrets():
    Settings(app_env="production", jwt_secret=STRONG, admin_api_key=STRONG + "y")
