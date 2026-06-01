"""SkillEngine tests with fully mocked Onyx."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import httpx
import pytest
import respx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dreamfi.db.models import Base, EvalRound, PromptVersion, Skill
from dreamfi.gold.registry import GoldExampleRegistry
from dreamfi.onyx.client import OnyxClient
from dreamfi.skills.engine import SkillEngine
from dreamfi.skills.registry import seed_registry

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = Session(engine)
    seed_registry(s, repo_root=REPO_ROOT, enforce_regression_minimum=False)
    # Attach a persona id to every skill.
    for skill in s.query(Skill).all():
        skill.onyx_persona_id = 100 + hash(skill.skill_id) % 100
    # Seed an active prompt version for meeting_summary
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


@respx.mock
def test_generate_calls_onyx_and_returns_result(session: Session) -> None:
    good = (
        "## Decisions\nDecision: Launch beta to 500 users on April 1.\n\n"
        "## Action Items\n- Sarah will send the pricing page to design by Friday March 21.\n\n"
        "## Open Questions\nOpen: Do we need legal review before EU launch?"
    )
    respx.post(re.compile(r".*/chat/create-chat-session")).mock(
        return_value=httpx.Response(200, json={"chat_session_id": "sess-1"})
    )
    stream = (
        b'{"answer_piece":"' + good.replace("\n", "\\n").encode() + b'"}\n'
        b'{"citations":{"1":"doc-123"}}\n'
        b'{"message_id":12}\n'
    )
    respx.post(re.compile(r".*/chat/send-chat-message")).mock(
        return_value=httpx.Response(200, content=stream)
    )

    onyx = OnyxClient(base_url="http://onyx.test", api_key="k")
    engine = SkillEngine(db=session, onyx=onyx)
    out = engine.generate(
        skill="meeting_summary",
        input_context={"transcript": "..."},
        test_input_label="input_1",
    )
    assert out.eval.pass_fail == "pass"
    assert out.onyx_chat_session_id == "sess-1"
    assert out.onyx_citations == {1: "doc-123"}
    assert out.confidence.confidence >= 0.0


def test_render_prompt_injects_gold_examples(session: Session) -> None:
    gold = GoldExampleRegistry(session)
    gold.capture(
        skill_id="meeting_summary",
        scenario_type="standup",
        input_context={"x": "y"},
        output_text="Decision: great.",
        prompt_version_id=session.scalar(
            EvalRound.__table__.select().limit(0)
        )
        and ""
        or session.query(PromptVersion).first().prompt_version_id,
        eval_passed=True,
    )
    onyx = OnyxClient(base_url="http://onyx.test", api_key="k")
    engine = SkillEngine(db=session, onyx=onyx, gold=gold)
    rendered = engine._render_prompt("meeting_summary", {"transcript": "..."})
    assert "Example (gold)" in rendered


def test_render_prompt_without_gold_omits_section(session: Session) -> None:
    onyx = OnyxClient(base_url="http://onyx.test", api_key="k")
    engine = SkillEngine(db=session, onyx=onyx)
    rendered = engine._render_prompt(
        "meeting_summary", {"transcript": "..."}, include_gold=False
    )
    assert "Example (gold)" not in rendered


# Silence unused
_ = uuid
