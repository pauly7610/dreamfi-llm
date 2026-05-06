"""Console workflow API for live asks and generated product artifacts."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from dreamfi.api.deps import get_db_session, get_onyx_client
from dreamfi.audit import add_audit_event, hash_text
from dreamfi.confidence.scorer import ConfidenceScorer
from dreamfi.config import get_settings
from dreamfi.db.models import EvalOutput, EvalRound, PromptVersion, Skill
from dreamfi.onyx.client import OnyxClient
from dreamfi.onyx.errors import OnyxError
from dreamfi.onyx.models import ChatResult, SearchHit
from dreamfi.trust.artifact import ExportReadinessInput, compute_export_readiness

router = APIRouter()

WorkflowSlug = Literal["weekly-brief", "technical-prd", "business-prd", "risk-brd"]
_PUBLISH_READY_CRITERIA = {
    "has_output",
    "meets_min_citations",
    "has_required_sections",
    "scope_declared",
    "has_review_checklist",
    "review_checklist_resolved",
}


@dataclass(frozen=True)
class WorkflowSpec:
    slug: WorkflowSlug
    title: str
    skill_id: str
    sections: tuple[str, ...]


WORKFLOW_SPECS: dict[str, WorkflowSpec] = {
    "weekly-brief": WorkflowSpec(
        slug="weekly-brief",
        title="Weekly PM Brief",
        skill_id="meeting_summary",
        sections=("Summary", "What changed", "Decisions", "Risks", "Next actions"),
    ),
    "technical-prd": WorkflowSpec(
        slug="technical-prd",
        title="Technical PRD",
        skill_id="agent_system_prompt",
        sections=("Problem", "Requirements", "Technical approach", "Dependencies", "Rollout"),
    ),
    "business-prd": WorkflowSpec(
        slug="business-prd",
        title="Business PRD",
        skill_id="landing_page_copy",
        sections=("Opportunity", "Customer impact", "Business case", "Launch plan", "Risks"),
    ),
    "risk-brd": WorkflowSpec(
        slug="risk-brd",
        title="Risk BRD",
        skill_id="support_agent",
        sections=("Risk context", "Evidence", "Policy decision", "Controls", "Open questions"),
    ),
}


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    topic_id: str | None = None
    source_id: str | None = None
    source_ids: list[str] = Field(default_factory=list)


class AskCitation(BaseModel):
    document_id: str
    title: str
    blurb: str
    score: float
    link: str | None = None
    updated_at: str | None = None


class AskResponse(BaseModel):
    question: str
    answer: str
    confidence: float
    citations: list[AskCitation]
    followups: list[str]


class GenerateArtifactRequest(BaseModel):
    workflow_slug: WorkflowSlug
    question: str | None = None
    topic_id: str | None = None
    source_id: str | None = None
    regenerate_from_output_id: str | None = None


class GenerateArtifactResponse(BaseModel):
    round_id: str
    output_id: str
    workflow_slug: str
    workflow_title: str
    skill_id: str
    pass_fail: str
    confidence: float
    export_readiness: float
    destination_href: str


def _scope_filters(
    *, topic_id: str | None, source_id: str | None, source_ids: list[str]
) -> dict[str, Any]:
    scoped_sources = sorted({source_id, *source_ids} - {None, ""})
    scope: dict[str, Any] = {}
    if topic_id:
        scope["topic_id"] = topic_id
    if scoped_sources:
        scope["source_ids"] = scoped_sources
    return {"dreamfi_scope": scope} if scope else {}


def _serialize_hit(hit: SearchHit) -> AskCitation:
    return AskCitation(
        document_id=hit.document_id,
        title=hit.semantic_identifier,
        blurb=hit.blurb,
        score=hit.score,
        link=hit.link,
        updated_at=hit.updated_at.isoformat() if hit.updated_at else None,
    )


def _compose_answer(question: str, hits: list[SearchHit]) -> str:
    if not hits:
        return (
            "Onyx did not return matching evidence for this ask. Keep the question in "
            "review and narrow it to a source or topic before generating an artifact."
        )

    lead = hits[0]
    supporting = hits[1:3]
    support_text = ""
    if supporting:
        titles = ", ".join(hit.semantic_identifier for hit in supporting)
        support_text = f" Supporting evidence also came from {titles}."
    return (
        f"Onyx found {len(hits)} evidence item(s) for: {question}. "
        f"The strongest source is {lead.semantic_identifier}: {lead.blurb}"
        f"{support_text}"
    )


def _followups(question: str, topic_id: str | None, source_ids: list[str]) -> list[str]:
    scoped_source = source_ids[0] if source_ids else None
    followups = [
        f"What evidence would change the answer to: {question}",
        "Which artifact should Product generate from this answer?",
    ]
    if topic_id:
        followups.append(f"What is still missing from the {topic_id} topic room?")
    if scoped_source:
        followups.append(f"What changed in {scoped_source} since the last decision?")
    return followups[:4]


@router.post("/api/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> AskResponse:
    source_ids = sorted({body.source_id, *body.source_ids} - {None, ""})
    try:
        hits = onyx.admin_search(
            query=body.question,
            filters=_scope_filters(
                topic_id=body.topic_id,
                source_id=body.source_id,
                source_ids=body.source_ids,
            ),
            limit=get_settings().dreamfi_ask_search_limit,
        )
    except (OnyxError, httpx.HTTPError) as exc:
        add_audit_event(
            session,
            category="access",
            action="onyx_search",
            outcome="error",
            request=request,
            severity="error",
            target_type="onyx_search",
            target_id=body.topic_id or body.source_id,
            reason=type(exc).__name__,
            metadata={
                "question_sha256": hash_text(body.question),
                "topic_id": body.topic_id,
                "source_ids": source_ids,
            },
        )
        session.commit()
        raise HTTPException(status_code=503, detail=f"Onyx search failed: {exc}") from exc

    confidence = round(min(1.0, len(hits) / max(1, get_settings().dreamfi_ask_search_limit)), 3)
    add_audit_event(
        session,
        category="access",
        action="onyx_search",
        outcome="success",
        request=request,
        target_type="onyx_search",
        target_id=body.topic_id or body.source_id,
        metadata={
            "question_sha256": hash_text(body.question),
            "topic_id": body.topic_id,
            "source_ids": source_ids,
            "hit_count": len(hits),
            "confidence": confidence,
        },
    )
    session.commit()
    return AskResponse(
        question=body.question,
        answer=_compose_answer(body.question, hits),
        confidence=confidence,
        citations=[_serialize_hit(hit) for hit in hits],
        followups=_followups(body.question, body.topic_id, source_ids),
    )


def _active_prompt_version(session: Session, skill_id: str) -> PromptVersion:
    active = session.scalar(
        select(PromptVersion)
        .where(PromptVersion.skill_id == skill_id, PromptVersion.is_active.is_(True))
        .limit(1)
    )
    if active is not None:
        return active

    latest_version = session.scalar(
        select(func.max(PromptVersion.version)).where(PromptVersion.skill_id == skill_id)
    ) or 0
    prompt_version = PromptVersion(
        skill_id=skill_id,
        version=int(latest_version) + 1,
        template="console_workflow",
        system_prompt="DreamFi console workflow bootstrap.",
        is_active=True,
        activated_at=datetime.now(timezone.utc),
    )
    session.add(prompt_version)
    session.flush()
    return prompt_version


def _freshness_from_chat(chat: ChatResult, scorer: ConfidenceScorer) -> float:
    updated_ats = []
    for doc in chat.documents:
        updated_at = doc.get("updated_at")
        if updated_at is None:
            continue
        if isinstance(updated_at, datetime):
            updated_ats.append(updated_at)
            continue
        if isinstance(updated_at, str):
            try:
                updated_ats.append(datetime.fromisoformat(updated_at.replace("Z", "+00:00")))
            except ValueError:
                continue
    return scorer.freshness_from_updated_at(updated_ats)


def _workflow_prompt(
    *, spec: WorkflowSpec, question: str, topic_id: str | None, source_id: str | None
) -> str:
    scope = []
    if topic_id:
        scope.append(f"topic_id={topic_id}")
    if source_id:
        scope.append(f"source_id={source_id}")
    scope_text = ", ".join(scope) if scope else "all available DreamFi product context"
    sections = "\n".join(f"- {section}" for section in spec.sections)
    return (
        f"You are drafting a {spec.title} for DreamFi's product team.\n"
        "Use Onyx retrieval evidence and include citation markers where available.\n"
        "Do not invent metrics, owners, dates, or policy claims that are not supported.\n"
        f"Scope: {scope_text}\n"
        f"Product question: {question}\n\n"
        "Return Markdown with these sections:\n"
        f"{sections}\n\n"
        "End with a short review checklist for anything that still needs human confirmation."
    )


def _source_hygiene(topic_id: str | None, source_id: str | None) -> float:
    if topic_id and source_id:
        return 1.0
    if topic_id or source_id:
        return 0.85
    return 0.65


def _section_text(markdown: str, section: str) -> str:
    match = re.search(
        rf"^\s{{0,3}}#{{1,6}}\s+{re.escape(section)}\b.*$",
        markdown,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if match is None:
        return ""
    next_heading = re.search(
        r"^\s{0,3}#{1,6}\s+",
        markdown[match.end() :],
        flags=re.MULTILINE,
    )
    end = match.end() + next_heading.start() if next_heading else len(markdown)
    return markdown[match.end() : end].strip()


def _has_required_section_content(markdown: str, sections: tuple[str, ...]) -> bool:
    min_words = get_settings().dreamfi_workflow_min_section_words
    for section in sections:
        section_text = _section_text(markdown, section)
        if len(section_text.split()) < min_words:
            return False
    return True


def _review_checklist_status(markdown: str) -> tuple[bool, bool]:
    tail = _section_text(markdown, "Review checklist")
    if not tail:
        return False, False

    normalized_tail = tail.lower()
    resolved_markers = {
        "no open review items",
        "no unresolved review items",
        "all review items resolved",
    }
    if any(marker in normalized_tail for marker in resolved_markers):
        return True, True

    unresolved_markers = {
        "[ ]",
        "confirm ",
        "missing",
        "needs confirmation",
        "needs human",
        "open item",
        "tbd",
        "unknown",
        "unresolved",
        "verify ",
    }
    return True, not any(marker in normalized_tail for marker in unresolved_markers)


def _criteria_for_workflow(
    *,
    spec: WorkflowSpec,
    question: str,
    topic_id: str | None,
    source_id: str | None,
    chat: ChatResult,
) -> dict[str, Any]:
    settings = get_settings()
    text = chat.text.strip()
    has_review_checklist, review_checklist_resolved = _review_checklist_status(text)
    citation_count = len(chat.citations)
    criteria = {
        "workflow_slug": spec.slug,
        "workflow_title": spec.title,
        "question": question,
        "topic_id": topic_id,
        "source_id": source_id,
        "has_output": bool(text),
        "citation_count": citation_count,
        "meets_min_citations": citation_count >= settings.dreamfi_workflow_min_citations,
        "has_required_sections": _has_required_section_content(text, spec.sections),
        "scope_declared": bool(topic_id or source_id)
        or not settings.dreamfi_workflow_require_scope,
        "has_review_checklist": has_review_checklist,
        "review_checklist_resolved": review_checklist_resolved,
    }
    return criteria


def _criteria_score(criteria: dict[str, Any]) -> float:
    values = [
        value
        for key, value in criteria.items()
        if key
        in _PUBLISH_READY_CRITERIA
    ]
    return sum(1 for value in values if value) / len(values) if values else 0.0


def _workflow_hard_gate_passes(criteria: dict[str, Any]) -> bool:
    return all(bool(criteria.get(key)) for key in _PUBLISH_READY_CRITERIA)


def _create_artifact_round(
    *,
    session: Session,
    spec: WorkflowSpec,
    prompt_version: PromptVersion,
    question: str,
    topic_id: str | None,
    source_id: str | None,
    chat_session_id: str,
    chat: ChatResult,
) -> EvalOutput:
    scorer = ConfidenceScorer(
        freshness_halflife_days=get_settings().dreamfi_freshness_halflife_days
    )
    criteria = _criteria_for_workflow(
        spec=spec,
        question=question,
        topic_id=topic_id,
        source_id=source_id,
        chat=chat,
    )
    eval_score = _criteria_score(criteria)
    pass_fail = "pass" if _workflow_hard_gate_passes(criteria) else "fail"
    freshness = _freshness_from_chat(chat, scorer)
    confidence = scorer.score(
        eval_score=eval_score,
        freshness_score=freshness,
        citation_count=len(chat.citations),
        hard_gate_passed=pass_fail == "pass",
    )
    claim_lineage_target = max(1, get_settings().dreamfi_claim_lineage_target_citations)
    export_readiness = compute_export_readiness(
        ExportReadinessInput(
            hard_gate_pass=pass_fail == "pass",
            confidence=confidence.confidence,
            gold_regression_pass_rate=1.0,
            claim_lineage_rate=min(len(chat.citations), claim_lineage_target)
            / claim_lineage_target,
            metric_freshness=confidence.freshness_score,
            planning_hygiene_score=_source_hygiene(topic_id, source_id),
        )
    )
    started = datetime.now(timezone.utc)
    round_row = EvalRound(
        skill_id=spec.skill_id,
        prompt_version_id=prompt_version.prompt_version_id,
        n_inputs=1,
        n_outputs_per_input=1,
        total_outputs=1,
        total_passes=1 if pass_fail == "pass" else 0,
        score=Decimal(f"{eval_score:.4f}"),
        previous_score=None,
        improvement=None,
        started_at=started,
        completed_at=started,
        artifacts_path=f"evals/results/{spec.slug}/rounds/pending",
    )
    session.add(round_row)
    session.flush()
    round_row.artifacts_path = f"evals/results/{spec.slug}/rounds/{round_row.round_id}"

    output = EvalOutput(
        round_id=round_row.round_id,
        test_input_label=question[:160],
        attempt=1,
        generated_text=chat.text,
        criteria_json=criteria,
        pass_fail=pass_fail,
        onyx_chat_session_id=chat_session_id,
        onyx_message_id=chat.message_id,
        onyx_citations_json={str(key): value for key, value in chat.citations.items()},
        freshness_score=confidence.freshness_score,
        confidence=confidence.confidence,
        export_readiness=export_readiness.value,
        export_breakdown_json=export_readiness.breakdown,
    )
    session.add(output)
    session.flush()
    return output


@router.post("/api/workflows/generate", response_model=GenerateArtifactResponse)
def generate_artifact(
    body: GenerateArtifactRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> GenerateArtifactResponse:
    spec = WORKFLOW_SPECS[body.workflow_slug]
    skill = session.get(Skill, spec.skill_id)
    if skill is None:
        raise HTTPException(status_code=409, detail="DreamFi skills are not seeded")
    if skill.onyx_persona_id is None:
        raise HTTPException(status_code=409, detail="Onyx personas are not seeded")

    prompt_version = _active_prompt_version(session, spec.skill_id)
    question = (
        body.question
        or f"Draft a {spec.title} from the current DreamFi product context."
    ).strip()
    if body.regenerate_from_output_id:
        previous = session.get(EvalOutput, body.regenerate_from_output_id)
        if previous is not None:
            question = f"{question}\n\nRegenerate from artifact {previous.output_id}."

    try:
        chat_session = onyx.create_chat_session(
            persona_id=skill.onyx_persona_id,
            description=f"dreamfi-workflow:{spec.slug}:{question[:80]}",
        )
        chat = onyx.send_message_sync(
            chat_session_id=chat_session.id,
            parent_message_id=None,
            message=_workflow_prompt(
                spec=spec,
                question=question,
                topic_id=body.topic_id,
                source_id=body.source_id,
            ),
        )
    except (OnyxError, httpx.HTTPError) as exc:
        add_audit_event(
            session,
            category="generation",
            action="workflow_generate",
            outcome="error",
            request=request,
            severity="error",
            target_type="workflow",
            target_id=body.workflow_slug,
            reason=type(exc).__name__,
            metadata={
                "workflow_slug": body.workflow_slug,
                "skill_id": spec.skill_id,
                "question_sha256": hash_text(question),
                "topic_id": body.topic_id,
                "source_id": body.source_id,
                "regenerate_from_output_id": body.regenerate_from_output_id,
            },
        )
        session.commit()
        raise HTTPException(status_code=503, detail=f"Onyx generation failed: {exc}") from exc

    output = _create_artifact_round(
        session=session,
        spec=spec,
        prompt_version=prompt_version,
        question=question,
        topic_id=body.topic_id,
        source_id=body.source_id,
        chat_session_id=chat_session.id,
        chat=chat,
    )
    add_audit_event(
        session,
        category="generation",
        action="workflow_generate",
        outcome="success" if output.pass_fail == "pass" else "blocked",
        request=request,
        severity="info" if output.pass_fail == "pass" else "warning",
        target_type="eval_output",
        target_id=output.output_id,
        metadata={
            "workflow_slug": spec.slug,
            "workflow_title": spec.title,
            "skill_id": spec.skill_id,
            "round_id": output.round_id,
            "question_sha256": hash_text(question),
            "topic_id": body.topic_id,
            "source_id": body.source_id,
            "regenerate_from_output_id": body.regenerate_from_output_id,
            "pass_fail": output.pass_fail,
            "confidence": float(output.confidence or 0.0),
            "export_readiness": float(output.export_readiness or 0.0),
            "citation_count": len(chat.citations),
            "criteria": output.criteria_json,
        },
    )
    session.commit()

    return GenerateArtifactResponse(
        round_id=output.round_id,
        output_id=output.output_id,
        workflow_slug=spec.slug,
        workflow_title=spec.title,
        skill_id=spec.skill_id,
        pass_fail=output.pass_fail,
        confidence=float(output.confidence or 0.0),
        export_readiness=float(output.export_readiness or 0.0),
        destination_href=f"/console/review?focus={output.output_id}",
    )


@router.get("/api/workflows")
def workflow_catalog() -> dict[str, list[dict[str, str]]]:
    return {
        "workflows": [
            {
                "slug": spec.slug,
                "title": spec.title,
                "skill_id": spec.skill_id,
            }
            for spec in WORKFLOW_SPECS.values()
        ]
    }
