"""Operational readiness checks for DreamFi setup and production monitoring."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from typing import Any

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from dreamfi.config import get_settings
from dreamfi.connectors import (
    CONNECTORS,
    REQUIRED_METADATA_KEYS,
    connector_document_set_aliases,
    normalize_document_set_name,
)
from dreamfi.db.models import AuditEvent, ReplayRun, ReplaySchedule
from dreamfi.onyx.client import OnyxClient
from dreamfi.onyx.errors import OnyxError


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def environment_readiness() -> dict[str, Any]:
    settings = get_settings()
    database_url = settings.resolved_database_url
    uses_sqlite = database_url.startswith("sqlite")
    database_configured = bool(settings.database_url or settings.pg_host) and not uses_sqlite
    placeholders = {"change-me-before-deploy", "onyx_pat_XXX", "sk-ant-XXX"}

    def is_placeholder(value: str | None) -> bool:
        return bool(value) and value in placeholders

    def has_explicit_env(*names: str) -> bool:
        return any(os.getenv(name) for name in names)

    onyx_url = settings.onyx_base_url.strip()
    onyx_host = (urlparse(onyx_url).hostname or "").lower()
    running_on_railway = bool(
        os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_ENVIRONMENT_NAME")
    )
    onyx_base_configured = bool(onyx_url) and (
        not running_on_railway
        or (
            has_explicit_env("ONYX_BASE_URL")
            and onyx_host not in {"localhost", "127.0.0.1", "::1"}
        )
    )
    onyx_key_configured = bool(settings.onyx_api_key) and not is_placeholder(
        settings.onyx_api_key
    )
    auth_secret_configured = any(
        secret and not is_placeholder(secret)
        for secret in (settings.dreamfi_api_token, settings.dreamfi_auth_password)
    )
    auth_configured = not settings.dreamfi_auth_enabled or auth_secret_configured
    required: list[dict[str, Any]] = [
        {
            "name": "DATABASE_URL",
            "present": bool(settings.database_url or settings.pg_host),
            "configured": database_configured,
            "detail": (
                "Persistent Postgres is configured."
                if database_configured
                else "Set production DATABASE_URL/PG* to persistent Postgres."
            ),
        },
        {
            "name": "ONYX_BASE_URL",
            "present": bool(settings.onyx_base_url),
            "configured": onyx_base_configured,
            "detail": settings.onyx_base_url,
        },
        {
            "name": "ONYX_API_KEY",
            "present": bool(settings.onyx_api_key),
            "configured": onyx_key_configured,
            "detail": "required for live Onyx setup",
        },
        {
            "name": "DREAMFI_AUTH",
            "present": bool(settings.dreamfi_api_token or settings.dreamfi_auth_password),
            "configured": auth_configured,
            "detail": "Basic auth or bearer token must be configured when auth is enabled.",
        },
    ]
    placeholder_values = {
        "DREAMFI_AUTH_PASSWORD": settings.dreamfi_auth_password,
        "DREAMFI_API_TOKEN": settings.dreamfi_api_token,
        "ONYX_API_KEY": settings.onyx_api_key,
    }
    placeholder_hits = sorted(
        key
        for key, value in placeholder_values.items()
        if value in placeholders
    )
    return {
        "checks": required,
        "placeholder_values": placeholder_hits,
        "ready": all(bool(item["configured"]) for item in required) and not placeholder_hits,
    }


def database_readiness(session: Session) -> dict[str, Any]:
    try:
        session.execute(text("select 1")).scalar_one()
        try:
            version = session.execute(text("select version_num from alembic_version")).scalar()
        except SQLAlchemyError:
            version = None
        return {
            "status": "ok",
            "alembic_version": version,
        }
    except SQLAlchemyError as exc:
        return {
            "status": "error",
            "reason": type(exc).__name__,
        }


def bootstrap_connector_document_sets(
    *,
    onyx: OnyxClient,
    apply: bool,
) -> list[dict[str, Any]]:
    document_sets = onyx.list_document_sets()
    document_sets_by_name = {
        normalize_document_set_name(document_set.name): document_set
        for document_set in document_sets
    }
    rows: list[dict[str, Any]] = []
    for connector in CONNECTORS:
        existing = document_sets_by_name.get(
            normalize_document_set_name(connector.expected_document_set)
        )
        created = False
        if existing is None and apply:
            existing = onyx.create_document_set(
                name=connector.expected_document_set,
                description=(
                    f"DreamFi source evidence for {connector.name}. "
                    f"Documents should include metadata keys: {', '.join(REQUIRED_METADATA_KEYS)}."
                ),
            )
            created = True
        rows.append(
            {
                "connector_id": connector.connector_id,
                "name": connector.name,
                "expected_document_set": connector.expected_document_set,
                "document_set_id": existing.id if existing is not None else None,
                "exists": existing is not None,
                "created": created,
                "metadata_keys": list(REQUIRED_METADATA_KEYS),
            }
        )
    return rows


def connector_readiness(
    *,
    onyx: OnyxClient,
    probe_search: bool = True,
) -> dict[str, Any]:
    settings = get_settings()
    try:
        document_sets = onyx.list_document_sets()
    except (OnyxError, httpx.HTTPError) as exc:
        return {
            "status": "error",
            "reason": type(exc).__name__,
            "connectors": [
                {
                    "connector_id": connector.connector_id,
                    "name": connector.name,
                    "expected_document_set": connector.expected_document_set,
                    "status": "degraded",
                    "document_set_present": False,
                    "retrieval_status": "not_checked",
                }
                for connector in CONNECTORS
            ],
        }

    document_set_names = {
        normalize_document_set_name(document_set.name)
        for document_set in document_sets
    }
    rows: list[dict[str, Any]] = []
    for connector in CONNECTORS:
        aliases = {
            normalize_document_set_name(alias)
            for alias in connector_document_set_aliases(connector)
        }
        document_set_present = bool(aliases & document_set_names)
        retrieval_status = "not_checked"
        freshest_document_at: str | None = None
        if document_set_present and probe_search:
            try:
                hits = onyx.admin_search(
                    query=f"{connector.name} latest DreamFi evidence",
                    filters={"dreamfi_scope": {"source_ids": [connector.connector_id]}},
                    limit=settings.dreamfi_connector_probe_search_limit,
                )
            except (OnyxError, httpx.HTTPError):
                retrieval_status = "error"
            else:
                updated_ats = [hit.updated_at for hit in hits if hit.updated_at is not None]
                if not hits:
                    retrieval_status = "empty"
                elif not updated_ats:
                    retrieval_status = "missing_freshness"
                else:
                    freshest = max(_as_utc(value) for value in updated_ats)
                    freshest_document_at = freshest.isoformat()
                    stale_after = timedelta(days=settings.dreamfi_connector_stale_after_days)
                    retrieval_status = (
                        "fresh"
                        if freshest >= datetime.now(timezone.utc) - stale_after
                        else "stale"
                    )

        status = "connected" if retrieval_status == "fresh" else "degraded"
        if not document_set_present:
            status = "not_configured"
        elif not probe_search:
            status = "available"
        rows.append(
            {
                "connector_id": connector.connector_id,
                "name": connector.name,
                "category": connector.category,
                "expected_document_set": connector.expected_document_set,
                "document_set_present": document_set_present,
                "retrieval_status": retrieval_status,
                "freshest_document_at": freshest_document_at,
                "status": status,
                "metadata_keys": list(REQUIRED_METADATA_KEYS),
            }
        )
    counts: dict[str, int] = {}
    for row in rows:
        status_value = str(row["status"])
        counts[status_value] = counts.get(status_value, 0) + 1
    return {
        "status": "ok",
        "counts": dict(sorted(counts.items())),
        "connectors": rows,
    }


def replay_readiness(session: Session) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    due_count = session.scalar(
        select(func.count())
        .select_from(ReplaySchedule)
        .where(
            ReplaySchedule.is_active.is_(True),
            ReplaySchedule.next_run_at <= now,
        )
    )
    error_count = session.scalar(
        select(func.count())
        .select_from(ReplayRun)
        .where(
            ReplayRun.status == "error",
            ReplayRun.started_at >= since,
        )
    )
    latest_run = session.scalar(
        select(ReplayRun).order_by(ReplayRun.started_at.desc()).limit(1)
    )
    return {
        "due_schedule_count": int(due_count or 0),
        "error_count_24h": int(error_count or 0),
        "latest_run": (
            {
                "replay_run_id": latest_run.replay_run_id,
                "status": latest_run.status,
                "started_at": latest_run.started_at.isoformat(),
                "completed_at": latest_run.completed_at.isoformat()
                if latest_run.completed_at
                else None,
                "reason": latest_run.reason,
            }
            if latest_run is not None
            else None
        ),
    }


def audit_readiness(session: Session) -> dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    latest_event = session.scalar(
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(1)
    )
    event_count = session.scalar(select(func.count()).select_from(AuditEvent))
    api_error_count = session.scalar(
        select(func.count())
        .select_from(AuditEvent)
        .where(
            AuditEvent.category == "access",
            AuditEvent.outcome.in_(("failure", "error")),
            AuditEvent.created_at >= since,
        )
    )
    audit_write_failure_count = session.scalar(
        select(func.count())
        .select_from(AuditEvent)
        .where(
            AuditEvent.category == "audit",
            AuditEvent.outcome.in_(("failure", "error")),
            AuditEvent.created_at >= since,
        )
    )
    return {
        "enabled": get_settings().dreamfi_audit_enabled,
        "event_count": int(event_count or 0),
        "api_error_count_24h": int(api_error_count or 0),
        "audit_failure_count_24h": int(audit_write_failure_count or 0),
        "latest_event": (
            {
                "event_id": latest_event.event_id,
                "event_type": latest_event.event_type,
                "outcome": latest_event.outcome,
                "created_at": latest_event.created_at.isoformat(),
            }
            if latest_event is not None
            else None
        ),
    }


def ops_status(session: Session, onyx: OnyxClient) -> dict[str, Any]:
    environment = environment_readiness()
    database = database_readiness(session)
    onyx_status = onyx.ping()
    connectors = (
        connector_readiness(onyx=onyx)
        if onyx_status == "reachable"
        else {"status": "error", "reason": "onyx_unreachable", "connectors": []}
    )
    replays = replay_readiness(session)
    audit = audit_readiness(session)
    failures = []
    if database["status"] != "ok":
        failures.append("database")
    if onyx_status != "reachable":
        failures.append("onyx")
    if connectors.get("counts", {}).get("degraded") or connectors.get("counts", {}).get("not_configured"):
        failures.append("connectors")
    if replays["error_count_24h"]:
        failures.append("replay")
    if audit["audit_failure_count_24h"]:
        failures.append("audit")
    if not environment["ready"]:
        failures.append("environment")
    return {
        "status": "ok" if not failures else "degraded",
        "failures": failures,
        "environment": environment,
        "database": database,
        "onyx": {"status": onyx_status},
        "connectors": connectors,
        "replays": replays,
        "audit": audit,
    }
