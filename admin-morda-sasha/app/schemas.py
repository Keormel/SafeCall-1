from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


UserRole = Literal["viewer", "operator", "admin", "main_admin"]
RiskLevel = Literal["UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

PHONE_PATTERN = r"^\+[1-9]\d{7,18}$"


# ---------- auth ----------

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    username: str


class AdminMeResponse(BaseModel):
    id: int
    username: str
    role: UserRole


# ---------- numbers ----------

class NumberItem(BaseModel):
    id: str
    phone_e164: str
    risk_level: RiskLevel
    score: int = Field(ge=0, le=100)
    reports_count: int
    unique_reporters_count: int
    campaign_id: int | None = None
    is_removed: bool
    updated_at: datetime


class NumberListResponse(BaseModel):
    items: list[NumberItem]
    total: int
    limit: int
    offset: int


class NumberCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone_e164: str = Field(pattern=PHONE_PATTERN, max_length=20)
    score: int = Field(default=0, ge=0, le=100)


class NumberUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    comment: str | None = Field(default=None, max_length=500)


# ---------- dashboard ----------

class DashboardOverview(BaseModel):
    active_users: int
    active_numbers: int
    high_risk_numbers: int
    critical_risk_numbers: int
    reports_pending: int
    api_errors_24h: int
    main_backend_status: Literal["ok", "degraded", "down", "stub"]
    generated_at: datetime


# ---------- audit ----------

class AuditLogItem(BaseModel):
    id: str
    timestamp: datetime
    actor: str
    action: str
    entity_type: str
    entity_id: str | None = None
    result: Literal["success", "failed", "denied"]
    details: dict = {}


class AuditListResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
