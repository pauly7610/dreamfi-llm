"""Settings and connector activation helpers."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from dreamfi.connectors import (
    CONNECTOR_BY_ID,
    CONNECTORS,
    REQUIRED_METADATA_KEYS,
    ConnectorSpec,
    connector_document_set_aliases,
    normalize_document_set_name,
)
from dreamfi.connector_secrets import (
    ConnectorSecretError,
    connector_secret_storage,
    encrypt_connector_secret,
    resolve_connector_secret,
)
from dreamfi.db.models import (
    ArtifactFeedback,
    AuditEvent,
    ConnectorDocument,
    ConnectorSetting,
    ConnectorSyncRun,
    EvalOutput,
    EvalRound,
    GoldExample,
    LearningProposal,
    ProductionOutcome,
    ReplayRun,
    ReplaySchedule,
)
from dreamfi.onyx.client import OnyxClient
from dreamfi.onyx.errors import OnyxError
from dreamfi.ops.readiness import (
    audit_readiness,
    connector_readiness,
    database_readiness,
    environment_readiness,
    replay_readiness,
)

EXPECTED_ALEMBIC_HEAD = "20260507_0010"
PLACEHOLDER_VALUES = {"", "change-me", "change-me-before-deploy", "onyx_pat_XXX", "sk-ant-XXX"}
MIN_SECRET_LENGTH = 8


def connector_or_none(connector_id: str) -> ConnectorSpec | None:
    return CONNECTOR_BY_ID.get(connector_id.strip().lower())


def mask_secret(value: str) -> str:
    stripped = value.strip()
    if len(stripped) <= 4:
        return "****"
    return f"****{stripped[-4:]}"


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def validate_secret_value(value: str) -> str:
    stripped = value.strip()
    if stripped in PLACEHOLDER_VALUES:
        raise ValueError("placeholder or empty API keys are not allowed")
    if len(stripped) < MIN_SECRET_LENGTH:
        raise ValueError(f"API key must be at least {MIN_SECRET_LENGTH} characters")
    return stripped


def actor_id_from_request_state(state: Any) -> str:
    actor_id = getattr(state, "actor_id", None)
    return str(actor_id) if actor_id else "system"


def get_or_create_connector_setting(
    session: Session,
    connector: ConnectorSpec,
    *,
    actor_id: str | None = None,
) -> ConnectorSetting:
    row = session.get(ConnectorSetting, connector.connector_id)
    if row is None:
        now = datetime.now(timezone.utc)
        row = ConnectorSetting(
            connector_id=connector.connector_id,
            provider=connector.name,
            credential_status="missing",
            validation_status="not_validated",
            document_set_present=False,
            activation_status="inactive",
            config_json=dict(connector.default_config or {}),
            created_by=actor_id,
            updated_by=actor_id,
            metadata_json={},
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
    return row


def upsert_connector_secret(
    session: Session,
    *,
    connector: ConnectorSpec,
    api_key: str,
    actor_id: str,
    label: str | None = None,
) -> ConnectorSetting:
    clean = validate_secret_value(api_key)
    encrypted = None
    if connector.requires_dreamfi_secret:
        encrypted = encrypt_connector_secret(clean)
    row = get_or_create_connector_setting(session, connector, actor_id=actor_id)
    now = datetime.now(timezone.utc)
    row.credential_status = "saved"
    row.secret_last_four = clean[-4:]
    row.secret_sha256 = hash_secret(clean)
    if encrypted is not None:
        row.secret_ciphertext = encrypted.ciphertext
        row.secret_key_id = encrypted.key_id
    row.secret_label = label.strip() if label and label.strip() else None
    row.validation_status = "not_validated"
    row.validation_error = "validation required"
    row.validated_at = None
    row.activation_status = "inactive" if row.activation_status == "active" else row.activation_status
    row.deactivated_at = now if row.activation_status != "active" else row.deactivated_at
    row.updated_by = actor_id
    row.updated_at = now
    session.flush()
    return row


def delete_connector_secret(
    session: Session,
    *,
    connector: ConnectorSpec,
    actor_id: str,
) -> ConnectorSetting:
    row = get_or_create_connector_setting(session, connector, actor_id=actor_id)
    now = datetime.now(timezone.utc)
    row.credential_status = "missing"
    row.secret_last_four = None
    row.secret_sha256 = None
    row.secret_ciphertext = None
    row.secret_key_id = None
    row.secret_label = None
    row.validation_status = "not_validated"
    row.validation_error = None
    row.validated_at = None
    row.activation_status = "inactive"
    row.activated_at = None
    row.deactivated_at = now
    row.updated_by = actor_id
    row.updated_at = now
    session.flush()
    return row


def persistence_readiness(session: Session) -> dict[str, Any]:
    database = database_readiness(session)
    audit = audit_readiness(session)
    bind = session.get_bind()
    drivername = getattr(getattr(bind, "url", None), "drivername", "")
    uses_sqlite = str(drivername).startswith("sqlite")
    try:
        alembic_version = session.execute(text("select version_num from alembic_version")).scalar()
    except SQLAlchemyError:
        alembic_version = None

    count_models = {
        "audit_events": AuditEvent,
        "eval_rounds": EvalRound,
        "eval_outputs": EvalOutput,
        "feedback": ArtifactFeedback,
        "gold_examples": GoldExample,
        "learning_proposals": LearningProposal,
        "replay_schedules": ReplaySchedule,
        "replay_runs": ReplayRun,
        "production_outcomes": ProductionOutcome,
        "connector_settings": ConnectorSetting,
        "connector_sync_runs": ConnectorSyncRun,
        "connector_documents": ConnectorDocument,
    }
    counts: dict[str, int] = {}
    for name, model in count_models.items():
        try:
            counts[name] = int(session.scalar(select(func.count()).select_from(model)) or 0)
        except SQLAlchemyError:
            counts[name] = 0

    checks = [
        {
            "name": "database_connection",
            "passed": database.get("status") == "ok",
            "detail": database.get("reason") or "database responded to select 1",
        },
        {
            "name": "persistent_postgres",
            "passed": not uses_sqlite,
            "detail": "SQLite is local-only; production activation requires Postgres."
            if uses_sqlite
            else "database bind is not SQLite",
        },
        {
            "name": "migration_head",
            "passed": alembic_version == EXPECTED_ALEMBIC_HEAD,
            "detail": alembic_version or "alembic_version table not found",
        },
        {
            "name": "audit_writable",
            "passed": bool(audit.get("enabled")) and int(audit.get("audit_failure_count_24h") or 0) == 0,
            "detail": "audit logging enabled and no audit write failures in the last 24h",
        },
    ]
    return {
        "ready": all(bool(check["passed"]) for check in checks),
        "uses_sqlite": uses_sqlite,
        "alembic_version": alembic_version,
        "expected_alembic_head": EXPECTED_ALEMBIC_HEAD,
        "checks": checks,
        "counts": counts,
        "audit": audit,
    }


def _find_document_set_row(onyx_rows: list[dict[str, Any]], connector: ConnectorSpec) -> dict[str, Any] | None:
    for row in onyx_rows:
        if row.get("connector_id") == connector.connector_id:
            return row
    return None


def _config_values(connector: ConnectorSpec, row: ConnectorSetting | None) -> dict[str, str]:
    values = dict(connector.default_config or {})
    if row is not None:
        for key, value in (row.config_json or {}).items():
            if value is not None:
                values[str(key)] = str(value)
    return values


def missing_connector_config_keys(connector: ConnectorSpec, row: ConnectorSetting | None) -> list[str]:
    values = _config_values(connector, row)
    return [key for key in connector.required_config_keys if not values.get(key, "").strip()]


def upsert_connector_config(
    session: Session,
    *,
    connector: ConnectorSpec,
    config_values: dict[str, Any],
    actor_id: str,
) -> ConnectorSetting:
    row = get_or_create_connector_setting(session, connector, actor_id=actor_id)
    allowed_keys = {field.key for field in connector.config_fields}
    cleaned: dict[str, str] = dict(connector.default_config or {})
    for key, value in config_values.items():
        normalized_key = str(key).strip()
        if normalized_key not in allowed_keys:
            continue
        if value is None:
            continue
        cleaned[normalized_key] = str(value).strip()
    now = datetime.now(timezone.utc)
    row.config_json = cleaned
    row.validation_status = "not_validated"
    row.validation_error = "validation required"
    row.activation_status = "inactive" if row.activation_status == "active" else row.activation_status
    row.updated_by = actor_id
    row.updated_at = now
    session.flush()
    return row


def _serialize_secret(row: ConnectorSetting | None, connector: ConnectorSpec) -> dict[str, Any]:
    storage = connector_secret_storage(row, connector)
    usable = storage in {"encrypted", "env"} or not connector.requires_dreamfi_secret
    return {
        "status": "saved" if storage in {"encrypted", "env"} else (row.credential_status if row is not None else "missing"),
        "masked": f"****{row.secret_last_four}" if row is not None and row.secret_last_four else None,
        "label": row.secret_label if row is not None else None,
        "validated_at": row.validated_at.isoformat() if row is not None and row.validated_at else None,
        "storage": storage,
        "usable": usable,
    }


def serialize_connector_setting(
    *,
    connector: ConnectorSpec,
    setting: ConnectorSetting | None,
    readiness_row: dict[str, Any] | None,
    latest_sync: ConnectorSyncRun | None,
    persistence_ready: bool,
    audit_ready: bool,
) -> dict[str, Any]:
    document_set_present = bool(
        (readiness_row or {}).get("document_set_present")
        or (setting.document_set_present if setting is not None else False)
    )
    retrieval_status = (
        str((readiness_row or {}).get("retrieval_status"))
        if readiness_row and readiness_row.get("retrieval_status") is not None
        else (setting.retrieval_status if setting is not None else None)
    )
    freshest_document_at = (
        str((readiness_row or {}).get("freshest_document_at"))
        if readiness_row and readiness_row.get("freshest_document_at") is not None
        else (
            setting.freshest_document_at.isoformat()
            if setting is not None and setting.freshest_document_at is not None
            else None
        )
    )
    validation_status = setting.validation_status if setting is not None else "not_validated"
    credential = _serialize_secret(setting, connector)
    activation_status = setting.activation_status if setting is not None else "inactive"
    health_probe_passed = retrieval_status == "fresh"
    missing_config_keys = missing_connector_config_keys(connector, setting)
    blockers = []
    if connector.requires_dreamfi_secret and not credential["usable"]:
        blockers.append("credential")
    if missing_config_keys:
        blockers.append("configuration")
    if validation_status != "validated":
        blockers.append("validation")
    if not document_set_present:
        blockers.append("document_set")
    if not health_probe_passed:
        blockers.append("freshness_probe")
    if not persistence_ready:
        blockers.append("persistence")
    if not audit_ready:
        blockers.append("audit")
    effective_status = activation_status
    if activation_status == "active" and not health_probe_passed:
        effective_status = "degraded"

    return {
        "connector_id": connector.connector_id,
        "name": connector.name,
        "category": connector.category,
        "purpose": connector.purpose,
        "used_for": list(connector.used_for),
        "expected_document_set": connector.expected_document_set,
        "connection_method": connector.connection_method,
        "setup_method": connector.setup_method,
        "setup_detail": connector.setup_detail,
        "requires_dreamfi_secret": connector.requires_dreamfi_secret,
        "config_schema": [field.as_dict() for field in connector.config_fields],
        "config": {
            "values": _config_values(connector, setting),
            "missing_keys": missing_config_keys,
        },
        "metadata_keys": list(REQUIRED_METADATA_KEYS),
        "credential": {
            **credential,
            "required": connector.requires_dreamfi_secret,
        },
        "validation_status": validation_status,
        "validation_error": setting.validation_error if setting is not None else None,
        "document_set_present": document_set_present,
        "document_set_id": (
            readiness_row.get("document_set_id")
            if readiness_row and readiness_row.get("document_set_id") is not None
            else (setting.document_set_id if setting is not None else None)
        ),
        "document_set_name": (
            setting.document_set_name
            if setting is not None and setting.document_set_name
            else connector.expected_document_set
        ),
        "retrieval_status": retrieval_status or "not_checked",
        "freshest_document_at": freshest_document_at,
        "last_probe_at": setting.last_probe_at.isoformat() if setting is not None and setting.last_probe_at else None,
        "activation_status": effective_status,
        "activated_at": setting.activated_at.isoformat() if setting is not None and setting.activated_at else None,
        "latest_sync": (
            {
                "sync_run_id": latest_sync.sync_run_id,
                "status": latest_sync.status,
                "trigger": latest_sync.trigger,
                "pulled_count": latest_sync.pulled_count,
                "persisted_count": latest_sync.persisted_count,
                "ingested_count": latest_sync.ingested_count,
                "error_count": latest_sync.error_count,
                "reason": latest_sync.reason,
                "started_at": latest_sync.started_at.isoformat(),
                "completed_at": latest_sync.completed_at.isoformat() if latest_sync.completed_at else None,
            }
            if latest_sync is not None
            else None
        ),
        "blockers": blockers,
        "can_activate": not blockers,
        "href": f"/console/settings?connector={connector.connector_id}",
    }


def settings_status(session: Session, onyx: OnyxClient) -> dict[str, Any]:
    environment = environment_readiness()
    persistence = persistence_readiness(session)
    replays = replay_readiness(session)
    audit = persistence["audit"]
    audit_ready = bool(audit.get("enabled")) and int(audit.get("audit_failure_count_24h") or 0) == 0

    try:
        readiness = connector_readiness(onyx=onyx)
    except (OnyxError, httpx.HTTPError) as exc:
        readiness = {"status": "error", "reason": type(exc).__name__, "connectors": []}
    readiness_rows = list(readiness.get("connectors", []))
    settings_by_id = {
        row.connector_id: row
        for row in session.scalars(select(ConnectorSetting)).all()
    }
    latest_sync_by_id = {
        connector.connector_id: session.scalar(
            select(ConnectorSyncRun)
            .where(ConnectorSyncRun.connector_id == connector.connector_id)
            .order_by(ConnectorSyncRun.started_at.desc())
            .limit(1)
        )
        for connector in CONNECTORS
    }
    connectors = [
        serialize_connector_setting(
            connector=connector,
            setting=settings_by_id.get(connector.connector_id),
            readiness_row=_find_document_set_row(readiness_rows, connector),
            latest_sync=latest_sync_by_id.get(connector.connector_id),
            persistence_ready=bool(persistence["ready"]),
            audit_ready=audit_ready,
        )
        for connector in CONNECTORS
    ]
    active_count = sum(1 for row in connectors if row["activation_status"] == "active")
    blocked_count = sum(1 for row in connectors if row["blockers"])
    configured_count = sum(
        1
        for row in connectors
        if row["document_set_present"]
        or (row["requires_dreamfi_secret"] and row["credential"]["usable"])
    )
    missing_required_credentials = [
        row
        for row in connectors
        if row["requires_dreamfi_secret"] and not row["credential"]["usable"]
    ]
    failures = []
    if not environment["ready"]:
        failures.append("environment")
    if not persistence["ready"]:
        failures.append("persistence")
    if not audit_ready:
        failures.append("audit")
    if missing_required_credentials:
        failures.append("credentials")
    if blocked_count:
        failures.append("connectors")
    overall = "ready" if not failures else ("degraded" if active_count else "blocked")
    return {
        "status": overall,
        "failures": failures,
        "summary": {
            "connector_count": len(connectors),
            "configured_connector_count": configured_count,
            "active_connector_count": active_count,
            "blocked_connector_count": blocked_count,
        },
        "environment": environment,
        "persistence": persistence,
        "jobs": {
            "replay": replays,
            "connector_health_checks": {
                "configured": bool(configured_count),
                "active_connector_count": active_count,
            },
        },
        "connectors": connectors,
    }


def ensure_connector_document_set(
    *,
    session: Session,
    onyx: OnyxClient,
    connector: ConnectorSpec,
    actor_id: str,
) -> ConnectorSetting:
    row = get_or_create_connector_setting(session, connector, actor_id=actor_id)
    existing = None
    document_sets = onyx.list_document_sets()
    aliases = {
        normalize_document_set_name(alias)
        for alias in connector_document_set_aliases(connector)
    }
    for document_set in document_sets:
        if normalize_document_set_name(document_set.name) in aliases:
            existing = document_set
            break
    if existing is None:
        existing = onyx.create_document_set(
            name=connector.expected_document_set,
            description=(
                f"DreamFi source evidence for {connector.name}. "
                f"Documents should include metadata keys: {', '.join(REQUIRED_METADATA_KEYS)}."
            ),
        )
    now = datetime.now(timezone.utc)
    row.document_set_id = existing.id
    row.document_set_name = existing.name
    row.document_set_present = True
    row.updated_by = actor_id
    row.updated_at = now
    session.flush()
    return row


def probe_connector(
    *,
    session: Session,
    onyx: OnyxClient,
    connector: ConnectorSpec,
    actor_id: str,
) -> ConnectorSetting:
    row = get_or_create_connector_setting(session, connector, actor_id=actor_id)
    now = datetime.now(timezone.utc)
    readiness = connector_readiness(onyx=onyx)
    readiness_row = _find_document_set_row(list(readiness.get("connectors", [])), connector)
    if readiness.get("status") == "error" or readiness_row is None:
        row.validation_status = "validation_failed"
        row.validation_error = str(readiness.get("reason") or "connector readiness failed")
        row.retrieval_status = "error"
        row.last_probe_at = now
    else:
        try:
            credential_ok = not connector.requires_dreamfi_secret or resolve_connector_secret(connector, row) is not None
        except ConnectorSecretError as exc:
            credential_ok = False
            row.validation_error = str(exc)
        row.validation_status = "validated" if credential_ok else "not_validated"
        row.validation_error = None if credential_ok else (row.validation_error or "credential missing")
        row.validated_at = now if credential_ok else None
        row.document_set_present = bool(readiness_row.get("document_set_present"))
        row.retrieval_status = str(readiness_row.get("retrieval_status") or "not_checked")
        row.freshest_document_at = _parse_datetime(readiness_row.get("freshest_document_at"))
        row.last_probe_at = now
        if readiness_row.get("document_set_id") is not None:
            row.document_set_id = int(readiness_row["document_set_id"])
        row.document_set_name = connector.expected_document_set
    row.updated_by = actor_id
    row.updated_at = now
    session.flush()
    return row


def activation_blockers(
    *,
    session: Session,
    connector: ConnectorSpec,
    setting: ConnectorSetting,
) -> list[str]:
    persistence = persistence_readiness(session)
    audit = persistence["audit"]
    blockers = []
    try:
        credential_ok = not connector.requires_dreamfi_secret or resolve_connector_secret(connector, setting) is not None
    except ConnectorSecretError:
        credential_ok = False
    if not credential_ok:
        blockers.append("credential")
    if missing_connector_config_keys(connector, setting):
        blockers.append("configuration")
    if setting.validation_status != "validated":
        blockers.append("validation")
    if not setting.document_set_present:
        blockers.append("document_set")
    if setting.retrieval_status != "fresh":
        blockers.append("freshness_probe")
    if not persistence["ready"]:
        blockers.append("persistence")
    if not bool(audit.get("enabled")) or int(audit.get("audit_failure_count_24h") or 0) != 0:
        blockers.append("audit")
    if connector.connector_id != setting.connector_id:
        blockers.append("connector_mismatch")
    return blockers


def activate_connector(
    *,
    session: Session,
    connector: ConnectorSpec,
    actor_id: str,
) -> tuple[ConnectorSetting, list[str]]:
    row = get_or_create_connector_setting(session, connector, actor_id=actor_id)
    blockers = activation_blockers(session=session, connector=connector, setting=row)
    if blockers:
        return row, blockers
    now = datetime.now(timezone.utc)
    row.activation_status = "active"
    row.activated_at = now
    row.deactivated_at = None
    row.updated_by = actor_id
    row.updated_at = now
    session.flush()
    return row, []


def deactivate_connector(
    *,
    session: Session,
    connector: ConnectorSpec,
    actor_id: str,
) -> ConnectorSetting:
    row = get_or_create_connector_setting(session, connector, actor_id=actor_id)
    now = datetime.now(timezone.utc)
    row.activation_status = "inactive"
    row.deactivated_at = now
    row.updated_by = actor_id
    row.updated_at = now
    session.flush()
    return row


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None
