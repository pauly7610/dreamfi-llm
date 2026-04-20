"""Minimal operator console (server-rendered Jinja)."""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from dreamfi.api.deps import get_db_session
from dreamfi.db.models import EvalOutput, EvalRound, PromptVersion, PublishLog, Skill

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
FRONTEND_DIST_DIR = REPO_ROOT / "generators" / "web" / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

router = APIRouter()


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
        "artifacts_path": round_row.artifacts_path if round_row is not None else None,
        "latest_publish": _serialize_publish(latest_publish) if latest_publish is not None else None,
    }


def _console_alerts(
    *,
    blocked_count: int,
    publish_ready_count: int,
    needs_review_count: int,
    outputs: Sequence[EvalOutput],
    publishes: Sequence[PublishLog],
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
    publishes: Sequence[PublishLog],
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

    return {
        "headline": "Trust, measured.",
        "summary": {
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
        },
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


@router.get("/api/console")
def console_data(session: Session = Depends(get_db_session)) -> dict[str, Any]:
    return _console_payload(session)


@router.get("/console/assets/{asset_path:path}")
def console_asset(asset_path: str) -> FileResponse:
    return FileResponse(_resolve_asset_path(asset_path))


@router.get("/console", response_class=HTMLResponse)
@router.get("/console/{path:path}", response_class=HTMLResponse)
def console(path: str = "", session: Session = Depends(get_db_session)) -> HTMLResponse:
    index_html = _frontend_index_html()
    if index_html is not None:
        return HTMLResponse(index_html)
    return _legacy_console(session)
