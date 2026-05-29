"""Skills API — list + history + promote."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from dreamfi.api.deps import get_db_session
from dreamfi.audit import add_audit_event
from dreamfi.db.models import EvalRound, GoldDriftEvent, GoldExample, PromptVersion, Skill
from dreamfi.promotion.gate import GoldResult, PromotionGate

router = APIRouter()


class PromoteRequest(BaseModel):
    round_id: str


class PromotionPreviewRequest(BaseModel):
    round_id: str


def _gold_failures_for_round(
    session: Session,
    *,
    skill_id: str,
    round_id: str,
) -> tuple[list[GoldResult], list[GoldResult]]:
    drift_rows = list(
        session.scalars(
            select(GoldDriftEvent).where(GoldDriftEvent.round_id == round_id)
        )
    )
    regression_failures = [
        GoldResult(
            gold_id=row.gold_id,
            prev="pass" if row.previous_result == "pass" else "fail",
            new="pass" if row.new_result == "pass" else "fail",
        )
        for row in drift_rows
    ]
    seen_regression_ids = {row.gold_id for row in drift_rows}
    rows = session.scalars(
        select(GoldExample).where(
            GoldExample.skill_id == skill_id,
            GoldExample.last_run_round_id == round_id,
            GoldExample.last_result == "fail",
            GoldExample.role.in_(["regression", "canary"]),
        )
    ).all()
    canary_failures: list[GoldResult] = []
    for row in rows:
        result = GoldResult(gold_id=row.gold_id, prev="pass", new="fail")
        if row.role == "canary":
            canary_failures.append(result)
        elif row.gold_id not in seen_regression_ids:
            regression_failures.append(result)
    return regression_failures, canary_failures


@router.get("/{skill_id}/history")
def history(skill_id: str, session: Session = Depends(get_db_session)) -> dict[str, Any]:
    skill = session.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"unknown skill {skill_id}")
    rounds = session.scalars(
        select(EvalRound)
        .where(EvalRound.skill_id == skill_id)
        .order_by(desc(EvalRound.completed_at))
        .limit(20)
    ).all()
    return {
        "skill_id": skill_id,
        "rounds": [
            {
                "round_id": r.round_id,
                "prompt_version_id": r.prompt_version_id,
                "score": float(r.score),
                "previous_score": float(r.previous_score) if r.previous_score is not None else None,
                "improvement": float(r.improvement) if r.improvement is not None else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in rounds
        ],
    }


@router.post("/{skill_id}/promote")
def promote(
    skill_id: str,
    body: PromoteRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    target_round = session.get(EvalRound, body.round_id)
    if target_round is None or target_round.skill_id != skill_id:
        raise HTTPException(status_code=404, detail="round not found")
    target_pv = session.get(PromptVersion, target_round.prompt_version_id)
    if target_pv is None:
        raise HTTPException(status_code=404, detail="prompt version missing")

    active_pv = session.scalar(
        select(PromptVersion).where(
            PromptVersion.skill_id == skill_id, PromptVersion.is_active.is_(True)
        )
    )
    previous_score = None
    if active_pv is not None and active_pv.prompt_version_id != target_pv.prompt_version_id:
        previous_round = session.scalar(
            select(EvalRound)
            .where(EvalRound.prompt_version_id == active_pv.prompt_version_id)
            .order_by(desc(EvalRound.completed_at))
            .limit(1)
        )
        if previous_round is not None:
            previous_score = float(previous_round.score)

    regression_failures, canary_failures = _gold_failures_for_round(
        session,
        skill_id=skill_id,
        round_id=target_round.round_id,
    )
    decision = PromotionGate().decide(
        new_score=float(target_round.score),
        previous_score=previous_score,
        regression_failures=regression_failures,
        canary_failures=canary_failures,
    )
    if not decision.promotable:
        add_audit_event(
            session,
            category="governance",
            action="prompt_promotion",
            outcome="blocked",
            request=request,
            severity="warning",
            target_type="prompt_version",
            target_id=target_pv.prompt_version_id,
            reason=decision.reason,
            metadata={
                "skill_id": skill_id,
                "round_id": target_round.round_id,
                "new_score": float(target_round.score),
                "previous_score": previous_score,
                "regression_failure_count": len(regression_failures),
                "canary_failure_count": len(canary_failures),
            },
        )
        session.commit()
        raise HTTPException(status_code=409, detail=decision.reason)

    now = datetime.now(timezone.utc)
    if active_pv is not None and active_pv.prompt_version_id != target_pv.prompt_version_id:
        active_pv.is_active = False
        active_pv.deactivated_at = now
        session.flush()
    target_pv.is_active = True
    target_pv.activated_at = now
    add_audit_event(
        session,
        category="governance",
        action="prompt_promotion",
        outcome="success",
        request=request,
        target_type="prompt_version",
        target_id=target_pv.prompt_version_id,
        reason=decision.reason,
        metadata={
            "skill_id": skill_id,
            "round_id": target_round.round_id,
            "previous_prompt_version_id": (
                active_pv.prompt_version_id
                if active_pv is not None and active_pv.prompt_version_id != target_pv.prompt_version_id
                else None
            ),
            "new_score": float(target_round.score),
            "previous_score": previous_score,
            "improvement": decision.improvement,
            "regression_failure_count": len(regression_failures),
            "canary_failure_count": len(canary_failures),
        },
    )
    session.commit()

    return {
        "skill_id": skill_id,
        "activated_prompt_version_id": target_pv.prompt_version_id,
        "reason": decision.reason,
        "improvement": decision.improvement,
    }


@router.post("/{skill_id}/promotion-preview")
def promotion_preview(
    skill_id: str,
    body: PromotionPreviewRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    target_round = session.get(EvalRound, body.round_id)
    if target_round is None or target_round.skill_id != skill_id:
        raise HTTPException(status_code=404, detail="round not found")

    active_pv = session.scalar(
        select(PromptVersion).where(
            PromptVersion.skill_id == skill_id,
            PromptVersion.is_active.is_(True),
        )
    )
    previous_score = None
    if active_pv is not None and active_pv.prompt_version_id != target_round.prompt_version_id:
        previous_round = session.scalar(
            select(EvalRound)
            .where(EvalRound.prompt_version_id == active_pv.prompt_version_id)
            .order_by(desc(EvalRound.completed_at))
            .limit(1)
        )
        if previous_round is not None:
            previous_score = float(previous_round.score)

    regression_failures, canary_failures = _gold_failures_for_round(
        session,
        skill_id=skill_id,
        round_id=target_round.round_id,
    )
    decision = PromotionGate().decide(
        new_score=float(target_round.score),
        previous_score=previous_score,
        regression_failures=regression_failures,
        canary_failures=canary_failures,
    )
    add_audit_event(
        session,
        category="governance",
        action="promotion_preview",
        outcome="success" if decision.promotable else "blocked",
        request=request,
        severity="info" if decision.promotable else "warning",
        target_type="eval_round",
        target_id=target_round.round_id,
        reason=decision.reason,
        metadata={
            "skill_id": skill_id,
            "prompt_version_id": target_round.prompt_version_id,
            "new_score": float(target_round.score),
            "previous_score": previous_score,
            "regression_failure_count": len(regression_failures),
            "canary_failure_count": len(canary_failures),
        },
    )
    session.commit()
    return {
        "skill_id": skill_id,
        "round_id": target_round.round_id,
        "new_score": float(target_round.score),
        "previous_score": previous_score,
        "promotable": decision.promotable,
        "reason": decision.reason,
        "improvement": decision.improvement,
    }
