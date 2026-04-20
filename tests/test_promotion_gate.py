from dreamfi.promotion.gate import GoldResult, PromotionGate


def test_promotion_blocked_by_regression_even_on_main_improvement() -> None:
    decision = PromotionGate().decide(
        new_score=0.95,
        previous_score=0.88,
        regression_failures=[GoldResult(gold_id="g1", prev="pass", new="fail")],
        canary_failures=[],
    )

    assert not decision.promotable
    assert "regression:g1" in decision.reason


def test_canary_alert_fires_without_blocking_main_score() -> None:
    decision = PromotionGate().decide(
        new_score=0.95,
        previous_score=0.88,
        regression_failures=[],
        canary_failures=[GoldResult(gold_id="c1", prev="pass", new="fail")],
    )

    assert decision.promotable
    assert "canary:c1" in decision.reason
