"""Confidence scorer (ADR-005) — DreamFi inputs wired to Onyx retrieval data."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class ConfidenceResult:
    confidence: float
    freshness_score: float
    citation_count: int
    hard_gate_passed: bool
    eval_score: float
    reasoning: list[str] = field(default_factory=list)


class ConfidenceScorer:
    def __init__(self, *, freshness_halflife_days: float = 14.0) -> None:
        self.halflife_days = freshness_halflife_days

    def score(
        self,
        *,
        eval_score: float,
        freshness_score: float,
        citation_count: int,
        hard_gate_passed: bool,
    ) -> ConfidenceResult:
        e = max(0.0, min(1.0, eval_score))
        f = max(0.0, min(1.0, freshness_score))
        citation_factor = min(citation_count, 5) / 5.0
        hard_gate_factor = 1.0 if hard_gate_passed else 0.5
        confidence = round(e * f * citation_factor * hard_gate_factor, 3)
        reasoning = [
            f"eval_score={e:.2f}",
            f"freshness={f:.2f}",
            f"citations={citation_count} (factor={citation_factor:.2f})",
            f"hard_gate={'pass' if hard_gate_passed else 'fail'} (factor={hard_gate_factor})",
        ]
        return ConfidenceResult(
            confidence=confidence,
            freshness_score=f,
            citation_count=citation_count,
            hard_gate_passed=hard_gate_passed,
            eval_score=e,
            reasoning=reasoning,
        )

    def freshness_from_updated_at(
        self,
        updated_ats: list[datetime | None],
        *,
        now: datetime | None = None,
    ) -> float:
        """Mean per-doc exponential-decay freshness."""
        if not updated_ats:
            return 0.0
        ref = now or datetime.now(UTC)
        vals = []
        for t in updated_ats:
            if t is None:
                continue
            if t.tzinfo is None:
                t = t.replace(tzinfo=UTC)
            age_days = max(0.0, (ref - t).total_seconds() / 86400.0)
            vals.append(math.exp(-math.log(2) * age_days / self.halflife_days))
        if not vals:
            return 0.0
        return sum(vals) / len(vals)
