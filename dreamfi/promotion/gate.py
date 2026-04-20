"""Promotion gate + publish guard."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from dreamfi.config import get_settings


@dataclass
class PromotionDecision:
    promotable: bool
    reason: str
    improvement: float | None


class PromotionGate:
    def __init__(
        self,
        *,
        improvement_threshold: float | None = None,
    ) -> None:
        self.improvement_threshold = (
            improvement_threshold
            if improvement_threshold is not None
            else get_settings().dreamfi_improvement_threshold
        )

    def decide(
        self,
        *,
        new_score: float | Decimal,
        previous_score: float | Decimal | None,
    ) -> PromotionDecision:
        new = float(new_score)
        if previous_score is None:
            return PromotionDecision(
                promotable=True,
                reason="No prior active version — promoting baseline.",
                improvement=None,
            )
        prev = float(previous_score)
        improvement = new - prev
        if improvement < self.improvement_threshold:
            return PromotionDecision(
                promotable=False,
                reason=(
                    f"REGRESSION: improvement {improvement:+.4f} "
                    f"< required {self.improvement_threshold:+.4f}"
                ),
                improvement=improvement,
            )
        return PromotionDecision(
            promotable=True,
            reason=f"Improvement {improvement:+.4f} meets threshold.",
            improvement=improvement,
        )


@dataclass
class PublishDecision:
    allowed: bool
    reason: str


class PublishGuard:
    def __init__(
        self,
        *,
        confidence_threshold: float | None = None,
    ) -> None:
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else get_settings().dreamfi_confidence_threshold
        )

    def check(
        self,
        *,
        pass_fail: str,
        confidence: float | Decimal | None,
    ) -> PublishDecision:
        if pass_fail != "pass":
            return PublishDecision(allowed=False, reason="Hard gate failed.")
        c = float(confidence or 0.0)
        if c < self.confidence_threshold:
            return PublishDecision(
                allowed=False,
                reason=f"Low confidence {c:.3f} < {self.confidence_threshold:.3f}",
            )
        return PublishDecision(allowed=True, reason="Ready to publish.")
