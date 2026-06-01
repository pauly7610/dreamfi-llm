"""Workflow trace mining for reviewed skill candidates.

This layer captures repeatable human workflows without storing raw starter
questions. It turns repeated traces into draft skill candidates; it does not
modify the active skill registry or locked eval files.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from dreamfi.config import get_settings
from dreamfi.db.models import SkillCandidate, WorkflowTrace

_EMAIL_RE = re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_SOURCE_IDENTIFIER_RE = re.compile(
    r"\b(?:tx|txn|transaction|decision|case|member|application|customer|account)[-_: #]*[A-Za-z0-9][A-Za-z0-9_-]{2,}\b",
    re.IGNORECASE,
)
_LONG_TOKEN_RE = re.compile(r"\b[A-Za-z]*\d[A-Za-z0-9_-]{5,}\b")
_SPACES_RE = re.compile(r"\s+")

_SOURCE_ROLES = {
    "confluence": "docs, policies, and PRDs",
    "dragonboat": "roadmap, initiatives, and objectives",
    "ga": "acquisition and traffic analytics",
    "jira": "delivery state, tickets, and sprint risk",
    "klaviyo": "lifecycle campaigns and audiences",
    "metabase": "SQL-backed metrics and dashboards",
    "netxd": "payments, ledger, and transaction state",
    "posthog": "product events, funnels, and sessions",
    "sardine": "fraud decisions, cases, and risk signals",
    "slack": "discussion context and decision breadcrumbs",
    "socure": "identity verification and KYC signals",
}
_OPERATIONAL_SOURCES = {"netxd", "sardine", "socure"}


@dataclass(frozen=True)
class SkillCandidateDraft:
    workspace_id: str
    workflow_type: str
    title: str
    source_trace_count: int
    trace_ids: list[str]
    intent_summary: str
    required_inputs: list[str]
    source_contract: dict[str, Any]
    tool_plan: list[dict[str, Any]]
    freshness_contract: dict[str, Any]
    answer_contract: dict[str, Any]
    refusal_rules: list[str]
    eval_seed_cases: list[dict[str, Any]]
    evidence: dict[str, Any]


def normalize_workflow_type(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return normalized or "general_workflow"


def starter_question_pattern(question: str) -> str:
    value = question.strip()
    value = _EMAIL_RE.sub("[email]", value)
    value = _UUID_RE.sub("[identifier]", value)
    value = _SOURCE_IDENTIFIER_RE.sub("[identifier]", value)
    value = _LONG_TOKEN_RE.sub("[identifier]", value)
    return _SPACES_RE.sub(" ", value).strip()


def starter_question_hash(question: str) -> str:
    return hashlib.sha256(question.strip().encode("utf-8")).hexdigest()


def _dedupe_lower(values: Sequence[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip().lower()
        if normalized and normalized not in seen:
            cleaned.append(normalized)
            seen.add(normalized)
    return cleaned


def _clean_mappings(values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{str(key): item[key] for key in item} for item in values]


def _clean_strings(values: Sequence[str]) -> list[str]:
    return [value.strip() for value in values if value.strip()]


def _title_for_workflow(workflow_type: str) -> str:
    return f"Skill candidate: {workflow_type.replace('_', ' ').title()}"


def _step_action(step: Mapping[str, Any]) -> str:
    for key in ("action", "name", "tool_name"):
        value = step.get(key)
        if isinstance(value, str) and value.strip():
            return _SPACES_RE.sub(" ", value.strip())
    return "Review workflow step"


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {
        key: count
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    }


def _source_contract(traces: Sequence[WorkflowTrace]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    for trace in traces:
        counts.update(trace.source_ids_json)
    source_ids = list(_counter_dict(counts).keys())
    return {
        "source_ids": source_ids,
        "source_counts": _counter_dict(counts),
        "source_roles": {
            source_id: _SOURCE_ROLES.get(source_id, "workflow-specific evidence source")
            for source_id in source_ids
        },
        "authoritative_source_rule": (
            "Use the source that owns the field or decision being claimed; do not "
            "substitute another fresh source for a stale authoritative one."
        ),
    }


def _required_inputs(traces: Sequence[WorkflowTrace]) -> list[str]:
    counts: Counter[str] = Counter()
    for trace in traces:
        counts.update(trace.required_identifiers_json)
    minimum = max(1, (len(traces) + 1) // 2)
    return [
        key
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if count >= minimum
    ]


def _tool_plan(traces: Sequence[WorkflowTrace]) -> list[dict[str, Any]]:
    max_steps = max((len(trace.steps_json) for trace in traces), default=0)
    plan: list[dict[str, Any]] = []
    for index in range(max_steps):
        actions: Counter[str] = Counter()
        sources: Counter[str] = Counter()
        tools: Counter[str] = Counter()
        for trace in traces:
            if len(trace.steps_json) <= index:
                continue
            step = trace.steps_json[index]
            actions[_step_action(step)] += 1
            source_id = str(step.get("source_id") or "").strip().lower()
            tool_name = str(step.get("tool_name") or "").strip()
            if source_id:
                sources[source_id] += 1
            if tool_name:
                tools[tool_name] += 1
        if not actions:
            continue
        action, observed_count = actions.most_common(1)[0]
        item: dict[str, Any] = {
            "order": index + 1,
            "action": action,
            "observed_count": observed_count,
        }
        if sources:
            item["source_id"] = sources.most_common(1)[0][0]
        if tools:
            item["tool_name"] = tools.most_common(1)[0][0]
        plan.append(item)
    return plan


def _freshness_contract(source_ids: Sequence[str]) -> dict[str, Any]:
    operational_sources = sorted(set(source_ids) & _OPERATIONAL_SOURCES)
    if operational_sources:
        return {
            "mode": "operational",
            "source_ids_requiring_source_of_truth_checks": operational_sources,
            "rules": [
                "Require the authoritative source for recent operational claims.",
                "Use exact identifiers before fetching or answering.",
                "Block conclusions when the authoritative source is stale or missing.",
                "Do not infer fraud, ledger, or identity reasons from a different source.",
            ],
        }
    return {
        "mode": "indexed",
        "rules": [
            "Use scoped indexed context with citations.",
            "Surface freshness gaps when retrieved documents are stale.",
            "Block unsupported claims instead of filling gaps with generic prose.",
        ],
    }


def _answer_contract(workflow_type: str) -> dict[str, Any]:
    sections = [
        "Summary",
        "Evidence by source",
        "Freshness and confidence",
        "Open questions",
        "Next action",
    ]
    if any(term in workflow_type for term in ("fraud", "risk", "decline", "kyc")):
        sections = [
            "Decision summary",
            "Timeline",
            "Source-by-source evidence",
            "Reason codes or policy drivers",
            "Freshness blockers",
            "Open questions",
        ]
    return {
        "sections": sections,
        "citation_rule": "Every material claim should cite the trace-selected source or stay open.",
        "tone": "clear, concise, and reviewable by product, risk, and engineering.",
    }


def _refusal_rules(required_inputs: Sequence[str]) -> list[str]:
    rules = [
        "Refuse or ask a follow-up when required identifiers are missing.",
        "Refuse unsupported source-of-truth claims when citations are absent.",
        "Refuse to merge contradictory source facts without naming the conflict.",
    ]
    if required_inputs:
        rules.insert(
            0,
            "Required before execution: " + ", ".join(required_inputs) + ".",
        )
    return rules


def _eval_seed_cases(
    traces: Sequence[WorkflowTrace],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for trace in traces[:limit]:
        cases.append(
            {
                "trace_id": trace.trace_id,
                "starter_question_pattern": trace.starter_question_pattern,
                "source_ids": trace.source_ids_json,
                "required_identifiers": trace.required_identifiers_json,
                "outcome": trace.outcome,
                "human_edit_count": len(trace.human_edits_json),
            }
        )
    return cases


def record_workflow_trace(
    session: Session,
    *,
    workspace_id: str,
    actor_id: str,
    workflow_type: str,
    starter_question: str,
    topic_id: str | None = None,
    source_ids: Sequence[str] = (),
    required_identifiers: Sequence[str] = (),
    steps: Sequence[Mapping[str, Any]] = (),
    accepted_evidence: Sequence[Mapping[str, Any]] = (),
    rejected_evidence: Sequence[Mapping[str, Any]] = (),
    human_edits: Sequence[str] = (),
    outcome: str = "completed",
    final_artifact_ref: str | None = None,
    duration_seconds: int | None = None,
    metadata: Mapping[str, Any] | None = None,
    private: bool = False,
) -> WorkflowTrace:
    trace = WorkflowTrace(
        workspace_id=workspace_id.strip() or "default",
        actor_id=actor_id.strip(),
        workflow_type=normalize_workflow_type(workflow_type),
        starter_question_hash=starter_question_hash(starter_question),
        starter_question_pattern=starter_question_pattern(starter_question),
        topic_id=topic_id.strip() if topic_id and topic_id.strip() else None,
        source_ids_json=_dedupe_lower(source_ids),
        required_identifiers_json=_dedupe_lower(required_identifiers),
        steps_json=_clean_mappings(steps),
        accepted_evidence_json=_clean_mappings(accepted_evidence),
        rejected_evidence_json=_clean_mappings(rejected_evidence),
        human_edits_json=_clean_strings(human_edits),
        outcome=normalize_workflow_type(outcome),
        final_artifact_ref=final_artifact_ref.strip() if final_artifact_ref else None,
        duration_seconds=duration_seconds,
        private=private,
        metadata_json=dict(metadata or {}),
    )
    session.add(trace)
    session.flush()
    return trace


def build_skill_candidate_drafts(
    session: Session,
    *,
    min_trace_count: int | None = None,
    window_days: int | None = None,
    workspace_id: str | None = None,
) -> list[SkillCandidateDraft]:
    settings = get_settings()
    minimum = min_trace_count or settings.dreamfi_skill_mining_min_traces
    since = datetime.now(timezone.utc) - timedelta(
        days=window_days or settings.dreamfi_skill_mining_window_days
    )
    stmt = (
        select(WorkflowTrace)
        .where(WorkflowTrace.created_at >= since, WorkflowTrace.private.is_(False))
        .order_by(desc(WorkflowTrace.created_at))
    )
    if workspace_id is not None:
        stmt = stmt.where(WorkflowTrace.workspace_id == workspace_id)
    traces = session.scalars(stmt).all()

    grouped: dict[tuple[str, str], list[WorkflowTrace]] = {}
    for trace in traces:
        grouped.setdefault((trace.workspace_id, trace.workflow_type), []).append(trace)

    drafts: list[SkillCandidateDraft] = []
    for (group_workspace_id, workflow_type), group in grouped.items():
        if len(group) < minimum:
            continue
        ordered = sorted(group, key=lambda item: item.created_at, reverse=True)
        source_contract = _source_contract(ordered)
        source_ids = list(source_contract["source_ids"])
        required_inputs = _required_inputs(ordered)
        tool_plan = _tool_plan(ordered)
        outcomes = Counter(trace.outcome for trace in ordered)
        human_edits = Counter(
            edit
            for trace in ordered
            for edit in trace.human_edits_json
        )
        intent_summary = (
            f"{len(ordered)} traces show users repeating {workflow_type.replace('_', ' ')} "
            f"with sources {', '.join(source_ids) or 'not yet declared'}."
        )
        drafts.append(
            SkillCandidateDraft(
                workspace_id=group_workspace_id,
                workflow_type=workflow_type,
                title=_title_for_workflow(workflow_type),
                source_trace_count=len(ordered),
                trace_ids=[trace.trace_id for trace in ordered],
                intent_summary=intent_summary,
                required_inputs=required_inputs,
                source_contract=source_contract,
                tool_plan=tool_plan,
                freshness_contract=_freshness_contract(source_ids),
                answer_contract=_answer_contract(workflow_type),
                refusal_rules=_refusal_rules(required_inputs),
                eval_seed_cases=_eval_seed_cases(
                    ordered,
                    limit=settings.dreamfi_skill_mining_eval_seed_limit,
                ),
                evidence={
                    "trace_ids": [trace.trace_id for trace in ordered],
                    "outcomes": _counter_dict(outcomes),
                    "human_edits": _counter_dict(human_edits),
                    "source_trace_count": len(ordered),
                },
            )
        )
    return sorted(drafts, key=lambda item: item.source_trace_count, reverse=True)


def generate_skill_candidates(
    session: Session,
    *,
    min_trace_count: int | None = None,
    window_days: int | None = None,
    workspace_id: str | None = None,
) -> list[SkillCandidate]:
    created: list[SkillCandidate] = []
    for draft in build_skill_candidate_drafts(
        session,
        min_trace_count=min_trace_count,
        window_days=window_days,
        workspace_id=workspace_id,
    ):
        existing = session.scalar(
            select(SkillCandidate)
            .where(
                SkillCandidate.workspace_id == draft.workspace_id,
                SkillCandidate.workflow_type == draft.workflow_type,
                SkillCandidate.status.in_(("draft", "approved")),
            )
            .limit(1)
        )
        if existing is not None:
            continue
        candidate = SkillCandidate(
            workspace_id=draft.workspace_id,
            workflow_type=draft.workflow_type,
            title=draft.title,
            status="draft",
            source_trace_count=draft.source_trace_count,
            trace_ids_json=draft.trace_ids,
            intent_summary=draft.intent_summary,
            required_inputs_json=draft.required_inputs,
            source_contract_json=draft.source_contract,
            tool_plan_json=draft.tool_plan,
            freshness_contract_json=draft.freshness_contract,
            answer_contract_json=draft.answer_contract,
            refusal_rules_json=draft.refusal_rules,
            eval_seed_cases_json=draft.eval_seed_cases,
            evidence_json=draft.evidence,
        )
        session.add(candidate)
        created.append(candidate)
    session.flush()
    return created


def review_skill_candidate(
    session: Session,
    *,
    candidate: SkillCandidate,
    status: str,
    reviewer_id: str,
    review_notes: str | None,
) -> SkillCandidate:
    if status not in {"approved", "rejected"}:
        raise ValueError("status must be approved or rejected")
    if candidate.status not in {"draft", "approved"}:
        raise ValueError(f"candidate is not reviewable: {candidate.status}")
    candidate.status = status
    candidate.reviewer_id = reviewer_id
    candidate.review_notes = review_notes
    candidate.reviewed_at = datetime.now(timezone.utc)
    session.flush()
    return candidate
