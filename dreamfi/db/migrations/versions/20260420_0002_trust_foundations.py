"""trust foundations

Revision ID: 20260420_0002
Revises: 20260419_0001
Create Date: 2026-04-20
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260420_0002"
down_revision = "20260419_0001"
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    return op.get_bind().dialect.name


def _json_type():
    if _dialect_name() == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _id_type():
    if _dialect_name() == "postgresql":
        return postgresql.UUID(as_uuid=False)
    return sa.String()


def _empty_json_default() -> sa.TextClause:
    if _dialect_name() == "postgresql":
        return sa.text("'{}'::jsonb")
    return sa.text("'{}'")


def _timestamp_default() -> sa.TextClause:
    if _dialect_name() == "postgresql":
        return sa.text("now()")
    return sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    with op.batch_alter_table("gold_examples") as batch_op:
        batch_op.add_column(
            sa.Column("role", sa.Text(), nullable=False, server_default="exemplar")
        )
        batch_op.create_check_constraint(
            "ck_gold_examples_role",
            "role IN ('exemplar','regression','counter_example','canary')",
        )
        batch_op.add_column(
            sa.Column(
                "expected_pass_criteria",
                _json_type(),
                nullable=False,
                server_default=_empty_json_default(),
            )
        )
        batch_op.add_column(sa.Column("last_run_round_id", _id_type(), nullable=True))
        batch_op.add_column(sa.Column("last_result", sa.Text(), nullable=True))

    op.create_table(
        "gold_drift_events",
        sa.Column("event_id", _id_type(), primary_key=True),
        sa.Column("workspace_id", _id_type(), nullable=False),
        sa.Column("skill_id", sa.Text(), nullable=False),
        sa.Column("gold_id", _id_type(), nullable=False),
        sa.Column("prompt_version_id", _id_type(), nullable=False),
        sa.Column("previous_result", sa.Text(), nullable=False),
        sa.Column("new_result", sa.Text(), nullable=False),
        sa.Column("round_id", _id_type(), nullable=False),
        sa.Column(
            "detected_at",
            sa.TIMESTAMP(timezone=True),
            server_default=_timestamp_default(),
            nullable=False,
        ),
    )

    with op.batch_alter_table("eval_outputs") as batch_op:
        batch_op.add_column(
            sa.Column("export_readiness", sa.Numeric(4, 3), nullable=True)
        )
        batch_op.add_column(
            sa.Column("export_breakdown_json", _json_type(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("eval_outputs") as batch_op:
        batch_op.drop_column("export_breakdown_json")
        batch_op.drop_column("export_readiness")

    op.drop_table("gold_drift_events")

    with op.batch_alter_table("gold_examples") as batch_op:
        batch_op.drop_column("last_result")
        batch_op.drop_column("last_run_round_id")
        batch_op.drop_column("expected_pass_criteria")
        batch_op.drop_constraint("ck_gold_examples_role", type_="check")
        batch_op.drop_column("role")
