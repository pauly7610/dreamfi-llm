"""C7: context memory token-overlap similarity + private isolation."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dreamfi.context.memory import record_question, similar_questions, tokenize
from dreamfi.db.models import Base


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_tokenize_strips_stop_words_and_lowercases() -> None:
    toks = tokenize("Why is the onboarding rollout blocked?")
    assert "onboarding" in toks
    assert "rollout" in toks
    assert "blocked" in toks
    for stop in ("why", "is", "the"):
        assert stop not in toks


def test_similar_question_returns_prior_answer(session: Session) -> None:
    record_question(
        session,
        workspace_id="w1",
        question="Why is the onboarding rollout blocked?",
        answer_excerpt="Blocked on legal for EU",
        asker="laila",
    )
    hits = similar_questions(
        session,
        workspace_id="w1",
        question="what blocks onboarding rollout?",
    )
    assert len(hits) == 1
    assert hits[0].answer_excerpt.startswith("Blocked on legal")
    assert hits[0].similarity >= 0.5


def test_workspace_isolation(session: Session) -> None:
    record_question(
        session,
        workspace_id="w1",
        question="Why is the onboarding rollout blocked?",
        answer_excerpt="Blocked on legal",
    )
    assert (
        similar_questions(
            session, workspace_id="w2", question="onboarding rollout blocked?"
        )
        == []
    )


def test_private_questions_only_surface_to_original_asker(session: Session) -> None:
    record_question(
        session,
        workspace_id="w1",
        question="How does Ahmed feel about the EU rollout?",
        answer_excerpt="Confidential note",
        asker="laila",
        private=True,
    )
    # Different asker — private row hidden.
    hits_other = similar_questions(
        session,
        workspace_id="w1",
        question="how does ahmed feel about eu rollout",
        asker="bob",
    )
    assert hits_other == []

    # Same asker — visible.
    hits_self = similar_questions(
        session,
        workspace_id="w1",
        question="how does ahmed feel about eu rollout",
        asker="laila",
    )
    assert len(hits_self) == 1


def test_threshold_filters_unrelated_questions(session: Session) -> None:
    record_question(
        session,
        workspace_id="w1",
        question="Why is the onboarding rollout blocked?",
        answer_excerpt="…",
    )
    hits = similar_questions(
        session,
        workspace_id="w1",
        question="What is our pricing strategy?",
    )
    assert hits == []
