from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
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
        Index(
            "ix_prompt_versions_one_active_per_skill",
            "skill_id",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active = 1"),
        ),
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


class ConsoleTopic(Base):
    __tablename__ = "console_topics"

    topic_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String, nullable=False, default="unassigned")
    status: Mapped[str] = mapped_column(String, nullable=False, default="discovery")
    target_decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    default_generator_slug: Mapped[str] = mapped_column(String, nullable=False, default="weekly-brief")
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
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, default=Decimal("0")
    )
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
    __tablename__ = "context_changes"

    change_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    topic_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    topic_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    change_type: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    old_bundle_id: Mapped[str | None] = mapped_column(String, nullable=True)
    new_bundle_id: Mapped[str | None] = mapped_column(String, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )


class MetricCatalogRow(Base):
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
    source_systems_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class MetricSnapshotRow(Base):
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


class ConnectorSetting(Base):
    __tablename__ = "connector_settings"
    __table_args__ = (
        Index("ix_connector_settings_activation_status", "activation_status"),
        Index("ix_connector_settings_validation_status", "validation_status"),
    )

    connector_id: Mapped[str] = mapped_column(String, primary_key=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    credential_status: Mapped[str] = mapped_column(String, nullable=False, default="missing")
    secret_last_four: Mapped[str | None] = mapped_column(String, nullable=True)
    secret_sha256: Mapped[str | None] = mapped_column(String, nullable=True)
    secret_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    secret_key_id: Mapped[str | None] = mapped_column(String, nullable=True)
    secret_label: Mapped[str | None] = mapped_column(String, nullable=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    validation_status: Mapped[str] = mapped_column(String, nullable=False, default="not_validated")
    validation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    document_set_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_set_name: Mapped[str | None] = mapped_column(String, nullable=True)
    document_set_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retrieval_status: Mapped[str | None] = mapped_column(String, nullable=True)
    freshest_document_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activation_status: Mapped[str] = mapped_column(String, nullable=False, default="inactive")
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_probe_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )


class ConnectorSyncRun(Base):
    __tablename__ = "connector_sync_runs"
    __table_args__ = (
        Index("ix_connector_sync_runs_connector_started", "connector_id", "started_at"),
        Index("ix_connector_sync_runs_status_started", "status", "started_at"),
    )

    sync_run_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    connector_id: Mapped[str] = mapped_column(ForeignKey("connector_settings.connector_id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    trigger: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    pulled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    persisted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ingested_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cursor_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConnectorDocument(Base):
    __tablename__ = "connector_documents"
    __table_args__ = (
        UniqueConstraint("connector_id", "external_id", name="uq_connector_documents_source_external"),
        Index("ix_connector_documents_connector_updated", "connector_id", "doc_updated_at"),
        Index("ix_connector_documents_content_hash", "content_hash"),
    )

    connector_document_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    connector_id: Mapped[str] = mapped_column(ForeignKey("connector_settings.connector_id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    sync_run_id: Mapped[str | None] = mapped_column(ForeignKey("connector_sync_runs.sync_run_id"), nullable=True)
    onyx_document_id: Mapped[str | None] = mapped_column(String, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )


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


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_created_at", "created_at"),
        Index("ix_audit_events_request_id", "request_id"),
        Index("ix_audit_events_actor_created_at", "actor_id", "created_at"),
        Index("ix_audit_events_target", "target_type", "target_id"),
        Index("ix_audit_events_category_action", "category", "action"),
    )

    event_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    event_hash: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False, default="info")
    actor_id: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_type: Mapped[str] = mapped_column(String, nullable=False, default="anonymous")
    auth_method: Mapped[str | None] = mapped_column(String, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String, nullable=True)
    http_method: Mapped[str | None] = mapped_column(String, nullable=True)
    path: Mapped[str | None] = mapped_column(String, nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_type: Mapped[str | None] = mapped_column(String, nullable=True)
    target_id: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)


class ArtifactFeedback(Base):
    __tablename__ = "artifact_feedback"
    __table_args__ = (
        Index("ix_artifact_feedback_output_created_at", "output_id", "created_at"),
        Index("ix_artifact_feedback_reviewer_created_at", "reviewer_id", "created_at"),
        Index("ix_artifact_feedback_outcome_created_at", "outcome", "created_at"),
    )

    feedback_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    output_id: Mapped[str] = mapped_column(ForeignKey("eval_outputs.output_id"), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_text_hash: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    gold_id: Mapped[str | None] = mapped_column(ForeignKey("gold_examples.gold_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)


class WorkflowTrace(Base):
    __tablename__ = "workflow_traces"
    __table_args__ = (
        Index("ix_workflow_traces_workspace_created", "workspace_id", "created_at"),
        Index("ix_workflow_traces_workflow_created", "workflow_type", "created_at"),
        Index("ix_workflow_traces_topic_created", "topic_id", "created_at"),
        Index("ix_workflow_traces_outcome_created", "outcome", "created_at"),
    )

    trace_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    actor_id: Mapped[str] = mapped_column(String, nullable=False)
    workflow_type: Mapped[str] = mapped_column(String, nullable=False)
    starter_question_hash: Mapped[str] = mapped_column(String, nullable=False)
    starter_question_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    topic_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    required_identifiers_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    steps_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    accepted_evidence_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    rejected_evidence_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    human_edits_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    outcome: Mapped[str] = mapped_column(String, nullable=False, default="completed")
    final_artifact_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)


class SkillCandidate(Base):
    __tablename__ = "skill_candidates"
    __table_args__ = (
        Index("ix_skill_candidates_status_created", "status", "created_at"),
        Index("ix_skill_candidates_workspace_workflow", "workspace_id", "workflow_type"),
    )

    candidate_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    workflow_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    source_trace_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trace_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    intent_summary: Mapped[str] = mapped_column(Text, nullable=False)
    required_inputs_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source_contract_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    tool_plan_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    freshness_contract_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    answer_contract_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    refusal_rules_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    eval_seed_cases_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reviewer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=_utc_now,
    )


class LearningProposal(Base):
    __tablename__ = "learning_proposals"
    __table_args__ = (
        Index("ix_learning_proposals_status_created_at", "status", "created_at"),
        Index("ix_learning_proposals_skill_status", "skill_id", "status"),
        Index("ix_learning_proposals_cluster", "cluster_key"),
    )

    proposal_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.skill_id"), nullable=False)
    prompt_version_id: Mapped[str | None] = mapped_column(ForeignKey("prompt_versions.prompt_version_id"), nullable=True)
    cluster_key: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_prompt_patch: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    source_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reviewer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_prompt_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("prompt_versions.prompt_version_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)


class ProductionOutcome(Base):
    __tablename__ = "production_outcomes"
    __table_args__ = (
        Index("ix_production_outcomes_output_created_at", "output_id", "created_at"),
        Index("ix_production_outcomes_outcome_created_at", "outcome", "created_at"),
    )

    outcome_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    output_id: Mapped[str] = mapped_column(ForeignKey("eval_outputs.output_id"), nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    actor_id: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_text_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)


class ReplaySchedule(Base):
    __tablename__ = "replay_schedules"
    __table_args__ = (
        Index("ix_replay_schedules_active_next_run", "is_active", "next_run_at"),
        Index("ix_replay_schedules_skill_active", "skill_id", "is_active"),
    )

    schedule_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    replay_type: Mapped[str] = mapped_column(String, nullable=False)
    skill_id: Mapped[str | None] = mapped_column(ForeignKey("skills.skill_id"), nullable=True)
    prompt_version_id: Mapped[str | None] = mapped_column(ForeignKey("prompt_versions.prompt_version_id"), nullable=True)
    cadence_days: Mapped[int] = mapped_column(Integer, nullable=False)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)


class ReplayRun(Base):
    __tablename__ = "replay_runs"
    __table_args__ = (
        Index("ix_replay_runs_schedule_started_at", "schedule_id", "started_at"),
        Index("ix_replay_runs_status_started_at", "status", "started_at"),
    )

    replay_run_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid_str)
    schedule_id: Mapped[str] = mapped_column(ForeignKey("replay_schedules.schedule_id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    skill_id: Mapped[str | None] = mapped_column(ForeignKey("skills.skill_id"), nullable=True)
    prompt_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("prompt_versions.prompt_version_id"), nullable=True
    )
    round_id: Mapped[str | None] = mapped_column(ForeignKey("eval_rounds.round_id"), nullable=True)
    output_id: Mapped[str | None] = mapped_column(ForeignKey("eval_outputs.output_id"), nullable=True)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = [
    "ArtifactFeedback",
    "AuditEvent",
    "Base",
    "ConnectorDocument",
    "ConnectorSetting",
    "ConnectorSyncRun",
    "ConsoleTopic",
    "ContextBundleRow",
    "ContextChangeRow",
    "ContextClaimRow",
    "ContextEntityRow",
    "ContextQuestionRow",
    "ContextSourceRow",
    "EvalOutput",
    "EvalRound",
    "GoldDriftEvent",
    "GoldExample",
    "GoldRole",
    "MetricCatalogRow",
    "MetricSnapshotRow",
    "OnyxDocumentMap",
    "OpenQuestionRow",
    "PromptVersion",
    "ProductionOutcome",
    "PublishLog",
    "LearningProposal",
    "ReplayRun",
    "ReplaySchedule",
    "ResultStatus",
    "Skill",
    "SkillCandidate",
    "TopicAliasRow",
    "TopicRelationRow",
    "TopicRow",
    "WorkflowTrace",
]
