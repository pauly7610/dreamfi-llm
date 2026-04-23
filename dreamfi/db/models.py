from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

GoldRole = Literal["exemplar", "regression", "counter_example", "canary"]
ResultStatus = Literal["pass", "fail"]


def _uuid_str() -> str:
    return str(uuid.uuid4())


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Skill(Base):
    __tablename__ = "skills"

    skill_id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    eval_template_path: Mapped[str] = mapped_column(String, nullable=False)
    eval_runner_path: Mapped[str] = mapped_column(String, nullable=False)
    criteria_json: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    onyx_persona_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)

    prompt_versions: Mapped[list[PromptVersion]] = relationship(back_populates="skill")
    eval_rounds: Mapped[list[EvalRound]] = relationship(back_populates="skill")
    gold_examples: Mapped[list[GoldExample]] = relationship(back_populates="skill")


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("skill_id", "version", name="uq_prompt_versions_skill_version"),
    )

    prompt_version_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.skill_id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parent_version_id: Mapped[str | None] = mapped_column(ForeignKey("prompt_versions.prompt_version_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    skill: Mapped[Skill] = relationship(back_populates="prompt_versions")


class EvalRound(Base):
    __tablename__ = "eval_rounds"

    round_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.skill_id"), nullable=False)
    prompt_version_id: Mapped[str] = mapped_column(ForeignKey("prompt_versions.prompt_version_id"), nullable=False)
    n_inputs: Mapped[int] = mapped_column(Integer, nullable=False)
    n_outputs_per_input: Mapped[int] = mapped_column(Integer, nullable=False)
    total_outputs: Mapped[int] = mapped_column(Integer, nullable=False)
    total_passes: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    previous_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    improvement: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    artifacts_path: Mapped[str] = mapped_column(String, nullable=False)

    skill: Mapped[Skill] = relationship(back_populates="eval_rounds")
    outputs: Mapped[list[EvalOutput]] = relationship(back_populates="round")


class EvalOutput(Base):
    __tablename__ = "eval_outputs"

    output_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    round_id: Mapped[str] = mapped_column(ForeignKey("eval_rounds.round_id", ondelete="CASCADE"), nullable=False)
    test_input_label: Mapped[str] = mapped_column(String, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_text: Mapped[str] = mapped_column(Text, nullable=False)
    criteria_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    pass_fail: Mapped[str] = mapped_column(String, nullable=False)
    onyx_chat_session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    onyx_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    onyx_citations_json: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    freshness_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    export_readiness: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    export_breakdown_json: Mapped[dict[str, float] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)

    round: Mapped[EvalRound] = relationship(back_populates="outputs")


class GoldExample(Base):
    __tablename__ = "gold_examples"

    gold_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False, default="")
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.skill_id"), nullable=False)
    scenario_type: Mapped[str] = mapped_column(String, nullable=False, default="default")
    input_context_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    output_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    prompt_version_id: Mapped[str] = mapped_column(ForeignKey("prompt_versions.prompt_version_id"), nullable=False, default="")
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="exemplar")
    expected_pass_criteria: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    last_run_round_id: Mapped[str | None] = mapped_column(String, nullable=True)
    last_result: Mapped[str | None] = mapped_column(Text, nullable=True)

    skill: Mapped[Skill] = relationship(back_populates="gold_examples")


class PublishLog(Base):
    __tablename__ = "publish_log"

    publish_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.skill_id"), nullable=False)
    prompt_version_id: Mapped[str] = mapped_column(ForeignKey("prompt_versions.prompt_version_id"), nullable=False)
    output_id: Mapped[str] = mapped_column(ForeignKey("eval_outputs.output_id"), nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    destination_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)


class OnyxDocumentMap(Base):
    __tablename__ = "onyx_document_map"

    onyx_document_id: Mapped[str] = mapped_column(String, primary_key=True)
    dreamfi_topic_tag: Mapped[str | None] = mapped_column(String, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)


class ContextBundleRow(Base):
    __tablename__ = "context_bundles"

    bundle_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    topic_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, index=True
    )
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    freshness_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    coverage_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)

    sources: Mapped[list[ContextSourceRow]] = relationship(
        back_populates="bundle", cascade="all, delete-orphan"
    )
    entities: Mapped[list[ContextEntityRow]] = relationship(
        back_populates="bundle", cascade="all, delete-orphan"
    )
    claims: Mapped[list[ContextClaimRow]] = relationship(
        back_populates="bundle", cascade="all, delete-orphan"
    )
    open_questions: Mapped[list[OpenQuestionRow]] = relationship(
        back_populates="bundle", cascade="all, delete-orphan"
    )


