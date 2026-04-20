"""Eval round API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from dreamfi.api.deps import get_db_session, get_onyx_client
from dreamfi.autoresearch.loop import run_round
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
    body: RunRoundRequest = RunRoundRequest(),
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> dict[str, Any]:
    if skill_id not in load_registry():
        raise HTTPException(status_code=404, detail=f"unknown skill {skill_id}")
    engine = SkillEngine(db=session, onyx=onyx)
    summary = run_round(
        session=session,
        engine=engine,
        skill_id=skill_id,
        n_outputs_per_input=body.n_outputs_per_input,
        prompt_version_id=body.prompt_version_id,
    )
    return {
        "round_id": summary.round_id,
        "skill_id": summary.skill_id,
        "score": summary.score,
        "previous_score": summary.previous_score,
        "improvement": summary.improvement,
        "artifacts_path": summary.artifacts_path,
    }
