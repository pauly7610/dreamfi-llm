"""C1: ContextBundle round-trips through Pydantic and persists via ORM."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from dreamfi.context import (
    ContextBundle,
    ContextClaim,
    ContextEntity,
    ContextSource,
    EntityRelation,
    OpenQuestion,
)
from dreamfi.db.models import (
    Base,
    ContextBundleRow,
    ContextClaimRow,
    ContextEntityRow,
    ContextSourceRow,
    OpenQuestionRow,
)


def _sample_bundle() -> ContextBundle:
    now = datetime.now(timezone.utc)
    return ContextBundle(
        workspace_id="ws_abc",
        topic="onboarding redesign",
        topic_key="onboarding-redesign",
        created_at=now,
        refreshed_at=now,
        ttl_seconds=3600,
        sources=[
            ContextSource(
                source_type="jira",
                source_id="ACT-321",
                fetched_at=now,
                payload_hash="sha256:abc",
                raw_ref="s3://dreamfi/ws_abc/jira/ACT-321.json",
            ),
            ContextSource(
                source_type="confluence",
                source_id="18432",
                fetched_at=now,
                payload_hash="sha256:def",
                raw_ref="s3://dreamfi/ws_abc/conf/18432.json",
            ),
        ],
        entities=[
            ContextEntity(
                entity_type="epic",
                entity_id="ACT-321",
                canonical_name="Onboarding v3",
                relationships=[
                    EntityRelation(relation_type="owns", target_entity_id="person:laila"),
                    EntityRelation(relation_type="cited_in", target_entity_id="doc:18432"),
                ],
            ),
        ],
        claims=[
            ContextClaim(
                statement="ACT-412 is blocked on design review",
                citation_ids=["jira:ACT-412"],
                confidence=0.9,
                last_verified_at=now,
            ),
        ],
        open_questions=[
            OpenQuestion(
                question="Is legal sign-off required for EU rollout?",
                why_open="no_source",
                suggested_owner="person:ahmed",
            ),
        ],
        freshness_score=0.91,
        coverage_score=0.78,
        confidence=0.84,
    )


def test_bundle_roundtrips_through_json() -> None:
    bundle = _sample_bundle()
    dumped = bundle.model_dump_json()
    restored = ContextBundle.model_validate_json(dumped)

    assert restored.bundle_id == bundle.bundle_id
    assert restored.topic_key == "onboarding-redesign"
    assert len(restored.sources) == 2
    assert restored.sources[0].source_type == "jira"
    assert restored.claims[0].citation_ids == ["jira:ACT-412"]
    assert restored.entities[0].relationships[0].relation_type == "owns"
    assert restored.open_questions[0].why_open == "no_source"


def test_bundle_rejects_unknown_literal_values() -> None:
    with pytest.raises(Exception):  # pydantic.ValidationError
        ContextSource(
            source_type="salesforce",  # type: ignore[arg-type]
            source_id="x",
            fetched_at=datetime.now(timezone.utc),
            payload_hash="h",
            raw_ref="r",
        )


def test_bundle_clamps_unit_interval_scores() -> None:
    # Values outside [0,1] are clamped by the validator.
    bundle = ContextBundle(
        workspace_id="w",
        topic="t",
        topic_key="t",
        freshness_score=5.0,
        coverage_score=-2.0,
        confidence=0.5,
    )
    assert bundle.freshness_score == 1.0
    assert bundle.coverage_score == 0.0
    assert bundle.confidence == 0.5


def test_bundle_persists_and_reloads_via_orm(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path}/ctx.db")
    Base.metadata.create_all(engine)
    session = Session(engine)

    src = _sample_bundle()
    row = ContextBundleRow(
        bundle_id=str(src.bundle_id),
        workspace_id=src.workspace_id,
        topic=src.topic,
        topic_key=src.topic_key,
        created_at=src.created_at,
        refreshed_at=src.refreshed_at,
        ttl_seconds=src.ttl_seconds,
        freshness_score=Decimal(str(src.freshness_score)),
        coverage_score=Decimal(str(src.coverage_score)),
        confidence=Decimal(str(src.confidence)),
    )
    row.sources = [
        ContextSourceRow(
            source_row_id=str(uuid4()),
            source_type=s.source_type,
            source_id=s.source_id,
            fetched_at=s.fetched_at,
            payload_hash=s.payload_hash,
            raw_ref=s.raw_ref,
        )
        for s in src.sources
    ]
    row.entities = [
        ContextEntityRow(
            entity_row_id=str(uuid4()),
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            canonical_name=e.canonical_name,
            relationships_json=[r.model_dump() for r in e.relationships],
        )
        for e in src.entities
    ]
    row.claims = [
        ContextClaimRow(
            claim_id=str(c.claim_id),
            statement=c.statement,
            sot_id=c.sot_id,
            citation_ids_json=list(c.citation_ids),
            confidence=Decimal(str(c.confidence)),
            last_verified_at=c.last_verified_at,
        )
        for c in src.claims
    ]
    row.open_questions = [
        OpenQuestionRow(
            question_id=str(uuid4()),
            question=q.question,
            why_open=q.why_open,
            suggested_owner=q.suggested_owner,
        )
        for q in src.open_questions
    ]
    session.add(row)
    session.commit()
    session.close()

    # Reload from a fresh session.
    session = Session(engine)
    loaded = session.scalar(
        select(ContextBundleRow).where(
            ContextBundleRow.bundle_id == str(src.bundle_id)
        )
    )
    assert loaded is not None
    assert loaded.topic_key == "onboarding-redesign"
    assert len(loaded.sources) == 2
    assert {s.source_type for s in loaded.sources} == {"jira", "confluence"}
    assert loaded.claims[0].citation_ids_json == ["jira:ACT-412"]
    assert loaded.entities[0].relationships_json[0]["relation_type"] == "owns"
