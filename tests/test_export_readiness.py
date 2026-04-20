from dreamfi.trust.artifact import ExportReadinessInput, compute_export_readiness


def test_export_readiness_zero_when_hard_gate_fails() -> None:
    result = compute_export_readiness(
        ExportReadinessInput(
            hard_gate_pass=False,
            confidence=1.0,
            gold_regression_pass_rate=1.0,
            claim_lineage_rate=1.0,
            metric_freshness=1.0,
            planning_hygiene_score=1.0,
        )
    )

    assert result.value == 0.0


def test_export_readiness_deterministic_weighted_formula() -> None:
    result = compute_export_readiness(
        ExportReadinessInput(
            hard_gate_pass=True,
            confidence=0.8,
            gold_regression_pass_rate=0.9,
            claim_lineage_rate=0.7,
            metric_freshness=1.0,
            planning_hygiene_score=0.6,
        )
    )

    assert result.value == 0.845
    assert result.breakdown["hard_gate"] == 1.0
