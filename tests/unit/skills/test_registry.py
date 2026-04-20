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


def test_active_pm_skills_registered() -> None:
    reg = load_registry()
    # X5: six marketing skills were archived; only the PM-adjacent three remain.
    assert set(reg.keys()) == {
        "meeting_summary",
        "agent_system_prompt",
        "support_agent",
    }


def test_archived_skills_are_not_in_active_registry() -> None:
    from dreamfi.skills.registry import ARCHIVED_SKILLS

    reg = load_registry()
    archived_ids = {s.skill_id for s in ARCHIVED_SKILLS}
    assert archived_ids.isdisjoint(reg.keys())
    # Archived files still exist on disk (ADR-003 lock).
    for spec in ARCHIVED_SKILLS:
        assert (REPO_ROOT / spec.eval_template_path).exists()
        assert (REPO_ROOT / spec.eval_runner_path).exists()


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
    first = seed_registry(session, repo_root=REPO_ROOT, enforce_regression_minimum=False)
    second = seed_registry(session, repo_root=REPO_ROOT, enforce_regression_minimum=False)
    assert first == 3
    assert second == 3
    assert session.query(Skill).count() == 3
