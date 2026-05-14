"""store gold replay round ids as strings

Revision ID: 20260514_0011
Revises: 20260507_0010
Create Date: 2026-05-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260514_0011"
down_revision = "20260507_0010"
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    return op.get_bind().dialect.name


def upgrade() -> None:
    if _dialect_name() == "postgresql":
        op.alter_column(
            "gold_examples",
            "last_run_round_id",
            existing_type=postgresql.UUID(as_uuid=False),
            type_=sa.String(),
            postgresql_using="last_run_round_id::text",
            nullable=True,
        )
        return

    with op.batch_alter_table("gold_examples") as batch_op:
        batch_op.alter_column(
            "last_run_round_id",
            existing_type=sa.String(),
            type_=sa.String(),
            nullable=True,
        )


def downgrade() -> None:
    if _dialect_name() == "postgresql":
        op.alter_column(
            "gold_examples",
            "last_run_round_id",
            existing_type=sa.String(),
            type_=postgresql.UUID(as_uuid=False),
            postgresql_using="last_run_round_id::uuid",
            nullable=True,
        )
        return

    with op.batch_alter_table("gold_examples") as batch_op:
        batch_op.alter_column(
            "last_run_round_id",
            existing_type=sa.String(),
            type_=sa.String(),
            nullable=True,
        )
