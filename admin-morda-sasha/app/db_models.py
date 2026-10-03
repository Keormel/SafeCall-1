from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy import Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


TZ = DateTime(timezone=True)


class Number(Base):
    __tablename__ = "numbers"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20))
    risk_score: Mapped[int] = mapped_column(default=0)
    risk_level: Mapped[str] = mapped_column(String(10))
    reports_count: Mapped[int] = mapped_column(default=0)
    unique_reporters_count: Mapped[int] = mapped_column(
        default=0
    )
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("public.campaigns.id")
    )
    is_removed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        TZ, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TZ, default=utcnow
    )


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = {"schema": "public"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(TZ)
    last_seen: Mapped[datetime] = mapped_column(TZ)
    reputation: Mapped[float]


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(primary_key=True)
    number_id: Mapped[int] = mapped_column(
        ForeignKey("public.numbers.id")
    )
    device_id: Mapped[UUID]
    category: Mapped[str] = mapped_column(String(20))
    actions: Mapped[dict] = mapped_column(JSON)
    fingerprint: Mapped[dict] = mapped_column(JSON)
    free_text_hash: Mapped[str | None] = mapped_column(
        String(64)
    )
    created_at: Mapped[datetime] = mapped_column(TZ)


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(20))
    risk_score: Mapped[int] = mapped_column(default=0)
    numbers_count: Mapped[int] = mapped_column(default=0)
    reports_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(TZ)
    updated_at: Mapped[datetime] = mapped_column(TZ)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "admin"}

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        TZ,
        default=utcnow,
        server_default=func.now(),
    )
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str | None] = mapped_column(
        String(64)
    )
    result: Mapped[str] = mapped_column(
        String(16), default="success"
    )
    details: Mapped[dict] = mapped_column(
        JSON, default=dict
    )
