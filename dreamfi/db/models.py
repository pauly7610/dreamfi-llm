"""SQLAlchemy ORM models for the DreamFi-owned database."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class Skill(Base):
    __tablename__ = "skills"

    skill_id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    eval_template_path: Mapped[str] = mapped_column(String, nullable=False)
    eval_runner_path: Mapped[str] = mapped_column(String, nullable=False)
    criteria_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    onyx_persona_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    prompt_versions: Mapped[list[PromptVersion]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("skill_id", "version", name="uq_prompt_versions_skill_version"),
        Index(
            "one_active_per_skill",
            "skill_id",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active"),
        ),
    )

    prompt_version_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    skill_id: Mapped[str] = mapped_column(
        String, ForeignKey("skills.skill_id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("prompt_versions.prompt_version_id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    skill: Mapped[Skill] = relationship(back_populates="prompt_versions")


class EvalRound(Base):
    __tablename__ = "eval_rounds"

    round_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    skill_id: Mapped[str] = mapped_column(
        String, ForeignKey("skills.skill_id"), nullable=False
    )
    prompt_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("prompt_versions.prompt_version_id"), nullable=False
    )
    n_inputs: Mapped[int] = mapped_column(Integer, nullable=False)
    n_outputs_per_input: Mapped[int] = mapped_column(Integer, nullable=False)
    total_outputs: Mapped[int] = mapped_column(Integer, nullable=False)
    total_passes: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    previous_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    improvement: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    artifacts_path: Mapped[str] = mapped_column(String, nullable=False)


class EvalOutput(Base):
    __tablename__ = "eval_outputs"

    output_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    round_id: Mapped[str] = mapped_column(
        String, ForeignKey("eval_rounds.round_id", ondelete="CASCADE"), nullable=False
    )
    test_input_label: Mapped[str] = mapped_column(String, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_text: Mapped[str] = mapped_column(Text, nullable=False)
    criteria_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    pass_fail: Mapped[str] = mapped_column(String, nullable=False)
    onyx_chat_session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    onyx_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    onyx_citations_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    freshness_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GoldExample(Base):
    __tablename__ = "gold_examples"
    __table_args__ = (
        Index("gold_examples_lookup", "skill_id", "scenario_type"),
    )

    gold_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    skill_id: Mapped[str] = mapped_column(String, ForeignKey("skills.skill_id"), nullable=False)
    scenario_type: Mapped[str] = mapped_column(String, nullable=False)
    input_context_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    output_text: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("prompt_versions.prompt_version_id"), nullable=False
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PublishLog(Base):
    __tablename__ = "publish_log"

    publish_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    skill_id: Mapped[str] = mapped_column(String, ForeignKey("skills.skill_id"), nullable=False)
    prompt_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("prompt_versions.prompt_version_id"), nullable=False
    )
    output_id: Mapped[str] = mapped_column(
        String, ForeignKey("eval_outputs.output_id"), nullable=False
    )
    destination: Mapped[str] = mapped_column(String, nullable=False)
    destination_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OnyxDocumentMap(Base):
    __tablename__ = "onyx_document_map"

    onyx_document_id: Mapped[str] = mapped_column(String, primary_key=True)
    dreamfi_topic_tag: Mapped[str | None] = mapped_column(String, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
