from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExportReadinessInput:
    hard_gate_pass: bool
    confidence: float
    gold_regression_pass_rate: float
    claim_lineage_rate: float
    metric_freshness: float
    planning_hygiene_score: float | None = None


@dataclass(frozen=True)
class ExportReadinessScore:
    value: float
    breakdown: dict[str, float]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_export_readiness(inputs: ExportReadinessInput) -> ExportReadinessScore:
    if not inputs.hard_gate_pass:
        return ExportReadinessScore(
            value=0.0,
            breakdown={
                "hard_gate": 0.0,
                "confidence": _clamp(inputs.confidence),
                "gold_regression": _clamp(inputs.gold_regression_pass_rate),
                "claim_lineage": _clamp(inputs.claim_lineage_rate),
                "metric_freshness": _clamp(inputs.metric_freshness),
                "planning_hygiene": _clamp(inputs.planning_hygiene_score or 1.0),
            },
        )

    hygiene = _clamp(inputs.planning_hygiene_score if inputs.planning_hygiene_score is not None else 1.0)
    confidence = _clamp(inputs.confidence)
    gold = _clamp(inputs.gold_regression_pass_rate)
    lineage = _clamp(inputs.claim_lineage_rate)
    freshness = _clamp(inputs.metric_freshness)

    value = (
        0.20 * 1.0
        + 0.15 * confidence
        + 0.25 * gold
        + 0.20 * lineage
        + 0.10 * freshness
        + 0.10 * hygiene
    )

    return ExportReadinessScore(
        value=round(_clamp(value), 3),
        breakdown={
            "hard_gate": 1.0,
            "confidence": confidence,
            "gold_regression": gold,
            "claim_lineage": lineage,
            "metric_freshness": freshness,
            "planning_hygiene": hygiene,
        },
    )
