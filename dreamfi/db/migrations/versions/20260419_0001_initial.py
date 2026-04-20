"""Initial DreamFi schema.

Revision ID: 20260419_0001
Revises:
Create Date: 2026-04-19

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260419_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("skill_id", sa.String(), primary_key=True),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("eval_template_path", sa.String(), nullable=False),
        sa.Column("eval_runner_path", sa.String(), nullable=False),
        sa.Column("criteria_json", sa.JSON(), nullable=False),
        sa.Column("onyx_persona_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "prompt_versions",
        sa.Column("prompt_version_id", sa.String(), primary_key=True),
        sa.Column(
            "skill_id",
            sa.String(),
            sa.ForeignKey("skills.skill_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "parent_version_id",
            sa.String(),
            sa.ForeignKey("prompt_versions.prompt_version_id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("skill_id", "version", name="uq_prompt_versions_skill_version"),
    )
    op.create_index(
        "one_active_per_skill",
        "prompt_versions",
        ["skill_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
        sqlite_where=sa.text("is_active"),
    )

    op.create_table(
        "eval_rounds",
        sa.Column("round_id", sa.String(), primary_key=True),
        sa.Column("skill_id", sa.String(), sa.ForeignKey("skills.skill_id"), nullable=False),
        sa.Column(
            "prompt_version_id",
            sa.String(),
            sa.ForeignKey("prompt_versions.prompt_version_id"),
            nullable=False,
        ),
        sa.Column("n_inputs", sa.Integer(), nullable=False),
        sa.Column("n_outputs_per_input", sa.Integer(), nullable=False),
        sa.Column("total_outputs", sa.Integer(), nullable=False),
        sa.Column("total_passes", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(6, 4), nullable=False),
        sa.Column("previous_score", sa.Numeric(6, 4), nullable=True),
        sa.Column("improvement", sa.Numeric(7, 4), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("artifacts_path", sa.String(), nullable=False),
    )

    op.create_table(
        "eval_outputs",
        sa.Column("output_id", sa.String(), primary_key=True),
        sa.Column(
            "round_id",
            sa.String(),
            sa.ForeignKey("eval_rounds.round_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("test_input_label", sa.String(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("generated_text", sa.Text(), nullable=False),
        sa.Column("criteria_json", sa.JSON(), nullable=False),
        sa.Column("pass_fail", sa.String(), nullable=False),
        sa.Column("onyx_chat_session_id", sa.String(), nullable=True),
        sa.Column("onyx_message_id", sa.Integer(), nullable=True),
        sa.Column("onyx_citations_json", sa.JSON(), nullable=True),
        sa.Column("freshness_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "gold_examples",
        sa.Column("gold_id", sa.String(), primary_key=True),
        sa.Column("skill_id", sa.String(), sa.ForeignKey("skills.skill_id"), nullable=False),
        sa.Column("scenario_type", sa.String(), nullable=False),
        sa.Column("input_context_json", sa.JSON(), nullable=False),
        sa.Column("output_text", sa.Text(), nullable=False),
        sa.Column(
            "prompt_version_id",
            sa.String(),
            sa.ForeignKey("prompt_versions.prompt_version_id"),
            nullable=False,
        ),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("gold_examples_lookup", "gold_examples", ["skill_id", "scenario_type"])

    op.create_table(
        "publish_log",
        sa.Column("publish_id", sa.String(), primary_key=True),
        sa.Column("skill_id", sa.String(), sa.ForeignKey("skills.skill_id"), nullable=False),
        sa.Column(
            "prompt_version_id",
            sa.String(),
            sa.ForeignKey("prompt_versions.prompt_version_id"),
            nullable=False,
        ),
        sa.Column(
            "output_id",
            sa.String(),
            sa.ForeignKey("eval_outputs.output_id"),
            nullable=False,
        ),
        sa.Column("destination", sa.String(), nullable=False),
        sa.Column("destination_ref", sa.String(), nullable=True),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "onyx_document_map",
        sa.Column("onyx_document_id", sa.String(), primary_key=True),
        sa.Column("dreamfi_topic_tag", sa.String(), nullable=True),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("onyx_document_map")
    op.drop_table("publish_log")
    op.drop_index("gold_examples_lookup", table_name="gold_examples")
    op.drop_table("gold_examples")
    op.drop_table("eval_outputs")
    op.drop_table("eval_rounds")
    op.drop_index("one_active_per_skill", table_name="prompt_versions")
    op.drop_table("prompt_versions")
    op.drop_table("skills")
