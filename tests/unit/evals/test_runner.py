"""Eval runner wrapper tests — runners are locked so we test the boundary."""
from __future__ import annotations

from pathlib import Path

import pytest

from dreamfi.evals.runner import run_eval
from dreamfi.skills.registry import load_registry


def test_meeting_summary_runner_on_known_pass() -> None:
    good = (
        "## Decisions\nDecision: Launch beta to 500 users on April 1.\n\n"
        "## Action Items\n- Sarah will send the pricing page to design by Friday March 21.\n\n"
        "## Open Questions\nOpen: Do we need legal review before EU launch?"
    )
    res = run_eval("meeting_summary", good, test_input_label="input_1")
    assert res.pass_fail == "pass"
    assert res.failed_criteria == []
    assert res.eval_score == pytest.approx(1.0)


def test_meeting_summary_runner_on_known_fail_wordlimit() -> None:
    long = "word " * 400
    res = run_eval("meeting_summary", long, "input_1")
    assert res.pass_fail == "fail"
    assert "word_limit" in res.failed_criteria


def test_runner_isolation_no_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    run_eval("meeting_summary", "x", "input_1")
    assert list(tmp_path.iterdir()) == []


def test_all_nine_runners_callable_with_empty_output() -> None:
    for skill in load_registry():
        res = run_eval(skill, "", "input_1")
        assert res.pass_fail == "fail"  # empty output must fail something


def test_unknown_skill_raises() -> None:
    with pytest.raises(KeyError):
        run_eval("does_not_exist", "hi", "input_1")
