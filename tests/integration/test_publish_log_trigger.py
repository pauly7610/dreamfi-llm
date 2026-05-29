"""DB-level enforcement of export_readiness on publish_log (X1, layer 3).

Postgres-only. Skipped unless DREAMFI_TEST_POSTGRES_URL points at a reachable
Postgres that can be mutated by the test (a throwaway DB).
"""
from __future__ import annotations

import os
from decimal import Decimal
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Migration module name starts with a digit; use the value directly.
# Keep in sync with versions/20260420_0003_publish_log_trigger.py::_DEFAULT_THRESHOLD.
_DEFAULT_THRESHOLD = 0.80

PG_URL = os.environ.get("DREAMFI_TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(
    not PG_URL, reason="DREAMFI_TEST_POSTGRES_URL not set; Postgres trigger test skipped"
)


@pytest.fixture
def pg_session():
    from dreamfi.db.models import Base

    engine = create_engine(PG_URL)  # type: ignore[arg-type]
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    # Apply migration 0003 manually (Postgres trigger).
    with engine.begin() as conn:
        conn.execute(
            text(
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
                        RAISE EXCEPTION 'publish_log: output % has NULL export_readiness', NEW.output_id;
                    END IF;
                    IF readiness < {_DEFAULT_THRESHOLD} THEN
                        RAISE EXCEPTION 'publish_log: output % export_readiness % below threshold',
                            NEW.output_id, readiness;
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                """
            )
        )
        conn.execute(
            text(
                """
                DROP TRIGGER IF EXISTS trg_publish_log_readiness_check ON publish_log;
                CREATE TRIGGER trg_publish_log_readiness_check
                BEFORE INSERT ON publish_log
                FOR EACH ROW
                EXECUTE FUNCTION dreamfi_publish_log_readiness_check();
                """
            )
        )

    s = Session(engine)
    yield s, engine
    s.close()
    Base.metadata.drop_all(engine)


def _make_output(session: Session, *, readiness: float | None) -> str:
    from dreamfi.db.models import EvalOutput, EvalRound, PromptVersion, Skill

    session.add(
        Skill(
            skill_id="meeting_summary",
            display_name="Meeting Summary",
            description="",
            eval_template_path="evals/meeting-summary.md",
            eval_runner_path="evals/runners/run_meeting_summary_eval.py",
            criteria_json={},
        )
    )
    pv = PromptVersion(
        skill_id="meeting_summary",
        version=1,
        template="t",
        system_prompt="",
        is_active=True,
    )
    session.add(pv)
    session.flush()
    round_row = EvalRound(
        skill_id="meeting_summary",
        prompt_version_id=pv.prompt_version_id,
        n_inputs=1,
        n_outputs_per_input=1,
        total_outputs=1,
        total_passes=1,
        score=Decimal("1.0"),
        started_at=datetime.now(timezone.utc),
        artifacts_path="",
    )
    session.add(round_row)
    session.flush()
    output = EvalOutput(
        round_id=round_row.round_id,
        test_input_label="l",
        attempt=1,
        generated_text="g",
        criteria_json={},
        pass_fail="pass",
        confidence=Decimal("0.9"),
        export_readiness=(None if readiness is None else Decimal(str(readiness))),
    )
    session.add(output)
    session.commit()
    return output.output_id


def test_trigger_rejects_insert_when_readiness_below_threshold(pg_session) -> None:
    session, engine = pg_session
    output_id = _make_output(session, readiness=0.50)

    with engine.begin() as conn, pytest.raises(Exception) as exc_info:
        conn.execute(
            text(
                """
                INSERT INTO publish_log
                (publish_id, skill_id, prompt_version_id, output_id, destination,
                 decision, created_at)
                VALUES
                ('pub-1', 'meeting_summary',
                 (SELECT prompt_version_id FROM prompt_versions LIMIT 1),
                 :oid, 'return-only', 'published', now())
                """
            ),
            {"oid": output_id},
        )
    assert "export_readiness" in str(exc_info.value).lower() or "below threshold" in str(exc_info.value)


def test_trigger_rejects_insert_when_readiness_null(pg_session) -> None:
    session, engine = pg_session
    output_id = _make_output(session, readiness=None)

    with engine.begin() as conn, pytest.raises(Exception) as exc_info:
        conn.execute(
            text(
                """
                INSERT INTO publish_log
                (publish_id, skill_id, prompt_version_id, output_id, destination,
                 decision, created_at)
                VALUES
                ('pub-2', 'meeting_summary',
                 (SELECT prompt_version_id FROM prompt_versions LIMIT 1),
                 :oid, 'return-only', 'published', now())
                """
            ),
            {"oid": output_id},
        )
    assert "null" in str(exc_info.value).lower() or "export_readiness" in str(exc_info.value).lower()


def test_trigger_allows_blocked_rows_regardless_of_readiness(pg_session) -> None:
    session, engine = pg_session
    output_id = _make_output(session, readiness=None)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO publish_log
                (publish_id, skill_id, prompt_version_id, output_id, destination,
                 decision, reason, created_at)
                VALUES
                ('pub-3', 'meeting_summary',
                 (SELECT prompt_version_id FROM prompt_versions LIMIT 1),
                 :oid, 'return-only', 'blocked', 'missing_export_readiness', now())
                """
            ),
            {"oid": output_id},
        )
    # No exception means the trigger correctly ignored non-published rows.
