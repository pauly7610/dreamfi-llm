"""All ORM models import cleanly."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def test_models_importable() -> None:
    from dreamfi.db.models import (
        AuditEvent,
        ArtifactFeedback,
        Base,
        ConsoleTopic,
        EvalOutput,
        EvalRound,
        GoldExample,
        LearningProposal,
        OnyxDocumentMap,
        PromptVersion,
        ProductionOutcome,
        PublishLog,
        ReplayRun,
        ReplaySchedule,
        Skill,
    )

    assert Base.metadata.tables
    for cls in (
        Skill,
        PromptVersion,
        EvalRound,
        EvalOutput,
        GoldExample,
        PublishLog,
        ConsoleTopic,
        OnyxDocumentMap,
        AuditEvent,
        ArtifactFeedback,
        LearningProposal,
        ProductionOutcome,
        ReplaySchedule,
        ReplayRun,
    ):
        assert cls.__tablename__ in Base.metadata.tables


def test_prompt_versions_allow_only_one_active_per_skill(tmp_path: Path) -> None:
    from dreamfi.db.models import Base, PromptVersion, Skill

    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(
        Skill(
            skill_id="meeting_summary",
            display_name="Meeting Summary",
            description="Summarize meetings.",
            eval_template_path="evals/meeting_summary.md",
            eval_runner_path="evals/runners/run_meeting_summary_eval.py",
            criteria_json={},
        )
    )
    session.add_all(
        [
            PromptVersion(
                skill_id="meeting_summary",
                version=1,
                template="meeting_summary.jinja",
                system_prompt="v1",
                is_active=True,
            ),
            PromptVersion(
                skill_id="meeting_summary",
                version=2,
                template="meeting_summary.jinja",
                system_prompt="v2",
                is_active=True,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        session.commit()
