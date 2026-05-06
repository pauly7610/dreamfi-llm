"""Publish API — enforces publish guard."""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from dreamfi.api.deps import get_db_session
from dreamfi.audit import add_audit_event
from dreamfi.db.models import EvalOutput, PublishLog
from dreamfi.promotion.gate import PublishGuard

router = APIRouter()

_RETURN_ONLY_DESTINATION = "return-only"


class PublishRequest(BaseModel):
    output_id: str
    destination: Literal["confluence", "jira", "return-only"] = "return-only"
    destination_ref: str | None = None


@router.post("/{skill_id}/publish")
def publish(
    skill_id: str,
    body: PublishRequest,
    request: Request,
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

    publish_decision = "published" if decision.allowed else "blocked"
    reason = decision.reason
    blocked_status_code = status.HTTP_409_CONFLICT
    if decision.allowed and body.destination != _RETURN_ONLY_DESTINATION:
        publish_decision = "blocked"
        reason = (
            f"External publishing to {body.destination} is not configured; "
            "no external write was attempted."
        )
        blocked_status_code = status.HTTP_501_NOT_IMPLEMENTED

    log = PublishLog(
        skill_id=skill_id,
        prompt_version_id=round_row.prompt_version_id,
        output_id=output.output_id,
        destination=body.destination,
        destination_ref=body.destination_ref,
        decision=publish_decision,
        reason=reason,
    )
    session.add(log)
    add_audit_event(
        session,
        category="publish",
        action="publish_attempt",
        outcome="success" if publish_decision == "published" else "blocked",
        request=request,
        severity="info" if publish_decision == "published" else "warning",
        target_type="eval_output",
        target_id=output.output_id,
        reason=reason,
        metadata={
            "skill_id": skill_id,
            "prompt_version_id": round_row.prompt_version_id,
            "publish_decision": publish_decision,
            "destination": body.destination,
            "destination_ref_present": body.destination_ref is not None,
            "pass_fail": output.pass_fail,
            "confidence": float(output.confidence) if output.confidence is not None else None,
        },
    )
    session.commit()

    if publish_decision != "published":
        raise HTTPException(status_code=blocked_status_code, detail=reason)

    return {
        "publish_id": log.publish_id,
        "decision": "published",
        "destination": body.destination,
        "destination_ref": body.destination_ref,
    }
