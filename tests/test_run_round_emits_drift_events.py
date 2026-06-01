"""X2: round N+1 fails a label that passed in round N → GoldDriftEvent + promote block."""
from __future__ import annotations

import re
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from dreamfi.api.app import create_app
from dreamfi.api.deps import get_db_session, get_onyx_client
from dreamfi.db.models import Base, GoldDriftEvent, PromptVersion, Skill
from dreamfi.onyx.client import OnyxClient
from dreamfi.skills.registry import seed_registry

REPO_ROOT = Path(__file__).resolve().parents[1]

GOOD = (
    "## Decisions\nDecision: Ship beta Monday April 1.\n\n"
    "## Action Items\n- Sarah will send the pricing page to design by Friday.\n\n"
    "## Open Questions\nOpen: Do we need legal review?"
)
BAD = "this is not a meeting summary at all"


@pytest.fixture
def session(tmp_path: Path) -> Session:
    eng = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(eng)
    s = Session(eng)
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


def _mock_onyx(text: str) -> None:
    respx.post(re.compile(r".*/chat/create-chat-session")).mock(
        return_value=httpx.Response(200, json={"chat_session_id": "sess-1"})
    )
    stream = (
        b'{"answer_piece":"' + text.replace("\n", "\\n").encode() + b'"}\n'
        b'{"citations":{"1":"doc-1"}}\n'
        b'{"message_id":17}\n'
    )
    respx.post(re.compile(r".*/chat/send-chat-message")).mock(
        return_value=httpx.Response(200, content=stream)
    )


@respx.mock
def test_round_over_round_regression_emits_drift_event_and_blocks_promote(
    client: TestClient, session: Session
) -> None:
    # Round 1 (active PV) — all labels pass.
    _mock_onyx(GOOD)
    r1 = client.post(
        "/v1/skills/meeting_summary/eval-round", json={"n_outputs_per_input": 1}
    )
    assert r1.status_code == 200

    # New PV for round 2 — outputs fail.
    new_pv = PromptVersion(
        skill_id="meeting_summary",
        version=2,
        template="meeting_summary.jinja",
        system_prompt="You write meeting summaries (v2).",
        is_active=False,
    )
    session.add(new_pv)
    session.commit()

    respx.reset()
    _mock_onyx(BAD)
    r2 = client.post(
        "/v1/skills/meeting_summary/eval-round",
        json={"n_outputs_per_input": 1, "prompt_version_id": new_pv.prompt_version_id},
    )
    assert r2.status_code == 200
    round2_id = r2.json()["round_id"]

    # Drift events were emitted for labels that regressed.
    drift_rows = list(
        session.scalars(select(GoldDriftEvent).where(GoldDriftEvent.round_id == round2_id))
    )
    assert len(drift_rows) >= 1
    assert all(r.previous_result == "pass" and r.new_result == "fail" for r in drift_rows)
    assert all(r.prompt_version_id == new_pv.prompt_version_id for r in drift_rows)

    # Promote is blocked by the regression, regardless of score math.
    promote = client.post(
        "/v1/skills/meeting_summary/promote",
        json={"round_id": round2_id},
    )
    assert promote.status_code == 409
    assert "blocked_by_regression" in promote.json()["detail"]


@respx.mock
def test_first_round_emits_no_drift_events(client: TestClient, session: Session) -> None:
    _mock_onyx(GOOD)
    r = client.post(
        "/v1/skills/meeting_summary/eval-round", json={"n_outputs_per_input": 1}
    )
    assert r.status_code == 200
    round_id = r.json()["round_id"]

    rows = list(session.scalars(select(GoldDriftEvent).where(GoldDriftEvent.round_id == round_id)))
    assert rows == []
