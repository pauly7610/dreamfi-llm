"""PublishGuard enforces the export_readiness threshold (X1, layer 2)."""
from __future__ import annotations

from dreamfi.promotion.gate import PublishGuard


def test_passes_when_all_signals_healthy() -> None:
    decision = PublishGuard(
        confidence_threshold=0.70, export_readiness_threshold=0.80
    ).check(pass_fail="pass", confidence=0.9, export_readiness=0.85)

    assert decision.allowed
    assert decision.reason == "eligible"


def test_blocks_when_readiness_below_threshold() -> None:
    decision = PublishGuard(
        confidence_threshold=0.70, export_readiness_threshold=0.80
    ).check(pass_fail="pass", confidence=0.9, export_readiness=0.50)

    assert not decision.allowed
    assert decision.reason.startswith("low_export_readiness:")
    assert "0.500" in decision.reason


def test_blocks_when_readiness_missing() -> None:
    decision = PublishGuard(
        confidence_threshold=0.70, export_readiness_threshold=0.80
    ).check(pass_fail="pass", confidence=0.9, export_readiness=None)

    assert not decision.allowed
    assert decision.reason == "missing_export_readiness"


def test_hard_gate_takes_precedence_over_readiness() -> None:
    decision = PublishGuard(export_readiness_threshold=0.80).check(
        pass_fail="fail", confidence=0.99, export_readiness=0.99
    )

    assert not decision.allowed
    assert decision.reason == "Hard gate failed"


def test_confidence_check_runs_before_readiness() -> None:
    decision = PublishGuard(
        confidence_threshold=0.90, export_readiness_threshold=0.80
    ).check(pass_fail="pass", confidence=0.50, export_readiness=0.99)

    assert not decision.allowed
    assert decision.reason.startswith("Low confidence:")
