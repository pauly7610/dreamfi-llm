"""Eval round orchestrator — generates N × M outputs, computes round score."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from dreamfi.db.models import EvalOutput, EvalRound, GoldDriftEvent, PromptVersion, Skill
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


def _label_passed_any(outputs: list[EvalOutput]) -> dict[str, str]:
    """Collapse per-attempt results to a label-level {label: pass|fail} map.

    A label is considered 'pass' if at least one attempt passed in that round.
    """
    by_label: dict[str, str] = {}
    for out in outputs:
        prev = by_label.get(out.test_input_label)
        if prev == "pass":
            continue
        by_label[out.test_input_label] = "pass" if out.pass_fail == "pass" else "fail"
    return by_label


def _prior_round(session: Session, *, skill_id: str, exclude_round_id: str) -> EvalRound | None:
    """Most recent completed round for this skill other than the given one."""
    stmt = (
        select(EvalRound)
        .where(
            EvalRound.skill_id == skill_id,
            EvalRound.round_id != exclude_round_id,
            EvalRound.completed_at.is_not(None),
        )
        .order_by(desc(EvalRound.completed_at))
        .limit(1)
    )
    return session.scalar(stmt)


def _emit_drift_events(
    session: Session, *, round_row: EvalRound, prompt_version_id: str
) -> list[GoldDriftEvent]:
    """Write GoldDriftEvent rows for labels that went pass → fail vs the prior round."""
    prior = _prior_round(session, skill_id=round_row.skill_id, exclude_round_id=round_row.round_id)
    if prior is None:
        return []

    prev_outputs = list(
        session.scalars(select(EvalOutput).where(EvalOutput.round_id == prior.round_id))
    )
    new_outputs = list(
        session.scalars(select(EvalOutput).where(EvalOutput.round_id == round_row.round_id))
    )
    previous = _label_passed_any(prev_outputs)
    new = _label_passed_any(new_outputs)

    events: list[GoldDriftEvent] = []
    for label, new_result in new.items():
        prev_result = previous.get(label)
        if prev_result == "pass" and new_result == "fail":
            ev = GoldDriftEvent(
                workspace_id="",
                skill_id=round_row.skill_id,
                # No FK on gold_id — we use the label as the drift key.
                gold_id=label,
                prompt_version_id=prompt_version_id,
                previous_result="pass",
                new_result="fail",
                round_id=round_row.round_id,
            )
            session.add(ev)
            events.append(ev)
    if events:
        session.flush()
    return events


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

    started = datetime.now(timezone.utc)
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
                    prompt_version_id=prompt_version_id,
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

    round_row.completed_at = datetime.now(timezone.utc)
    session.flush()

    _emit_drift_events(session, round_row=round_row, prompt_version_id=prompt_version_id)

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
