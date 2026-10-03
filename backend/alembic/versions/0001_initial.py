"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-03
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.models import UTCDateTime

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("last_seen", UTCDateTime(), nullable=False),
        sa.Column("reputation", sa.Float(), nullable=False, server_default="1.0"),
    )
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("fingerprint", JSONType, nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("numbers_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reports_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
    )
    op.create_index("ix_campaigns_updated_at", "campaigns", ["updated_at"])

    op.create_table(
        "numbers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("phone", sa.String(20), nullable=False, unique=True),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("risk_level", sa.String(10), nullable=False, server_default="UNKNOWN"),
        sa.Column("reports_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_reporters_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_removed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
    )
    op.create_index("ix_numbers_risk_level", "numbers", ["risk_level"])
    op.create_index("ix_numbers_campaign_id", "numbers", ["campaign_id"])
    op.create_index("ix_numbers_updated_at", "numbers", ["updated_at"])

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("number_id", sa.Integer(), sa.ForeignKey("numbers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("actions", JSONType, nullable=False),
        sa.Column("fingerprint", JSONType, nullable=False),
        sa.Column("free_text_hash", sa.String(64), nullable=True),
        sa.Column("report_day", sa.Date(), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.UniqueConstraint("number_id", "device_id", "report_day", name="uq_reports_number_device_day"),
    )
    op.create_index("ix_reports_number_id", "reports", ["number_id"])

    op.create_table(
        "campaign_numbers",
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("number_id", sa.Integer(), sa.ForeignKey("numbers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("similarity_score", sa.Float(), nullable=False, server_default="0"),
    )

    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("number_id", sa.Integer(), sa.ForeignKey("numbers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("was_correct", sa.Boolean(), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
    )
    op.create_index("ix_feedback_number_id", "feedback", ["number_id"])


def downgrade() -> None:
    op.drop_table("feedback")
    op.drop_table("campaign_numbers")
    op.drop_table("reports")
    op.drop_table("numbers")
    op.drop_table("campaigns")
    op.drop_table("devices")
