from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dreamfi.api.app import create_app
from dreamfi.api.deps import get_db_session, get_onyx_client
from dreamfi.config import get_settings
from dreamfi.db.models import AuditEvent, Base, ConnectorDocument, ConnectorSetting
from dreamfi.onyx.client import OnyxClient


def _session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    return Session(engine)


def _client(session: Session) -> TestClient:
    app = create_app()

    def _session_override():
        yield session

    def _onyx_override() -> OnyxClient:
        return OnyxClient(base_url="http://onyx.test", api_key="k")

    app.dependency_overrides[get_db_session] = _session_override
    app.dependency_overrides[get_onyx_client] = _onyx_override
    return TestClient(app)


@respx.mock
def test_settings_status_surfaces_persistence_and_connector_blockers(tmp_path: Path) -> None:
    session = _session(tmp_path)
    respx.get("http://onyx.test/api/document-set").mock(
        return_value=httpx.Response(200, json={"document_sets": []})
    )

    response = _client(session).get("/api/settings/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert "persistence" in body["failures"]
    assert body["persistence"]["uses_sqlite"] is True
    jira = next(row for row in body["connectors"] if row["connector_id"] == "jira")
    assert jira["credential"]["status"] == "missing"
    assert jira["credential"]["required"] is False
    assert jira["connection_method"] == "onyx_native"
    assert jira["setup_method"] == "Onyx native connector"
    assert {"document_set", "persistence"} <= set(jira["blockers"])
    assert "credential" not in jira["blockers"]
    metabase = next(row for row in body["connectors"] if row["connector_id"] == "metabase")
    assert metabase["credential"]["required"] is True
    assert metabase["credential"]["usable"] is False
    assert {"credential", "configuration"} <= set(metabase["blockers"])


@respx.mock
def test_connector_config_save_persists_allowed_fields_and_audits(
    tmp_path: Path,
) -> None:
    session = _session(tmp_path)
    respx.get("http://onyx.test/api/document-set").mock(
        return_value=httpx.Response(200, json={"document_sets": []})
    )

    response = _client(session).post(
        "/api/settings/connectors/metabase/config",
        json={
            "config": {
                "base_url": "https://metabase.company.test",
                "ignored": "nope",
            }
        },
    )

    assert response.status_code == 200, response.text
    connector = response.json()["connector"]
    expected_config = {
        "auth_header": "x-api-key",
        "auth_scheme": "",
        "base_url": "https://metabase.company.test",
        "endpoints": "/api/card,/api/dashboard",
    }
    assert connector["config"]["values"] == expected_config
    assert connector["config"]["missing_keys"] == []
    row = session.get(ConnectorSetting, "metabase")
    assert row is not None
    assert row.config_json == expected_config
    audit = session.query(AuditEvent).filter_by(action="connector_config_save").one()
    assert audit.metadata_json["config_keys"] == ["auth_header", "auth_scheme", "base_url", "endpoints"]


@respx.mock
def test_custom_connector_secret_requires_encryption_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DREAMFI_CONNECTOR_SECRET_KEY", raising=False)
    get_settings.cache_clear()
    session = _session(tmp_path)

    response = _client(session).post(
        "/api/settings/connectors/metabase/secret",
        json={"api_key": "metabase-secret-token"},
    )

    assert response.status_code == 422
    assert "DREAMFI_CONNECTOR_SECRET_KEY" in response.text
    assert session.get(ConnectorSetting, "metabase") is None


@respx.mock
def test_connector_secret_save_redacts_raw_key_and_audits_metadata(tmp_path: Path) -> None:
    session = _session(tmp_path)
    respx.get("http://onyx.test/api/document-set").mock(
        return_value=httpx.Response(200, json={"document_sets": []})
    )
    raw_key = "jira-live-token-123456"

    response = _client(session).post(
        "/api/settings/connectors/jira/secret",
        json={"api_key": raw_key, "label": "prod jira"},
    )

    assert response.status_code == 201, response.text
    payload_text = response.text
    assert raw_key not in payload_text
    assert "3456" in payload_text
    row = session.get(ConnectorSetting, "jira")
    assert row is not None
    assert row.credential_status == "saved"
    assert row.validation_status == "not_validated"
    assert row.secret_last_four == "3456"
    assert row.secret_sha256 is not None
    assert raw_key not in json.dumps(row.metadata_json)
    audit = session.query(AuditEvent).filter_by(action="connector_secret_save").one()
    assert raw_key not in json.dumps(audit.metadata_json)
    assert audit.metadata_json["secret_sha256"] == row.secret_sha256


@respx.mock
def test_connector_secret_rejects_placeholder_values(tmp_path: Path) -> None:
    session = _session(tmp_path)

    response = _client(session).post(
        "/api/settings/connectors/jira/secret",
        json={"api_key": "change-me-before-deploy"},
    )

    assert response.status_code == 422
    assert session.get(ConnectorSetting, "jira") is None
    audit = session.query(AuditEvent).filter_by(action="connector_secret_save").one()
    assert audit.outcome == "blocked"


@respx.mock
def test_document_set_setup_creates_missing_connector_docset(tmp_path: Path) -> None:
    session = _session(tmp_path)
    respx.get("http://onyx.test/api/document-set").mock(
        return_value=httpx.Response(200, json={"document_sets": []})
    )
    created_payloads: list[dict[str, object]] = []

    def _create(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        created_payloads.append(payload)
        return httpx.Response(200, json={"id": 42, "name": payload["name"]})

    respx.post("http://onyx.test/api/admin/document-set").mock(side_effect=_create)

    response = _client(session).post("/api/settings/connectors/jira/document-set")

    assert response.status_code == 200, response.text
    assert created_payloads[0]["name"] == "dreamfi-source-jira"
    row = session.get(ConnectorSetting, "jira")
    assert row is not None
    assert row.document_set_present is True
    assert row.document_set_id == 42
    audit = session.query(AuditEvent).filter_by(action="connector_document_set_ensure").one()
    assert audit.target_id == "jira"


@respx.mock
def test_validate_records_probe_result_and_activation_blocks_without_persistence(tmp_path: Path) -> None:
    session = _session(tmp_path)
    client = _client(session)
    fresh_timestamp = datetime.now(timezone.utc).isoformat()
    respx.get("http://onyx.test/api/document-set").mock(
        return_value=httpx.Response(
            200,
            json={"document_sets": [{"id": 1, "name": "dreamfi-source-jira"}]},
        )
    )
    respx.post("http://onyx.test/api/admin/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "documents": [
                    {
                        "document_id": "jira-doc-1",
                        "semantic_identifier": "Jira evidence",
                        "blurb": "Recent delivery evidence.",
                        "score": 0.91,
                        "updated_at": fresh_timestamp,
                    }
                ]
            },
        )
    )
    validate_response = client.post("/api/settings/connectors/jira/validate")
    activate_response = client.post("/api/settings/connectors/jira/activate")

    assert validate_response.status_code == 200, validate_response.text
    connector = validate_response.json()["connector"]
    assert connector["validation_status"] == "validated"
    assert connector["document_set_present"] is True
    assert connector["retrieval_status"] == "fresh"
    assert activate_response.status_code == 422
    assert "persistence" in activate_response.json()["detail"]["blockers"]


