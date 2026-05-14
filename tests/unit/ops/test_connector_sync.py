from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dreamfi.config import get_settings
from dreamfi.connectors import CONNECTOR_BY_ID, CONNECTORS
from dreamfi.connector_sync.providers import ADAPTERS
from dreamfi.connector_sync.service import sync_connector
from dreamfi.db.models import Base, ConnectorDocument, ConnectorSetting
from dreamfi.onyx.client import OnyxClient
from dreamfi.settings_activation import upsert_connector_config, upsert_connector_secret


def _session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    return Session(engine)


@respx.mock
def test_custom_connector_sync_persists_and_ingests_changed_documents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DREAMFI_CONNECTOR_SECRET_KEY", "unit-test-connector-secret-key")
    get_settings.cache_clear()
    session = _session(tmp_path)
    connector = CONNECTOR_BY_ID["metabase"]
    upsert_connector_config(
        session,
        connector=connector,
        config_values={"base_url": "http://metabase.test"},
        actor_id="tester",
    )
    upsert_connector_secret(
        session,
        connector=connector,
        api_key="metabase-live-token",
        actor_id="tester",
    )
    session.commit()

    respx.get("http://onyx.test/api/document-set").mock(
        return_value=httpx.Response(200, json={"document_sets": []})
    )
    respx.post("http://onyx.test/api/admin/document-set").mock(
        return_value=httpx.Response(200, json={"id": 77, "name": "dreamfi-source-metabase"})
    )
    ingest_route = respx.post("http://onyx.test/api/onyx-api/ingestion").mock(
        return_value=httpx.Response(200, json={"document_id": "onyx-doc-1", "already_existed": False})
    )
    card_route = respx.get("http://metabase.test/api/card").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "id": 10,
                    "name": "KYC conversion",
                    "updated_at": "2026-05-07T12:00:00Z",
                    "dataset_query": {"database": 1},
                }
            ],
        )
    )
    respx.get("http://metabase.test/api/dashboard").mock(
        return_value=httpx.Response(200, json=[])
    )

    run = sync_connector(
        session=session,
        onyx=OnyxClient(base_url="http://onyx.test", api_key="onyx"),
        connector=connector,
        actor_id="tester",
    )

    assert run.status == "success"
    assert run.pulled_count == 1
    assert run.persisted_count == 1
    assert run.ingested_count == 1
    assert card_route.calls.last.request.headers["x-api-key"] == "metabase-live-token"
    body = json.loads(ingest_route.calls.last.request.content)
    assert body["document"]["id"].startswith("dreamfi:metabase:")
    assert body["document"]["metadata"]["dreamfi_scope"]["source_ids"] == ["metabase"]
    assert "metabase-live-token" not in json.dumps(body)
    row = session.query(ConnectorDocument).filter_by(connector_id="metabase").one()
    assert row.title == "KYC conversion"
    assert row.onyx_document_id == "onyx-doc-1"
    setting = session.get(ConnectorSetting, "metabase")
    assert setting is not None
    assert setting.retrieval_status == "fresh"
    assert setting.secret_ciphertext is not None
    assert "metabase-live-token" not in setting.secret_ciphertext
    get_settings.cache_clear()


def test_all_custom_connectors_have_registered_adapters() -> None:
    custom_connector_ids = {
        connector.connector_id
        for connector in CONNECTORS
        if connector.connection_method == "custom_ingestion"
    }
    assert custom_connector_ids == set(ADAPTERS)


def test_custom_connector_schema_exposes_adapter_configuration() -> None:
    expected_fields = {
        "dragonboat": {"base_url", "endpoints", "auth_header", "auth_scheme", "product_area", "topic_ids", "owner"},
        "metabase": {"base_url", "endpoints", "auth_header", "auth_scheme", "product_area", "topic_ids", "owner"},
        "posthog": {"project_id", "base_url", "endpoints", "product_area", "topic_ids", "owner"},
        "ga": {
            "property_id",
            "base_url",
            "start_date",
            "end_date",
            "dimensions",
            "metrics",
            "product_area",
            "topic_ids",
            "owner",
        },
        "klaviyo": {"base_url", "endpoints", "revision", "product_area", "topic_ids", "owner"},
        "netxd": {"base_url", "endpoints", "auth_header", "auth_scheme", "product_area", "topic_ids", "owner"},
        "sardine": {"base_url", "endpoints", "auth_header", "auth_scheme", "product_area", "topic_ids", "owner"},
        "socure": {"base_url", "endpoints", "auth_header", "auth_scheme", "product_area", "topic_ids", "owner"},
    }
    for connector_id, field_keys in expected_fields.items():
        connector = CONNECTOR_BY_ID[connector_id]
        assert {field.key for field in connector.config_fields} >= field_keys


@respx.mock
def test_ga_adapter_uses_configurable_report_shape() -> None:
    connector = CONNECTOR_BY_ID["ga"]
    route = respx.post("http://ga.test/v1beta/properties/987654:runReport").mock(
        return_value=httpx.Response(
            200,
            json={
                "rows": [
                    {
                        "dimensionValues": [{"value": "US"}, {"value": "mobile"}],
                        "metricValues": [{"value": "12"}, {"value": "9"}],
                    }
                ]
            },
        )
    )

    docs = ADAPTERS["ga"].fetch_documents(
        connector=connector,
        config={
            "property_id": "987654",
            "base_url": "http://ga.test",
            "start_date": "2026-05-01",
            "end_date": "2026-05-07",
            "dimensions": "country,deviceCategory",
            "metrics": "sessions,engagedSessions",
            "product_area": "growth",
            "topic_ids": "acquisition,conversion",
            "owner": "analytics@dreamfi.com",
        },
        secret="ga-token",
        limit=10,
    )

    body = json.loads(route.calls.last.request.content)
    assert body["dateRanges"] == [{"startDate": "2026-05-01", "endDate": "2026-05-07"}]
    assert body["dimensions"] == [{"name": "country"}, {"name": "deviceCategory"}]
    assert body["metrics"] == [{"name": "sessions"}, {"name": "engagedSessions"}]
    assert route.calls.last.request.headers["authorization"] == "Bearer ga-token"
    assert docs[0].metadata["product_area"] == "growth"
    assert docs[0].metadata["topic_ids"] == ["acquisition", "conversion"]
    assert docs[0].metadata["owner"] == "analytics@dreamfi.com"
