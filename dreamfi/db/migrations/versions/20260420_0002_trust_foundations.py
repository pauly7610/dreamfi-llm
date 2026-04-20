"""trust foundations

Revision ID: 20260420_0002
Revises: 20260419_0001
Create Date: 2026-04-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260420_0002"
down_revision = "20260419_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gold_examples", sa.Column("role", sa.Text(), nullable=False, server_default="exemplar"))
    op.create_check_constraint(
        "ck_gold_examples_role",
        "gold_examples",
        "role IN ('exemplar','regression','counter_example','canary')",
    )
    op.add_column(
        "gold_examples",
        sa.Column("expected_pass_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column("gold_examples", sa.Column("last_run_round_id", postgresql.UUID(as_uuid=False), nullable=True))
    op.add_column("gold_examples", sa.Column("last_result", sa.Text(), nullable=True))

    op.create_table(
        "gold_drift_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("skill_id", sa.Text(), nullable=False),
        sa.Column("gold_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("prompt_version_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("previous_result", sa.Text(), nullable=False),
        sa.Column("new_result", sa.Text(), nullable=False),
        sa.Column("round_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("detected_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.add_column("eval_outputs", sa.Column("export_readiness", sa.Numeric(4, 3), nullable=True))
    op.add_column(
        "eval_outputs", sa.Column("export_breakdown_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("eval_outputs", "export_breakdown_json")
    op.drop_column("eval_outputs", "export_readiness")
    op.drop_table("gold_drift_events")
    op.drop_column("gold_examples", "last_result")
    op.drop_column("gold_examples", "last_run_round_id")
    op.drop_column("gold_examples", "expected_pass_criteria")
    op.drop_constraint("ck_gold_examples_role", "gold_examples", type_="check")
    op.drop_column("gold_examples", "role")
