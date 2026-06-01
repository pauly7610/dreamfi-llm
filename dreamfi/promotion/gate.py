from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from dreamfi.config import get_settings

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
    improvement: float | None = None


@dataclass(frozen=True)
class PublishDecision:
    allowed: bool
    reason: str


class PromotionGate:
    """Backward-compatible promotion gate.

    Supports the original threshold-based promotion logic and newer
    regression/canary trust signals.
    """

    def __init__(self, improvement_threshold: float | None = None) -> None:
        self.improvement_threshold = (
            improvement_threshold
            if improvement_threshold is not None
            else get_settings().dreamfi_improvement_threshold
        )

    def _to_float(self, value: float | Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)

    def decide(
        self,
        *,
        new_score: float | Decimal,
        previous_score: float | Decimal | None,
        regression_failures: list[GoldResult] | None = None,
        canary_failures: list[GoldResult] | None = None,
    ) -> PromotionDecision:
        regressions = regression_failures or []
        canaries = canary_failures or []
        new_score_f = float(new_score)
        previous_score_f = self._to_float(previous_score)

        if regressions:
            ids = ",".join(sorted(f"regression:{r.gold_id}" for r in regressions))
            return PromotionDecision(False, f"blocked_by_regression:{ids}")

        if previous_score_f is None:
            if canaries:
                ids = ",".join(sorted(f"canary:{r.gold_id}" for r in canaries))
                return PromotionDecision(True, f"promote_with_canary_alert:{ids}", None)
            return PromotionDecision(True, "eligible", None)

        improvement = new_score_f - previous_score_f
        if new_score_f < previous_score_f:
            return PromotionDecision(
                False,
                f"REGRESSION: {new_score_f:.4f} < {previous_score_f:.4f}",
                improvement,
            )

        if improvement < self.improvement_threshold:
            return PromotionDecision(
                False,
                (
                    f"Improvement {improvement:.4f} below threshold "
                    f"{self.improvement_threshold:.4f}"
                ),
                improvement,
            )

        if canaries:
            ids = ",".join(sorted(f"canary:{r.gold_id}" for r in canaries))
            return PromotionDecision(True, f"promote_with_canary_alert:{ids}", improvement)

        return PromotionDecision(True, "eligible", improvement)


class PublishGuard:
    def __init__(
        self,
        confidence_threshold: float | None = None,
        export_readiness_threshold: float | None = None,
    ) -> None:
        settings = get_settings()
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.dreamfi_confidence_threshold
        )
        self.export_readiness_threshold = (
            export_readiness_threshold
            if export_readiness_threshold is not None
            else settings.dreamfi_export_readiness_threshold
        )

    def check(
        self,
        *,
        pass_fail: str,
        confidence: float | Decimal | None,
        export_readiness: float | Decimal | None = None,
    ) -> PublishDecision:
        if pass_fail != "pass":
            return PublishDecision(False, "Hard gate failed")

        if confidence is None:
            return PublishDecision(False, "Low confidence: missing confidence score")

        confidence_f = float(confidence)
        if confidence_f < self.confidence_threshold:
            return PublishDecision(
                False,
                (
                    f"Low confidence: {confidence_f:.3f} < "
                    f"{self.confidence_threshold:.3f}"
                ),
            )

        if export_readiness is None:
            return PublishDecision(False, "missing_export_readiness")

        readiness_f = float(export_readiness)
        if readiness_f < self.export_readiness_threshold:
            return PublishDecision(
                False,
                f"low_export_readiness:{readiness_f:.3f}",
            )

        return PublishDecision(True, "eligible")
