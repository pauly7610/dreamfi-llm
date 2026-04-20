"""CLI: run one eval round for a skill.

Example:
    python -m scripts.run_eval_round --skill meeting_summary --n 10
"""
from __future__ import annotations

import sys

import click

from dreamfi.api.deps import get_onyx_client
from dreamfi.autoresearch.loop import run_round
from dreamfi.db.session import get_sessionmaker
from dreamfi.skills.engine import SkillEngine
from dreamfi.skills.registry import load_registry


@click.command()
@click.option("--skill", required=True, help="Skill ID, e.g. meeting_summary")
@click.option("--n", "n_outputs_per_input", default=10, show_default=True, type=int)
def main(skill: str, n_outputs_per_input: int) -> None:
    if skill not in load_registry():
        click.echo(f"Unknown skill: {skill}", err=True)
        sys.exit(2)
    session = get_sessionmaker()()
    onyx = get_onyx_client()
    try:
        engine = SkillEngine(db=session, onyx=onyx)
        summary = run_round(
            session=session,
            engine=engine,
            skill_id=skill,
            n_outputs_per_input=n_outputs_per_input,
        )
    finally:
        session.close()
    click.echo(
        f"round_id={summary.round_id} "
        f"score={summary.score:.4f} "
        f"prev={summary.previous_score} "
        f"improvement={summary.improvement} "
        f"artifacts={summary.artifacts_path}"
    )
    # Non-zero exit if regression vs previous
    if summary.previous_score is not None and summary.score < summary.previous_score:
        sys.exit(1)


if __name__ == "__main__":
    main()
