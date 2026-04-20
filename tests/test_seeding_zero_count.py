"""X3: zero-count skills are reported and block registration at boot."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dreamfi.db.models import Base, GoldExample
from dreamfi.skills.registry import (
    SKILLS,
    InsufficientRegressionCoverage,
    seed_registry,
)
from dreamfi.trust.seeding import missing_regression_examples

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_deficit_reports_skills_with_zero_regression_examples() -> None:
    # Skill A has some, skill B has none.
    examples = [
        GoldExample(gold_id="g1", workspace_id="w", skill_id="A", role="regression"),
        GoldExample(gold_id="g2", workspace_id="w", skill_id="A", role="regression"),
    ]
    deficits = missing_regression_examples(
        examples, minimum_per_skill=5, all_skill_ids={"A", "B"}
    )
    assert deficits == {"A": 3, "B": 5}


def test_deficit_without_all_skill_ids_still_misses_zero_skills() -> None:
    # Historical behavior: without all_skill_ids a zero-count skill is invisible.
    examples = [
        GoldExample(gold_id="g1", workspace_id="w", skill_id="A", role="regression"),
    ]
    deficits = missing_regression_examples(examples, minimum_per_skill=5)
    assert "B" not in deficits
    assert deficits == {"A": 4}


def test_seed_registry_raises_when_any_skill_below_minimum(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    session = Session(engine)

    with pytest.raises(InsufficientRegressionCoverage) as exc_info:
        seed_registry(session, repo_root=REPO_ROOT)  # default: strict

    deficits = exc_info.value.deficits
    # All 9 registered skills should be reported as deficient (none have gold yet).
    assert set(deficits.keys()) == {spec.skill_id for spec in SKILLS}
    assert all(v == 5 for v in deficits.values())


def test_seed_registry_passes_when_enforcement_disabled(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    session = Session(engine)

    count = seed_registry(
        session, repo_root=REPO_ROOT, enforce_regression_minimum=False
    )
    assert count == 3
