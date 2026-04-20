from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ResultStatus = Literal["pass", "fail"]


@dataclass(frozen=True)
class GoldResult:
    gold_id: str
    prev: ResultStatus
    new: ResultStatus


@dataclass(frozen=True)
class PromotionDecision:
    promotable: bool
    reason: str


class PromotionGate:
    """Trust-first promotion gate with regression blocking."""

    def decide(
        self,
        *,
        new_score: float,
        previous_score: float,
        regression_failures: list[GoldResult],
        canary_failures: list[GoldResult],
    ) -> PromotionDecision:
        if regression_failures:
            ids = ",".join(sorted(f"regression:{r.gold_id}" for r in regression_failures))
            return PromotionDecision(False, f"blocked_by_regression:{ids}")

        if new_score <= previous_score:
            return PromotionDecision(False, "no_main_score_improvement")

        if canary_failures:
            ids = ",".join(sorted(f"canary:{r.gold_id}" for r in canary_failures))
            return PromotionDecision(True, f"promote_with_canary_alert:{ids}")

        return PromotionDecision(True, "eligible")
