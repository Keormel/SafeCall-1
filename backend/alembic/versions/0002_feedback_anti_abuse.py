"""Protect feedback from duplicate votes and self-review.

Revision ID: 0002_feedback_anti_abuse
Revises: 0001_initial
Create Date: 2026-10-03
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002_feedback_anti_abuse"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("uq_feedback_device_number", "feedback", ["device_id", "number_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_feedback_device_number", table_name="feedback")
