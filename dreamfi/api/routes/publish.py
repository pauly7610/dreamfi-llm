"""Publish API — enforces publish guard."""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from dreamfi.api.deps import get_db_session
from dreamfi.db.models import EvalOutput, PublishLog
from dreamfi.promotion.gate import PublishGuard

router = APIRouter()


class PublishRequest(BaseModel):
    output_id: str
    destination: Literal["confluence", "jira", "return-only"] = "return-only"
    destination_ref: str | None = None


@router.post("/{skill_id}/publish")
def publish(
    skill_id: str,
    body: PublishRequest,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    output = session.get(EvalOutput, body.output_id)
    if output is None:
        raise HTTPException(status_code=404, detail="output not found")

    # Look up the round to find the prompt version
    from dreamfi.db.models import EvalRound

    round_row = session.get(EvalRound, output.round_id)
    if round_row is None or round_row.skill_id != skill_id:
        raise HTTPException(status_code=400, detail="output does not belong to this skill")

    decision = PublishGuard().check(
        pass_fail=output.pass_fail, confidence=output.confidence
    )

    log = PublishLog(
        skill_id=skill_id,
        prompt_version_id=round_row.prompt_version_id,
        output_id=output.output_id,
        destination=body.destination,
        destination_ref=body.destination_ref,
        decision="published" if decision.allowed else "blocked",
        reason=decision.reason,
    )
    session.add(log)
    session.commit()

    if not decision.allowed:
        raise HTTPException(status_code=409, detail=decision.reason)

    return {
        "publish_id": log.publish_id,
        "decision": "published",
        "destination": body.destination,
        "destination_ref": body.destination_ref,
    }
