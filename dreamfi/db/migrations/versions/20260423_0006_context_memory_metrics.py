"""context memory, change events, metric catalog (C6, C7, T2')

Revision ID: 20260423_0006
Revises: 20260422_0005
Create Date: 2026-04-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260423_0006"
down_revision = "20260422_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "context_questions",
        sa.Column("question_id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("asker", sa.String(), nullable=False, server_default=""),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("question_norm", sa.String(), nullable=False),
        sa.Column("topic_id", sa.String(), nullable=True),
        sa.Column("bundle_id", sa.String(), nullable=True),
        sa.Column("answer_excerpt", sa.Text(), nullable=False, server_default=""),
        sa.Column("tokens_json", sa.JSON(), nullable=False),
        sa.Column(
            "private", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "asked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_context_questions_workspace_id",
        "context_questions",
        ["workspace_id"],
    )
    op.create_index(
        "ix_context_questions_question_norm",
        "context_questions",
        ["question_norm"],
    )
    op.create_index(
        "ix_context_questions_topic_id", "context_questions", ["topic_id"]
    )

    op.create_table(
        "context_changes",
        sa.Column("change_id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("topic_id", sa.String(), nullable=True),
        sa.Column("topic_key", sa.String(), nullable=False),
        sa.Column("change_type", sa.String(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("old_bundle_id", sa.String(), nullable=True),
        sa.Column("new_bundle_id", sa.String(), nullable=True),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_context_changes_workspace_id", "context_changes", ["workspace_id"]
    )
    op.create_index(
        "ix_context_changes_topic_id", "context_changes", ["topic_id"]
    )
    op.create_index(
        "ix_context_changes_topic_key", "context_changes", ["topic_key"]
    )

    op.create_table(
        "metric_catalog",
        sa.Column("row_id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("metric_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("source_systems_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "workspace_id", "metric_id", name="uq_metric_catalog_ws_metric"
        ),
    )
    op.create_index(
        "ix_metric_catalog_workspace_id", "metric_catalog", ["workspace_id"]
    )

    op.create_table(
        "metric_snapshots",
        sa.Column("snapshot_id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("metric_id", sa.String(), nullable=False),
        sa.Column("source_system", sa.String(), nullable=False),
        sa.Column("as_of_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Numeric(18, 6), nullable=False),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_metric_snapshots_workspace_id",
        "metric_snapshots",
        ["workspace_id"],
    )
    op.create_index(
        "ix_metric_snapshots_metric_id", "metric_snapshots", ["metric_id"]
    )
    op.create_index(
        "ix_metric_snapshots_as_of_date", "metric_snapshots", ["as_of_date"]
    )


def downgrade() -> None:
    for name in (
        "ix_metric_snapshots_as_of_date",
        "ix_metric_snapshots_metric_id",
        "ix_metric_snapshots_workspace_id",
    ):
        op.drop_index(name, table_name="metric_snapshots")
    op.drop_table("metric_snapshots")

    op.drop_index("ix_metric_catalog_workspace_id", table_name="metric_catalog")
    op.drop_table("metric_catalog")

    for name in (
        "ix_context_changes_topic_key",
        "ix_context_changes_topic_id",
        "ix_context_changes_workspace_id",
    ):
        op.drop_index(name, table_name="context_changes")
    op.drop_table("context_changes")

    for name in (
        "ix_context_questions_topic_id",
        "ix_context_questions_question_norm",
        "ix_context_questions_workspace_id",
    ):
        op.drop_index(name, table_name="context_questions")
    op.drop_table("context_questions")
