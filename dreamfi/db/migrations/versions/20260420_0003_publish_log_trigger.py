"""publish_log export-readiness trigger

Revision ID: 20260420_0003
Revises: 20260420_0002
Create Date: 2026-04-20

Adds a Postgres BEFORE INSERT trigger on `publish_log` that refuses to
record a `decision='published'` row for an `eval_outputs` row whose
`export_readiness` is NULL or below the configured threshold.

The trigger is Postgres-only. SQLite test environments rely on the
Python-level `PublishGuard` check in `dreamfi/promotion/gate.py` for
equivalent protection.
"""

from alembic import op


revision = "20260420_0003"
down_revision = "20260420_0002"
branch_labels = None
depends_on = None


# Keep in sync with Settings.dreamfi_export_readiness_threshold.
_DEFAULT_THRESHOLD = 0.80


def _dialect_name() -> str:
    return op.get_bind().dialect.name


def upgrade() -> None:
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

            IF readiness < {_DEFAULT_THRESHOLD} THEN
                RAISE EXCEPTION
                    'publish_log: output % export_readiness % below threshold {_DEFAULT_THRESHOLD}',
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


def downgrade() -> None:
    if _dialect_name() != "postgresql":
        return

    op.execute(
        "DROP TRIGGER IF EXISTS trg_publish_log_readiness_check ON publish_log;"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS dreamfi_publish_log_readiness_check();"
    )
