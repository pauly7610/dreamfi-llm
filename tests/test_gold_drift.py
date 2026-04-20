from dreamfi.db.models import GoldExample
from dreamfi.trust.gold import detect_drift_events


def test_detects_pass_to_fail_for_regression() -> None:
    events = detect_drift_events(
        examples=[
            GoldExample(gold_id="g1", workspace_id="w1", skill_id="s1", role="regression"),
            GoldExample(gold_id="g2", workspace_id="w1", skill_id="s1", role="exemplar"),
        ],
        previous_results={"g1": "pass", "g2": "pass"},
        new_results={"g1": "fail", "g2": "fail"},
        prompt_version_id="p1",
        round_id="r1",
    )

    assert len(events) == 1
    assert events[0].gold_id == "g1"


def test_ignores_fail_to_fail() -> None:
    events = detect_drift_events(
        examples=[GoldExample(gold_id="g1", workspace_id="w1", skill_id="s1", role="regression")],
        previous_results={"g1": "fail"},
        new_results={"g1": "fail"},
        prompt_version_id="p1",
        round_id="r1",
    )

    assert events == []
