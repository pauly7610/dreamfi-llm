"""Eval round API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from dreamfi.api.deps import get_db_session, get_onyx_client
from dreamfi.audit import add_audit_event
from dreamfi.autoresearch.loop import run_round
from dreamfi.config import get_settings
from dreamfi.onyx.client import OnyxClient
from dreamfi.skills.engine import SkillEngine
from dreamfi.skills.registry import load_registry

router = APIRouter()


class RunRoundRequest(BaseModel):
    prompt_version_id: str | None = None
    n_outputs_per_input: int = 3


@router.post("/{skill_id}/eval-round")
def run_eval_round(
    skill_id: str,
    request: Request,
    body: RunRoundRequest = RunRoundRequest(),
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> dict[str, Any]:
    if skill_id not in load_registry():
        raise HTTPException(status_code=404, detail=f"unknown skill {skill_id}")
    settings = get_settings()
    if not (
        settings.dreamfi_min_outputs_per_eval_input
        <= body.n_outputs_per_input
        <= settings.dreamfi_max_outputs_per_eval_input
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "n_outputs_per_input must be between "
                f"{settings.dreamfi_min_outputs_per_eval_input} and "
                f"{settings.dreamfi_max_outputs_per_eval_input}"
            ),
        )
    engine = SkillEngine(db=session, onyx=onyx)
    summary = run_round(
        session=session,
        engine=engine,
        skill_id=skill_id,
        n_outputs_per_input=body.n_outputs_per_input,
        prompt_version_id=body.prompt_version_id,
    )
    add_audit_event(
        session,
        category="generation",
        action="eval_round_run",
        outcome="success",
        request=request,
        target_type="eval_round",
        target_id=summary.round_id,
        metadata={
            "skill_id": skill_id,
            "prompt_version_id": body.prompt_version_id,
            "n_outputs_per_input": body.n_outputs_per_input,
            "score": summary.score,
            "previous_score": summary.previous_score,
            "improvement": summary.improvement,
        },
    )
    session.commit()
    return {
        "round_id": summary.round_id,
        "skill_id": summary.skill_id,
        "score": summary.score,
        "previous_score": summary.previous_score,
        "improvement": summary.improvement,
        "artifacts_path": summary.artifacts_path,
    }
