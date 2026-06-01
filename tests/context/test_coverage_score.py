"""C1: coverage_score = claims_covering_question / total_subquestions."""
from __future__ import annotations

from dreamfi.context import compute_coverage_score


def test_full_coverage() -> None:
    assert compute_coverage_score(answered_subquestions=4, total_subquestions=4) == 1.0


def test_partial_coverage() -> None:
    assert compute_coverage_score(answered_subquestions=3, total_subquestions=4) == 0.75


def test_no_subquestions_is_zero_coverage() -> None:
    assert compute_coverage_score(answered_subquestions=0, total_subquestions=0) == 0.0


def test_clamps_overflow_and_negatives() -> None:
    # More "answered" than there are sub-questions is still capped at 1.0.
    assert compute_coverage_score(answered_subquestions=10, total_subquestions=4) == 1.0
    # Negative answered counts collapse to 0.0.
    assert compute_coverage_score(answered_subquestions=-1, total_subquestions=4) == 0.0
