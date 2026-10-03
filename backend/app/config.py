from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SafeCall API"
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://safecall:safecall@localhost:5432/safecall"
    db_echo: bool = False

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 30

    admin_api_key: str = "change-me-admin-key"
    admin_token_expire_hours: int = 12

    default_region: str = "MD"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"
    llm_timeout_seconds: float = 8.0
    llm_cache_size: int = 1024
    llm_cache_ttl_seconds: int = 7 * 24 * 3600

    # Shared state for several API workers: rate limits + fingerprint cache.
    # Empty -> everything stays in process memory (fine for a single worker).
    redis_url: str | None = None
    free_text_max_length: int = 1000

    rate_limit_enabled: bool = True
    rate_limit_report: str = "10/hour"
    rate_limit_check: str = "60/minute"
    rate_limit_default: str = "120/minute"

    # Report ageing: full weight for the grace period, then halves every half-life.
    report_grace_days: int = 30
    report_half_life_days: int = 90

    scheduler_enabled: bool = True
    recalc_interval_minutes: int = 5
    full_recalc_hour_utc: int = 3

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    gzip_minimum_size: int = 1024

    sync_default_limit: int = 1000
    sync_max_limit: int = 5000

    @model_validator(mode="after")
    def _no_default_secrets_in_production(self) -> "Settings":
        """Refuse to boot a production server with placeholder or weak secrets."""
        if self.app_env.lower() not in {"production", "prod"}:
            return self
        problems = []
        for name in ("jwt_secret", "admin_api_key"):
            value = getattr(self, name)
            if "change-me" in value or len(value) < 32:
                problems.append(f"{name.upper()} must be set to a random value of at least 32 characters")
        if problems:
            raise ValueError("; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
