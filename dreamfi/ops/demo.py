"""Idempotent demo data for evaluating DreamFi without live connectors."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from dreamfi.audit import add_audit_event, hash_text
from dreamfi.db.models import (
    ArtifactFeedback,
    ConsoleTopic,
    EvalOutput,
    EvalRound,
    GoldExample,
    LearningProposal,
    ProductionOutcome,
    PromptVersion,
    PublishLog,
    ReplaySchedule,
    Skill,
)
from dreamfi.skills.engine import PROMPTS_DIR, PROMPT_FILE_BY_SKILL
from dreamfi.skills.registry import seed_registry

REPO_ROOT = Path(__file__).resolve().parents[2]


def ensure_active_prompts(session: Session) -> None:
    seed_registry(session, repo_root=REPO_ROOT, enforce_regression_minimum=False)
    for skill in session.scalars(select(Skill)).all():
        active = session.scalar(
            select(PromptVersion)
            .where(
                PromptVersion.skill_id == skill.skill_id,
                PromptVersion.is_active.is_(True),
            )
            .limit(1)
        )
        if active is not None:
            continue
        latest_version = session.scalar(
            select(func.max(PromptVersion.version)).where(
                PromptVersion.skill_id == skill.skill_id
            )
        ) or 0
        template = PROMPT_FILE_BY_SKILL[skill.skill_id]
        system_prompt = (PROMPTS_DIR / template).read_text(encoding="utf-8")
        session.add(
            PromptVersion(
                skill_id=skill.skill_id,
                version=int(latest_version) + 1,
                template=template,
                system_prompt=system_prompt,
                is_active=True,
                activated_at=datetime.now(timezone.utc),
            )
        )
    session.flush()


def _prompt(session: Session, skill_id: str) -> PromptVersion:
    prompt = session.scalar(
        select(PromptVersion)
        .where(PromptVersion.skill_id == skill_id, PromptVersion.is_active.is_(True))
        .limit(1)
    )
    if prompt is None:
        raise RuntimeError(f"missing active prompt for {skill_id}")
    return prompt


def _ensure_topic(
    session: Session,
    *,
    topic_id: str,
    title: str,
    summary: str,
    question: str,
    source_ids: list[str],
    generator_slug: str,
    owner: str,
    status: str,
) -> None:
    if session.get(ConsoleTopic, topic_id) is not None:
        return
    session.add(
        ConsoleTopic(
            topic_id=topic_id,
            title=title,
            summary=summary,
            question=question,
            owner=owner,
            status=status,
            target_decision_at=datetime.now(timezone.utc) + timedelta(days=7),
            source_ids_json=source_ids,
            default_generator_slug=generator_slug,
        )
    )


def _ensure_round_and_output(
    session: Session,
    *,
    skill_id: str,
    label: str,
    generated_text: str,
    criteria: dict[str, object],
    pass_fail: str,
    confidence: str,
    export_readiness: str,
    freshness: str,
) -> EvalOutput:
    existing = session.scalar(
        select(EvalOutput).where(EvalOutput.test_input_label == label).limit(1)
    )
    if existing is not None:
        return existing

    prompt = _prompt(session, skill_id)
    now = datetime.now(timezone.utc)
    round_row = EvalRound(
        skill_id=skill_id,
        prompt_version_id=prompt.prompt_version_id,
        n_inputs=1,
        n_outputs_per_input=1,
        total_outputs=1,
        total_passes=1 if pass_fail == "pass" else 0,
        score=Decimal("1.0000") if pass_fail == "pass" else Decimal("0.0000"),
        previous_score=Decimal("0.8200"),
        improvement=Decimal("0.0500") if pass_fail == "pass" else Decimal("-0.1200"),
        started_at=now - timedelta(minutes=5),
        completed_at=now - timedelta(minutes=4),
        artifacts_path=f"evals/results/{skill_id}/rounds/demo",
    )
    session.add(round_row)
    session.flush()
    output = EvalOutput(
        round_id=round_row.round_id,
        test_input_label=label,
        attempt=1,
        generated_text=generated_text,
        criteria_json=criteria,
        pass_fail=pass_fail,
        onyx_chat_session_id=f"demo-{skill_id}",
        onyx_message_id=100,
        onyx_citations_json={"1": "demo-doc-1", "2": "demo-doc-2"} if pass_fail == "pass" else {},
        freshness_score=Decimal(freshness),
        confidence=Decimal(confidence),
        export_readiness=Decimal(export_readiness),
        export_breakdown_json={
            "hard_gate": 1.0 if pass_fail == "pass" else 0.0,
            "confidence": float(confidence),
            "freshness": float(freshness),
        },
    )
    session.add(output)
    session.flush()
    return output


def seed_demo_data(session: Session) -> dict[str, int]:
    ensure_active_prompts(session)
    _ensure_topic(
        session,
        topic_id="kyc-conversion",
        title="KYC conversion",
        summary="Track identity verification conversion, support friction, and risk controls.",
        question="What changed in KYC conversion and what should product review this week?",
        source_ids=["jira", "socure", "posthog"],
        generator_slug="risk-brd",
        owner="Product Ops",
        status="in_review",
    )
    _ensure_topic(
        session,
        topic_id="onboarding-readiness",
        title="Onboarding readiness",
        summary="Prepare launch readiness across product analytics, tickets, and specs.",
        question="What launch risks are unresolved for onboarding this sprint?",
        source_ids=["jira", "confluence", "posthog"],
        generator_slug="technical-prd",
        owner="PM Lead",
        status="discovery",
    )

    approved = _ensure_round_and_output(
        session,
        skill_id="meeting_summary",
        label="demo:weekly-kyc-brief",
        generated_text=(
            "# Summary\nKYC completion recovered after retry copy changes.\n"
            "# Decisions\nKeep manual review controls active through Friday.\n"
            "# Next actions\nProduct Ops will review Socure fallout with support."
        ),
        criteria={
            "workflow_slug": "weekly-brief",
            "workflow_title": "Weekly PM Brief",
            "topic_id": "kyc-conversion",
            "source_id": "socure",
            "has_output": True,
            "citation_count": 2,
            "meets_min_citations": True,
            "has_required_sections": True,
            "scope_declared": True,
            "has_review_checklist": True,
            "review_checklist_resolved": True,
        },
        pass_fail="pass",
        confidence="0.910",
        export_readiness="0.890",
        freshness="0.920",
    )
    rejected = _ensure_round_and_output(
        session,
        skill_id="support_agent",
        label="demo:thin-risk-brd",
        generated_text="KYC risk changed. Hold launch.",
        criteria={
            "workflow_slug": "risk-brd",
            "workflow_title": "Risk BRD",
            "topic_id": "kyc-conversion",
            "source_id": "socure",
            "has_output": True,
            "citation_count": 0,
            "meets_min_citations": False,
            "has_required_sections": False,
            "scope_declared": True,
            "has_review_checklist": False,
            "review_checklist_resolved": False,
        },
        pass_fail="fail",
        confidence="0.330",
        export_readiness="0.210",
        freshness="0.200",
    )
    needs_review = _ensure_round_and_output(
        session,
        skill_id="agent_system_prompt",
        label="demo:onboarding-technical-prd",
        generated_text=(
            "# Problem\nOnboarding drop-off increased on retry.\n"
            "# Requirements\nClarify retries, telemetry, and support fallback.\n"
            "# Rollout\nPilot to 10% after analytics owner approval."
        ),
        criteria={
            "workflow_slug": "technical-prd",
            "workflow_title": "Technical PRD",
            "topic_id": "onboarding-readiness",
            "source_id": "jira",
            "has_output": True,
            "citation_count": 1,
            "meets_min_citations": True,
            "has_required_sections": True,
            "scope_declared": True,
            "has_review_checklist": False,
            "review_checklist_resolved": False,
        },
        pass_fail="fail",
        confidence="0.620",
        export_readiness="0.510",
        freshness="0.740",
    )

    prompt = _prompt(session, "meeting_summary")
    if not session.scalar(select(PublishLog).where(PublishLog.output_id == approved.output_id)):
        session.add(
            PublishLog(
                skill_id="meeting_summary",
                prompt_version_id=prompt.prompt_version_id,
                output_id=approved.output_id,
                destination="return-only",
                destination_ref=None,
                decision="published",
                reason="demo publish receipt",
            )
        )
    if not session.scalar(select(ArtifactFeedback).where(ArtifactFeedback.output_id == approved.output_id)):
        feedback = ArtifactFeedback(
            output_id=approved.output_id,
            reviewer_id="demo-reviewer",
            outcome="approved",
            reason="decision_ready",
            notes="Good evidence receipt and clear next action.",
            final_text_hash=hash_text(approved.generated_text) or "",
            metadata_json={"demo": True},
        )
        session.add(feedback)
        session.flush()
        gold = GoldExample(
            workspace_id="default",
            skill_id="meeting_summary",
            scenario_type="demo-approved-weekly-brief",
            input_context_json={"text": approved.test_input_label, "topic_id": "kyc-conversion"},
            output_text=approved.generated_text,
            prompt_version_id=prompt.prompt_version_id,
            role="exemplar",
            expected_pass_criteria={"feedback_id": feedback.feedback_id},
        )
        session.add(gold)
        session.flush()
        feedback.gold_id = gold.gold_id
    if not session.scalar(select(ArtifactFeedback).where(ArtifactFeedback.output_id == rejected.output_id)):
        session.add(
            ArtifactFeedback(
                output_id=rejected.output_id,
                reviewer_id="demo-reviewer",
                outcome="rejected",
                reason="missing_required_sections",
                notes="Thin cited response should not look publishable.",
                final_text_hash=hash_text(rejected.generated_text) or "",
                metadata_json={"demo": True},
            )
        )
    if not session.scalar(select(ProductionOutcome).where(ProductionOutcome.output_id == approved.output_id)):
        session.add(
            ProductionOutcome(
                output_id=approved.output_id,
                outcome="used_in_decision",
                actor_id="demo-product-lead",
                notes="Used to prepare the weekly product/risk readout.",
                final_text_hash=hash_text(approved.generated_text),
                metadata_json={"demo": True, "decision": "keep controls active"},
            )
        )
    if not session.scalar(
        select(LearningProposal)
        .where(
            LearningProposal.skill_id == "support_agent",
            LearningProposal.cluster_key == "missing_section:required_sections",
        )
        .limit(1)
    ):
        session.add(
            LearningProposal(
                skill_id="support_agent",
                prompt_version_id=_prompt(session, "support_agent").prompt_version_id,
                cluster_key="missing_section:required_sections",
                title="Improve missing section coverage",
                rationale=(
                    "Demo risk BRD failures are missing required sections and review checklist detail."
                ),
                proposed_prompt_patch=(
                    "Before finalizing a risk BRD, verify Risk context, Evidence, Policy decision, "
                    "Controls, and Open questions are present with cited substance."
                ),
                status="draft",
                source_failure_count=2,
                evidence_json={
                    "output_ids": [rejected.output_id, needs_review.output_id],
                    "workflow_slugs": ["risk-brd", "technical-prd"],
                },
            )
        )
    if not session.scalar(select(ReplaySchedule).where(ReplaySchedule.replay_type == "gold").limit(1)):
        session.add(
            ReplaySchedule(
                replay_type="gold",
                skill_id="meeting_summary",
                prompt_version_id=prompt.prompt_version_id,
                cadence_days=7,
                next_run_at=datetime.now(timezone.utc) + timedelta(days=1),
                is_active=True,
                created_by="demo-seed",
                payload_json={"demo": True},
            )
        )
    add_audit_event(
        session,
        category="configuration",
        action="demo_seed",
        outcome="success",
        target_type="demo_data",
        target_id="default",
        metadata={
            "topics": ["kyc-conversion", "onboarding-readiness"],
            "outputs": [
                approved.output_id,
                rejected.output_id,
                needs_review.output_id,
            ],
        },
    )
    session.commit()
    return {
        "topics": 2,
        "outputs": 3,
        "feedback": 2,
        "production_outcomes": 1,
        "learning_proposals": 1,
        "replay_schedules": 1,
    }
