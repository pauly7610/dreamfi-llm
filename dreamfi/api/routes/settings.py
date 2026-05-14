"""Settings and connector activation API."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from dreamfi.api.deps import get_db_session, get_onyx_client
from dreamfi.audit import add_audit_event
from dreamfi.connector_sync import SourceDocument, ingest_bridge_documents, sync_connector
from dreamfi.onyx.client import OnyxClient
from dreamfi.onyx.errors import OnyxError
from dreamfi.settings_activation import (
    activate_connector,
    actor_id_from_request_state,
    connector_or_none,
    deactivate_connector,
    delete_connector_secret,
    ensure_connector_document_set,
    mask_secret,
    probe_connector,
    settings_status,
    upsert_connector_config,
    upsert_connector_secret,
    validate_secret_value,
)

router = APIRouter(prefix="/api/settings")


class ConnectorSecretRequest(BaseModel):
    api_key: str = Field(min_length=1)
    label: str | None = None


class ConnectorConfigRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class ConnectorSyncRequest(BaseModel):
    limit: int | None = Field(default=None, ge=1, le=500)


class BridgeDocumentRequest(BaseModel):
    external_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_url: str | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BridgeIngestRequest(BaseModel):
    documents: list[BridgeDocumentRequest] = Field(min_length=1, max_length=500)


def _connector_or_404(connector_id: str):
    connector = connector_or_none(connector_id)
    if connector is None:
        raise HTTPException(status_code=404, detail="connector not found")
    return connector


def _safe_connector_payload(
    *,
    session: Session,
    onyx: OnyxClient,
    connector_id: str,
) -> dict[str, Any]:
    payload = settings_status(session, onyx)
    connector = next(
        item for item in payload["connectors"] if item["connector_id"] == connector_id
    )
    return {"connector": connector, "settings_status": payload["status"]}


def _serialize_sync_run(run) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    return {
        "sync_run_id": run.sync_run_id,
        "connector_id": run.connector_id,
        "status": run.status,
        "trigger": run.trigger,
        "pulled_count": run.pulled_count,
        "persisted_count": run.persisted_count,
        "ingested_count": run.ingested_count,
        "skipped_count": run.skipped_count,
        "error_count": run.error_count,
        "reason": run.reason,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


@router.get("/status")
def read_settings_status(
    request: Request,
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> dict[str, Any]:
    payload = settings_status(session, onyx)
    add_audit_event(
        session,
        category="configuration",
        action="settings_status_read",
        outcome="success",
        request=request,
        target_type="settings",
        target_id="activation",
        metadata={
            "status": payload["status"],
            "failures": payload["failures"],
            "summary": payload["summary"],
        },
    )
    session.commit()
    return payload


@router.post("/connectors/{connector_id}/secret", status_code=status.HTTP_201_CREATED)
def save_connector_secret(
    connector_id: str,
    body: ConnectorSecretRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> dict[str, Any]:
    connector = _connector_or_404(connector_id)
    actor_id = actor_id_from_request_state(request.state)
    try:
        preview = validate_secret_value(body.api_key)
    except ValueError as exc:
        add_audit_event(
            session,
            category="configuration",
            action="connector_secret_save",
            outcome="blocked",
            request=request,
            severity="warning",
            target_type="connector",
            target_id=connector.connector_id,
            reason=str(exc),
            metadata={"connector_id": connector.connector_id},
        )
        session.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        row = upsert_connector_secret(
            session,
            connector=connector,
            api_key=body.api_key,
            actor_id=actor_id,
            label=body.label,
        )
    except ValueError as exc:
        add_audit_event(
            session,
            category="configuration",
            action="connector_secret_save",
            outcome="blocked",
            request=request,
            severity="warning",
            target_type="connector",
            target_id=connector.connector_id,
            reason=str(exc),
            metadata={"connector_id": connector.connector_id},
        )
        session.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    add_audit_event(
        session,
        category="configuration",
        action="connector_secret_save",
        outcome="success",
        request=request,
        target_type="connector",
        target_id=connector.connector_id,
        metadata={
            "connector_id": connector.connector_id,
            "masked_secret": mask_secret(preview),
            "secret_sha256": row.secret_sha256,
            "label_present": bool(body.label and body.label.strip()),
        },
    )
    session.commit()
    return _safe_connector_payload(session=session, onyx=onyx, connector_id=connector.connector_id)


@router.post("/connectors/{connector_id}/config")
def save_connector_config(
    connector_id: str,
    body: ConnectorConfigRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> dict[str, Any]:
    connector = _connector_or_404(connector_id)
    row = upsert_connector_config(
        session,
        connector=connector,
        config_values=body.config,
        actor_id=actor_id_from_request_state(request.state),
    )
    add_audit_event(
        session,
        category="configuration",
        action="connector_config_save",
        outcome="success",
        request=request,
        target_type="connector",
        target_id=connector.connector_id,
        metadata={
            "connector_id": connector.connector_id,
            "config_keys": sorted((row.config_json or {}).keys()),
        },
    )
    session.commit()
    return _safe_connector_payload(session=session, onyx=onyx, connector_id=connector.connector_id)


@router.delete("/connectors/{connector_id}/secret")
def remove_connector_secret(
    connector_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> dict[str, Any]:
    connector = _connector_or_404(connector_id)
    row = delete_connector_secret(
        session,
        connector=connector,
        actor_id=actor_id_from_request_state(request.state),
    )
    add_audit_event(
        session,
        category="configuration",
        action="connector_secret_delete",
        outcome="success",
        request=request,
        target_type="connector",
        target_id=connector.connector_id,
        metadata={"connector_id": connector.connector_id, "activation_status": row.activation_status},
    )
    session.commit()
    return _safe_connector_payload(session=session, onyx=onyx, connector_id=connector.connector_id)


@router.post("/connectors/{connector_id}/sync")
def run_connector_sync(
    connector_id: str,
    body: ConnectorSyncRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> dict[str, Any]:
    connector = _connector_or_404(connector_id)
    run = sync_connector(
        session=session,
        onyx=onyx,
        connector=connector,
        actor_id=actor_id_from_request_state(request.state),
        trigger="manual",
        limit=body.limit,
    )
    add_audit_event(
        session,
        category="configuration",
        action="connector_sync_run",
        outcome="success" if run.status == "success" else "blocked",
        request=request,
        severity="info" if run.status == "success" else "warning",
        target_type="connector",
        target_id=connector.connector_id,
        reason=run.reason,
        metadata=_serialize_sync_run(run),
    )
    session.commit()
    payload = _safe_connector_payload(session=session, onyx=onyx, connector_id=connector.connector_id)
    payload["sync_run"] = _serialize_sync_run(run)
    return payload


@router.post("/connectors/{connector_id}/documents", status_code=status.HTTP_201_CREATED)
def ingest_connector_documents(
    connector_id: str,
    body: BridgeIngestRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> dict[str, Any]:
    connector = _connector_or_404(connector_id)
    if connector.connection_method != "custom_ingestion":
        raise HTTPException(status_code=422, detail="bridge ingest is only supported for custom connectors")
    documents = [
        SourceDocument(
            connector_id=connector.connector_id,
            external_id=item.external_id,
            title=item.title,
            text=item.text,
            source_url=item.source_url,
            updated_at=item.updated_at or datetime.now(timezone.utc),
            metadata=item.metadata,
        )
        for item in body.documents
    ]
    run = ingest_bridge_documents(
        session=session,
        onyx=onyx,
        connector=connector,
        actor_id=actor_id_from_request_state(request.state),
        documents=documents,
    )
    add_audit_event(
        session,
        category="configuration",
        action="connector_bridge_ingest",
        outcome="success" if run.status == "success" else "blocked",
        request=request,
        severity="info" if run.status == "success" else "warning",
        target_type="connector",
        target_id=connector.connector_id,
        reason=run.reason,
        metadata={
            **_serialize_sync_run(run),
            "external_ids": [item.external_id for item in body.documents],
        },
    )
    session.commit()
    payload = _safe_connector_payload(session=session, onyx=onyx, connector_id=connector.connector_id)
    payload["sync_run"] = _serialize_sync_run(run)
    return payload


@router.post("/connectors/{connector_id}/document-set")
def create_connector_document_set(
    connector_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> dict[str, Any]:
    connector = _connector_or_404(connector_id)
    try:
        row = ensure_connector_document_set(
            session=session,
            onyx=onyx,
            connector=connector,
            actor_id=actor_id_from_request_state(request.state),
        )
    except (OnyxError, httpx.HTTPError) as exc:
        session.rollback()
        raise HTTPException(status_code=502, detail=f"Onyx document-set setup failed: {type(exc).__name__}") from exc

    add_audit_event(
        session,
        category="configuration",
        action="connector_document_set_ensure",
        outcome="success",
        request=request,
        target_type="connector",
        target_id=connector.connector_id,
        metadata={
            "connector_id": connector.connector_id,
            "document_set_id": row.document_set_id,
            "document_set_name": row.document_set_name,
        },
    )
    session.commit()
    return _safe_connector_payload(session=session, onyx=onyx, connector_id=connector.connector_id)


@router.post("/connectors/{connector_id}/validate")
def validate_connector(
    connector_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> dict[str, Any]:
    connector = _connector_or_404(connector_id)
    try:
        row = probe_connector(
            session=session,
            onyx=onyx,
            connector=connector,
            actor_id=actor_id_from_request_state(request.state),
        )
    except (OnyxError, httpx.HTTPError) as exc:
        session.rollback()
        raise HTTPException(status_code=502, detail=f"connector validation failed: {type(exc).__name__}") from exc

    outcome = "success" if row.validation_status == "validated" else "blocked"
    add_audit_event(
        session,
        category="configuration",
        action="connector_validate",
        outcome=outcome,  # type: ignore[arg-type]
        request=request,
        severity="info" if outcome == "success" else "warning",
        target_type="connector",
        target_id=connector.connector_id,
        reason=row.validation_error,
        metadata={
            "connector_id": connector.connector_id,
            "document_set_present": row.document_set_present,
            "retrieval_status": row.retrieval_status,
        },
    )
    session.commit()
    return _safe_connector_payload(session=session, onyx=onyx, connector_id=connector.connector_id)


@router.post("/connectors/{connector_id}/activate")
def activate_connector_endpoint(
    connector_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> dict[str, Any]:
    connector = _connector_or_404(connector_id)
    row, blockers = activate_connector(
        session=session,
        connector=connector,
        actor_id=actor_id_from_request_state(request.state),
    )
    if blockers:
        add_audit_event(
            session,
            category="configuration",
            action="connector_activate",
            outcome="blocked",
            request=request,
            severity="warning",
            target_type="connector",
            target_id=connector.connector_id,
            reason="activation blockers",
            metadata={"connector_id": connector.connector_id, "blockers": blockers},
        )
        session.commit()
        raise HTTPException(status_code=422, detail={"blockers": blockers})

    add_audit_event(
        session,
        category="configuration",
        action="connector_activate",
        outcome="success",
        request=request,
        target_type="connector",
        target_id=connector.connector_id,
        metadata={
            "connector_id": connector.connector_id,
            "activation_status": row.activation_status,
            "document_set_id": row.document_set_id,
        },
    )
    session.commit()
    return _safe_connector_payload(session=session, onyx=onyx, connector_id=connector.connector_id)


@router.post("/connectors/{connector_id}/deactivate")
def deactivate_connector_endpoint(
    connector_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
    onyx: OnyxClient = Depends(get_onyx_client),
) -> dict[str, Any]:
    connector = _connector_or_404(connector_id)
    row = deactivate_connector(
        session=session,
        connector=connector,
        actor_id=actor_id_from_request_state(request.state),
    )
    add_audit_event(
        session,
        category="configuration",
        action="connector_deactivate",
        outcome="success",
        request=request,
        target_type="connector",
        target_id=connector.connector_id,
        metadata={"connector_id": connector.connector_id, "activation_status": row.activation_status},
    )
    session.commit()
    return _safe_connector_payload(session=session, onyx=onyx, connector_id=connector.connector_id)
