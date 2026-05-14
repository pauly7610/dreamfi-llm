"""Connector sync service: pull, persist, and ingest custom source evidence."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from dreamfi.config import get_settings
from dreamfi.connectors import ConnectorSpec
from dreamfi.connector_secrets import ConnectorSecretError, resolve_connector_secret
from dreamfi.connector_sync.providers import ConnectorAdapterError, adapter_for
from dreamfi.connector_sync.types import SourceDocument, as_utc
from dreamfi.db.models import ConnectorDocument, ConnectorSetting, ConnectorSyncRun
from dreamfi.onyx.client import OnyxClient
from dreamfi.onyx.errors import OnyxError
from dreamfi.settings_activation import (
    ensure_connector_document_set,
    get_or_create_connector_setting,
    missing_connector_config_keys,
)


class ConnectorSyncError(RuntimeError):
    """Raised when a connector sync cannot complete."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _effective_config(connector: ConnectorSpec, setting: ConnectorSetting) -> dict[str, str]:
    values = dict(connector.default_config or {})
    for key, value in (setting.config_json or {}).items():
        if value is not None:
            values[str(key)] = str(value)
    return values


def _latest_sync_run(session: Session, connector_id: str) -> ConnectorSyncRun | None:
    return session.scalar(
        select(ConnectorSyncRun)
        .where(ConnectorSyncRun.connector_id == connector_id)
        .order_by(ConnectorSyncRun.started_at.desc())
        .limit(1)
    )


def _sync_run(
    session: Session,
    *,
    connector: ConnectorSpec,
    trigger: str,
) -> ConnectorSyncRun:
    row = ConnectorSyncRun(
        connector_id=connector.connector_id,
        status="running",
        trigger=trigger,
        pulled_count=0,
        persisted_count=0,
        ingested_count=0,
        skipped_count=0,
        error_count=0,
        cursor_json={},
        metadata_json={},
        started_at=_now(),
    )
    session.add(row)
    session.flush()
    return row


