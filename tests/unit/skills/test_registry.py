"""Skill registry tests."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dreamfi.db.models import Base, Skill
from dreamfi.evals.loader import parse_eval_template
from dreamfi.skills.registry import load_registry, seed_registry

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_all_nine_skills_registered() -> None:
    reg = load_registry()
    assert set(reg.keys()) == {
        "meeting_summary",
        "cold_email",
        "landing_page_copy",
        "newsletter_headline",
        "product_description",
        "resume_bullet",
        "short_form_script",
        "agent_system_prompt",
        "support_agent",
    }


def test_each_skill_has_eval_template_and_runner() -> None:
    for spec in load_registry().values():
        assert (REPO_ROOT / spec.eval_template_path).exists(), spec.eval_template_path
        assert (REPO_ROOT / spec.eval_runner_path).exists(), spec.eval_runner_path


def test_criteria_parsed_from_template() -> None:
    spec = parse_eval_template(REPO_ROOT / "evals/meeting-summary.md")
    assert len(spec.criteria) >= 4
    assert all(c.id.startswith("C") for c in spec.criteria)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_seed_registry_is_idempotent(session: Session) -> None:
    first = seed_registry(session, repo_root=REPO_ROOT)
    second = seed_registry(session, repo_root=REPO_ROOT)
    assert first == 9
    assert second == 9
    assert session.query(Skill).count() == 9
