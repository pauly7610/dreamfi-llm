"""add workspace id to gold examples

Revision ID: 20260506_0008
Revises: 20260504_0007
Create Date: 2026-05-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260506_0008"
down_revision = "20260504_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("gold_examples") as batch_op:
        batch_op.add_column(
            sa.Column(
                "workspace_id",
                sa.String(),
                nullable=False,
                server_default="default",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("gold_examples") as batch_op:
        batch_op.drop_column("workspace_id")
