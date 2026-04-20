"""context engine (C1)

Revision ID: 20260421_0004
Revises: 20260420_0003
Create Date: 2026-04-21

Adds the tables that back the typed ContextBundle:

- ``context_bundles`` — one row per bundle, workspace-scoped, indexed on
  ``topic_key`` and ``refreshed_at`` for cache lookup and staleness scans.
- ``context_sources`` — raw inputs (Jira issue, Confluence page, etc.) with
  a ``payload_hash`` for change detection and a ``raw_ref`` pointing at the
  cached payload in object storage.
- ``context_entities`` — canonical entities extracted from sources, with
  their relationships stored as JSON on the row.
- ``context_claims`` — what we believe is true, each with ``sot_id`` and
  ``citation_ids_json`` for provenance.
- ``open_questions`` — what we don't know yet and why.
"""
from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260421_0004"
down_revision = "20260420_0003"
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


def upgrade() -> None:
    op.create_table(
        "context_bundles",
        sa.Column("bundle_id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("topic_key", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=_timestamp_default(),
            nullable=False,
        ),
        sa.Column(
            "refreshed_at",
            sa.DateTime(timezone=True),
            server_default=_timestamp_default(),
            nullable=False,
        ),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("freshness_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("coverage_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
    )
    op.create_index(
        "ix_context_bundles_workspace_topic_key",
        "context_bundles",
        ["workspace_id", "topic_key"],
    )
    op.create_index(
        "ix_context_bundles_refreshed_at",
        "context_bundles",
        ["refreshed_at"],
    )

    op.create_table(
        "context_sources",
        sa.Column("source_row_id", sa.String(), primary_key=True),
        sa.Column(
            "bundle_id",
            sa.String(),
            sa.ForeignKey("context_bundles.bundle_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_hash", sa.String(), nullable=False),
        sa.Column("raw_ref", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_context_sources_bundle_id", "context_sources", ["bundle_id"]
    )

    op.create_table(
        "context_entities",
        sa.Column("entity_row_id", sa.String(), primary_key=True),
        sa.Column(
            "bundle_id",
            sa.String(),
            sa.ForeignKey("context_bundles.bundle_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("relationships_json", _json_type(), nullable=False),
    )
    op.create_index(
        "ix_context_entities_bundle_id", "context_entities", ["bundle_id"]
    )
    op.create_index(
        "ix_context_entities_type_id",
        "context_entities",
        ["entity_type", "entity_id"],
    )

    op.create_table(
        "context_claims",
        sa.Column("claim_id", sa.String(), primary_key=True),
        sa.Column(
            "bundle_id",
            sa.String(),
            sa.ForeignKey("context_bundles.bundle_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("sot_id", sa.String(), nullable=True),
        sa.Column("citation_ids_json", _json_type(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default="0"),
        sa.Column(
            "last_verified_at",
            sa.DateTime(timezone=True),
            server_default=_timestamp_default(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_context_claims_bundle_id", "context_claims", ["bundle_id"]
    )

    op.create_table(
        "open_questions",
        sa.Column("question_id", sa.String(), primary_key=True),
        sa.Column(
            "bundle_id",
            sa.String(),
            sa.ForeignKey("context_bundles.bundle_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("why_open", sa.String(), nullable=False),
        sa.Column("suggested_owner", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_open_questions_bundle_id", "open_questions", ["bundle_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_open_questions_bundle_id", table_name="open_questions")
    op.drop_table("open_questions")

    op.drop_index("ix_context_claims_bundle_id", table_name="context_claims")
    op.drop_table("context_claims")

    op.drop_index("ix_context_entities_type_id", table_name="context_entities")
    op.drop_index("ix_context_entities_bundle_id", table_name="context_entities")
    op.drop_table("context_entities")

    op.drop_index("ix_context_sources_bundle_id", table_name="context_sources")
    op.drop_table("context_sources")

    op.drop_index("ix_context_bundles_refreshed_at", table_name="context_bundles")
    op.drop_index(
        "ix_context_bundles_workspace_topic_key", table_name="context_bundles"
    )
    op.drop_table("context_bundles")
