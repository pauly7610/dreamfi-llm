"""SkillEngine writes export_readiness + breakdown to EvalOutput (X1, layer 1)."""
from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dreamfi.db.models import (
    Base,
    EvalOutput,
    EvalRound,
    GoldExample,
    PromptVersion,
    Skill,
)
from dreamfi.onyx.client import OnyxClient
from dreamfi.skills.engine import SkillEngine
from dreamfi.skills.registry import seed_registry

REPO_ROOT = Path(__file__).resolve().parents[1]

GOOD_OUTPUT = (
    "## Decisions\nDecision: Launch beta to 500 users on April 1.\n\n"
    "## Action Items\n- Sarah will send the pricing page to design by Friday March 21.\n\n"
    "## Open Questions\nOpen: Do we need legal review before EU launch?"
)

BAD_OUTPUT = "this is not a meeting summary at all"


@pytest.fixture
def session(tmp_path: Path) -> Session:
    eng = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(eng)
    s = Session(eng)
    seed_registry(s, repo_root=REPO_ROOT, enforce_regression_minimum=False)
    for skill in s.query(Skill).all():
        skill.onyx_persona_id = 100
    pv = PromptVersion(
        skill_id="meeting_summary",
        version=1,
        template="meeting_summary.jinja",
        system_prompt="You write meeting summaries.",
        is_active=True,
    )
    s.add(pv)
    s.commit()
    return s


def _round(session: Session, skill_id: str = "meeting_summary") -> EvalRound:
    pv = session.query(PromptVersion).filter_by(skill_id=skill_id).first()
    assert pv is not None
    from datetime import datetime, timezone

    row = EvalRound(
        skill_id=skill_id,
        prompt_version_id=pv.prompt_version_id,
        n_inputs=1,
        n_outputs_per_input=1,
        total_outputs=0,
        total_passes=0,
        score=Decimal("0.0"),
        started_at=datetime.now(timezone.utc),
        artifacts_path="",
    )
    session.add(row)
    session.flush()
    return row


def _mock_onyx(text: str) -> None:
    respx.post(re.compile(r".*/chat/create-chat-session")).mock(
        return_value=httpx.Response(200, json={"chat_session_id": "sess-1"})
    )
    stream = (
        b'{"answer_piece":"' + text.replace("\n", "\\n").encode() + b'"}\n'
        b'{"citations":{"1":"doc-1","2":"doc-2"}}\n'
        b'{"documents":[{"id":"d1","updated_at":"2026-04-18T00:00:00Z"}]}\n'
        b'{"message_id":17}\n'
    )
    respx.post(re.compile(r".*/chat/send-chat-message")).mock(
        return_value=httpx.Response(200, content=stream)
    )


def _seed_regression(session: Session, *, last_result: str = "pass") -> None:
    pv = session.query(PromptVersion).filter_by(skill_id="meeting_summary").first()
    assert pv is not None
    session.add(
        GoldExample(
            skill_id="meeting_summary",
            workspace_id="w1",
            scenario_type="default",
            input_context_json={},
            output_text="sample",
            prompt_version_id=pv.prompt_version_id,
            role="regression",
            last_result=last_result,
        )
    )
    session.commit()


@respx.mock
def test_happy_path_persists_readiness_and_breakdown(session: Session) -> None:
    _seed_regression(session, last_result="pass")
    _mock_onyx(GOOD_OUTPUT)
    round_row = _round(session)

    onyx = OnyxClient(base_url="http://onyx.test", api_key="k")
    out = SkillEngine(db=session, onyx=onyx).generate(
        skill="meeting_summary",
        input_context={"transcript": "..."},
        test_input_label="input_1",
        round_id=round_row.round_id,
    )

    assert out.export_readiness is not None
    assert out.export_readiness.value > 0.0

    row = session.get(EvalOutput, out.output_id)
    assert row is not None
    assert row.export_readiness is not None
    assert float(row.export_readiness) == out.export_readiness.value
    assert row.export_breakdown_json is not None
    assert row.export_breakdown_json["hard_gate"] == 1.0


@respx.mock
def test_hard_gate_failure_sets_readiness_zero(session: Session) -> None:
    _seed_regression(session, last_result="pass")
    _mock_onyx(BAD_OUTPUT)
    round_row = _round(session)

    onyx = OnyxClient(base_url="http://onyx.test", api_key="k")
    out = SkillEngine(db=session, onyx=onyx).generate(
        skill="meeting_summary",
        input_context={"transcript": "..."},
        test_input_label="input_1",
        round_id=round_row.round_id,
    )

    assert out.eval.pass_fail == "fail"
    assert out.export_readiness is not None
    assert out.export_readiness.value == 0.0

    row = session.get(EvalOutput, out.output_id)
    assert row is not None
    assert float(row.export_readiness) == 0.0
    assert row.export_breakdown_json["hard_gate"] == 0.0


@respx.mock
def test_missing_regression_signal_leaves_readiness_null(session: Session) -> None:
    # No regression gold examples seeded → readiness cannot be computed.
    _mock_onyx(GOOD_OUTPUT)
    round_row = _round(session)

    onyx = OnyxClient(base_url="http://onyx.test", api_key="k")
    out = SkillEngine(db=session, onyx=onyx).generate(
        skill="meeting_summary",
        input_context={"transcript": "..."},
        test_input_label="input_1",
        round_id=round_row.round_id,
    )

    assert out.eval.pass_fail == "pass"
    assert out.export_readiness is None

    row = session.get(EvalOutput, out.output_id)
    assert row is not None
    assert row.export_readiness is None
    assert row.export_breakdown_json is None