def _upsert_document(
    session: Session,
    *,
    connector: ConnectorSpec,
    run: ConnectorSyncRun,
    doc: SourceDocument,
) -> tuple[ConnectorDocument, bool]:
    if doc.connector_id != connector.connector_id:
        raise ConnectorSyncError("document connector_id does not match requested connector")
    existing = session.scalar(
        select(ConnectorDocument).where(
            ConnectorDocument.connector_id == connector.connector_id,
            ConnectorDocument.external_id == doc.external_id,
        )
    )
    now = _now()
    if existing is None:
        existing = ConnectorDocument(
            connector_id=connector.connector_id,
            external_id=doc.external_id,
            title=doc.title,
            body_text=doc.text,
            source_url=doc.source_url,
            doc_updated_at=as_utc(doc.updated_at),
            content_hash=doc.content_hash,
            metadata_json=doc.onyx_metadata(),
            sync_run_id=run.sync_run_id,
            onyx_document_id=doc.onyx_document_id,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(existing)
        session.flush()
        return existing, True

    changed = existing.content_hash != doc.content_hash or existing.last_ingested_at is None
    existing.title = doc.title
    existing.body_text = doc.text
    existing.source_url = doc.source_url
    existing.doc_updated_at = as_utc(doc.updated_at)
    existing.content_hash = doc.content_hash
    existing.metadata_json = doc.onyx_metadata()
    existing.sync_run_id = run.sync_run_id
    existing.onyx_document_id = existing.onyx_document_id or doc.onyx_document_id
    existing.last_seen_at = now
    existing.updated_at = now
    session.flush()
    return existing, changed


def _ingest_document(onyx: OnyxClient, row: ConnectorDocument) -> str:
    result = onyx.ingest_document(
        doc_id=row.onyx_document_id or f"dreamfi:{row.connector_id}:{row.connector_document_id}",
        text=row.body_text,
        semantic_identifier=row.title,
        metadata=row.metadata_json,
        source_url=row.source_url,
        doc_updated_at=as_utc(row.doc_updated_at).isoformat(),
        title=row.title,
    )
    return result.document_id


def _finish_setting(
    *,
    setting: ConnectorSetting,
    docs: Iterable[SourceDocument],
    actor_id: str,
) -> None:
    docs_list = list(docs)
    now = _now()
    if docs_list:
        freshest = max(as_utc(doc.updated_at) for doc in docs_list)
        stale_after = timedelta(days=get_settings().dreamfi_connector_stale_after_days)
        setting.retrieval_status = "fresh" if freshest >= now - stale_after else "stale"
        setting.freshest_document_at = freshest
    else:
        setting.retrieval_status = "empty"
    setting.validation_status = "validated"
    setting.validation_error = None
    setting.validated_at = now
    setting.last_probe_at = now
    setting.updated_by = actor_id
    setting.updated_at = now


def _mark_failed(run: ConnectorSyncRun, setting: ConnectorSetting, reason: str) -> None:
    now = _now()
    run.status = "failed"
    run.reason = reason
    run.error_count = max(run.error_count, 1)
    run.completed_at = now
    setting.validation_status = "validation_failed"
    setting.validation_error = reason
    setting.retrieval_status = "error"
    setting.last_probe_at = now
    setting.updated_at = now


def _persist_and_ingest(
    *,
    session: Session,
    onyx: OnyxClient,
    connector: ConnectorSpec,
    setting: ConnectorSetting,
    run: ConnectorSyncRun,
    docs: list[SourceDocument],
    actor_id: str,
) -> ConnectorSyncRun:
    ensure_connector_document_set(
        session=session,
        onyx=onyx,
        connector=connector,
        actor_id=actor_id,
    )
    run.pulled_count = len(docs)
    for doc in docs:
        row, changed = _upsert_document(session, connector=connector, run=run, doc=doc)
        run.persisted_count += 1
        if not changed:
            run.skipped_count += 1
            continue
        onyx_document_id = _ingest_document(onyx, row)
        row.onyx_document_id = onyx_document_id
        row.last_ingested_at = _now()
        run.ingested_count += 1
        session.flush()

    _finish_setting(setting=setting, docs=docs, actor_id=actor_id)
    run.status = "success"
    run.completed_at = _now()
    run.cursor_json = {
        "freshest_document_at": setting.freshest_document_at.isoformat()
        if setting.freshest_document_at
        else None,
    }
    session.flush()
    return run


def sync_connector(
    *,
    session: Session,
    onyx: OnyxClient,
    connector: ConnectorSpec,
    actor_id: str,
    trigger: str = "manual",
    limit: int | None = None,
    transport: httpx.BaseTransport | None = None,
) -> ConnectorSyncRun:
    """Pull a custom provider, persist normalized rows, and ingest changed docs into Onyx."""
    setting = get_or_create_connector_setting(session, connector, actor_id=actor_id)
    run = _sync_run(session, connector=connector, trigger=trigger)
    if connector.connection_method != "custom_ingestion":
        _mark_failed(run, setting, "connector is native Onyx; configure it in Onyx instead")
        return run

    missing_config = missing_connector_config_keys(connector, setting)
    if missing_config:
        _mark_failed(run, setting, f"missing configuration: {', '.join(missing_config)}")
        return run

    try:
        secret = resolve_connector_secret(connector, setting)
    except ConnectorSecretError as exc:
        _mark_failed(run, setting, str(exc))
        return run
    if connector.requires_dreamfi_secret and not secret:
        _mark_failed(run, setting, "connector API key is missing")
        return run

    try:
        adapter = adapter_for(connector.connector_id)
        docs = adapter.fetch_documents(
            connector=connector,
            config=_effective_config(connector, setting),
            secret=secret or "",
            limit=limit or get_settings().dreamfi_connector_sync_batch_size,
            transport=transport,
        )
        return _persist_and_ingest(
            session=session,
            onyx=onyx,
            connector=connector,
            setting=setting,
            run=run,
            docs=docs,
            actor_id=actor_id,
        )
    except (ConnectorAdapterError, httpx.HTTPError, OnyxError, ConnectorSyncError) as exc:
        _mark_failed(run, setting, f"{type(exc).__name__}: {exc}")
        return run


def ingest_bridge_documents(
    *,
    session: Session,
    onyx: OnyxClient,
    connector: ConnectorSpec,
    actor_id: str,
    documents: list[SourceDocument],
    trigger: str = "bridge",
) -> ConnectorSyncRun:
    """Accept pre-normalized documents from an external source bridge/export job."""
    setting = get_or_create_connector_setting(session, connector, actor_id=actor_id)
    run = _sync_run(session, connector=connector, trigger=trigger)
    try:
        return _persist_and_ingest(
            session=session,
            onyx=onyx,
            connector=connector,
            setting=setting,
            run=run,
            docs=documents,
            actor_id=actor_id,
        )
    except (OnyxError, httpx.HTTPError, ConnectorSyncError) as exc:
        _mark_failed(run, setting, f"{type(exc).__name__}: {exc}")
        return run
