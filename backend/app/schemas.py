import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import RiskLevel
from app.services.fingerprint import Action, Category

PhoneStr = Field(min_length=3, max_length=32, examples=["+37369123456"])


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


# --- auth
class DeviceAuthRequest(BaseModel):
    device_id: uuid.UUID


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Seconds until expiry")


# --- numbers
class CheckNumberRequest(BaseModel):
    phone: str = PhoneStr


class CheckNumberResponse(BaseModel):
    phone: str
    risk_level: RiskLevel
    risk_score: int
    campaign_id: int | None = None
    campaign_type: str | None = None
    reports_count: int = 0


class NumberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phone: str
    risk_level: RiskLevel
    risk_score: int
    reports_count: int
    unique_reporters_count: int
    campaign_id: int | None
    campaign_type: str | None = None
    updated_at: datetime


class NumberList(BaseModel):
    items: list[NumberOut]
    total: int
    limit: int
    offset: int


# --- reports
class ReportRequest(BaseModel):
    phone: str = PhoneStr
    category: Category
    actions: list[Action] = Field(default_factory=list, max_length=len(Action))
    free_text: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional complaint text. Used only to build a fingerprint, never stored.",
    )


class ReportAccepted(BaseModel):
    status: Literal["accepted"] = "accepted"


# --- sync
class SyncItem(BaseModel):
    phone: str
    risk_level: RiskLevel
    risk_score: int
    campaign_type: str | None
    updated_at: datetime
    removed: bool = Field(description="Delete this phone from the local DB")


class SyncResponse(BaseModel):
    items: list[SyncItem]
    server_time: datetime = Field(description="Pass as `since` in the next sync once all pages are fetched")
    full_snapshot: bool
    next_cursor: str | None = None
    has_more: bool


# --- assistant
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20, description="Whole dialogue, oldest first")

    @model_validator(mode="after")
    def _ends_with_user(self) -> "ChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("the last message must be from the user")
        return self


class ChatReply(BaseModel):
    reply: str


# --- feedback
class FeedbackRequest(BaseModel):
    phone: str = PhoneStr
    was_correct: bool


class FeedbackAccepted(BaseModel):
    status: Literal["accepted"] = "accepted"


# --- campaigns
class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    fingerprint: list[str]
    risk_score: int
    numbers_count: int
    reports_count: int
    created_at: datetime
    updated_at: datetime


class CampaignNumberOut(BaseModel):
    phone: str
    risk_level: RiskLevel
    risk_score: int
    reports_count: int
    similarity_score: float


class CampaignDetail(CampaignOut):
    numbers: list[CampaignNumberOut]


class CampaignList(BaseModel):
    items: list[CampaignOut]
    total: int
    limit: int
    offset: int


# --- admin
class AdminStats(BaseModel):
    numbers_count: int
    reports_count: int
    campaigns_count: int
    devices_count: int
    feedback_count: int
    by_risk_level: dict[RiskLevel, int]


class AdminReportOut(BaseModel):
    id: int
    phone: str
    category: str
    actions: list[str]
    fingerprint: list[str]
    has_free_text: bool = Field(description="A complaint text was sent (the text itself is never stored)")
    risk_level: RiskLevel
    campaign_id: int | None
    created_at: datetime


class AdminReportList(BaseModel):
    items: list[AdminReportOut]
    total: int
    limit: int
    offset: int


class ActivityDay(BaseModel):
    date: date
    reports: int
    reporters: int = Field(description="Distinct devices that reported that day")
    new_numbers: int = Field(description="Numbers seen for the first time that day")


class ActivityResponse(BaseModel):
    days: list[ActivityDay] = Field(description="Oldest first, one entry per day, zero-filled")


class RecalculateResult(BaseModel):
    numbers_changed: int
    campaigns_created: int


class RemoveNumberResult(BaseModel):
    phone: str
    removed: bool
