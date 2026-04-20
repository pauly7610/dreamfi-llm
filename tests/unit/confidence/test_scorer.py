"""Confidence scorer tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from dreamfi.confidence.scorer import ConfidenceScorer


def test_confidence_zero_when_no_citations() -> None:
    s = ConfidenceScorer()
    r = s.score(
        eval_score=1.0, freshness_score=1.0, citation_count=0, hard_gate_passed=True
    )
    assert r.confidence == 0.0


def test_confidence_halved_on_hard_gate_fail() -> None:
    s = ConfidenceScorer()
    passing = s.score(
        eval_score=1.0, freshness_score=1.0, citation_count=5, hard_gate_passed=True
    ).confidence
    failing = s.score(
        eval_score=1.0, freshness_score=1.0, citation_count=5, hard_gate_passed=False
    ).confidence
    assert abs(failing - passing * 0.5) < 1e-6


def test_freshness_zero_when_no_dates() -> None:
    assert ConfidenceScorer().freshness_from_updated_at([]) == 0.0


def test_freshness_decays_over_time() -> None:
    now = datetime.now(timezone.utc)
    s = ConfidenceScorer(freshness_halflife_days=14.0)
    fresh = s.freshness_from_updated_at([now], now=now)
    old = s.freshness_from_updated_at([now - timedelta(days=14)], now=now)
    assert fresh > old
    assert abs(old - 0.5) < 1e-3
