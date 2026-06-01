"""C5: topic resolution + topic graph semantics."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from dreamfi.context import (
    ContextBundle,
    ContextEntity,
    TopicHint,
    add_alias,
    link_entities,
    normalize_alias,
    resolve_topic,
)
from dreamfi.db.models import Base, TopicRelationRow, TopicRow


@pytest.fixture
def session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_normalize_alias_strips_articles_and_common_suffixes() -> None:
    assert normalize_alias("The Activation Squad") == "activation"
    assert normalize_alias("activation") == "activation"
    assert normalize_alias("Act Squad!") == "act"
    assert normalize_alias("Onboarding v3") == "onboarding-v3"


def test_resolve_topic_creates_then_returns_same_id(session: Session) -> None:
    first = resolve_topic(
        session, workspace_id="w1", question="the onboarding redesign"
    )
    assert first.is_new is True

    second = resolve_topic(
        session, workspace_id="w1", question="onboarding redesign"
    )
    assert second.is_new is False
    assert second.topic_id == first.topic_id


def test_resolve_topic_respects_workspace_isolation(session: Session) -> None:
    a = resolve_topic(session, workspace_id="w1", question="activation")
    b = resolve_topic(session, workspace_id="w2", question="activation")
    assert a.topic_id != b.topic_id


def test_resolve_topic_uses_epic_key_when_hinted(session: Session) -> None:
    r = resolve_topic(
        session,
        workspace_id="w1",
        question="what's happening with the epic",
        hint=TopicHint(epic_key="ACT-321"),
    )
    assert r.type == "epic"
    assert r.canonical_name == "ACT-321"

    # Second resolve with same hint returns the same topic.
    r2 = resolve_topic(
        session,
        workspace_id="w1",
        question="totally different wording",
        hint=TopicHint(epic_key="ACT-321"),
    )
    assert r2.topic_id == r.topic_id
    assert r2.is_new is False


def test_add_alias_makes_previously_unknown_phrase_resolve(session: Session) -> None:
    r = resolve_topic(session, workspace_id="w1", question="activation")
    add_alias(session, workspace_id="w1", topic_id=r.topic_id, alias="act squad")

    r2 = resolve_topic(session, workspace_id="w1", question="act squad")
    assert r2.topic_id == r.topic_id


def test_link_entities_dedups_across_bundles(session: Session) -> None:
    r = resolve_topic(session, workspace_id="w1", question="onboarding redesign")

    now = datetime.now(timezone.utc)
    bundle_a = ContextBundle(
        workspace_id="w1",
        topic="onboarding redesign",
        topic_key="onboarding-redesign",
        entities=[
            ContextEntity(
                entity_type="issue",
                entity_id="ACT-412",
                canonical_name="ACT-412",
            ),
        ],
        refreshed_at=now,
    )
    bundle_b = ContextBundle(
        workspace_id="w1",
        topic="onboarding redesign",
        topic_key="onboarding-redesign",
        entities=[
            ContextEntity(
                entity_type="issue",
                entity_id="ACT-412",
                canonical_name="ACT-412",  # same entity — must dedup
            ),
        ],
        refreshed_at=now,
    )

    edges_a = link_entities(session, bundle=bundle_a, topic_id=r.topic_id)
    edges_b = link_entities(session, bundle=bundle_b, topic_id=r.topic_id)
    assert len(edges_a) == 1
    assert len(edges_b) == 0  # deduped

    topics = list(session.scalars(select(TopicRow).where(TopicRow.workspace_id == "w1")))
    # Source topic + one issue node.
    assert len(topics) == 2

    edges = list(session.scalars(select(TopicRelationRow)))
    assert len(edges) == 1
    assert edges[0].relation_type == "related_to"
