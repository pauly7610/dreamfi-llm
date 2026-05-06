"""add connector settings

Revision ID: 20260506_0009
Revises: 20260506_0008
Create Date: 2026-05-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260506_0009"
down_revision = "20260506_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_settings",
        sa.Column("connector_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("credential_status", sa.String(), nullable=False),
        sa.Column("secret_last_four", sa.String(), nullable=True),
        sa.Column("secret_sha256", sa.String(), nullable=True),
        sa.Column("secret_label", sa.String(), nullable=True),
        sa.Column("validation_status", sa.String(), nullable=False),
        sa.Column("validation_error", sa.Text(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("document_set_id", sa.Integer(), nullable=True),
        sa.Column("document_set_name", sa.String(), nullable=True),
        sa.Column("document_set_present", sa.Boolean(), nullable=False),
        sa.Column("retrieval_status", sa.String(), nullable=True),
        sa.Column("freshest_document_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activation_status", sa.String(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_probe_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("connector_id"),
    )
    op.create_index(
        "ix_connector_settings_activation_status",
        "connector_settings",
        ["activation_status"],
    )
    op.create_index(
        "ix_connector_settings_validation_status",
        "connector_settings",
        ["validation_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_connector_settings_validation_status", table_name="connector_settings")
    op.drop_index("ix_connector_settings_activation_status", table_name="connector_settings")
    op.drop_table("connector_settings")
