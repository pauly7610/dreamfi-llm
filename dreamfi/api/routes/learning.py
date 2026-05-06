"""Learning loop API: feedback, clusters, proposals, gold growth, replay, outcomes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from dreamfi.api.deps import get_db_session, get_onyx_client
from dreamfi.audit import add_audit_event, hash_text
from dreamfi.config import get_settings
from dreamfi.db.models import (
    ArtifactFeedback,
    EvalOutput,
    GoldExample,
    LearningProposal,
    ProductionOutcome,
    ReplayRun,
    ReplaySchedule,
)
from dreamfi.learning.loop import (
    approve_learning_proposal,
    build_failure_clusters,
    create_gold_from_feedback,
    generate_learning_proposals,
    production_summary,
    reject_learning_proposal,
    run_replay_schedule,
)
from dreamfi.onyx.client import OnyxClient

router = APIRouter(prefix="/api/learning")

FeedbackOutcome = Literal["approved", "edited", "rejected"]
GoldGrowthRole = Literal["exemplar", "regression", "counter_example", "canary"]
ProposalStatus = Literal["draft", "approved", "rejected", "applied"]
ProductionOutcomeValue = Literal["published", "revised", "ignored", "reverted", "used_in_decision"]
ReplayType = Literal["gold", "workflow"]


class FeedbackRequest(BaseModel):
    output_id: str
    reviewer_id: str = Field(min_length=1)
    outcome: FeedbackOutcome
    reason: str | None = None
    notes: str | None = None
    final_text: str | None = None
    final_text_hash: str | None = None
    promote_to_gold_role: GoldGrowthRole | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GoldGrowthRequest(BaseModel):
    role: GoldGrowthRole
    final_text: str | None = None


class ProposalReviewRequest(BaseModel):
    reviewer_id: str = Field(min_length=1)
    review_notes: str | None = None


class GenerateProposalsRequest(BaseModel):
    min_count: int | None = Field(default=None, ge=1)


class ProductionOutcomeRequest(BaseModel):
    output_id: str
    outcome: ProductionOutcomeValue
    actor_id: str = Field(min_length=1)
    notes: str | None = None
    final_text: str | None = None
    final_text_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayScheduleRequest(BaseModel):
    replay_type: ReplayType
    skill_id: str | None = None
    prompt_version_id: str | None = None
    cadence_days: int | None = Field(default=None, ge=1)
    next_run_at: datetime | None = None
    created_by: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


def _feedback_hash(body: FeedbackRequest, output: EvalOutput) -> str:
    if body.final_text_hash:
        return body.final_text_hash
    if body.final_text is not None:
        return hash_text(body.final_text) or ""
    return hash_text(output.generated_text) or ""


def _outcome_hash(body: ProductionOutcomeRequest) -> str | None:
    if body.final_text_hash:
        return body.final_text_hash
    if body.final_text is not None:
        return hash_text(body.final_text)
    return None


def _serialize_feedback(row: ArtifactFeedback) -> dict[str, Any]:
    return {
        "feedback_id": row.feedback_id,
        "output_id": row.output_id,
        "reviewer_id": row.reviewer_id,
        "outcome": row.outcome,
        "reason": row.reason,
        "notes": row.notes,
        "final_text_hash": row.final_text_hash,
        "metadata": row.metadata_json,
        "gold_id": row.gold_id,
        "created_at": row.created_at.isoformat(),
    }


def _serialize_gold(row: GoldExample) -> dict[str, Any]:
    return {
        "gold_id": row.gold_id,
        "skill_id": row.skill_id,
        "scenario_type": row.scenario_type,
        "role": row.role,
        "prompt_version_id": row.prompt_version_id,
        "captured_at": row.captured_at.isoformat(),
    }


def _serialize_proposal(row: LearningProposal) -> dict[str, Any]:
    return {
        "proposal_id": row.proposal_id,
        "skill_id": row.skill_id,
        "prompt_version_id": row.prompt_version_id,
        "cluster_key": row.cluster_key,
        "title": row.title,
        "rationale": row.rationale,
        "proposed_prompt_patch": row.proposed_prompt_patch,
        "status": row.status,
        "source_failure_count": row.source_failure_count,
        "evidence": row.evidence_json,
        "reviewer_id": row.reviewer_id,
        "review_notes": row.review_notes,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "created_prompt_version_id": row.created_prompt_version_id,
        "created_at": row.created_at.isoformat(),
    }


def _serialize_outcome(row: ProductionOutcome) -> dict[str, Any]:
    return {
        "outcome_id": row.outcome_id,
        "output_id": row.output_id,
        "outcome": row.outcome,
        "actor_id": row.actor_id,
        "notes": row.notes,
        "final_text_hash": row.final_text_hash,
        "metadata": row.metadata_json,
        "created_at": row.created_at.isoformat(),
    }


def _serialize_schedule(row: ReplaySchedule) -> dict[str, Any]:
    return {
        "schedule_id": row.schedule_id,
        "replay_type": row.replay_type,
        "skill_id": row.skill_id,
        "prompt_version_id": row.prompt_version_id,
        "cadence_days": row.cadence_days,
        "next_run_at": row.next_run_at.isoformat(),
        "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
        "is_active": row.is_active,
        "created_by": row.created_by,
        "payload": row.payload_json,
        "created_at": row.created_at.isoformat(),
    }


def _serialize_replay_run(row: ReplayRun) -> dict[str, Any]:
    return {
        "replay_run_id": row.replay_run_id,
        "schedule_id": row.schedule_id,
        "status": row.status,
        "skill_id": row.skill_id,
        "prompt_version_id": row.prompt_version_id,
        "round_id": row.round_id,
        "output_id": row.output_id,
        "summary": row.summary_json,
        "reason": row.reason,
        "started_at": row.started_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
def capture_feedback(
    body: FeedbackRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    output = session.get(EvalOutput, body.output_id)
    if output is None:
        raise HTTPException(status_code=404, detail="output not found")

    feedback = ArtifactFeedback(
        output_id=output.output_id,
        reviewer_id=body.reviewer_id,
        outcome=body.outcome,
        reason=body.reason,
        notes=body.notes,
        final_text_hash=_feedback_hash(body, output),
        metadata_json=body.metadata,
    )
    session.add(feedback)
    session.flush()

    gold = None
    if body.promote_to_gold_role is not None:
        gold = create_gold_from_feedback(
            session,
            feedback=feedback,
            role=body.promote_to_gold_role,
            final_text=body.final_text,
        )

    add_audit_event(
        session,
        category="learning",
        action="feedback_capture",
        outcome="success",
        request=request,
        target_type="eval_output",
        target_id=output.output_id,
        metadata={
            "feedback_id": feedback.feedback_id,
            "reviewer_id": body.reviewer_id,
            "review_outcome": body.outcome,
            "reason": body.reason,
            "notes_present": body.notes is not None,
            "final_text_sha256": feedback.final_text_hash,
            "gold_id": gold.gold_id if gold is not None else None,
            "gold_role": gold.role if gold is not None else None,
        },
    )
    session.commit()
    return {
        "feedback": _serialize_feedback(feedback),
        "gold": _serialize_gold(gold) if gold is not None else None,
    }


@router.get("/feedback")
def list_feedback(
    output_id: str | None = None,
    session: Session = Depends(get_db_session),
) -> dict[str, list[dict[str, Any]]]:
    stmt = select(ArtifactFeedback).order_by(desc(ArtifactFeedback.created_at)).limit(100)
    if output_id is not None:
        stmt = (
            select(ArtifactFeedback)
            .where(ArtifactFeedback.output_id == output_id)
            .order_by(desc(ArtifactFeedback.created_at))
        )
    rows = session.scalars(stmt).all()
    return {"feedback": [_serialize_feedback(row) for row in rows]}


@router.post("/feedback/{feedback_id}/gold", status_code=status.HTTP_201_CREATED)
def promote_feedback_to_gold(
    feedback_id: str,
    body: GoldGrowthRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    feedback = session.get(ArtifactFeedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="feedback not found")
    try:
        gold = create_gold_from_feedback(
            session,
            feedback=feedback,
            role=body.role,
            final_text=body.final_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    add_audit_event(
        session,
        category="learning",
        action="gold_growth",
        outcome="success",
        request=request,
        target_type="gold_example",
        target_id=gold.gold_id,
        metadata={
            "feedback_id": feedback.feedback_id,
            "output_id": feedback.output_id,
            "role": gold.role,
            "feedback_outcome": feedback.outcome,
        },
    )
    session.commit()
    return {"gold": _serialize_gold(gold)}


@router.get("/failure-clusters")
def failure_clusters(
    window_days: int | None = Query(default=None, ge=1, le=365),
    min_count: int = Query(default=1, ge=1, le=100),
    session: Session = Depends(get_db_session),
) -> dict[str, list[dict[str, Any]]]:
    clusters = build_failure_clusters(
        session,
        window_days=window_days,
        min_count=min_count,
    )
    return {"clusters": [cluster.as_dict() for cluster in clusters]}


@router.post("/proposals/generate", status_code=status.HTTP_201_CREATED)
def create_learning_proposals(
    body: GenerateProposalsRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, list[dict[str, Any]]]:
    proposals = generate_learning_proposals(session, min_count=body.min_count)
    add_audit_event(
        session,
        category="learning",
        action="proposal_generate",
        outcome="success",
        request=request,
        target_type="learning_proposals",
        target_id="batch",
        metadata={
            "proposal_count": len(proposals),
            "min_count": body.min_count or get_settings().dreamfi_learning_cluster_min_count,
            "proposal_ids": [proposal.proposal_id for proposal in proposals],
        },
    )
    session.commit()
    return {"proposals": [_serialize_proposal(proposal) for proposal in proposals]}


@router.get("/proposals")
def list_learning_proposals(
    status_value: ProposalStatus | None = None,
    session: Session = Depends(get_db_session),
) -> dict[str, list[dict[str, Any]]]:
    stmt = select(LearningProposal).order_by(desc(LearningProposal.created_at)).limit(100)
    if status_value is not None:
        stmt = (
            select(LearningProposal)
            .where(LearningProposal.status == status_value)
            .order_by(desc(LearningProposal.created_at))
        )
    rows = session.scalars(stmt).all()
    return {"proposals": [_serialize_proposal(row) for row in rows]}


@router.post("/proposals/{proposal_id}/approve")
def approve_proposal(
    proposal_id: str,
    body: ProposalReviewRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    proposal = session.get(LearningProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    try:
        prompt = approve_learning_proposal(
            session,
            proposal=proposal,
            reviewer_id=body.reviewer_id,
            review_notes=body.review_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    add_audit_event(
        session,
        category="learning",
        action="proposal_approve",
        outcome="success",
        request=request,
        target_type="learning_proposal",
        target_id=proposal.proposal_id,
        metadata={
            "reviewer_id": body.reviewer_id,
            "skill_id": proposal.skill_id,
            "cluster_key": proposal.cluster_key,
            "created_prompt_version_id": prompt.prompt_version_id,
            "created_prompt_version": prompt.version,
        },
    )
    session.commit()
    return {
        "proposal": _serialize_proposal(proposal),
        "created_prompt_version_id": prompt.prompt_version_id,
    }


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(
    proposal_id: str,
    body: ProposalReviewRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    proposal = session.get(LearningProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    try:
        reject_learning_proposal(
            session,
            proposal=proposal,
            reviewer_id=body.reviewer_id,
            review_notes=body.review_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    add_audit_event(
        session,
        category="learning",
        action="proposal_reject",
        outcome="blocked",
        request=request,
        severity="warning",
        target_type="learning_proposal",
        target_id=proposal.proposal_id,
        metadata={
            "reviewer_id": body.reviewer_id,
            "skill_id": proposal.skill_id,
            "cluster_key": proposal.cluster_key,
        },
    )
    session.commit()
    return {"proposal": _serialize_proposal(proposal)}


@router.post("/outcomes", status_code=status.HTTP_201_CREATED)
def record_production_outcome(
    body: ProductionOutcomeRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    output = session.get(EvalOutput, body.output_id)
    if output is None:
        raise HTTPException(status_code=404, detail="output not found")

    outcome = ProductionOutcome(
        output_id=body.output_id,
        outcome=body.outcome,
        actor_id=body.actor_id,
        notes=body.notes,
        final_text_hash=_outcome_hash(body),
        metadata_json=body.metadata,
    )
    session.add(outcome)
    add_audit_event(
        session,
        category="learning",
        action="production_outcome",
        outcome="success",
        request=request,
        target_type="eval_output",
        target_id=body.output_id,
        metadata={
            "production_outcome": body.outcome,
            "actor_id": body.actor_id,
            "notes_present": body.notes is not None,
            "final_text_sha256": outcome.final_text_hash,
        },
    )
    session.commit()
    return {"outcome": _serialize_outcome(outcome), "summary": production_summary(session)}


@router.get("/outcomes")
def list_production_outcomes(
    output_id: str | None = None,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(ProductionOutcome).order_by(desc(ProductionOutcome.created_at)).limit(100)
    if output_id is not None:
        stmt = (
            select(ProductionOutcome)
            .where(ProductionOutcome.output_id == output_id)
            .order_by(desc(ProductionOutcome.created_at))
        )
    rows = session.scalars(stmt).all()
    return {
        "outcomes": [_serialize_outcome(row) for row in rows],
        "summary": production_summary(session),
    }


@router.post("/replay-schedules", status_code=status.HTTP_201_CREATED)
def create_replay_schedule(
    body: ReplayScheduleRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    if body.replay_type == "gold" and body.skill_id is None:
        raise HTTPException(status_code=422, detail="gold replay requires skill_id")
    if body.replay_type == "workflow" and not body.payload.get("workflow_slug"):
        raise HTTPException(status_code=422, detail="workflow replay requires payload.workflow_slug")

    now = datetime.now(timezone.utc)
    cadence_days = body.cadence_days or get_settings().dreamfi_learning_replay_default_cadence_days
    schedule = ReplaySchedule(
        replay_type=body.replay_type,
        skill_id=body.skill_id,
        prompt_version_id=body.prompt_version_id,
        cadence_days=cadence_days,
        next_run_at=body.next_run_at or now,
        is_active=True,
        created_by=body.created_by,
        payload_json=body.payload,
    )
    session.add(schedule)
    session.flush()
    add_audit_event(
        session,
        category="learning",
        action="replay_schedule_create",
        outcome="success",
        request=request,
        target_type="replay_schedule",
        target_id=schedule.schedule_id,
        metadata={
            "replay_type": schedule.replay_type,
            "skill_id": schedule.skill_id,
            "prompt_version_id": schedule.prompt_version_id,
            "cadence_days": schedule.cadence_days,
            "payload_keys": sorted(schedule.payload_json.keys()),
        },
    )
    session.commit()
    return {"schedule": _serialize_schedule(schedule)}


@router.get("/replay-schedules")
def list_replay_schedules(
    active_only: bool = True,
    session: Session = Depends(get_db_session),
) -> dict[str, list[dict[str, Any]]]:
    stmt = select(ReplaySchedule).order_by(desc(ReplaySchedule.created_at)).limit(100)
    if active_only:
        stmt = (
            select(ReplaySchedule)
            .where(ReplaySchedule.is_active.is_(True))
            .order_by(desc(ReplaySchedule.created_at))
        )
    rows = session.scalars(stmt).all()
    return {"schedules": [_serialize_schedule(row) for row in rows]}


@router.post("/replay-schedules/run-due")
def run_due_replay_schedules(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> dict[str, list[dict[str, Any]]]:
    now = datetime.now(timezone.utc)
    schedules = session.scalars(
        select(ReplaySchedule)
        .where(
            ReplaySchedule.is_active.is_(True),
            ReplaySchedule.next_run_at <= now,
        )
        .order_by(ReplaySchedule.next_run_at)
        .limit(limit)
    ).all()
    runs = [run_replay_schedule(session, schedule=schedule, onyx=onyx) for schedule in schedules]
    add_audit_event(
        session,
        category="learning",
        action="replay_run_due",
        outcome="success",
        request=request,
        target_type="replay_schedules",
        target_id="due",
        metadata={
            "schedule_count": len(schedules),
            "run_ids": [run.replay_run_id for run in runs],
            "statuses": [run.status for run in runs],
        },
    )
    session.commit()
    return {"runs": [_serialize_replay_run(run) for run in runs]}
