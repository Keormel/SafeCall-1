import enum
import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    TypeDecorator,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware UTC datetime on every backend (SQLite drops tzinfo otherwise)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        value = value.astimezone(UTC)
        if dialect.name == "sqlite":
            return value.replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


JSONType = JSON().with_variant(JSONB(), "postgresql")


class RiskLevel(enum.StrEnum):
    UNKNOWN = "UNKNOWN"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    reputation: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)


class Number(Base):
    __tablename__ = "numbers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), default=RiskLevel.UNKNOWN.value, nullable=False, index=True)
    reports_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_reporters_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Soft removal (false positive / moderation). Synced to clients as removed=true.
    is_removed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    # Bumped only when sync-relevant fields change, so delta sync stays small.
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False, index=True)


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("number_id", "device_id", "report_day", name="uq_reports_number_device_day"),
        Index("ix_reports_number_id", "number_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    number_id: Mapped[int] = mapped_column(ForeignKey("numbers.id", ondelete="CASCADE"), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    actions: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    fingerprint: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    # HMAC of the complaint text. The text itself is never stored.
    free_text_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    report_day: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    fingerprint: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    numbers_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reports_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False, index=True)


class CampaignNumber(Base):
    __tablename__ = "campaign_numbers"

    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True)
    number_id: Mapped[int] = mapped_column(ForeignKey("numbers.id", ondelete="CASCADE"), primary_key=True)
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class Feedback(Base):
    __tablename__ = "feedback"
    # A unique index (not a constraint) to match migration 0002 exactly; both enforce one vote per device.
    __table_args__ = (Index("uq_feedback_device_number", "device_id", "number_id", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    number_id: Mapped[int] = mapped_column(ForeignKey("numbers.id", ondelete="CASCADE"), nullable=False, index=True)
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
