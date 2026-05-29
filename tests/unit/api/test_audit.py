from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx
import respx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dreamfi.api.app import create_app
from dreamfi.api.deps import get_db_session, get_onyx_client
from dreamfi.audit import add_audit_event, hash_text
from dreamfi.db.models import AuditEvent, Base, EvalOutput, EvalRound, PromptVersion, Skill
from dreamfi.onyx.client import OnyxClient
from dreamfi.skills.registry import seed_registry

REPO_ROOT = Path(__file__).resolve().parents[3]


def _session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    session = Session(engine)
    seed_registry(session, repo_root=REPO_ROOT, enforce_regression_minimum=False)
    for skill in session.query(Skill).all():
        skill.onyx_persona_id = 100
    session.add(
        PromptVersion(
            skill_id="meeting_summary",
            version=1,
            template="meeting_summary.jinja",
            system_prompt="You write meeting summaries.",
            is_active=True,
        )
    )
    session.commit()
    return session


def _client(session: Session) -> TestClient:
    app = create_app()

    def _session_override():
        yield session

    def _onyx_override() -> OnyxClient:
        return OnyxClient(base_url="http://onyx.test", api_key="k")

    app.dependency_overrides[get_db_session] = _session_override
    app.dependency_overrides[get_onyx_client] = _onyx_override
    return TestClient(app)


def test_audit_metadata_is_redacted_and_hashed(tmp_path: Path) -> None:
    session = _session(tmp_path)

    add_audit_event(
        session,
        category="test",
        action="redaction_check",
        outcome="success",
        metadata={
            "prompt": "do not persist this prompt",
            "api_key": "do-not-persist-this-key",
            "safe_count": 3,
        },
    )
    session.commit()

    event = session.query(AuditEvent).filter_by(action="redaction_check").one()
    serialized = json.dumps(event.metadata_json, sort_keys=True)
    assert "do not persist" not in serialized
    assert "do-not-persist" not in serialized
    assert event.metadata_json["prompt_sha256"] == hash_text("do not persist this prompt")
    assert event.metadata_json["api_key_sha256"] == hash_text("do-not-persist-this-key")
    assert event.event_hash != "pending"
    assert len(event.event_hash) == 64


@respx.mock
def test_ask_records_hashed_audit_event_without_question_text(tmp_path: Path) -> None:
    session = _session(tmp_path)
    client = _client(session)
    question = "Why did KYC conversion move?"
    respx.post("http://onyx.test/api/admin/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "documents": [
                    {
                        "document_id": "doc-1",
                        "semantic_identifier": "KYC funnel report",
                        "blurb": "KYC completion moved after retry policy changes.",
                        "score": 0.92,
                        "updated_at": "2026-04-28T00:00:00Z",
                    }
                ]
            },
        )
    )

    response = client.post(
        "/api/ask",
        json={
            "question": question,
            "topic_id": "kyc-conversion",
            "source_id": "socure",
        },
        headers={"X-Request-ID": "audit-test-request"},
    )

    assert response.status_code == 200
    event = session.query(AuditEvent).filter_by(action="onyx_search").one()
    assert event.request_id == "audit-test-request"
    assert event.target_type == "onyx_search"
    assert event.metadata_json["question_sha256"] == hash_text(question)
    assert question not in json.dumps(event.metadata_json)
    assert event.metadata_json["source_ids"] == ["socure"]
    assert event.metadata_json["hit_count"] == 1


def test_publish_attempt_audit_event_omits_destination_ref(tmp_path: Path) -> None:
    session = _session(tmp_path)
    client = _client(session)
    prompt_version = session.query(PromptVersion).filter_by(skill_id="meeting_summary").one()
    now = datetime.now(timezone.utc)
    round_row = EvalRound(
        skill_id="meeting_summary",
        prompt_version_id=prompt_version.prompt_version_id,
        n_inputs=1,
        n_outputs_per_input=1,
        total_outputs=1,
        total_passes=1,
        score=Decimal("1.0000"),
        started_at=now,
        completed_at=now,
        artifacts_path="evals/results/meeting-summary/rounds/audit",
    )
    session.add(round_row)
    session.flush()
    output = EvalOutput(
        round_id=round_row.round_id,
        test_input_label="audit",
        attempt=1,
        generated_text="approved output",
        criteria_json={},
        pass_fail="pass",
        confidence=Decimal("0.990"),
        export_readiness=Decimal("0.990"),
        export_breakdown_json={"hard_gate": 1.0},
    )
    session.add(output)
    session.commit()

    response = client.post(
        "/v1/skills/meeting_summary/publish",
        json={
            "output_id": output.output_id,
            "destination": "confluence",
            "destination_ref": "sensitive-confluence-page",
        },
    )

    assert response.status_code == 501
    event = session.query(AuditEvent).filter_by(action="publish_attempt").one()
    serialized = json.dumps(event.metadata_json, sort_keys=True)
    assert event.outcome == "blocked"
    assert event.target_id == output.output_id
    assert event.metadata_json["destination"] == "confluence"
    assert event.metadata_json["destination_ref_present"] is True
    assert "sensitive-confluence-page" not in serialized


def test_console_topic_mutation_records_changed_fields(tmp_path: Path) -> None:
    session = _session(tmp_path)
    client = _client(session)

    create_response = client.post(
        "/api/console/topics",
        json={
            "title": "KYC conversion",
            "question": "What moved KYC conversion?",
            "source_ids": ["jira", "socure"],
            "default_generator_slug": "risk-brd",
        },
    )
    assert create_response.status_code == 201
    topic_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/console/topics/{topic_id}",
        json={"owner": "Product Ops", "status": "in_review"},
    )

    assert update_response.status_code == 200
    create_event = session.query(AuditEvent).filter_by(action="topic_create").one()
    update_event = session.query(AuditEvent).filter_by(action="topic_update").one()
    assert create_event.target_id == topic_id
    assert create_event.metadata_json["source_ids"] == ["jira", "socure"]
    assert update_event.target_id == topic_id
    assert update_event.metadata_json["changed_fields"] == ["owner", "status"]
