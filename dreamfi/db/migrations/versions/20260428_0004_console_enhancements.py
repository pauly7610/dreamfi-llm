"""console enhancements

Revision ID: 20260428_0004
Revises: 20260427_0003
Create Date: 2026-04-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260428_0004"
down_revision = "20260427_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "console_topics",
        sa.Column("owner", sa.String(), nullable=False, server_default="unassigned"),
    )
    op.add_column(
        "console_topics",
        sa.Column("status", sa.String(), nullable=False, server_default="discovery"),
    )
    op.add_column(
        "console_topics",
        sa.Column("target_decision_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("console_topics", "target_decision_at")
    op.drop_column("console_topics", "status")
    op.drop_column("console_topics", "owner")