@respx.mock
def test_delete_secret_deactivates_connector(tmp_path: Path) -> None:
    session = _session(tmp_path)
    respx.get("http://onyx.test/api/document-set").mock(
        return_value=httpx.Response(200, json={"document_sets": []})
    )
    client = _client(session)
    client.post(
        "/api/settings/connectors/jira/secret",
        json={"api_key": "jira-live-token-123456"},
    )

    response = client.delete("/api/settings/connectors/jira/secret")

    assert response.status_code == 200, response.text
    row = session.get(ConnectorSetting, "jira")
    assert row is not None
    assert row.credential_status == "missing"
    assert row.secret_sha256 is None
    assert row.activation_status == "inactive"


@respx.mock
def test_bridge_document_ingest_persists_and_audits_without_raw_text(tmp_path: Path) -> None:
    session = _session(tmp_path)
    respx.get("http://onyx.test/api/document-set").mock(
        return_value=httpx.Response(200, json={"document_sets": []})
    )
    respx.post("http://onyx.test/api/admin/document-set").mock(
        return_value=httpx.Response(200, json={"id": 12, "name": "dreamfi-source-socure"})
    )
    respx.post("http://onyx.test/api/onyx-api/ingestion").mock(
        return_value=httpx.Response(200, json={"document_id": "socure-doc", "already_existed": False})
    )
    raw_text = "KYC approval trend improved for thin-file applicants."

    response = _client(session).post(
        "/api/settings/connectors/socure/documents",
        json={
            "documents": [
                {
                    "external_id": "decision-summary-1",
                    "title": "Socure decision summary",
                    "text": raw_text,
                    "updated_at": "2026-05-07T12:30:00Z",
                    "metadata": {"product_area": "identity", "topic_ids": ["kyc"]},
                }
            ]
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["sync_run"]["status"] == "success"
    document = session.query(ConnectorDocument).filter_by(connector_id="socure").one()
    assert document.title == "Socure decision summary"
    assert document.metadata_json["dreamfi_scope"]["source_ids"] == ["socure"]
    audit = session.query(AuditEvent).filter_by(action="connector_bridge_ingest").one()
    assert raw_text not in json.dumps(audit.metadata_json)
