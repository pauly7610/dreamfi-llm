"""All ORM models import cleanly."""
from __future__ import annotations


def test_models_importable() -> None:
    from dreamfi.db.models import (
        Base,
        EvalOutput,
        EvalRound,
        GoldExample,
        OnyxDocumentMap,
        PromptVersion,
        PublishLog,
        Skill,
    )

    assert Base.metadata.tables
    for cls in (Skill, PromptVersion, EvalRound, EvalOutput, GoldExample, PublishLog, OnyxDocumentMap):
        assert cls.__tablename__ in Base.metadata.tables
