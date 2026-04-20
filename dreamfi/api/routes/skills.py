"""Skills API — list + history + promote."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from dreamfi.api.deps import get_db_session
from dreamfi.db.models import EvalRound, PromptVersion, Skill
from dreamfi.promotion.gate import PromotionGate

router = APIRouter()


class PromoteRequest(BaseModel):
    round_id: str


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

    decision = PromotionGate().decide(
        new_score=float(target_round.score), previous_score=previous_score
    )
    if not decision.promotable:
        raise HTTPException(status_code=409, detail=decision.reason)

    now = datetime.now(UTC)
    if active_pv is not None and active_pv.prompt_version_id != target_pv.prompt_version_id:
        active_pv.is_active = False
        active_pv.deactivated_at = now
    target_pv.is_active = True
    target_pv.activated_at = now
    session.commit()

    return {
        "skill_id": skill_id,
        "activated_prompt_version_id": target_pv.prompt_version_id,
        "reason": decision.reason,
        "improvement": decision.improvement,
    }
