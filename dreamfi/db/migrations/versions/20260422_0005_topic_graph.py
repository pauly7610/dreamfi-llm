"""topic graph (C5)

Revision ID: 20260422_0005
Revises: 20260421_0004
Create Date: 2026-04-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260422_0005"
down_revision = "20260421_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "topics",
        sa.Column("topic_id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("canonical_name", sa.String(), nullable=False),
        sa.Column("attributes_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
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
        sa.UniqueConstraint(
            "workspace_id", "alias_norm", name="uq_topic_aliases_ws_norm"
        ),
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
        sa.Column(
            "confidence", sa.Numeric(4, 3), nullable=False, server_default="1.000"
        ),
        sa.Column("source_bundle_id", sa.String(), nullable=True),
    )
    op.create_index("ix_topic_relations_from_id", "topic_relations", ["from_id"])
    op.create_index("ix_topic_relations_to_id", "topic_relations", ["to_id"])


def downgrade() -> None:
    op.drop_index("ix_topic_relations_to_id", table_name="topic_relations")
    op.drop_index("ix_topic_relations_from_id", table_name="topic_relations")
    op.drop_table("topic_relations")

    op.drop_index("ix_topic_aliases_topic_id", table_name="topic_aliases")
    op.drop_index("ix_topic_aliases_workspace_id", table_name="topic_aliases")
    op.drop_table("topic_aliases")

    op.drop_index("ix_topics_type", table_name="topics")
    op.drop_index("ix_topics_workspace_id", table_name="topics")
    op.drop_table("topics")
