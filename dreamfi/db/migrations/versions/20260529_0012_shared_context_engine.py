"""shared context engine

Revision ID: 20260529_0012
Revises: 20260514_0011
Create Date: 2026-05-29
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260529_0012"
down_revision = "20260514_0011"
branch_labels = None
depends_on = None


_DEFAULT_EXPORT_READINESS_THRESHOLD = 0.80


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


def _create_publish_readiness_trigger() -> None:
    if _dialect_name() != "postgresql":
        return

    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION dreamfi_publish_log_readiness_check()
        RETURNS TRIGGER AS $$
        DECLARE
            readiness NUMERIC;
        BEGIN
            IF NEW.decision <> 'published' THEN
                RETURN NEW;
            END IF;

            SELECT export_readiness INTO readiness
            FROM eval_outputs
            WHERE output_id = NEW.output_id;

            IF readiness IS NULL THEN
                RAISE EXCEPTION
                    'publish_log: output % has NULL export_readiness',
                    NEW.output_id;
            END IF;

            IF readiness < {_DEFAULT_EXPORT_READINESS_THRESHOLD} THEN
                RAISE EXCEPTION
                    'publish_log: output % export_readiness % below threshold {_DEFAULT_EXPORT_READINESS_THRESHOLD}',
                    NEW.output_id, readiness;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_publish_log_readiness_check ON publish_log;
        CREATE TRIGGER trg_publish_log_readiness_check
        BEFORE INSERT ON publish_log
        FOR EACH ROW
        EXECUTE FUNCTION dreamfi_publish_log_readiness_check();
        """
    )


def upgrade() -> None:
    _create_publish_readiness_trigger()

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
        "ix_context_bundles_workspace_id", "context_bundles", ["workspace_id"]
    )
    op.create_index(
        "ix_context_bundles_topic_key", "context_bundles", ["topic_key"]
    )
    op.create_index(
        "ix_context_bundles_workspace_topic_key",
        "context_bundles",
        ["workspace_id", "topic_key"],
    )
    op.create_index(
        "ix_context_bundles_refreshed_at", "context_bundles", ["refreshed_at"]
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
    op.create_index("ix_context_sources_bundle_id", "context_sources", ["bundle_id"])

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
    op.create_index("ix_context_claims_bundle_id", "context_claims", ["bundle_id"])

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
    op.create_index("ix_open_questions_bundle_id", "open_questions", ["bundle_id"])

    op.create_table(
        "topics",
        sa.Column("topic_id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("canonical_name", sa.String(), nullable=False),
        sa.Column("attributes_json", _json_type(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=_timestamp_default(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "workspace_id", "canonical_name", "type", name="uq_topics_ws_name_type"
        ),
    )
    op.create_index("ix_topics_workspace_id", "topics", ["workspace_id"])
    op.create_index("ix_topics_type", "topics", ["type"])

    op.create_table(
        "topic_aliases",
        sa.Column("alias_id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column(
            "topic_id",
            sa.String(),
            sa.ForeignKey("topics.topic_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(), nullable=False),
        sa.Column("alias_norm", sa.String(), nullable=False),
        sa.UniqueConstraint("workspace_id", "alias_norm", name="uq_topic_aliases_ws_norm"),
    )
    op.create_index(
        "ix_topic_aliases_workspace_id", "topic_aliases", ["workspace_id"]
    )
    op.create_index("ix_topic_aliases_topic_id", "topic_aliases", ["topic_id"])

    op.create_table(
        "topic_relations",
        sa.Column("relation_id", sa.String(), primary_key=True),
        sa.Column(
            "from_id",
            sa.String(),
            sa.ForeignKey("topics.topic_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "to_id",
            sa.String(),
            sa.ForeignKey("topics.topic_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relation_type", sa.String(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default="1"),
        sa.Column("source_bundle_id", sa.String(), nullable=True),
    )
    op.create_index("ix_topic_relations_from_id", "topic_relations", ["from_id"])
    op.create_index("ix_topic_relations_to_id", "topic_relations", ["to_id"])

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
        sa.Column("tokens_json", _json_type(), nullable=False),
        sa.Column("private", sa.Boolean(), nullable=False, server_default=_false_default()),
        sa.Column(
            "asked_at",
            sa.DateTime(timezone=True),
            server_default=_timestamp_default(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_context_questions_workspace_id", "context_questions", ["workspace_id"]
    )
    op.create_index(
        "ix_context_questions_question_norm", "context_questions", ["question_norm"]
    )
    op.create_index("ix_context_questions_topic_id", "context_questions", ["topic_id"])

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
            server_default=_timestamp_default(),
            nullable=False,
        ),
    )
    op.create_index("ix_context_changes_workspace_id", "context_changes", ["workspace_id"])
    op.create_index("ix_context_changes_topic_id", "context_changes", ["topic_id"])
    op.create_index("ix_context_changes_topic_key", "context_changes", ["topic_key"])

    op.create_table(
        "metric_catalog",
        sa.Column("row_id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("metric_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("source_systems_json", _json_type(), nullable=False),
        sa.UniqueConstraint(
            "workspace_id", "metric_id", name="uq_metric_catalog_ws_metric"
        ),
    )
    op.create_index("ix_metric_catalog_workspace_id", "metric_catalog", ["workspace_id"])

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
            server_default=_timestamp_default(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_metric_snapshots_workspace_id", "metric_snapshots", ["workspace_id"]
    )
    op.create_index("ix_metric_snapshots_metric_id", "metric_snapshots", ["metric_id"])
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

    op.drop_index("ix_topic_relations_to_id", table_name="topic_relations")
    op.drop_index("ix_topic_relations_from_id", table_name="topic_relations")
    op.drop_table("topic_relations")

    op.drop_index("ix_topic_aliases_topic_id", table_name="topic_aliases")
    op.drop_index("ix_topic_aliases_workspace_id", table_name="topic_aliases")
    op.drop_table("topic_aliases")

    op.drop_index("ix_topics_type", table_name="topics")
    op.drop_index("ix_topics_workspace_id", table_name="topics")
    op.drop_table("topics")

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
    op.drop_index("ix_context_bundles_workspace_topic_key", table_name="context_bundles")
    op.drop_index("ix_context_bundles_topic_key", table_name="context_bundles")
    op.drop_index("ix_context_bundles_workspace_id", table_name="context_bundles")
    op.drop_table("context_bundles")

    if _dialect_name() == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_publish_log_readiness_check ON publish_log;"
        )
        op.execute("DROP FUNCTION IF EXISTS dreamfi_publish_log_readiness_check();")