class ContextSourceRow(Base):
    __tablename__ = "context_sources"

    source_row_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    bundle_id: Mapped[str] = mapped_column(
        ForeignKey("context_bundles.bundle_id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String, nullable=False)
    raw_ref: Mapped[str] = mapped_column(Text, nullable=False)

    bundle: Mapped[ContextBundleRow] = relationship(back_populates="sources")


class ContextEntityRow(Base):
    __tablename__ = "context_entities"

    entity_row_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    bundle_id: Mapped[str] = mapped_column(
        ForeignKey("context_bundles.bundle_id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    relationships_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )

    bundle: Mapped[ContextBundleRow] = relationship(back_populates="entities")


class ContextClaimRow(Base):
    __tablename__ = "context_claims"

    claim_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    bundle_id: Mapped[str] = mapped_column(
        ForeignKey("context_bundles.bundle_id", ondelete="CASCADE"), nullable=False
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    sot_id: Mapped[str | None] = mapped_column(String, nullable=True)
    citation_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, default=Decimal("0"))
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    bundle: Mapped[ContextBundleRow] = relationship(back_populates="claims")


class OpenQuestionRow(Base):
    __tablename__ = "open_questions"

    question_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    bundle_id: Mapped[str] = mapped_column(
        ForeignKey("context_bundles.bundle_id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    why_open: Mapped[str] = mapped_column(String, nullable=False)
    suggested_owner: Mapped[str | None] = mapped_column(String, nullable=True)

    bundle: Mapped[ContextBundleRow] = relationship(back_populates="open_questions")


class ContextQuestionRow(Base):
    """Memory layer (C7) — every Ask call writes a row so repeat questions can
    surface prior answers."""

    __tablename__ = "context_questions"

    question_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    asker: Mapped[str] = mapped_column(String, nullable=False, default="")
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_norm: Mapped[str] = mapped_column(String, nullable=False, index=True)
    topic_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    bundle_id: Mapped[str | None] = mapped_column(String, nullable=True)
    answer_excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tokens_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    asked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )


class ContextChangeRow(Base):
    """C6 — diff event emitted by the watcher when a bundle refreshed and
    something material changed."""

    __tablename__ = "context_changes"

    change_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    topic_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    topic_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    change_type: Mapped[str] = mapped_column(String, nullable=False)  # claim_added/removed/source_lost/question_resolved
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    old_bundle_id: Mapped[str | None] = mapped_column(String, nullable=True)
    new_bundle_id: Mapped[str | None] = mapped_column(String, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )


class MetricCatalogRow(Base):
    """T2' — source-of-truth metric catalog."""

    __tablename__ = "metric_catalog"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "metric_id", name="uq_metric_catalog_ws_metric"
        ),
    )

    row_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    metric_id: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    owner: Mapped[str | None] = mapped_column(String, nullable=True)
    source_systems_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )


class MetricSnapshotRow(Base):
    """T2' — point-in-time metric reading; enables discrepancy checks."""

    __tablename__ = "metric_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    metric_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String, nullable=False)
    as_of_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )


class TopicRow(Base):
    """Canonical topic node in the Topic Graph (C5)."""

    __tablename__ = "topics"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "canonical_name", "type", name="uq_topics_ws_name_type"
        ),
    )

    topic_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String, nullable=False)
    attributes_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    aliases: Mapped[list[TopicAliasRow]] = relationship(
        back_populates="topic", cascade="all, delete-orphan"
    )


class TopicAliasRow(Base):
    __tablename__ = "topic_aliases"
    __table_args__ = (
        UniqueConstraint("workspace_id", "alias_norm", name="uq_topic_aliases_ws_norm"),
    )

    alias_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    topic_id: Mapped[str] = mapped_column(
        ForeignKey("topics.topic_id", ondelete="CASCADE"), nullable=False, index=True
    )
    alias: Mapped[str] = mapped_column(String, nullable=False)
    alias_norm: Mapped[str] = mapped_column(String, nullable=False)

    topic: Mapped[TopicRow] = relationship(back_populates="aliases")


class TopicRelationRow(Base):
    __tablename__ = "topic_relations"

    relation_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    from_id: Mapped[str] = mapped_column(
        ForeignKey("topics.topic_id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_id: Mapped[str] = mapped_column(
        ForeignKey("topics.topic_id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, default=Decimal("1.000")
    )
    source_bundle_id: Mapped[str | None] = mapped_column(String, nullable=True)


class GoldDriftEvent(Base):
    __tablename__ = "gold_drift_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    gold_id: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version_id: Mapped[str] = mapped_column(String, nullable=False)
    previous_result: Mapped[str] = mapped_column(Text, nullable=False)
    new_result: Mapped[str] = mapped_column(Text, nullable=False)
    round_id: Mapped[str] = mapped_column(String, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)


__all__ = [
    "Base",
    "ContextBundleRow",
    "ContextChangeRow",
    "ContextClaimRow",
    "ContextEntityRow",
    "ContextQuestionRow",
    "ContextSourceRow",
    "MetricCatalogRow",
    "MetricSnapshotRow",
    "EvalOutput",
    "EvalRound",
    "GoldDriftEvent",
    "GoldExample",
    "GoldRole",
    "OnyxDocumentMap",
    "OpenQuestionRow",
    "PromptVersion",
    "PublishLog",
    "ResultStatus",
    "Skill",
    "TopicAliasRow",
    "TopicRelationRow",
    "TopicRow",
]
