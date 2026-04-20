"""Eval round orchestrator — generates N × M outputs, computes round score."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from dreamfi.db.models import EvalRound, PromptVersion, Skill
from dreamfi.evals.loader import parse_eval_template
from dreamfi.skills.engine import SkillEngine
from dreamfi.skills.registry import load_registry

ARTIFACTS_ROOT = Path("evals/results")
_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class RoundSummary:
    round_id: str
    skill_id: str
    score: float
    previous_score: float | None
    improvement: float | None
    artifacts_path: str


def _prev_active_score(session: Session, skill_id: str) -> float | None:
    stmt = (
        select(EvalRound)
        .join(
            PromptVersion,
            PromptVersion.prompt_version_id == EvalRound.prompt_version_id,
        )
        .where(
            EvalRound.skill_id == skill_id,
            PromptVersion.is_active.is_(True),
        )
        .order_by(EvalRound.completed_at.desc())
        .limit(1)
    )
    prev = session.scalar(stmt)
    return float(prev.score) if prev is not None else None


def _artifacts_dir(skill_id: str, round_id: str) -> Path:
    reg = load_registry()
    spec = reg[skill_id]
    template_dir = Path(spec.eval_template_path).stem  # e.g. meeting-summary
    base = Path.cwd() / ARTIFACTS_ROOT / template_dir / "rounds" / round_id
    base.mkdir(parents=True, exist_ok=True)
    return base


def run_round(
    *,
    session: Session,
    engine: SkillEngine,
    skill_id: str,
    n_outputs_per_input: int = 3,
    prompt_version_id: str | None = None,
    repo_root: Path | None = None,
) -> RoundSummary:
    skill = session.get(Skill, skill_id)
    if skill is None:
        raise KeyError(f"skill not found: {skill_id}")

    if prompt_version_id is None:
        active = session.scalar(
            select(PromptVersion).where(
                PromptVersion.skill_id == skill_id, PromptVersion.is_active.is_(True)
            )
        )
        if active is None:
            raise RuntimeError(f"No active prompt version for skill {skill_id}")
        prompt_version_id = active.prompt_version_id

    spec = parse_eval_template((repo_root or _DEFAULT_REPO_ROOT) / skill.eval_template_path)
    test_inputs = spec.test_inputs
    if not test_inputs:
        raise RuntimeError(f"No test inputs for skill {skill_id}")

    started = datetime.now(UTC)
    round_row = EvalRound(
        skill_id=skill_id,
        prompt_version_id=prompt_version_id,
        n_inputs=len(test_inputs),
        n_outputs_per_input=n_outputs_per_input,
        total_outputs=0,
        total_passes=0,
        score=Decimal("0.0"),
        started_at=started,
        artifacts_path="",
    )
    session.add(round_row)
    session.flush()

    artifacts = _artifacts_dir(skill_id, round_row.round_id)
    round_row.artifacts_path = str(artifacts)

    total = 0
    passes = 0
    results_log = artifacts / "results.log"
    outputs_log = artifacts / "outputs.jsonl"
    with results_log.open("w", encoding="utf-8") as rlog, outputs_log.open(
        "w", encoding="utf-8"
    ) as olog:
        for ti in test_inputs:
            for attempt in range(1, n_outputs_per_input + 1):
                gen = engine.generate(
                    skill=skill_id,
                    input_context={"text": ti.text},
                    test_input_label=ti.label,
                    round_id=round_row.round_id,
                    attempt=attempt,
                )
                total += 1
                if gen.eval.pass_fail == "pass":
                    passes += 1
                rlog.write(
                    json.dumps(
                        {
                            "label": ti.label,
                            "attempt": attempt,
                            "pass_fail": gen.eval.pass_fail,
                            "failed_criteria": gen.eval.failed_criteria,
                            "confidence": gen.confidence.confidence,
                        }
                    )
                    + "\n"
                )
                olog.write(
                    json.dumps(
                        {
                            "label": ti.label,
                            "attempt": attempt,
                            "text": gen.generated_text,
                            "citations": gen.onyx_citations,
                        }
                    )
                    + "\n"
                )

    score = passes / total if total else 0.0
    round_row.total_outputs = total
    round_row.total_passes = passes
    round_row.score = Decimal(f"{score:.4f}")

    previous_score = _prev_active_score(session, skill_id)
    if previous_score is not None:
        round_row.previous_score = Decimal(f"{previous_score:.4f}")
        round_row.improvement = Decimal(f"{score - previous_score:.4f}")

    round_row.completed_at = datetime.now(UTC)
    session.flush()

    # Append to changelog
    skill_dir = artifacts.parent.parent  # evals/results/<skill>/
    changelog = skill_dir / "changelog.md"
    changelog.parent.mkdir(parents=True, exist_ok=True)
    with changelog.open("a", encoding="utf-8") as fh:
        fh.write(
            f"\n- round_id={round_row.round_id} "
            f"score={score:.4f} "
            f"previous={previous_score if previous_score is not None else 'n/a'} "
            f"at={round_row.completed_at.isoformat()}\n"
        )

    # Per-round analysis + learnings
    (artifacts / "analysis.md").write_text(
        f"# Round {round_row.round_id}\n\n"
        f"- skill: {skill_id}\n"
        f"- total outputs: {total}\n"
        f"- passes: {passes}\n"
        f"- score: {score:.4f}\n"
        f"- previous_score: {previous_score if previous_score is not None else 'n/a'}\n",
        encoding="utf-8",
    )
    (artifacts / "learnings.md").write_text(
        "# Learnings\n\nFill in human or LLM-authored reflections here.\n",
        encoding="utf-8",
    )

    session.commit()

    return RoundSummary(
        round_id=round_row.round_id,
        skill_id=skill_id,
        score=score,
        previous_score=previous_score,
        improvement=None if previous_score is None else score - previous_score,
        artifacts_path=str(artifacts),
    )
