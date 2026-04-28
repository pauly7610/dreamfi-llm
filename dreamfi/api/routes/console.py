"""Minimal operator console (server-rendered Jinja)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from dreamfi.api.deps import get_db_session
from dreamfi.config import get_settings
from dreamfi.db.models import ConsoleTopic, EvalOutput, EvalRound, PromptVersion, PublishLog, Skill

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
FRONTEND_DIST_DIR = REPO_ROOT / "generators" / "web" / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
FRONTEND_PUBLIC_DIR = REPO_ROOT / "generators" / "web" / "public"
LLMS_TXT_PATH = REPO_ROOT / "llms.txt"
TOPIC_GENERATOR_SLUGS = {"weekly-brief", "technical-prd", "business-prd", "risk-brd"}
TOPIC_STATUSES = {"discovery", "in_review", "ready", "blocked", "done"}
_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

router = APIRouter()


def _normalize_topic_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-") or "new-topic"


def _next_topic_id(session: Session, preferred_topic_id: str) -> str:
    existing_ids = set(session.scalars(select(ConsoleTopic.topic_id)).all())
    topic_id = _normalize_topic_id(preferred_topic_id)
    if topic_id not in existing_ids:
        return topic_id

    suffix = 2
    while f"{topic_id}-{suffix}" in existing_ids:
        suffix += 1
    return f"{topic_id}-{suffix}"


def _valid_integration_ids() -> set[str]:
    return {str(integration["id"]) for integration in _integrations()}


def _serialize_console_topic(topic: ConsoleTopic) -> dict[str, object]:
    target_decision_at = topic.target_decision_at
    if target_decision_at is not None and target_decision_at.tzinfo is None:
        target_decision_at = target_decision_at.replace(tzinfo=timezone.utc)
    return {
        "id": topic.topic_id,
        "title": topic.title,
        "summary": topic.summary,
        "question": topic.question,
        "owner": topic.owner,
        "status": topic.status,
        "target_decision_at": target_decision_at.isoformat() if target_decision_at else None,
        "source_ids": list(topic.source_ids_json),
        "default_generator_slug": topic.default_generator_slug,
        "created_at": topic.created_at.isoformat(),
    }


def _serialize_console_topics(session: Session) -> list[dict[str, object]]:
    topics = session.scalars(
        select(ConsoleTopic).order_by(desc(ConsoleTopic.created_at))
    ).all()
    return [_serialize_console_topic(topic) for topic in topics]


def _coerce_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be a string",
        )
    normalized_value = value.strip()
    if not normalized_value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} is required",
        )
    return normalized_value


def _normalize_source_ids(value: Any) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="source_ids must be a list of connector ids",
        )

    normalized_source_ids = list(dict.fromkeys(item.strip() for item in value if item.strip()))
    if not normalized_source_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="source_ids must include at least one connector id",
        )

    valid_source_ids = _valid_integration_ids()
    invalid_source_ids = [source_id for source_id in normalized_source_ids if source_id not in valid_source_ids]
    if invalid_source_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unknown connector ids: {', '.join(invalid_source_ids)}",
        )

    return normalized_source_ids


def _normalize_default_generator_slug(value: Any) -> str:
    if value is None:
        return "weekly-brief"
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="default_generator_slug must be a string",
        )
    normalized_slug = value.strip() or "weekly-brief"
    if normalized_slug not in TOPIC_GENERATOR_SLUGS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="default_generator_slug is not supported",
        )
    return normalized_slug


def _normalize_topic_status(value: Any) -> str:
    if value is None:
        return "discovery"
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="status must be a string",
        )
    normalized = value.strip().lower() or "discovery"
    if normalized not in TOPIC_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"status must be one of: {', '.join(sorted(TOPIC_STATUSES))}",
        )
    return normalized


def _normalize_topic_owner(value: Any) -> str:
    if value is None:
        return "unassigned"
    return _coerce_string(value, field_name="owner")


def _normalize_topic_decision_date(value: Any) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="target_decision_at must be an ISO datetime string",
        )
    parsed = _parse_created_at(value)
    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="target_decision_at must be an ISO datetime string",
        )
    return parsed


def _serialize_round(round_row: EvalRound) -> dict[str, object]:
    return {
        "round_id": round_row.round_id,
        "prompt_version_id": round_row.prompt_version_id,
        "score": float(round_row.score),
        "previous_score": float(round_row.previous_score) if round_row.previous_score is not None else None,
        "improvement": float(round_row.improvement) if round_row.improvement is not None else None,
        "completed_at": round_row.completed_at.isoformat() if round_row.completed_at else None,
        "artifacts_path": round_row.artifacts_path,
    }


def _serialize_publish(log: PublishLog) -> dict[str, object]:
    return {
        "publish_id": log.publish_id,
        "skill_id": log.skill_id,
        "destination": log.destination,
        "destination_ref": log.destination_ref,
        "decision": log.decision,
        "reason": log.reason,
        "created_at": log.created_at.isoformat(),
    }


def _artifact_status(output: EvalOutput, latest_publish: PublishLog | None) -> str:
    if latest_publish is not None and latest_publish.decision == "published":
        return "published"
    if output.pass_fail != "pass":
        return "blocked"
    if output.export_readiness is not None and float(output.export_readiness) >= 0.8:
        return "publish_ready"
    return "needs_review"


def _serialize_artifact(
    output: EvalOutput,
    round_row: EvalRound | None,
    skill: Skill | None,
    latest_publish: PublishLog | None,
) -> dict[str, object]:
    return {
        "output_id": output.output_id,
        "skill_id": skill.skill_id if skill is not None else None,
        "skill_display_name": skill.display_name if skill is not None else None,
        "round_id": output.round_id,
        "test_input_label": output.test_input_label,
        "attempt": output.attempt,
        "pass_fail": output.pass_fail,
        "confidence": float(output.confidence) if output.confidence is not None else None,
        "export_readiness": float(output.export_readiness) if output.export_readiness is not None else None,
        "created_at": output.created_at.isoformat(),
        "status": _artifact_status(output, latest_publish),
        "policy_checks": _policy_checks(output, latest_publish),
        "artifacts_path": round_row.artifacts_path if round_row is not None else None,
        "latest_publish": _serialize_publish(latest_publish) if latest_publish is not None else None,
    }


def _policy_checks(output: EvalOutput, latest_publish: PublishLog | None) -> dict[str, object]:
    settings = get_settings()
    confidence = float(output.confidence) if output.confidence is not None else None
    checks = [
        {
            "name": "hard_gate",
            "passed": output.pass_fail == "pass",
            "detail": "pass_fail must be pass",
        },
        {
            "name": "confidence_threshold",
            "passed": confidence is not None and confidence >= settings.dreamfi_confidence_threshold,
            "detail": (
                f"confidence={confidence:.3f} threshold={settings.dreamfi_confidence_threshold:.3f}"
                if confidence is not None
                else "confidence missing"
            ),
        },
        {
            "name": "export_readiness",
            "passed": output.export_readiness is not None and float(output.export_readiness) >= 0.8,
            "detail": (
                f"export_readiness={float(output.export_readiness):.3f} threshold=0.800"
                if output.export_readiness is not None
                else "export_readiness missing"
            ),
        },
    ]
    if latest_publish is not None:
        checks.append(
            {
                "name": "publish_attempt",
                "passed": latest_publish.decision == "published",
                "detail": latest_publish.reason or latest_publish.decision,
            }
        )
    return {"checks": checks}


def _console_alerts(
    *,
    blocked_count: int,
    publish_ready_count: int,
    needs_review_count: int,
    outputs: list[EvalOutput],
    publishes: list[PublishLog],
) -> list[dict[str, object]]:
    alerts: list[dict[str, object]] = []
    if blocked_count:
        alerts.append(
            {
                "id": "blocked-artifacts",
                "severity": "critical",
                "title": "Blocked artifacts need review",
                "message": f"{blocked_count} recent artifacts are currently blocked by trust gates.",
                "href": "/console/review?status=blocked",
                "created_at": outputs[0].created_at.isoformat() if outputs else None,
            }
        )
    if needs_review_count:
        alerts.append(
            {
                "id": "needs-review",
                "severity": "warning",
                "title": "Artifacts waiting on operator review",
                "message": f"{needs_review_count} recent artifacts need review before they are safe to move forward.",
                "href": "/console/review?status=needs_review",
                "created_at": outputs[0].created_at.isoformat() if outputs else None,
            }
        )
    if publish_ready_count:
        alerts.append(
            {
                "id": "publish-ready",
                "severity": "info",
                "title": "Artifacts are ready to publish",
                "message": f"{publish_ready_count} recent artifacts appear ready for publish approval.",
                "href": "/console/artifacts?status=publish_ready",
                "created_at": outputs[0].created_at.isoformat() if outputs else None,
            }
        )
    latest_blocked_publish = next((log for log in publishes if log.decision != "published"), None)
    if latest_blocked_publish is not None:
        alerts.append(
            {
                "id": f"publish-{latest_blocked_publish.publish_id}",
                "severity": "warning",
                "title": "Recent publish attempt was blocked",
                "message": latest_blocked_publish.reason or "A recent publish attempt failed policy checks.",
                "href": "/console/publish",
                "created_at": latest_blocked_publish.created_at.isoformat(),
            }
        )
    return alerts[:4]


def _quick_actions() -> list[dict[str, str]]:
    return [
        {
            "id": "weekly-brief",
            "label": "Run weekly PM brief",
            "href": "/console/generate/weekly-brief",
            "kind": "primary",
        },
        {
            "id": "technical-prd",
            "label": "Create Technical PRD",
            "href": "/console/generate/technical-prd",
            "kind": "secondary",
        },
        {
            "id": "business-prd",
            "label": "Create Business PRD",
            "href": "/console/generate/business-prd",
            "kind": "secondary",
        },
        {
            "id": "risk-brd",
            "label": "Create Risk BRD",
            "href": "/console/generate/risk-brd",
            "kind": "secondary",
        },
        {
            "id": "review-blocked",
            "label": "Review blocked artifacts",
            "href": "/console/review?status=blocked",
            "kind": "secondary",
        },
        {
            "id": "trust-dashboard",
            "label": "Open trust dashboard",
            "href": "/console/trust",
            "kind": "secondary",
        },
    ]


def _integrations() -> list[dict[str, object]]:
    return [
        {
            "id": "jira",
            "name": "Jira",
            "category": "planning",
            "purpose": "Sprints, issues, and delivery state",
            "used_for": ["weekly-brief", "technical-prd", "risk-brd"],
            "status": "available",
            "href": "/console/integrations/jira",
        },
        {
            "id": "dragonboat",
            "name": "Dragonboat",
            "category": "planning",
            "purpose": "Roadmap, initiatives, and OKR alignment",
            "used_for": ["business-prd", "weekly-brief"],
            "status": "available",
            "href": "/console/integrations/dragonboat",
        },
        {
            "id": "confluence",
            "name": "Confluence",
            "category": "docs",
            "purpose": "Source docs and publish target for PRDs and specs",
            "used_for": ["technical-prd", "business-prd", "risk-brd"],
            "status": "available",
            "href": "/console/integrations/confluence",
        },
        {
            "id": "metabase",
            "name": "Metabase",
            "category": "metrics",
            "purpose": "SQL-backed KPI and funnel dashboards",
            "used_for": ["weekly-brief", "business-prd"],
            "status": "available",
            "href": "/console/integrations/metabase",
        },
        {
            "id": "posthog",
            "name": "PostHog",
            "category": "product_analytics",
            "purpose": "Product events, funnels, and session data",
            "used_for": ["weekly-brief", "technical-prd"],
            "status": "available",
            "href": "/console/integrations/posthog",
        },
        {
            "id": "ga",
            "name": "Google Analytics",
            "category": "marketing_analytics",
            "purpose": "Acquisition, traffic, and conversion signals",
            "used_for": ["business-prd"],
            "status": "available",
            "href": "/console/integrations/ga",
        },
        {
            "id": "klaviyo",
            "name": "Klaviyo",
            "category": "marketing",
            "purpose": "Lifecycle campaigns, audiences, and sends",
            "used_for": ["business-prd"],
            "status": "available",
            "href": "/console/integrations/klaviyo",
        },
        {
            "id": "netxd",
            "name": "NetXD",
            "category": "payments",
            "purpose": "Payments and ledger transaction context",
            "used_for": ["risk-brd", "technical-prd"],
            "status": "available",
            "href": "/console/integrations/netxd",
        },
        {
            "id": "sardine",
            "name": "Sardine",
            "category": "risk",
            "purpose": "Fraud and risk signal enrichment",
            "used_for": ["risk-brd"],
            "status": "available",
            "href": "/console/integrations/sardine",
        },
        {
            "id": "socure",
            "name": "Socure",
            "category": "identity",
            "purpose": "Identity verification and KYC signals",
            "used_for": ["risk-brd"],
            "status": "available",
            "href": "/console/integrations/socure",
        },
    ]


def _domain_health(
    *,
    average_latest_score: float | None,
    average_confidence: float | None,
    average_export_readiness: float | None,
    hard_gate_pass_rate: float | None,
    publish_success_rate: float | None,
    blocked_count: int,
    needs_review_count: int,
    publishes: list[PublishLog],
) -> list[dict[str, object]]:
    blocked_publish_count = sum(1 for log in publishes if log.decision != "published")
    return [
        {
            "domain": "planning",
            "trust_score": average_export_readiness,
            "pass_rate": hard_gate_pass_rate,
            "issue_count": needs_review_count,
        },
        {
            "domain": "metrics",
            "trust_score": average_confidence,
            "pass_rate": hard_gate_pass_rate,
            "issue_count": blocked_count,
        },
        {
            "domain": "generation",
            "trust_score": average_latest_score,
            "pass_rate": hard_gate_pass_rate,
            "issue_count": blocked_count + needs_review_count,
        },
        {
            "domain": "publish",
            "trust_score": average_export_readiness,
            "pass_rate": publish_success_rate,
            "issue_count": blocked_publish_count,
        },
    ]


def _parse_created_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _bucket_days(days: int) -> str:
    return f"{days}d"


def _historical_metrics(
    outputs: list[EvalOutput],
    publishes: list[PublishLog],
    *,
    now: datetime | None = None,
) -> dict[str, dict[str, float | int | None]]:
    ref = now or datetime.now(timezone.utc)
    windows = [7, 30, 90]
    rows: dict[str, dict[str, float | int | None]] = {}
    for days in windows:
        start = ref - timedelta(days=days)
        window_outputs = [row for row in outputs if _as_utc(row.created_at) >= start]
        window_publishes = [row for row in publishes if _as_utc(row.created_at) >= start]
        output_count = len(window_outputs)
        pass_count = sum(1 for row in window_outputs if row.pass_fail == "pass")
        blocked_count = sum(1 for row in window_outputs if row.pass_fail != "pass")
        published_count = sum(1 for row in window_publishes if row.decision == "published")
        rows[_bucket_days(days)] = {
            "output_count": output_count,
            "pass_rate": round(pass_count / output_count, 3) if output_count else None,
            "blocked_rate": round(blocked_count / output_count, 3) if output_count else None,
            "publish_success_rate": (
                round(published_count / len(window_publishes), 3) if window_publishes else None
            ),
        }
    return rows


def _confidence_calibration(outputs: list[EvalOutput]) -> list[dict[str, object]]:
    bins = [(0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 0.9), (0.9, 1.01)]
    rows: list[dict[str, object]] = []
    for start, end in bins:
        bucket = [
            row
            for row in outputs
            if row.confidence is not None and start <= float(row.confidence) < end
        ]
        count = len(bucket)
        pass_rate = sum(1 for row in bucket if row.pass_fail == "pass") / count if count else None
        rows.append(
            {
                "bucket": f"{start:.2f}-{min(end, 1.0):.2f}",
                "count": count,
                "observed_pass_rate": round(pass_rate, 3) if pass_rate is not None else None,
            }
        )
    return rows


def _failure_clusters(outputs: list[EvalOutput]) -> list[dict[str, object]]:
    clusters: dict[str, dict[str, object]] = {}
    for output in outputs:
        if output.pass_fail == "pass":
            continue
        criteria = output.criteria_json if isinstance(output.criteria_json, dict) else {}
        failed = sorted(
            key
            for key, value in criteria.items()
            if value is False or value in {"fail", "failed", "false"}
        )
        cluster_key = ",".join(failed) if failed else "unclassified"
        record = clusters.setdefault(
            cluster_key,
            {
                "cluster_id": cluster_key,
                "count": 0,
                "sample_output_ids": [],
                "recommended_action": (
                    "Review failed criteria and add targeted prompt instructions."
                    if failed
                    else "Add richer eval criteria diagnostics for failed outputs."
                ),
            },
        )
        record["count"] = int(record["count"]) + 1
        if len(record["sample_output_ids"]) < 3:
            record["sample_output_ids"].append(output.output_id)
    return sorted(clusters.values(), key=lambda row: int(row["count"]), reverse=True)


def _slo_status(summary: dict[str, float | int | None]) -> dict[str, object]:
    settings = get_settings()
    hard_gate = summary.get("hard_gate_pass_rate")
    blocked = summary.get("blocked_artifact_count")
    total = (summary.get("blocked_artifact_count") or 0) + (summary.get("publish_ready_count") or 0) + (
        summary.get("published_artifact_count") or 0
    ) + (summary.get("needs_review_count") or 0)
    blocked_rate = (float(blocked) / float(total)) if total else None
    publish_success = summary.get("publish_success_rate")
    checks = [
        {
            "name": "hard_gate_pass_rate",
            "target": settings.dreamfi_slo_hard_gate_pass_rate,
            "actual": hard_gate,
            "met": hard_gate is not None and float(hard_gate) >= settings.dreamfi_slo_hard_gate_pass_rate,
        },
        {
            "name": "blocked_rate",
            "target": settings.dreamfi_slo_blocked_rate,
            "actual": round(blocked_rate, 3) if blocked_rate is not None else None,
            "met": blocked_rate is not None and blocked_rate <= settings.dreamfi_slo_blocked_rate,
        },
        {
            "name": "publish_success_rate",
            "target": settings.dreamfi_slo_publish_success_rate,
            "actual": publish_success,
            "met": publish_success is not None and float(publish_success) >= settings.dreamfi_slo_publish_success_rate,
        },
    ]
    return {
        "checks": checks,
        "all_met": all(bool(item["met"]) for item in checks),
    }


def _console_payload(session: Session) -> dict[str, Any]:
    skills = session.scalars(select(Skill).order_by(Skill.skill_id)).all()
    active_prompt_versions = session.scalars(
        select(PromptVersion).where(PromptVersion.is_active.is_(True))
    ).all()
    active_by_skill = {prompt.skill_id: prompt for prompt in active_prompt_versions}

    outputs = session.scalars(
        select(EvalOutput).order_by(desc(EvalOutput.created_at)).limit(50)
    ).all()
    publishes = session.scalars(
        select(PublishLog).order_by(desc(PublishLog.created_at)).limit(10)
    ).all()
    publish_log_rows = session.scalars(
        select(PublishLog).order_by(desc(PublishLog.created_at)).limit(50)
    ).all()

    round_ids = list({output.round_id for output in outputs})
    rounds = session.scalars(
        select(EvalRound).where(EvalRound.round_id.in_(round_ids))
    ).all() if round_ids else []
    round_by_id = {round_row.round_id: round_row for round_row in rounds}
    skill_by_id = {skill.skill_id: skill for skill in skills}
    latest_publish_by_output: dict[str, PublishLog] = {}
    for log in publish_log_rows:
        if log.output_id not in latest_publish_by_output:
            latest_publish_by_output[log.output_id] = log

    confidence_values = [float(output.confidence) for output in outputs if output.confidence is not None]
    readiness_values = [
        float(output.export_readiness)
        for output in outputs
        if output.export_readiness is not None
    ]
    pass_count = sum(1 for output in outputs if output.pass_fail == "pass")
    blocked_count = 0
    publish_ready_count = 0
    published_count = 0
    artifact_queue: list[dict[str, object]] = []
    for output in outputs:
        round_row = round_by_id.get(output.round_id)
        skill = skill_by_id.get(round_row.skill_id) if round_row is not None else None
        latest_publish = latest_publish_by_output.get(output.output_id)
        status = _artifact_status(output, latest_publish)
        if status == "blocked":
            blocked_count += 1
        elif status == "publish_ready":
            publish_ready_count += 1
        elif status == "published":
            published_count += 1
        if len(artifact_queue) < 12:
            artifact_queue.append(
                _serialize_artifact(output, round_row, skill, latest_publish)
            )
    needs_review_count = len(outputs) - blocked_count - publish_ready_count - published_count

    latest_scores: list[float] = []
    skill_cards: list[dict[str, object]] = []
    for skill in skills:
        rounds = session.scalars(
            select(EvalRound)
            .where(EvalRound.skill_id == skill.skill_id)
            .order_by(desc(EvalRound.completed_at))
            .limit(5)
        ).all()
        latest_round = rounds[0] if rounds else None
        if latest_round is not None:
            latest_scores.append(float(latest_round.score))
        active_prompt = active_by_skill.get(skill.skill_id)
        skill_cards.append(
            {
                "skill_id": skill.skill_id,
                "display_name": skill.display_name,
                "description": skill.description,
                "criteria_count": len(skill.criteria_json),
                "active_prompt_version": active_prompt.version if active_prompt is not None else None,
                "latest_round": _serialize_round(latest_round) if latest_round is not None else None,
                "recent_rounds": [_serialize_round(round_row) for round_row in rounds],
            }
        )

    publish_total = len(publishes)
    published_total = sum(1 for log in publishes if log.decision == "published")
    summary: dict[str, float | int | None] = {
        "skill_count": len(skills),
        "active_prompt_count": len(active_prompt_versions),
        "average_latest_score": round(sum(latest_scores) / len(latest_scores), 3) if latest_scores else None,
        "average_confidence": round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else None,
        "average_export_readiness": round(sum(readiness_values) / len(readiness_values), 3) if readiness_values else None,
        "publish_success_rate": round(published_total / publish_total, 3) if publish_total else None,
        "hard_gate_pass_rate": round(pass_count / len(outputs), 3) if outputs else None,
        "blocked_artifact_count": blocked_count,
        "publish_ready_count": publish_ready_count,
        "published_artifact_count": published_count,
        "needs_review_count": needs_review_count,
    }
    output_ids = {output.output_id for output in outputs}
    recent_publishes = [log for log in publish_log_rows if log.output_id in output_ids]
    return {
        "headline": "Trust, measured.",
        "summary": summary,
        "skills": skill_cards,
        "artifact_queue": artifact_queue,
        "publish_activity": [_serialize_publish(log) for log in publishes],
        "alerts": _console_alerts(
            blocked_count=blocked_count,
            publish_ready_count=publish_ready_count,
            needs_review_count=needs_review_count,
            outputs=outputs,
            publishes=publishes,
        ),
        "quick_actions": _quick_actions(),
        "integrations": _integrations(),
        "custom_topics": _serialize_console_topics(session),
        "historical_metrics": _historical_metrics(outputs, recent_publishes),
        "confidence_calibration": _confidence_calibration(outputs),
        "failure_clusters": _failure_clusters(outputs),
        "slo_status": _slo_status(summary),
        "scenario_packs": [
            {
                "id": "trust-review-drill",
                "title": "Trust review drill",
                "description": "Practice queue triage with blocked and borderline artifacts.",
            },
            {
                "id": "prompt-regression-drill",
                "title": "Prompt regression drill",
                "description": "Run eval rounds and verify promotion eligibility before rollout.",
            },
        ],
        "domain_health": _domain_health(
            average_latest_score=round(sum(latest_scores) / len(latest_scores), 3) if latest_scores else None,
            average_confidence=round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else None,
            average_export_readiness=round(sum(readiness_values) / len(readiness_values), 3) if readiness_values else None,
            hard_gate_pass_rate=round(pass_count / len(outputs), 3) if outputs else None,
            publish_success_rate=round(published_total / publish_total, 3) if publish_total else None,
            blocked_count=blocked_count,
            needs_review_count=needs_review_count,
            publishes=publishes,
        ),
    }


def _legacy_console(session: Session) -> HTMLResponse:
    skills = session.scalars(select(Skill).order_by(Skill.skill_id)).all()
    rounds_by_skill: dict[str, list[dict[str, object]]] = {}
    for skill in skills:
        rounds = session.scalars(
            select(EvalRound)
            .where(EvalRound.skill_id == skill.skill_id)
            .order_by(desc(EvalRound.completed_at))
            .limit(20)
        ).all()
        rounds_by_skill[skill.skill_id] = [
            {
                "round_id": round_row.round_id,
                "score": float(round_row.score),
                "completed_at": (round_row.completed_at.isoformat() if round_row.completed_at else "n/a"),
            }
            for round_row in rounds
        ]
    tpl = _env.get_template("console.html")
    return HTMLResponse(tpl.render(skills=skills, rounds_by_skill=rounds_by_skill))


def _frontend_index_html() -> str | None:
    index_path = FRONTEND_DIST_DIR / "index.html"
    if not index_path.exists():
        return None
    return index_path.read_text(encoding="utf-8")


def _resolve_asset_path(asset_path: str) -> Path:
    candidate = (FRONTEND_ASSETS_DIR / asset_path).resolve()
    try:
        candidate.relative_to(FRONTEND_ASSETS_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="asset not found") from exc
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="asset not found")
    return candidate


def _resolve_public_path(path: str) -> Path:
    candidate = (FRONTEND_PUBLIC_DIR / path).resolve()
    try:
        candidate.relative_to(FRONTEND_PUBLIC_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="asset not found") from exc
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="asset not found")
    return candidate


@router.get("/")
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/console", status_code=307)


@router.get("/api/console")
def console_data(session: Session = Depends(get_db_session)) -> dict[str, Any]:
    return _console_payload(session)


@router.get("/api/console/metrics")
def console_metrics(session: Session = Depends(get_db_session)) -> dict[str, object]:
    payload = _console_payload(session)
    return {
        "summary": payload["summary"],
        "historical_metrics": payload["historical_metrics"],
        "confidence_calibration": payload["confidence_calibration"],
        "slo_status": payload["slo_status"],
    }


@router.get("/api/console/simulator")
def console_simulator(session: Session = Depends(get_db_session)) -> dict[str, object]:
    payload = _console_payload(session)
    return {
        "scenarios": payload["scenario_packs"],
        "failure_clusters": payload["failure_clusters"],
        "sample_queue": payload["artifact_queue"][:5],
    }


@router.post("/api/console/topics", status_code=status.HTTP_201_CREATED)
def create_console_topic(payload: dict[str, Any], session: Session = Depends(get_db_session)) -> dict[str, object]:
    title = _coerce_string(payload.get("title"), field_name="title")
    question = _coerce_string(payload.get("question"), field_name="question")
    summary_value = payload.get("summary")
    if summary_value is None:
        summary = f"Track {title.lower()} across the connected product evidence."
    elif isinstance(summary_value, str):
        summary = summary_value.strip() or f"Track {title.lower()} across the connected product evidence."
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="summary must be a string",
        )

    source_ids = _normalize_source_ids(payload.get("source_ids"))
    default_generator_slug = _normalize_default_generator_slug(payload.get("default_generator_slug"))
    owner = _normalize_topic_owner(payload.get("owner"))
    topic_status = _normalize_topic_status(payload.get("status"))
    target_decision_at = _normalize_topic_decision_date(payload.get("target_decision_at"))
    requested_topic_id = payload.get("id")
    topic_id_seed = requested_topic_id if isinstance(requested_topic_id, str) and requested_topic_id.strip() else title
    topic_id = _next_topic_id(session, topic_id_seed)

    topic = ConsoleTopic(
        topic_id=topic_id,
        title=title,
        summary=summary,
        question=question if question.endswith(("?", "!", ".")) else f"{question}?",
        owner=owner,
        status=topic_status,
        target_decision_at=target_decision_at,
        source_ids_json=source_ids,
        default_generator_slug=default_generator_slug,
    )
    session.add(topic)
    session.commit()
    session.refresh(topic)
    return _serialize_console_topic(topic)


@router.patch("/api/console/topics/{topic_id}")
def update_console_topic(
    topic_id: str,
    payload: dict[str, Any],
    session: Session = Depends(get_db_session),
) -> dict[str, object]:
    topic = session.get(ConsoleTopic, topic_id)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="topic not found")

    if "title" in payload:
        topic.title = _coerce_string(payload.get("title"), field_name="title")
    if "summary" in payload:
        topic.summary = _coerce_string(payload.get("summary"), field_name="summary")
    if "question" in payload:
        question = _coerce_string(payload.get("question"), field_name="question")
        topic.question = question if question.endswith(("?", "!", ".")) else f"{question}?"
    if "owner" in payload:
        topic.owner = _normalize_topic_owner(payload.get("owner"))
    if "status" in payload:
        topic.status = _normalize_topic_status(payload.get("status"))
    if "target_decision_at" in payload:
        topic.target_decision_at = _normalize_topic_decision_date(payload.get("target_decision_at"))
    if "source_ids" in payload:
        topic.source_ids_json = _normalize_source_ids(payload.get("source_ids"))
    if "default_generator_slug" in payload:
        topic.default_generator_slug = _normalize_default_generator_slug(payload.get("default_generator_slug"))

    session.commit()
    session.refresh(topic)
    return _serialize_console_topic(topic)


@router.get("/console/assets/{asset_path:path}")
def console_asset(asset_path: str) -> FileResponse:
    return FileResponse(_resolve_asset_path(asset_path))


@router.get("/favicon.svg")
@router.get("/console/favicon.svg")
def console_favicon() -> FileResponse:
    return FileResponse(_resolve_public_path("favicon.svg"))


@router.get("/llms.txt")
def llms_txt() -> FileResponse:
    if not LLMS_TXT_PATH.exists() or not LLMS_TXT_PATH.is_file():
        raise HTTPException(status_code=404, detail="llms.txt not found")
    return FileResponse(LLMS_TXT_PATH)


@router.get("/console", response_class=HTMLResponse)
@router.get("/console/{path:path}", response_class=HTMLResponse)
def console(path: str = "", session: Session = Depends(get_db_session)) -> HTMLResponse:
    index_html = _frontend_index_html()
    if index_html is not None:
        return HTMLResponse(index_html)
    return _legacy_console(session)
