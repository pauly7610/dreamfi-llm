"""Experience-driven learning loop utilities.

The loop is intentionally metric-gated and human-gated:
experience -> clusters -> proposal -> approved prompt candidate -> replay/eval.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from dreamfi.autoresearch.loop import run_round
from dreamfi.config import get_settings
from dreamfi.db.models import (
    ArtifactFeedback,
    EvalOutput,
    EvalRound,
    GoldExample,
    LearningProposal,
    PromptVersion,
    ReplayRun,
    ReplaySchedule,
    Skill,
)
from dreamfi.onyx.client import OnyxClient
from dreamfi.skills.engine import SkillEngine

EXPORT_READINESS_THRESHOLD = 0.8


@dataclass(frozen=True)
class FailureCluster:
    cluster_key: str
    category: str
    label: str
    failure_count: int
    output_ids: list[str]
    skill_ids: list[str]
    workflow_slugs: list[str]
    source_ids: list[str]
    criteria_keys: list[str]
    latest_at: datetime
    suggested_action: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "cluster_key": self.cluster_key,
            "category": self.category,
            "label": self.label,
            "failure_count": self.failure_count,
            "output_ids": self.output_ids,
            "skill_ids": self.skill_ids,
            "workflow_slugs": self.workflow_slugs,
            "source_ids": self.source_ids,
            "criteria_keys": self.criteria_keys,
            "latest_at": self.latest_at.isoformat(),
            "suggested_action": self.suggested_action,
        }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _criteria(output: EvalOutput) -> dict[str, Any]:
    return output.criteria_json if isinstance(output.criteria_json, dict) else {}


def _signal_parts(signal: str) -> tuple[str, str]:
    category, _, label = signal.partition(":")
    return category or "general", label or signal


def _signal_label(signal: str) -> str:
    category, label = _signal_parts(signal)
    return f"{category.replace('_', ' ')}: {label.replace('_', ' ')}"


def _suggested_action(signal: str) -> str:
    if signal.startswith("criteria:"):
        return "Add a prompt checklist item and a gold regression for this failed criterion."
    if signal.startswith("workflow:"):
        return "Replay this workflow with recent approved and rejected artifacts before changing prompts."
    if signal.startswith("source:"):
        return "Check connector scope, citation coverage, and source-specific prompt instructions."
    if signal.startswith("missing_section:"):
        return "Make the required section explicit and reject artifacts when the section has thin content."
    if signal.startswith("evidence:low_citation"):
        return "Require stronger citation grounding and ask Onyx for narrower source-scoped evidence."
    if signal.startswith("evidence:stale"):
        return "Refresh source documents or add a freshness warning before generation."
    if signal.startswith("review:"):
        return "Tighten review checklist instructions and keep unresolved items out of publish-ready status."
    return "Review sample failures and add the smallest prompt or gold-example correction."


def failure_signals(output: EvalOutput) -> list[str]:
    settings = get_settings()
    criteria = _criteria(output)
    signals: set[str] = set()

    if output.pass_fail != "pass":
        signals.add("hard_gate:failed")

    workflow_slug = criteria.get("workflow_slug")
    if isinstance(workflow_slug, str) and workflow_slug:
        signals.add(f"workflow:{workflow_slug}")

    source_id = criteria.get("source_id")
    if isinstance(source_id, str) and source_id:
        signals.add(f"source:{source_id}")

    for key, value in criteria.items():
        if value is False:
            signals.add(f"criteria:{key}")

    if criteria.get("has_required_sections") is False:
        signals.add("missing_section:required_sections")
    if criteria.get("has_review_checklist") is False:
        signals.add("missing_section:review_checklist")
    if criteria.get("review_checklist_resolved") is False:
        signals.add("review:unresolved_checklist")

    citation_count = criteria.get("citation_count")
    if isinstance(citation_count, int):
        if citation_count < settings.dreamfi_workflow_min_citations:
            signals.add("evidence:low_citation")
    elif not output.onyx_citations_json:
        signals.add("evidence:low_citation")

    if (
        output.freshness_score is not None
        and float(output.freshness_score) < settings.dreamfi_learning_stale_freshness_threshold
    ):
        signals.add("evidence:stale")

    if (
        output.export_readiness is not None
        and float(output.export_readiness) < EXPORT_READINESS_THRESHOLD
    ):
        signals.add("readiness:low_export")

    return sorted(signals)


def _round_by_id(session: Session, outputs: list[EvalOutput]) -> dict[str, EvalRound]:
    round_ids = {output.round_id for output in outputs}
    if not round_ids:
        return {}
    rounds = session.scalars(select(EvalRound).where(EvalRound.round_id.in_(round_ids))).all()
    return {round_row.round_id: round_row for round_row in rounds}


def build_failure_clusters(
    session: Session,
    *,
    window_days: int | None = None,
    min_count: int = 1,
    limit: int = 100,
) -> list[FailureCluster]:
    settings = get_settings()
    since = datetime.now(timezone.utc) - timedelta(
        days=window_days or settings.dreamfi_learning_cluster_window_days
    )
    outputs = session.scalars(
        select(EvalOutput)
        .where(
            EvalOutput.created_at >= since,
            (
                (EvalOutput.pass_fail != "pass")
                | (EvalOutput.export_readiness < Decimal(str(EXPORT_READINESS_THRESHOLD)))
            ),
        )
        .order_by(desc(EvalOutput.created_at))
        .limit(limit)
    ).all()
    rounds = _round_by_id(session, list(outputs))

    grouped: dict[str, list[EvalOutput]] = defaultdict(list)
    for output in outputs:
        for signal in failure_signals(output):
            grouped[signal].append(output)

    clusters: list[FailureCluster] = []
    for signal, signal_outputs in grouped.items():
        if len(signal_outputs) < min_count:
            continue
        category, _ = _signal_parts(signal)
        skill_ids = sorted(
            {
                rounds[output.round_id].skill_id
                for output in signal_outputs
                if output.round_id in rounds
            }
        )
        workflow_slugs = sorted(
            {
                str(_criteria(output).get("workflow_slug"))
                for output in signal_outputs
                if _criteria(output).get("workflow_slug")
            }
        )
        source_ids = sorted(
            {
                str(_criteria(output).get("source_id"))
                for output in signal_outputs
                if _criteria(output).get("source_id")
            }
        )
        criteria_keys = sorted(
            {
                key
                for output in signal_outputs
                for key, value in _criteria(output).items()
                if value is False
            }
        )
        clusters.append(
            FailureCluster(
                cluster_key=signal,
                category=category,
                label=_signal_label(signal),
                failure_count=len(signal_outputs),
                output_ids=[output.output_id for output in signal_outputs[:10]],
                skill_ids=skill_ids,
                workflow_slugs=workflow_slugs,
                source_ids=source_ids,
                criteria_keys=criteria_keys,
                latest_at=max(_as_utc(output.created_at) for output in signal_outputs),
                suggested_action=_suggested_action(signal),
            )
        )

    return sorted(clusters, key=lambda item: (item.failure_count, item.latest_at), reverse=True)


def _active_prompt(session: Session, skill_id: str) -> PromptVersion | None:
    return session.scalar(
        select(PromptVersion)
        .where(PromptVersion.skill_id == skill_id, PromptVersion.is_active.is_(True))
        .limit(1)
    )


def _primary_skill_id(cluster: FailureCluster) -> str | None:
    return cluster.skill_ids[0] if cluster.skill_ids else None


def _proposal_patch(cluster: FailureCluster) -> str:
    if cluster.cluster_key.startswith("missing_section:"):
        return (
            "Before answering, verify every required section is present with concrete, "
            "source-backed substance. If any required section is missing or thin, state "
            "the missing section in the review checklist instead of presenting the artifact as complete."
        )
    if cluster.cluster_key.startswith("evidence:low_citation"):
        return (
            "Require at least one relevant citation for each material claim. Prefer a "
            "narrower Onyx query over unsupported prose, and mark unsupported claims as open review items."
        )
    if cluster.cluster_key.startswith("evidence:stale"):
        return (
            "Check source freshness before drafting. When retrieved evidence is stale, "
            "surface the freshness gap and avoid launch, policy, or metric claims until sources are refreshed."
        )
    if cluster.cluster_key.startswith("review:"):
        return (
            "End every artifact with a resolved review checklist. Do not use publish-ready language "
            "while any owner, metric, source, or policy item still needs human confirmation."
        )
    if cluster.cluster_key.startswith("criteria:"):
        criterion = cluster.cluster_key.split(":", 1)[1].replace("_", " ")
        return f"Add a final self-check for criterion '{criterion}' and revise the artifact until it passes."
    return cluster.suggested_action


def generate_learning_proposals(
    session: Session,
    *,
    min_count: int | None = None,
) -> list[LearningProposal]:
    threshold = min_count or get_settings().dreamfi_learning_cluster_min_count
    clusters = build_failure_clusters(session, min_count=threshold)
    created: list[LearningProposal] = []

    for cluster in clusters:
        skill_id = _primary_skill_id(cluster)
        if skill_id is None:
            continue
        existing = session.scalar(
            select(LearningProposal)
            .where(
                LearningProposal.skill_id == skill_id,
                LearningProposal.cluster_key == cluster.cluster_key,
                LearningProposal.status.in_(("draft", "approved", "applied")),
            )
            .limit(1)
        )
        if existing is not None:
            continue
        prompt = _active_prompt(session, skill_id)
        proposal = LearningProposal(
            skill_id=skill_id,
            prompt_version_id=prompt.prompt_version_id if prompt is not None else None,
            cluster_key=cluster.cluster_key,
            title=f"Improve {cluster.label}",
            rationale=(
                f"{cluster.failure_count} recent outputs clustered under {cluster.label}. "
                f"Suggested action: {cluster.suggested_action}"
            ),
            proposed_prompt_patch=_proposal_patch(cluster),
            status="draft",
            source_failure_count=cluster.failure_count,
            evidence_json=cluster.as_dict(),
        )
        session.add(proposal)
        created.append(proposal)

    session.flush()
    return created


def approve_learning_proposal(
    session: Session,
    *,
    proposal: LearningProposal,
    reviewer_id: str,
    review_notes: str | None,
) -> PromptVersion:
    if proposal.status not in {"draft", "approved"}:
        raise ValueError(f"proposal is not approvable: {proposal.status}")

    base = (
        session.get(PromptVersion, proposal.prompt_version_id)
        if proposal.prompt_version_id is not None
        else _active_prompt(session, proposal.skill_id)
    )
    if base is None:
        raise ValueError(f"no base prompt version for skill {proposal.skill_id}")

    latest_version = session.scalar(
        select(func.max(PromptVersion.version)).where(PromptVersion.skill_id == proposal.skill_id)
    ) or 0
    new_prompt = PromptVersion(
        skill_id=proposal.skill_id,
        version=int(latest_version) + 1,
        template=base.template,
        system_prompt=(
            f"{base.system_prompt.rstrip()}\n\n"
            f"Learning proposal {proposal.proposal_id}:\n"
            f"{proposal.proposed_prompt_patch.strip()}"
        ),
        is_active=False,
        parent_version_id=base.prompt_version_id,
    )
    session.add(new_prompt)
    session.flush()

    proposal.status = "applied"
    proposal.reviewer_id = reviewer_id
    proposal.review_notes = review_notes
    proposal.reviewed_at = datetime.now(timezone.utc)
    proposal.created_prompt_version_id = new_prompt.prompt_version_id
    return new_prompt


def reject_learning_proposal(
    session: Session,
    *,
    proposal: LearningProposal,
    reviewer_id: str,
    review_notes: str | None,
) -> LearningProposal:
    if proposal.status not in {"draft", "approved"}:
        raise ValueError(f"proposal is not rejectable: {proposal.status}")
    proposal.status = "rejected"
    proposal.reviewer_id = reviewer_id
    proposal.review_notes = review_notes
    proposal.reviewed_at = datetime.now(timezone.utc)
    session.flush()
    return proposal


def feedback_input_context(output: EvalOutput, feedback: ArtifactFeedback) -> dict[str, Any]:
    criteria = _criteria(output)
    return {
        "text": output.test_input_label,
        "workflow_slug": criteria.get("workflow_slug"),
        "workflow_title": criteria.get("workflow_title"),
        "topic_id": criteria.get("topic_id"),
        "source_id": criteria.get("source_id"),
        "review_outcome": feedback.outcome,
        "review_reason": feedback.reason,
    }


def create_gold_from_feedback(
    session: Session,
    *,
    feedback: ArtifactFeedback,
    role: str,
    final_text: str | None,
) -> GoldExample:
    if feedback.gold_id is not None:
        existing = session.get(GoldExample, feedback.gold_id)
        if existing is not None:
            if existing.role != role:
                raise ValueError(
                    f"feedback already promoted to {existing.role} gold"
                )
            return existing

    output = session.get(EvalOutput, feedback.output_id)
    if output is None:
        raise ValueError("feedback output is missing")
    round_row = session.get(EvalRound, output.round_id)
    if round_row is None:
        raise ValueError("feedback output round is missing")

    positive_roles = {"exemplar", "canary"}
    negative_roles = {"regression", "counter_example", "canary"}
    if feedback.outcome in {"approved", "edited"} and role not in positive_roles:
        raise ValueError("approved or edited feedback can only become exemplar/canary gold")
    if feedback.outcome == "rejected" and role not in negative_roles:
        raise ValueError("rejected feedback can only become regression/counter_example/canary gold")

    gold = GoldExample(
        workspace_id="default",
        skill_id=round_row.skill_id,
        scenario_type=str(_criteria(output).get("workflow_slug") or output.test_input_label[:80] or "feedback"),
        input_context_json=feedback_input_context(output, feedback),
        output_text=final_text or output.generated_text,
        prompt_version_id=round_row.prompt_version_id,
        role=role,
        expected_pass_criteria={
            "feedback_id": feedback.feedback_id,
            "feedback_outcome": feedback.outcome,
            "reason": feedback.reason,
            "final_text_hash": feedback.final_text_hash,
        },
    )
    session.add(gold)
    session.flush()
    feedback.gold_id = gold.gold_id
    return gold


def run_replay_schedule(
    session: Session,
    *,
    schedule: ReplaySchedule,
    onyx: OnyxClient,
) -> ReplayRun:
    now = datetime.now(timezone.utc)
    run = ReplayRun(
        schedule_id=schedule.schedule_id,
        status="running",
        skill_id=schedule.skill_id,
        prompt_version_id=schedule.prompt_version_id,
        started_at=now,
        summary_json={},
    )
    session.add(run)
    session.flush()

    try:
        if schedule.replay_type == "gold":
            if schedule.skill_id is None:
                raise ValueError("gold replay schedule requires skill_id")
            engine = SkillEngine(db=session, onyx=onyx)
            summary = run_round(
                session=session,
                engine=engine,
                skill_id=schedule.skill_id,
                n_outputs_per_input=1,
                prompt_version_id=schedule.prompt_version_id,
            )
            run.status = "success"
            run.round_id = summary.round_id
            run.prompt_version_id = schedule.prompt_version_id
            run.summary_json = {
                "score": summary.score,
                "previous_score": summary.previous_score,
                "improvement": summary.improvement,
                "artifacts_path": summary.artifacts_path,
            }
        elif schedule.replay_type == "workflow":
            from dreamfi.api.routes.workflows import (
                WORKFLOW_SPECS,
                _active_prompt_version,
                _create_artifact_round,
                _workflow_prompt,
            )

            workflow_slug = str(schedule.payload_json.get("workflow_slug") or "")
            if workflow_slug not in WORKFLOW_SPECS:
                raise ValueError("workflow replay schedule requires workflow_slug")
            spec = WORKFLOW_SPECS[workflow_slug]
            skill = session.get(Skill, spec.skill_id)
            if skill is None or skill.onyx_persona_id is None:
                raise ValueError("workflow replay skill/persona is not seeded")
            prompt_version = _active_prompt_version(session, spec.skill_id)
            question = str(
                schedule.payload_json.get("question")
                or f"Replay {spec.title} from the current DreamFi product context."
            ).strip()
            topic_id = schedule.payload_json.get("topic_id")
            source_id = schedule.payload_json.get("source_id")
            chat_session = onyx.create_chat_session(
                persona_id=skill.onyx_persona_id,
                description=f"dreamfi-replay:{workflow_slug}:{question[:80]}",
            )
            chat = onyx.send_message_sync(
                chat_session_id=chat_session.id,
                parent_message_id=None,
                message=_workflow_prompt(
                    spec=spec,
                    question=question,
                    topic_id=str(topic_id) if topic_id else None,
                    source_id=str(source_id) if source_id else None,
                ),
            )
            output = _create_artifact_round(
                session=session,
                spec=spec,
                prompt_version=prompt_version,
                question=question,
                topic_id=str(topic_id) if topic_id else None,
                source_id=str(source_id) if source_id else None,
                chat_session_id=chat_session.id,
                chat=chat,
            )
            run.status = "success"
            run.skill_id = spec.skill_id
            run.prompt_version_id = prompt_version.prompt_version_id
            run.round_id = output.round_id
            run.output_id = output.output_id
            run.summary_json = {
                "workflow_slug": workflow_slug,
                "pass_fail": output.pass_fail,
                "confidence": float(output.confidence or 0.0),
                "export_readiness": float(output.export_readiness or 0.0),
            }
        elif schedule.replay_type == "source_refresh":
            from dreamfi.connector_sync import sync_connector
            from dreamfi.connectors import CONNECTOR_BY_ID
            from dreamfi.settings_activation import ensure_connector_document_set

            raw_source_ids = schedule.payload_json.get("source_ids") or list(CONNECTOR_BY_ID.keys())
            if not isinstance(raw_source_ids, list):
                raise ValueError("source_refresh schedule requires source_ids list")
            source_ids = [str(source_id).strip().lower() for source_id in raw_source_ids if str(source_id).strip()]
            sync_limit = schedule.payload_json.get("limit")
            connector_results: list[dict[str, Any]] = []
            for source_id in source_ids:
                connector = CONNECTOR_BY_ID.get(source_id)
                if connector is None:
                    connector_results.append(
                        {
                            "connector_id": source_id,
                            "status": "failed",
                            "reason": "unknown connector",
                        }
                    )
                    continue
                if connector.connection_method == "custom_ingestion":
                    connector_run = sync_connector(
                        session=session,
                        onyx=onyx,
                        connector=connector,
                        actor_id="source-refresh-schedule",
                        trigger="scheduled",
                        limit=sync_limit if isinstance(sync_limit, int) else None,
                    )
                    connector_results.append(
                        {
                            "connector_id": connector.connector_id,
                            "connection_method": connector.connection_method,
                            "status": connector_run.status,
                            "sync_run_id": connector_run.sync_run_id,
                            "pulled_count": connector_run.pulled_count,
                            "persisted_count": connector_run.persisted_count,
                            "ingested_count": connector_run.ingested_count,
                            "skipped_count": connector_run.skipped_count,
                            "error_count": connector_run.error_count,
                            "reason": connector_run.reason,
                        }
                    )
                    continue
                try:
                    setting = ensure_connector_document_set(
                        session=session,
                        onyx=onyx,
                        connector=connector,
                        actor_id="source-refresh-schedule",
                    )
                    connector_results.append(
                        {
                            "connector_id": connector.connector_id,
                            "connection_method": connector.connection_method,
                            "status": "success",
                            "document_set_id": setting.document_set_id,
                            "document_set_name": setting.document_set_name,
                        }
                    )
                except Exception as exc:
                    connector_results.append(
                        {
                            "connector_id": connector.connector_id,
                            "connection_method": connector.connection_method,
                            "status": "failed",
                            "reason": f"{type(exc).__name__}: {exc}",
                        }
                    )

            failed_results = [item for item in connector_results if item.get("status") != "success"]
            run.status = "success" if not failed_results else "error"
            run.reason = None if not failed_results else f"{len(failed_results)} source refresh task(s) failed"
            run.summary_json = {
                "source_refresh": connector_results,
                "source_count": len(connector_results),
                "failed_count": len(failed_results),
            }
        else:
            raise ValueError(f"unsupported replay_type: {schedule.replay_type}")
    except Exception as exc:
        run.status = "error"
        run.reason = type(exc).__name__
        run.summary_json = {"error": str(exc)[:500]}
    finally:
        completed_at = datetime.now(timezone.utc)
        run.completed_at = completed_at
        schedule.last_run_at = completed_at
        schedule.next_run_at = completed_at + timedelta(days=schedule.cadence_days)
        session.flush()

    return run


def production_summary(session: Session) -> dict[str, Any]:
    from dreamfi.db.models import ProductionOutcome

    rows = session.scalars(select(ProductionOutcome)).all()
    by_outcome = Counter(row.outcome for row in rows)
    return {
        "total_outcomes": len(rows),
        "by_outcome": dict(sorted(by_outcome.items())),
    }
