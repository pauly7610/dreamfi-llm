"""C6: watcher diff semantics + persistence."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from dreamfi.context.bundle import (
    ContextBundle,
    ContextClaim,
    ContextSource,
    OpenQuestion,
)
from dreamfi.context.watcher import diff_bundles, watch_and_persist
from dreamfi.db.models import Base, ContextChangeRow


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    return Session(engine)


def _src(source_type: str, source_id: str) -> ContextSource:
    return ContextSource(
        source_type=source_type,
        source_id=source_id,
        fetched_at=datetime.now(timezone.utc),
        payload_hash="h",
        raw_ref="r",
    )


def _bundle(
    *,
    claims: list[str],
    sources: list[tuple[str, str]],
    questions: list[str],
) -> ContextBundle:
    return ContextBundle(
        workspace_id="w1",
        topic="t",
        topic_key="t",
        refreshed_at=datetime.now(timezone.utc),
        sources=[_src(t, i) for (t, i) in sources],
        claims=[ContextClaim(statement=s, citation_ids=["x"]) for s in claims],
        open_questions=[
            OpenQuestion(question=q, why_open="ambiguous") for q in questions
        ],
    )


def test_first_bundle_produces_no_diff() -> None:
    current = _bundle(claims=["a"], sources=[("jira", "J1")], questions=[])
    assert diff_bundles(previous=None, current=current) == []


def test_claim_added_and_removed_detected() -> None:
    prev = _bundle(claims=["alpha"], sources=[("jira", "J1")], questions=[])
    curr = _bundle(claims=["beta"], sources=[("jira", "J1")], questions=[])
    changes = diff_bundles(previous=prev, current=curr)
    kinds = sorted(c.change_type for c in changes)
    assert kinds == ["claim_added", "claim_removed"]


def test_source_lost_and_question_resolved_detected() -> None:
    prev = _bundle(
        claims=["a"],
        sources=[("jira", "J1"), ("confluence", "C1")],
        questions=["unknown"],
    )
    curr = _bundle(
        claims=["a"],
        sources=[("jira", "J1")],
        questions=[],
    )
    changes = diff_bundles(previous=prev, current=curr)
    kinds = sorted(c.change_type for c in changes)
    assert kinds == ["question_resolved", "source_lost"]


def test_watch_and_persist_writes_one_row_per_change(session: Session) -> None:
    prev = _bundle(claims=["alpha"], sources=[("jira", "J1")], questions=[])
    curr = _bundle(
        claims=["alpha", "beta"],
        sources=[("jira", "J1"), ("jira", "J2")],
        questions=[],
    )
    rows = watch_and_persist(
        session, previous=prev, current=curr, topic_id="topic-1"
    )
    assert len(rows) == 1

    stored = list(session.scalars(select(ContextChangeRow)))
    assert len(stored) == 1
    assert stored[0].change_type == "claim_added"
    assert stored[0].topic_id == "topic-1"
