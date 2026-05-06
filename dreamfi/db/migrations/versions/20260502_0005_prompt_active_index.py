"""enforce one active prompt per skill

Revision ID: 20260502_0005
Revises: 20260428_0004
Create Date: 2026-05-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260502_0005"
down_revision = "20260428_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    active_rows = connection.execute(
        sa.text(
            """
            SELECT prompt_version_id, skill_id
            FROM prompt_versions
            WHERE is_active = :active
            ORDER BY skill_id, COALESCE(activated_at, created_at) DESC, created_at DESC
            """
        ),
        {"active": True},
    ).mappings()

    seen_skill_ids: set[str] = set()
    duplicate_prompt_ids: list[str] = []
    for row in active_rows:
        skill_id = str(row["skill_id"])
        if skill_id in seen_skill_ids:
            duplicate_prompt_ids.append(str(row["prompt_version_id"]))
        else:
            seen_skill_ids.add(skill_id)

    for prompt_version_id in duplicate_prompt_ids:
        connection.execute(
            sa.text(
                """
                UPDATE prompt_versions
                SET is_active = :inactive, deactivated_at = CURRENT_TIMESTAMP
                WHERE prompt_version_id = :prompt_version_id
                """
            ),
            {"inactive": False, "prompt_version_id": prompt_version_id},
        )

    op.create_index(
        "ix_prompt_versions_one_active_per_skill",
        "prompt_versions",
        ["skill_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
        sqlite_where=sa.text("is_active = 1"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_prompt_versions_one_active_per_skill",
        table_name="prompt_versions",
    )
