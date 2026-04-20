"""CLI sanity — unknown skills exit non-zero."""
from __future__ import annotations

from click.testing import CliRunner

from scripts.run_eval_round import main as run_eval_round


def test_unknown_skill_exits_non_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(run_eval_round, ["--skill", "nope"])
    assert result.exit_code == 2
    assert "Unknown skill" in result.output
