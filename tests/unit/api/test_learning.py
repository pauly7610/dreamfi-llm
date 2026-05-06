from __future__ import annotations

import re
from datetime import datetime, timezone
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
from dreamfi.audit import hash_text
from dreamfi.db.models import (
    ArtifactFeedback,
    Base,
    EvalOutput,
    EvalRound,
    GoldExample,
    LearningProposal,
    ProductionOutcome,
    PromptVersion,
    ReplayRun,
    ReplaySchedule,
    Skill,
)
from dreamfi.onyx.client import OnyxClient
from dreamfi.skills.registry import seed_registry

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    db = Session(engine)
    seed_registry(db, repo_root=REPO_ROOT)
    for skill in db.query(Skill).all():
        skill.onyx_persona_id = 100
    db.add(
        PromptVersion(
            skill_id="meeting_summary",
            version=1,
            template="meeting_summary.jinja",
            system_prompt="You write meeting summaries.",
            is_active=True,
        )
    )
    db.commit()
    return db


@pytest.fixture
def client(
    session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.chdir(tmp_path)
    app = create_app()

    def _session_override():
        yield session

    def _onyx_override() -> OnyxClient:
        return OnyxClient(base_url="http://onyx.test", api_key="k")

    app.dependency_overrides[get_db_session] = _session_override
    app.dependency_overrides[get_onyx_client] = _onyx_override
    return TestClient(app)


def _active_prompt(db: Session) -> PromptVersion:
    prompt = (
        db.query(PromptVersion)
        .filter_by(skill_id="meeting_summary", is_active=True)
        .one()
    )
    return prompt


def _make_round(db: Session, *, total_outputs: int = 1) -> EvalRound:
    prompt = _active_prompt(db)
    now = datetime.now(timezone.utc)
    round_row = EvalRound(
        skill_id="meeting_summary",
        prompt_version_id=prompt.prompt_version_id,
        n_inputs=total_outputs,
        n_outputs_per_input=1,
        total_outputs=total_outputs,
        total_passes=0,
        score=Decimal("0.0000"),
        started_at=now,
        completed_at=now,
        artifacts_path="evals/results/meeting-summary/rounds/test-learning",
    )
    db.add(round_row)
    db.flush()
    return round_row


def _make_output(
    db: Session,
    *,
    round_row: EvalRound | None = None,
    label: str = "learning-case",
    pass_fail: str = "pass",
    criteria: dict[str, object] | None = None,
    generated_text: str = "Approved artifact with a cited decision.",
) -> EvalOutput:
    target_round = round_row or _make_round(db)
    output = EvalOutput(
        round_id=target_round.round_id,
        test_input_label=label,
        attempt=1,
        generated_text=generated_text,
        criteria_json=criteria or {},
        pass_fail=pass_fail,
        onyx_citations_json={"1": "doc-1"} if pass_fail == "pass" else {},
        freshness_score=Decimal("0.900") if pass_fail == "pass" else Decimal("0.100"),
        confidence=Decimal("0.900") if pass_fail == "pass" else Decimal("0.100"),
        export_readiness=Decimal("0.900") if pass_fail == "pass" else Decimal("0.100"),
    )
    db.add(output)
    db.commit()
    return output


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


def test_feedback_capture_can_create_gold_without_storing_final_text(
    client: TestClient,
    session: Session,
) -> None:
    output = _make_output(session)
    final_text = "Final approved artifact after reviewer edits."

    response = client.post(
        "/api/learning/feedback",
        json={
            "output_id": output.output_id,
            "reviewer_id": "reviewer-1",
            "outcome": "approved",
            "reason": "good_enough",
            "notes": "Approved after a light edit.",
            "final_text": final_text,
            "promote_to_gold_role": "exemplar",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    feedback = session.get(ArtifactFeedback, body["feedback"]["feedback_id"])
    assert feedback is not None
    assert feedback.final_text_hash == hash_text(final_text)
    assert final_text not in str(feedback.metadata_json)
    gold = session.get(GoldExample, feedback.gold_id)
    assert gold is not None
    assert gold.role == "exemplar"
    assert gold.output_text == final_text
    assert gold.expected_pass_criteria["feedback_outcome"] == "approved"


def test_rejected_feedback_can_become_regression_gold(
    client: TestClient,
    session: Session,
) -> None:
    output = _make_output(
        session,
        pass_fail="fail",
        generated_text="Thin artifact with no required decisions.",
    )

    response = client.post(
        "/api/learning/feedback",
        json={
            "output_id": output.output_id,
            "reviewer_id": "reviewer-2",
            "outcome": "rejected",
            "reason": "missing_required_sections",
            "promote_to_gold_role": "regression",
        },
    )

    assert response.status_code == 201, response.text
    feedback = session.query(ArtifactFeedback).filter_by(output_id=output.output_id).one()
    gold = session.get(GoldExample, feedback.gold_id)
    assert gold is not None
    assert gold.role == "regression"
    assert gold.output_text == output.generated_text


def test_invalid_inline_gold_promotion_returns_422_without_feedback(
    client: TestClient,
    session: Session,
) -> None:
    output = _make_output(session)

    response = client.post(
        "/api/learning/feedback",
        json={
            "output_id": output.output_id,
            "reviewer_id": "reviewer-3",
            "outcome": "approved",
            "reason": "good_artifact",
            "promote_to_gold_role": "regression",
        },
    )

    assert response.status_code == 422
    assert "can only become exemplar/canary" in response.json()["detail"]
    assert session.query(ArtifactFeedback).filter_by(output_id=output.output_id).count() == 0
    assert session.query(GoldExample).count() == 0


def test_promoting_feedback_to_gold_is_idempotent_and_conflict_checked(
    client: TestClient,
    session: Session,
) -> None:
    output = _make_output(session)
    feedback_response = client.post(
        "/api/learning/feedback",
        json={
            "output_id": output.output_id,
            "reviewer_id": "reviewer-4",
            "outcome": "approved",
            "reason": "clear_decision_support",
            "promote_to_gold_role": "exemplar",
        },
    )
    feedback_id = feedback_response.json()["feedback"]["feedback_id"]
    gold_id = feedback_response.json()["gold"]["gold_id"]

    repeat_response = client.post(
        f"/api/learning/feedback/{feedback_id}/gold",
        json={"role": "exemplar"},
    )
    conflict_response = client.post(
        f"/api/learning/feedback/{feedback_id}/gold",
        json={"role": "canary"},
    )

    assert repeat_response.status_code == 201, repeat_response.text
    assert repeat_response.json()["gold"]["gold_id"] == gold_id
    assert conflict_response.status_code == 422
    assert "already promoted" in conflict_response.json()["detail"]
    assert session.query(GoldExample).count() == 1


def test_failure_clusters_generate_and_approve_prompt_proposal(
    client: TestClient,
    session: Session,
) -> None:
    active_prompt = _active_prompt(session)
    criteria = {
        "workflow_slug": "risk-brd",
        "source_id": "socure",
        "has_required_sections": False,
        "has_review_checklist": False,
        "review_checklist_resolved": False,
        "citation_count": 0,
        "meets_min_citations": False,
    }
    round_row = _make_round(session, total_outputs=2)
    _make_output(
        session,
        round_row=round_row,
        label="failed-risk-1",
        pass_fail="fail",
        criteria=criteria,
        generated_text="KYC risk moved.",
    )
    _make_output(
        session,
        round_row=round_row,
        label="failed-risk-2",
        pass_fail="fail",
        criteria=criteria,
        generated_text="Hold launch.",
    )

    clusters_response = client.get("/api/learning/failure-clusters?min_count=2")
    assert clusters_response.status_code == 200
    cluster_keys = {
        cluster["cluster_key"]
        for cluster in clusters_response.json()["clusters"]
    }
    assert "missing_section:required_sections" in cluster_keys
    assert "evidence:low_citation" in cluster_keys

    proposal_response = client.post(
        "/api/learning/proposals/generate",
        json={"min_count": 2},
    )
    assert proposal_response.status_code == 201, proposal_response.text
    proposals = proposal_response.json()["proposals"]
    proposal = next(
        item
        for item in proposals
        if item["cluster_key"] == "missing_section:required_sections"
    )

    approval_response = client.post(
        f"/api/learning/proposals/{proposal['proposal_id']}/approve",
        json={"reviewer_id": "prompt-reviewer", "review_notes": "Create candidate."},
    )

    assert approval_response.status_code == 200, approval_response.text
    created_prompt = session.get(
        PromptVersion,
        approval_response.json()["created_prompt_version_id"],
    )
    assert created_prompt is not None
    assert created_prompt.is_active is False
    assert created_prompt.parent_version_id == active_prompt.prompt_version_id
    session.refresh(active_prompt)
    assert active_prompt.is_active is True
    reviewed = session.get(LearningProposal, proposal["proposal_id"])
    assert reviewed is not None
    assert reviewed.status == "applied"


def test_reject_prompt_proposal_preserves_active_prompt(
    client: TestClient,
    session: Session,
) -> None:
    active_prompt = _active_prompt(session)
    proposal = LearningProposal(
        skill_id="meeting_summary",
        prompt_version_id=active_prompt.prompt_version_id,
        cluster_key="evidence:low_citation",
        title="Improve evidence: low citation",
        rationale="Repeated low-citation failures need review.",
        proposed_prompt_patch="Require source-backed claims.",
        status="draft",
        source_failure_count=3,
        evidence_json={"output_ids": ["out-1", "out-2", "out-3"]},
    )
    session.add(proposal)
    session.commit()

    response = client.post(
        f"/api/learning/proposals/{proposal.proposal_id}/reject",
        json={"reviewer_id": "prompt-reviewer", "review_notes": "Do not change prompt yet."},
    )

    assert response.status_code == 200, response.text
    reviewed = session.get(LearningProposal, proposal.proposal_id)
    assert reviewed is not None
    assert reviewed.status == "rejected"
    assert reviewed.reviewer_id == "prompt-reviewer"
    assert reviewed.reviewed_at is not None
    assert session.query(PromptVersion).filter_by(skill_id="meeting_summary").count() == 1
    session.refresh(active_prompt)
    assert active_prompt.is_active is True


def test_production_outcome_records_summary(
    client: TestClient,
    session: Session,
) -> None:
    output = _make_output(session)
    final_text = "Artifact used in the lifecycle messaging decision."

    response = client.post(
        "/api/learning/outcomes",
        json={
            "output_id": output.output_id,
            "outcome": "used_in_decision",
            "actor_id": "product-lead",
            "notes": "Used in decision review.",
            "final_text": final_text,
        },
    )

    assert response.status_code == 201, response.text
    row = session.query(ProductionOutcome).filter_by(output_id=output.output_id).one()
    assert row.outcome == "used_in_decision"
    assert row.final_text_hash == hash_text(final_text)
    assert response.json()["summary"]["by_outcome"] == {"used_in_decision": 1}


@respx.mock
def test_run_due_gold_replay_schedule_runs_round(
    client: TestClient,
    session: Session,
) -> None:
    _mock_onyx_success()
    prompt = _active_prompt(session)
    session.add(
        GoldExample(
            gold_id="learning-regression-1",
            workspace_id="default",
            skill_id="meeting_summary",
            scenario_type="review-rejection",
            input_context_json={"text": "Summarize the rejected launch review."},
            output_text="Expected summary with decisions and actions.",
            prompt_version_id=prompt.prompt_version_id,
            role="regression",
        )
    )
    session.commit()

    schedule_response = client.post(
        "/api/learning/replay-schedules",
        json={
            "replay_type": "gold",
            "skill_id": "meeting_summary",
            "cadence_days": 1,
            "created_by": "ops",
        },
    )
    assert schedule_response.status_code == 201, schedule_response.text

    run_response = client.post("/api/learning/replay-schedules/run-due")

    assert run_response.status_code == 200, run_response.text
    runs = run_response.json()["runs"]
    assert len(runs) == 1
    assert runs[0]["status"] == "success"
    assert runs[0]["round_id"]
    schedule = session.query(ReplaySchedule).one()
    assert schedule.last_run_at is not None
    assert schedule.next_run_at > schedule.last_run_at
    replay_run = session.query(ReplayRun).one()
    assert replay_run.round_id == runs[0]["round_id"]


def test_workflow_replay_schedule_requires_workflow_slug(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/learning/replay-schedules",
        json={"replay_type": "workflow", "cadence_days": 1, "payload": {}},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "workflow replay requires payload.workflow_slug"


def test_due_workflow_replay_records_error_for_unknown_workflow(
    client: TestClient,
    session: Session,
) -> None:
    schedule_response = client.post(
        "/api/learning/replay-schedules",
        json={
            "replay_type": "workflow",
            "cadence_days": 1,
            "created_by": "ops",
            "payload": {"workflow_slug": "not-a-workflow"},
        },
    )
    assert schedule_response.status_code == 201, schedule_response.text

    run_response = client.post("/api/learning/replay-schedules/run-due")

    assert run_response.status_code == 200, run_response.text
    run = run_response.json()["runs"][0]
    assert run["status"] == "error"
    assert run["reason"] == "ValueError"
    assert "workflow replay schedule requires workflow_slug" in run["summary"]["error"]
    schedule = session.query(ReplaySchedule).one()
    assert schedule.last_run_at is not None
