"""add custom connector sync tables

Revision ID: 20260507_0010
Revises: 20260506_0009
Create Date: 2026-05-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260507_0010"
down_revision = "20260506_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("connector_settings") as batch_op:
        batch_op.add_column(sa.Column("secret_ciphertext", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("secret_key_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("config_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))

    with op.batch_alter_table("connector_settings") as batch_op:
        batch_op.alter_column("config_json", server_default=None)

    op.create_table(
        "connector_sync_runs",
        sa.Column("sync_run_id", sa.String(), nullable=False),
        sa.Column("connector_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("trigger", sa.String(), nullable=False),
        sa.Column("pulled_count", sa.Integer(), nullable=False),
        sa.Column("persisted_count", sa.Integer(), nullable=False),
        sa.Column("ingested_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("cursor_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["connector_id"], ["connector_settings.connector_id"]),
        sa.PrimaryKeyConstraint("sync_run_id"),
    )
    op.create_index(
        "ix_connector_sync_runs_connector_started",
        "connector_sync_runs",
        ["connector_id", "started_at"],
    )
    op.create_index(
        "ix_connector_sync_runs_status_started",
        "connector_sync_runs",
        ["status", "started_at"],
    )

    op.create_table(
        "connector_documents",
        sa.Column("connector_document_id", sa.String(), nullable=False),
        sa.Column("connector_id", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("doc_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("sync_run_id", sa.String(), nullable=True),
        sa.Column("onyx_document_id", sa.String(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["connector_settings.connector_id"]),
        sa.ForeignKeyConstraint(["sync_run_id"], ["connector_sync_runs.sync_run_id"]),
        sa.PrimaryKeyConstraint("connector_document_id"),
        sa.UniqueConstraint("connector_id", "external_id", name="uq_connector_documents_source_external"),
    )
    op.create_index(
        "ix_connector_documents_connector_updated",
        "connector_documents",
        ["connector_id", "doc_updated_at"],
    )
    op.create_index(
        "ix_connector_documents_content_hash",
        "connector_documents",
        ["content_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_connector_documents_content_hash", table_name="connector_documents")
    op.drop_index("ix_connector_documents_connector_updated", table_name="connector_documents")
    op.drop_table("connector_documents")
    op.drop_index("ix_connector_sync_runs_status_started", table_name="connector_sync_runs")
    op.drop_index("ix_connector_sync_runs_connector_started", table_name="connector_sync_runs")
    op.drop_table("connector_sync_runs")

    with op.batch_alter_table("connector_settings") as batch_op:
        batch_op.drop_column("config_json")
        batch_op.drop_column("secret_key_id")
        batch_op.drop_column("secret_ciphertext")
