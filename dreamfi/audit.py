"""Persistent audit event helpers.

Audit metadata must stay evidence-grade: structured, queryable, and free of
secrets, prompts, generated artifact text, or raw user questions.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from dreamfi.config import get_settings
from dreamfi.db.models import AuditEvent
from dreamfi.db.session import get_sessionmaker

AuditOutcome = Literal["success", "failure", "blocked", "error"]
AuditSeverity = Literal["info", "warning", "error", "critical"]

AUDIT_SCHEMA_VERSION = 1
SENSITIVE_KEY_FRAGMENTS = {
    "answer",
    "api_key",
    "authorization",
    "body",
    "content",
    "generated_text",
    "message",
    "password",
    "prompt",
    "question",
    "secret",
    "system_prompt",
    "template",
    "text",
    "token",
}

logger = logging.getLogger(__name__)


def hash_text(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    if normalized.endswith("_sha256"):
        return False
    return any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS)


def _sanitize_metadata(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if _is_sensitive_key(key):
                sanitized[f"{key}_sha256"] = hash_text(str(raw_value))
            else:
                sanitized[key] = _sanitize_metadata(raw_value)
        return sanitized
    if isinstance(value, list | tuple | set):
        return [_sanitize_metadata(item) for item in value]
    return str(value)


def _request_id(request: Request | None) -> str | None:
    if request is None:
        return None
    request_id = getattr(request.state, "request_id", None)
    return str(request_id) if request_id else None


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else None


def _actor_context(request: Request | None) -> dict[str, str | None]:
    if request is None:
        return {
            "actor_id": "system",
            "actor_type": "system",
            "auth_method": None,
        }
    actor_id = getattr(request.state, "actor_id", None)
    actor_type = getattr(request.state, "actor_type", None)
    auth_method = getattr(request.state, "auth_method", None)
    return {
        "actor_id": str(actor_id) if actor_id else "anonymous",
        "actor_type": str(actor_type) if actor_type else "anonymous",
        "auth_method": str(auth_method) if auth_method else None,
    }


def _event_hash_payload(event: AuditEvent) -> dict[str, Any]:
    return {
        "schema_version": event.schema_version,
        "event_id": event.event_id,
        "event_type": event.event_type,
        "category": event.category,
        "action": event.action,
        "outcome": event.outcome,
        "severity": event.severity,
        "actor_id": event.actor_id,
        "actor_type": event.actor_type,
        "auth_method": event.auth_method,
        "request_id": event.request_id,
        "http_method": event.http_method,
        "path": event.path,
        "status_code": event.status_code,
        "client_ip": event.client_ip,
        "target_type": event.target_type,
        "target_id": event.target_id,
        "reason": event.reason,
        "metadata_json": event.metadata_json,
        "created_at": event.created_at.isoformat(),
    }


def _compute_event_hash(event: AuditEvent) -> str:
    payload = json.dumps(_event_hash_payload(event), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def add_audit_event(
    session: Session,
    *,
    category: str,
    action: str,
    outcome: AuditOutcome,
    request: Request | None = None,
    severity: AuditSeverity = "info",
    target_type: str | None = None,
    target_id: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
    status_code: int | None = None,
) -> AuditEvent | None:
    if not get_settings().dreamfi_audit_enabled:
        return None

    actor = _actor_context(request)
    event = AuditEvent(
        event_id=str(uuid.uuid4()),
        schema_version=AUDIT_SCHEMA_VERSION,
        event_hash="pending",
        event_type=f"{category}.{action}",
        category=category,
        action=action,
        outcome=outcome,
        severity=severity,
        actor_id=actor["actor_id"],
        actor_type=actor["actor_type"] or "anonymous",
        auth_method=actor["auth_method"],
        request_id=_request_id(request),
        http_method=request.method if request is not None else None,
        path=request.url.path if request is not None else None,
        status_code=status_code,
        client_ip=_client_ip(request),
        user_agent=request.headers.get("user-agent") if request is not None else None,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        metadata_json=_sanitize_metadata(metadata or {}),
        created_at=datetime.now(timezone.utc),
    )
    event.event_hash = _compute_event_hash(event)
    session.add(event)
    return event


def write_audit_event_best_effort(
    *,
    category: str,
    action: str,
    outcome: AuditOutcome,
    request: Request | None = None,
    severity: AuditSeverity = "info",
    target_type: str | None = None,
    target_id: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
    status_code: int | None = None,
) -> None:
    if not get_settings().dreamfi_audit_enabled:
        return

    session: Session | None = None
    try:
        session = get_sessionmaker()()
        add_audit_event(
            session,
            category=category,
            action=action,
            outcome=outcome,
            request=request,
            severity=severity,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            metadata=metadata,
            status_code=status_code,
        )
        session.commit()
    except Exception:
        if session is not None:
            try:
                session.rollback()
            except SQLAlchemyError:
                logger.exception("failed to roll back audit event session")
        logger.exception("failed to persist audit event")
    finally:
        if session is not None:
            session.close()
