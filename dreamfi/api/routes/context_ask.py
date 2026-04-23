"""C4 — POST /v1/context/ask.

Assembles a ContextBundle for the question (via ContextBuilder), checks
every claim is source-grounded, persists a memory row, and returns a
citable answer shape. This endpoint is the PM-facing surface of the
Context Engine.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from dreamfi.api.deps import get_context_builder, get_db_session
from dreamfi.context.builder import ContextBuilder
from dreamfi.context.memory import record_question, similar_questions
from dreamfi.context.model_router import ContextStructuringError
from dreamfi.context.topics import TopicHint

router = APIRouter()


class AskHint(BaseModel):
    epic_key: str | None = None
    squad: str | None = None


class AskRequest(BaseModel):
    workspace_id: str
    asker: str = ""
    question: str = Field(min_length=1)
    hint: AskHint | None = None
    include_memory: bool = True


class CitedClaim(BaseModel):
    statement: str
    citations: list[str]
    confidence: float


class OpenQuestionOut(BaseModel):
    question: str
    why_open: str
    suggested_owner: str | None = None


class MemoryHitOut(BaseModel):
    question: str
    answer_excerpt: str
    similarity: float


class AskResponse(BaseModel):
    bundle_id: str
    topic: str
    topic_id: str | None = None
    claims: list[CitedClaim]
    open_questions: list[OpenQuestionOut]
    freshness_score: float
    coverage_score: float
    confidence: float
    memory: list[MemoryHitOut] = Field(default_factory=list)


class UngroundedClaimError(HTTPException):
    """412 — the model produced a claim with zero citations.

    Surfacing this loudly, instead of silently downgrading the claim, is
    the Context Engine's grounding contract: **no claim, no cite, no ship.**
    """


def _check_grounding(claim_statements: list[list[str]]) -> None:
    for citations in claim_statements:
        if not citations:
            raise UngroundedClaimError(
                status_code=412,
                detail="ungrounded_claim_rejected",
            )


@router.post("/v1/context/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    session: Session = Depends(get_db_session),
    builder: ContextBuilder = Depends(get_context_builder),
) -> AskResponse:
    hint = TopicHint(
        epic_key=body.hint.epic_key if body.hint else None,
        squad=body.hint.squad if body.hint else None,
    )
    try:
        bundle, resolution = builder.build_and_link(
            workspace_id=body.workspace_id,
            topic=body.question,
            topic_hint=hint,
        )
    except ContextStructuringError as e:
        raise HTTPException(
            status_code=502, detail=f"model_structuring_error: {e}"
        ) from e

    _check_grounding([list(c.citation_ids) for c in bundle.claims])

    memory: list[MemoryHitOut] = []
    if body.include_memory:
        for hit in similar_questions(
            session,
            workspace_id=body.workspace_id,
            question=body.question,
            asker=body.asker,
        ):
            memory.append(
                MemoryHitOut(
                    question=hit.question,
                    answer_excerpt=hit.answer_excerpt,
                    similarity=round(hit.similarity, 3),
                )
            )

    # Record the fresh Q&A in memory.
    excerpt = " | ".join(c.statement for c in bundle.claims[:3])
    record_question(
        session,
        workspace_id=body.workspace_id,
        question=body.question,
        answer_excerpt=excerpt,
        asker=body.asker,
        topic_id=resolution.topic_id,
        bundle_id=str(bundle.bundle_id),
    )

    return AskResponse(
        bundle_id=str(bundle.bundle_id),
        topic=bundle.topic,
        topic_id=resolution.topic_id,
        claims=[
            CitedClaim(
                statement=c.statement,
                citations=list(c.citation_ids),
                confidence=c.confidence,
            )
            for c in bundle.claims
        ],
        open_questions=[
            OpenQuestionOut(
                question=q.question,
                why_open=q.why_open,
                suggested_owner=q.suggested_owner,
            )
            for q in bundle.open_questions
        ],
        freshness_score=bundle.freshness_score,
        coverage_score=bundle.coverage_score,
        confidence=bundle.confidence,
        memory=memory,
    )


__all__ = ["router", "AskRequest", "AskResponse", "UngroundedClaimError"]


# Silence unused-import check for fallthrough typing.
_ = Any
