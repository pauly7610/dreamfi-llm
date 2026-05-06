"""add learning loop tables

Revision ID: 20260504_0007
Revises: 20260504_0006
Create Date: 2026-05-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260504_0007"
down_revision = "20260504_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artifact_feedback",
        sa.Column("feedback_id", sa.String(), nullable=False),
        sa.Column("output_id", sa.String(), nullable=False),
        sa.Column("reviewer_id", sa.String(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("final_text_hash", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("gold_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["gold_id"], ["gold_examples.gold_id"]),
        sa.ForeignKeyConstraint(["output_id"], ["eval_outputs.output_id"]),
        sa.PrimaryKeyConstraint("feedback_id"),
    )
    op.create_index(
        "ix_artifact_feedback_output_created_at",
        "artifact_feedback",
        ["output_id", "created_at"],
    )
    op.create_index(
        "ix_artifact_feedback_reviewer_created_at",
        "artifact_feedback",
        ["reviewer_id", "created_at"],
    )
    op.create_index(
        "ix_artifact_feedback_outcome_created_at",
        "artifact_feedback",
        ["outcome", "created_at"],
    )

    op.create_table(
        "learning_proposals",
        sa.Column("proposal_id", sa.String(), nullable=False),
        sa.Column("skill_id", sa.String(), nullable=False),
        sa.Column("prompt_version_id", sa.String(), nullable=True),
        sa.Column("cluster_key", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("proposed_prompt_patch", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("source_failure_count", sa.Integer(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("reviewer_id", sa.String(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_prompt_version_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_prompt_version_id"], ["prompt_versions.prompt_version_id"]),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["prompt_versions.prompt_version_id"]),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.skill_id"]),
        sa.PrimaryKeyConstraint("proposal_id"),
    )
    op.create_index(
        "ix_learning_proposals_status_created_at",
        "learning_proposals",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_learning_proposals_skill_status",
        "learning_proposals",
        ["skill_id", "status"],
    )
    op.create_index(
        "ix_learning_proposals_cluster",
        "learning_proposals",
        ["cluster_key"],
    )

    op.create_table(
        "production_outcomes",
        sa.Column("outcome_id", sa.String(), nullable=False),
        sa.Column("output_id", sa.String(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("final_text_hash", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["output_id"], ["eval_outputs.output_id"]),
        sa.PrimaryKeyConstraint("outcome_id"),
    )
    op.create_index(
        "ix_production_outcomes_output_created_at",
        "production_outcomes",
        ["output_id", "created_at"],
    )
    op.create_index(
        "ix_production_outcomes_outcome_created_at",
        "production_outcomes",
        ["outcome", "created_at"],
    )

    op.create_table(
        "replay_schedules",
        sa.Column("schedule_id", sa.String(), nullable=False),
        sa.Column("replay_type", sa.String(), nullable=False),
        sa.Column("skill_id", sa.String(), nullable=True),
        sa.Column("prompt_version_id", sa.String(), nullable=True),
        sa.Column("cadence_days", sa.Integer(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["prompt_versions.prompt_version_id"]),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.skill_id"]),
        sa.PrimaryKeyConstraint("schedule_id"),
    )
    op.create_index(
        "ix_replay_schedules_active_next_run",
        "replay_schedules",
        ["is_active", "next_run_at"],
    )
    op.create_index(
        "ix_replay_schedules_skill_active",
        "replay_schedules",
        ["skill_id", "is_active"],
    )

    op.create_table(
        "replay_runs",
        sa.Column("replay_run_id", sa.String(), nullable=False),
        sa.Column("schedule_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("skill_id", sa.String(), nullable=True),
        sa.Column("prompt_version_id", sa.String(), nullable=True),
        sa.Column("round_id", sa.String(), nullable=True),
        sa.Column("output_id", sa.String(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["output_id"], ["eval_outputs.output_id"]),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["prompt_versions.prompt_version_id"]),
        sa.ForeignKeyConstraint(["round_id"], ["eval_rounds.round_id"]),
        sa.ForeignKeyConstraint(["schedule_id"], ["replay_schedules.schedule_id"]),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.skill_id"]),
        sa.PrimaryKeyConstraint("replay_run_id"),
    )
    op.create_index(
        "ix_replay_runs_schedule_started_at",
        "replay_runs",
        ["schedule_id", "started_at"],
    )
    op.create_index(
        "ix_replay_runs_status_started_at",
        "replay_runs",
        ["status", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_replay_runs_status_started_at", table_name="replay_runs")
    op.drop_index("ix_replay_runs_schedule_started_at", table_name="replay_runs")
    op.drop_table("replay_runs")
    op.drop_index("ix_replay_schedules_skill_active", table_name="replay_schedules")
    op.drop_index("ix_replay_schedules_active_next_run", table_name="replay_schedules")
    op.drop_table("replay_schedules")
    op.drop_index("ix_production_outcomes_outcome_created_at", table_name="production_outcomes")
    op.drop_index("ix_production_outcomes_output_created_at", table_name="production_outcomes")
    op.drop_table("production_outcomes")
    op.drop_index("ix_learning_proposals_cluster", table_name="learning_proposals")
    op.drop_index("ix_learning_proposals_skill_status", table_name="learning_proposals")
    op.drop_index("ix_learning_proposals_status_created_at", table_name="learning_proposals")
    op.drop_table("learning_proposals")
    op.drop_index("ix_artifact_feedback_outcome_created_at", table_name="artifact_feedback")
    op.drop_index("ix_artifact_feedback_reviewer_created_at", table_name="artifact_feedback")
    op.drop_index("ix_artifact_feedback_output_created_at", table_name="artifact_feedback")
    op.drop_table("artifact_feedback")
