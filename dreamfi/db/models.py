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
    "ConsoleTopic",
    "EvalOutput",
    "EvalRound",
    "GoldDriftEvent",
    "GoldExample",
    "GoldRole",
    "OnyxDocumentMap",
    "PromptVersion",
    "PublishLog",
    "ResultStatus",
    "Skill",
]
