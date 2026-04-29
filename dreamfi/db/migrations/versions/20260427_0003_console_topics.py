"""console topics

Revision ID: 20260427_0003
Revises: 20260420_0002
Create Date: 2026-04-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260427_0003"
down_revision = "20260420_0002"
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    return op.get_bind().dialect.name


def _json_type():
    if _dialect_name() == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _empty_array_default() -> sa.TextClause:
    if _dialect_name() == "postgresql":
        return sa.text("'[]'::jsonb")
    return sa.text("'[]'")


def _timestamp_default() -> sa.TextClause:
    if _dialect_name() == "postgresql":
        return sa.text("now()")
    return sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    op.create_table(
        "console_topics",
        sa.Column("topic_id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column(
            "source_ids_json",
            _json_type(),
            nullable=False,
            server_default=_empty_array_default(),
        ),
        sa.Column(
            "default_generator_slug",
            sa.String(),
            nullable=False,
            server_default="weekly-brief",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=_timestamp_default(),
        ),
    )


def downgrade() -> None:
    op.drop_table("console_topics")
