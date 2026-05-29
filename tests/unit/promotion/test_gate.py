"""PromotionGate + PublishGuard tests."""
from __future__ import annotations

from decimal import Decimal

from dreamfi.promotion.gate import PromotionGate, PublishGuard


def test_promotion_first_version_always_allowed() -> None:
    d = PromotionGate(improvement_threshold=0.02).decide(
        new_score=0.8, previous_score=None
    )
    assert d.promotable is True
    assert d.improvement is None


def test_promotion_blocks_regression() -> None:
    d = PromotionGate(improvement_threshold=0.02).decide(
        new_score=Decimal("0.78"), previous_score=Decimal("0.80")
    )
    assert d.promotable is False
    assert "REGRESSION" in d.reason


def test_promotion_allows_meaningful_improvement() -> None:
    d = PromotionGate(improvement_threshold=0.02).decide(
        new_score=0.84, previous_score=0.80
    )
    assert d.promotable is True


def test_promotion_blocks_flat() -> None:
    d = PromotionGate(improvement_threshold=0.02).decide(
        new_score=0.80, previous_score=0.80
    )
    assert d.promotable is False


def test_publish_guard_blocks_failed_hard_gate() -> None:
    g = PublishGuard(confidence_threshold=0.75)
    assert g.check(pass_fail="fail", confidence=0.99).allowed is False


def test_publish_guard_blocks_low_confidence() -> None:
    g = PublishGuard(confidence_threshold=0.75)
    d = g.check(pass_fail="pass", confidence=0.4)
    assert d.allowed is False
    assert "Low confidence" in d.reason


def test_publish_guard_allows_good() -> None:
    g = PublishGuard(confidence_threshold=0.75, export_readiness_threshold=0.80)
    assert (
        g.check(pass_fail="pass", confidence=0.80, export_readiness=0.85).allowed
        is True
    )


def test_publish_guard_none_confidence_blocks() -> None:
    g = PublishGuard(confidence_threshold=0.75)
    assert g.check(pass_fail="pass", confidence=None).allowed is False
