"""add workflow traces and skill candidates

Revision ID: 20260529_0013
Revises: 20260529_0012
Create Date: 2026-05-29
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260529_0013"
down_revision = "20260529_0012"
branch_labels = None
depends_on = None


def _dialect_name() -> str:
    return str(op.get_bind().dialect.name)


def _json_type() -> Any:
    if _dialect_name() == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())  # type: ignore[no-untyped-call]
    return sa.JSON()


def _timestamp_default() -> sa.TextClause:
    if _dialect_name() == "postgresql":
        return sa.text("now()")
    return sa.text("CURRENT_TIMESTAMP")


def _false_default() -> sa.TextClause:
    if _dialect_name() == "postgresql":
        return sa.text("false")
    return sa.text("0")


def upgrade() -> None:
    op.create_table(
        "workflow_traces",
        sa.Column("trace_id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("workflow_type", sa.String(), nullable=False),
        sa.Column("starter_question_hash", sa.String(), nullable=False),
        sa.Column("starter_question_pattern", sa.Text(), nullable=False),
        sa.Column("topic_id", sa.String(), nullable=True),
        sa.Column("source_ids_json", _json_type(), nullable=False),
        sa.Column("required_identifiers_json", _json_type(), nullable=False),
        sa.Column("steps_json", _json_type(), nullable=False),
        sa.Column("accepted_evidence_json", _json_type(), nullable=False),
        sa.Column("rejected_evidence_json", _json_type(), nullable=False),
        sa.Column("human_edits_json", _json_type(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False, server_default="completed"),
        sa.Column("final_artifact_ref", sa.String(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("private", sa.Boolean(), nullable=False, server_default=_false_default()),
        sa.Column("metadata_json", _json_type(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=_timestamp_default(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_workflow_traces_workspace_created",
        "workflow_traces",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_workflow_traces_workflow_created",
        "workflow_traces",
        ["workflow_type", "created_at"],
    )
    op.create_index(
        "ix_workflow_traces_topic_created",
        "workflow_traces",
        ["topic_id", "created_at"],
    )
    op.create_index(
        "ix_workflow_traces_outcome_created",
        "workflow_traces",
        ["outcome", "created_at"],
    )

    op.create_table(
        "skill_candidates",
        sa.Column("candidate_id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("workflow_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("source_trace_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trace_ids_json", _json_type(), nullable=False),
        sa.Column("intent_summary", sa.Text(), nullable=False),
        sa.Column("required_inputs_json", _json_type(), nullable=False),
        sa.Column("source_contract_json", _json_type(), nullable=False),
        sa.Column("tool_plan_json", _json_type(), nullable=False),
        sa.Column("freshness_contract_json", _json_type(), nullable=False),
        sa.Column("answer_contract_json", _json_type(), nullable=False),
        sa.Column("refusal_rules_json", _json_type(), nullable=False),
        sa.Column("eval_seed_cases_json", _json_type(), nullable=False),
        sa.Column("evidence_json", _json_type(), nullable=False),
        sa.Column("reviewer_id", sa.String(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=_timestamp_default(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=_timestamp_default(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_skill_candidates_status_created",
        "skill_candidates",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_skill_candidates_workspace_workflow",
        "skill_candidates",
        ["workspace_id", "workflow_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_skill_candidates_workspace_workflow", table_name="skill_candidates"
    )
    op.drop_index("ix_skill_candidates_status_created", table_name="skill_candidates")
    op.drop_table("skill_candidates")

    op.drop_index("ix_workflow_traces_outcome_created", table_name="workflow_traces")
    op.drop_index("ix_workflow_traces_topic_created", table_name="workflow_traces")
    op.drop_index("ix_workflow_traces_workflow_created", table_name="workflow_traces")
    op.drop_index("ix_workflow_traces_workspace_created", table_name="workflow_traces")
    op.drop_table("workflow_traces")
