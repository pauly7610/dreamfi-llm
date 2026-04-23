"""Typed ContextBundle and its component schemas (C1).

A ContextBundle is the unit of "what we know about a topic right now."
It is not a blob of retrieved chunks; it is a structured, citable,
scored object with provenance for every claim.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

SourceType = Literal[
    "jira", "confluence", "metabase", "posthog", "ga", "slack", "doc", "onyx"
]
EntityType = Literal[
    "epic", "issue", "doc", "metric", "person", "squad", "release", "experiment"
]
RelationType = Literal[
    "parent_of", "child_of", "owns", "owned_by", "cited_in", "blocked_by",
    "blocks", "related_to",
]
OpenQuestionReason = Literal[
    "no_source", "stale_source", "conflicting_sources", "ambiguous"
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EntityRelation(BaseModel):
    relation_type: RelationType
    target_entity_id: str


class ContextSource(BaseModel):
    source_type: SourceType
    source_id: str
    fetched_at: datetime
    payload_hash: str
    raw_ref: str


class ContextEntity(BaseModel):
    entity_type: EntityType
    entity_id: str
    canonical_name: str
    relationships: list[EntityRelation] = Field(default_factory=list)


class ContextClaim(BaseModel):
    claim_id: UUID = Field(default_factory=uuid4)
    statement: str
    sot_id: str | None = None
    citation_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    last_verified_at: datetime = Field(default_factory=_utc_now)

    @field_validator("confidence")
    @classmethod
    def _clamp_confidence(cls, value: float) -> float:
        return max(0.0, min(1.0, value))


class OpenQuestion(BaseModel):
    question: str
    why_open: OpenQuestionReason
    suggested_owner: str | None = None


class ContextBundle(BaseModel):
    bundle_id: UUID = Field(default_factory=uuid4)
    workspace_id: str
    topic: str
    topic_key: str
    created_at: datetime = Field(default_factory=_utc_now)
    refreshed_at: datetime = Field(default_factory=_utc_now)
    ttl_seconds: int = 3600
    sources: list[ContextSource] = Field(default_factory=list)
    entities: list[ContextEntity] = Field(default_factory=list)
    claims: list[ContextClaim] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    freshness_score: float = 0.0
    coverage_score: float = 0.0
    confidence: float = 0.0

    @field_validator("freshness_score", "coverage_score", "confidence")
    @classmethod
    def _clamp_unit(cls, value: float) -> float:
        return max(0.0, min(1.0, value))

    def is_stale(self, *, now: datetime | None = None) -> bool:
        """True when the bundle's age exceeds its TTL."""
        reference = now or _utc_now()
        if self.refreshed_at.tzinfo is None:
            refreshed = self.refreshed_at.replace(tzinfo=timezone.utc)
        else:
            refreshed = self.refreshed_at
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        age_seconds = (reference - refreshed).total_seconds()
        return age_seconds > float(self.ttl_seconds)


def compute_coverage_score(*, answered_subquestions: int, total_subquestions: int) -> float:
    """Fraction of sub-questions the bundle's claims can answer.

    Defined per the C1 spec as
    ``claims_covering_question / total_subquestions``. Returns 0.0 when
    there are no sub-questions (nothing can be covered).
    """
    if total_subquestions <= 0:
        return 0.0
    if answered_subquestions < 0:
        return 0.0
    return max(0.0, min(1.0, answered_subquestions / total_subquestions))
