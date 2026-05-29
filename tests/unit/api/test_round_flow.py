"""End-to-end-ish tests for the round → promote → publish flow."""
from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dreamfi.api.app import create_app
from dreamfi.api.deps import get_db_session, get_onyx_client
from dreamfi.db.models import (
    Base,
    EvalOutput,
    EvalRound,
    GoldDriftEvent,
    GoldExample,
    PromptVersion,
    Skill,
)
from dreamfi.onyx.client import OnyxClient
from dreamfi.skills.registry import seed_registry

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    s = Session(engine)
    seed_registry(s, repo_root=REPO_ROOT, enforce_regression_minimum=False)
    for skill in s.query(Skill).all():
        skill.onyx_persona_id = 100
    s.add(
        PromptVersion(
            skill_id="meeting_summary",
            version=1,
            template="meeting_summary.jinja",
            system_prompt="You write meeting summaries.",
            is_active=True,
        )
    )
    s.commit()
    return s


@pytest.fixture
def client(session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    app = create_app()

    def _session_override():
        yield session

    def _onyx_override() -> OnyxClient:
        return OnyxClient(base_url="http://onyx.test", api_key="k")

    app.dependency_overrides[get_db_session] = _session_override
    app.dependency_overrides[get_onyx_client] = _onyx_override
    return TestClient(app)


def _mock_onyx_success() -> None:
    good = (
        "## Decisions\nDecision: Ship beta Monday April 1.\n\n"
        "## Action Items\n- Sarah will send the pricing page to design by Friday.\n\n"
        "## Open Questions\nOpen: Do we need legal review?"
    )
    respx.post(re.compile(r".*/chat/create-chat-session")).mock(
        return_value=httpx.Response(200, json={"chat_session_id": "sess-1"})
    )
    stream = (
        b'{"answer_piece":"' + good.replace("\n", "\\n").encode() + b'"}\n'
        b'{"citations":{"1":"doc-1","2":"doc-2"}}\n'
        b'{"documents":[{"id":"d1","updated_at":"2026-04-18T00:00:00Z"}]}\n'
        b'{"message_id":17}\n'
    )
    respx.post(re.compile(r".*/chat/send-chat-message")).mock(
        return_value=httpx.Response(200, content=stream)
    )


@respx.mock
def test_run_round_creates_artifacts_and_rows(
    client: TestClient, session: Session, tmp_path: Path
) -> None:
    _mock_onyx_success()
    resp = client.post(
        "/v1/skills/meeting_summary/eval-round",
        json={"n_outputs_per_input": 2},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    round_id = body["round_id"]
    rows = session.query(EvalOutput).filter_by(round_id=round_id).count()
    # 3 inputs × 2 attempts
    assert rows == 6
    # Artifacts present
    results_log = (
        tmp_path / "evals/results/meeting-summary/rounds" / round_id / "results.log"
    )
    assert results_log.exists()


def test_run_round_rejects_unbounded_output_counts(client: TestClient) -> None:
    response = client.post(
        "/v1/skills/meeting_summary/eval-round",
        json={"n_outputs_per_input": 0},
    )

    assert response.status_code == 422
    assert "n_outputs_per_input" in response.json()["detail"]


@respx.mock
def test_publish_blocks_failed_hard_gate(
    client: TestClient, session: Session, tmp_path: Path
) -> None:
    _mock_onyx_success()
    resp = client.post(
        "/v1/skills/meeting_summary/eval-round",
        json={"n_outputs_per_input": 1},
    )
    round_id = resp.json()["round_id"]
    # Pick one output and force it to fail
    output = session.query(EvalOutput).filter_by(round_id=round_id).first()
    assert output is not None
    output.pass_fail = "fail"
    output.confidence = 0.99
    session.commit()
    r = client.post(
        "/v1/skills/meeting_summary/publish",
        json={"output_id": output.output_id, "destination": "return-only"},
    )
    assert r.status_code == 409
    from dreamfi.db.models import PublishLog
    log = session.query(PublishLog).filter_by(output_id=output.output_id).first()
    assert log is not None
    assert log.decision == "blocked"


@respx.mock
def test_publish_blocks_external_destination_without_writer(
    client: TestClient, session: Session
) -> None:
    _mock_onyx_success()
    resp = client.post(
        "/v1/skills/meeting_summary/eval-round",
        json={"n_outputs_per_input": 1},
    )
    round_id = resp.json()["round_id"]
    output = session.query(EvalOutput).filter_by(round_id=round_id).first()
    assert output is not None
    output.pass_fail = "pass"
    output.confidence = 0.99
    output.export_readiness = Decimal("0.990")
    output.export_breakdown_json = {"hard_gate": 1.0}
    session.commit()

    response = client.post(
        "/v1/skills/meeting_summary/publish",
        json={
            "output_id": output.output_id,
            "destination": "confluence",
            "destination_ref": "exec-review",
        },
    )

    assert response.status_code == 501
    assert "no external write was attempted" in response.json()["detail"]
    from dreamfi.db.models import PublishLog

    log = session.query(PublishLog).filter_by(output_id=output.output_id).one()
    assert log.decision == "blocked"
    assert log.destination == "confluence"


@respx.mock
def test_run_round_replays_gold_regressions_and_records_drift(
    client: TestClient, session: Session
) -> None:
    prompt_version = session.query(PromptVersion).filter_by(skill_id="meeting_summary").one()
    gold = GoldExample(
        gold_id="gold-regression-round",
        workspace_id="default",
        skill_id="meeting_summary",
        scenario_type="gold-regression",
        input_context_json={"text": "Summarize the launch review."},
        output_text="Expected launch review summary.",
        prompt_version_id=prompt_version.prompt_version_id,
        role="regression",
        last_result="pass",
    )
    session.add(gold)
    session.commit()
    failing_output = "A short unsupported note without decisions or action items."
    respx.post(re.compile(r".*/chat/create-chat-session")).mock(
        return_value=httpx.Response(200, json={"chat_session_id": "sess-1"})
    )
    stream = (
        b'{"answer_piece":"' + failing_output.encode() + b'"}\n'
        b'{"citations":{}}\n'
        b'{"documents":[]}\n'
        b'{"message_id":18}\n'
    )
    respx.post(re.compile(r".*/chat/send-chat-message")).mock(
        return_value=httpx.Response(200, content=stream)
    )

    response = client.post(
        "/v1/skills/meeting_summary/eval-round",
        json={"n_outputs_per_input": 1},
    )

    assert response.status_code == 200, response.text
    round_id = response.json()["round_id"]
    session.refresh(gold)
    assert gold.last_run_round_id == round_id
    assert gold.last_result == "fail"
    assert session.query(EvalOutput).filter_by(round_id=round_id).count() == 4
    drift_event = session.query(GoldDriftEvent).filter_by(gold_id=gold.gold_id).one()
    assert drift_event.previous_result == "pass"
    assert drift_event.new_result == "fail"


@respx.mock
def test_promote_blocked_on_regression(
    client: TestClient, session: Session, tmp_path: Path
) -> None:
    _mock_onyx_success()
    # Run two rounds on the same (only) active prompt version — second one "regresses"
    r1 = client.post(
        "/v1/skills/meeting_summary/eval-round", json={"n_outputs_per_input": 1}
    )
    assert r1.status_code == 200
    # Create a new prompt version (inactive) and a round under it
    new_pv = PromptVersion(
        skill_id="meeting_summary",
        version=2,
        template="meeting_summary.jinja",
        system_prompt="You write meeting summaries (v2).",
        is_active=False,
    )
    session.add(new_pv)
    session.commit()
    r2 = client.post(
        "/v1/skills/meeting_summary/eval-round",
        json={"n_outputs_per_input": 1, "prompt_version_id": new_pv.prompt_version_id},
    )
    assert r2.status_code == 200
    new_round_id = r2.json()["round_id"]

    # Force the new round score below the previous
    from dreamfi.db.models import EvalRound
    new_round = session.get(EvalRound, new_round_id)
    assert new_round is not None
    new_round.score = float(new_round.score) - 0.10
    session.commit()

    resp = client.post(
        "/v1/skills/meeting_summary/promote",
        json={"round_id": new_round_id},
    )
    assert resp.status_code == 409
    assert "REGRESSION" in resp.json()["detail"]


@respx.mock
def test_promote_switches_active_prompt_under_unique_index(
    client: TestClient, session: Session
) -> None:
    _mock_onyx_success()
    baseline = client.post(
        "/v1/skills/meeting_summary/eval-round", json={"n_outputs_per_input": 1}
    )
    assert baseline.status_code == 200
    baseline_round = session.get(EvalRound, baseline.json()["round_id"])
    assert baseline_round is not None
    baseline_round.score = 0.90
    session.commit()
    new_pv = PromptVersion(
        skill_id="meeting_summary",
        version=2,
        template="meeting_summary.jinja",
        system_prompt="You write meeting summaries (v2).",
        is_active=False,
    )
    session.add(new_pv)
    session.commit()
    candidate = client.post(
        "/v1/skills/meeting_summary/eval-round",
        json={"n_outputs_per_input": 1, "prompt_version_id": new_pv.prompt_version_id},
    )
    assert candidate.status_code == 200
    candidate_round = session.get(EvalRound, candidate.json()["round_id"])
    assert candidate_round is not None
    candidate_round.score = 0.95
    session.commit()

    response = client.post(
        "/v1/skills/meeting_summary/promote",
        json={"round_id": candidate_round.round_id},
    )

    assert response.status_code == 200, response.text
    active_versions = session.query(PromptVersion).filter_by(
        skill_id="meeting_summary",
        is_active=True,
    ).all()
    assert [version.prompt_version_id for version in active_versions] == [
        new_pv.prompt_version_id
    ]


@respx.mock
def test_promote_blocked_on_gold_regression(
    client: TestClient, session: Session
) -> None:
    _mock_onyx_success()
    baseline = client.post(
        "/v1/skills/meeting_summary/eval-round", json={"n_outputs_per_input": 1}
    )
    assert baseline.status_code == 200
    new_pv = PromptVersion(
        skill_id="meeting_summary",
        version=2,
        template="meeting_summary.jinja",
        system_prompt="You write meeting summaries (v2).",
        is_active=False,
    )
    session.add(new_pv)
    session.commit()
    candidate = client.post(
        "/v1/skills/meeting_summary/eval-round",
        json={"n_outputs_per_input": 1, "prompt_version_id": new_pv.prompt_version_id},
    )
    assert candidate.status_code == 200
    candidate_round_id = candidate.json()["round_id"]
    session.add(
        GoldExample(
            gold_id="gold-regression-1",
            workspace_id="default",
            skill_id="meeting_summary",
            prompt_version_id=new_pv.prompt_version_id,
            role="regression",
            last_run_round_id=candidate_round_id,
            last_result="fail",
        )
    )
    session.commit()

    response = client.post(
        "/v1/skills/meeting_summary/promote",
        json={"round_id": candidate_round_id},
    )

    assert response.status_code == 409
    assert "blocked_by_regression" in response.json()["detail"]


@respx.mock
def test_promotion_preview_endpoint(
    client: TestClient, session: Session
) -> None:
    _mock_onyx_success()
    round_response = client.post(
        "/v1/skills/meeting_summary/eval-round",
        json={"n_outputs_per_input": 1},
    )
    assert round_response.status_code == 200
    round_id = round_response.json()["round_id"]

    preview = client.post(
        "/v1/skills/meeting_summary/promotion-preview",
        json={"round_id": round_id},
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["round_id"] == round_id
    assert body["skill_id"] == "meeting_summary"
    assert "promotable" in body
    assert "reason" in body
