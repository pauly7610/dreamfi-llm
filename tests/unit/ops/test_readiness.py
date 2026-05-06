from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import respx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dreamfi.connectors import CONNECTORS
from dreamfi.db.models import (
    ArtifactFeedback,
    Base,
    ConsoleTopic,
    EvalOutput,
    LearningProposal,
    ProductionOutcome,
    ReplaySchedule,
)
from dreamfi.onyx.client import OnyxClient
from dreamfi.ops.demo import seed_demo_data
from dreamfi.ops.readiness import (
    bootstrap_connector_document_sets,
    connector_readiness,
    ops_status,
)


def _session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path}/dreamfi.db")
    Base.metadata.create_all(engine)
    return Session(engine)


@respx.mock
def test_bootstrap_connector_document_sets_creates_missing_expected_docsets() -> None:
    onyx = OnyxClient(base_url="http://onyx.test", api_key="k")
    respx.get("http://onyx.test/api/document-set").mock(
        return_value=httpx.Response(200, json={"document_sets": []})
    )
    created_names: list[str] = []

    def _create(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        created_names.append(payload["name"])
        return httpx.Response(
            200,
            json={
                "id": len(created_names),
                "name": payload["name"],
                "description": payload["description"],
            },
        )

    respx.post("http://onyx.test/api/admin/document-set").mock(side_effect=_create)

    rows = bootstrap_connector_document_sets(onyx=onyx, apply=True)

    assert len(rows) == len(CONNECTORS)
    assert all(row["exists"] for row in rows)
    assert {connector.expected_document_set for connector in CONNECTORS} == set(created_names)


@respx.mock
def test_connector_readiness_checks_docsets_and_freshness() -> None:
    onyx = OnyxClient(base_url="http://onyx.test", api_key="k")
    respx.get("http://onyx.test/api/document-set").mock(
        return_value=httpx.Response(
            200,
            json={
                "document_sets": [
                    {"id": 1, "name": "dreamfi-source-jira"},
                    {"id": 2, "name": "dreamfi-source-socure"},
                ]
            },
        )
    )
    fresh_timestamp = datetime.now(timezone.utc).isoformat()

    def _search_response(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        source_id = payload["filters"]["dreamfi_scope"]["source_ids"][0]
        updated_at = fresh_timestamp if source_id == "jira" else "2020-01-01T00:00:00Z"
        return httpx.Response(
            200,
            json={
                "documents": [
                    {
                        "document_id": f"{source_id}-doc",
                        "semantic_identifier": f"{source_id} evidence",
                        "blurb": "Recent connector evidence.",
                        "score": 0.91,
                        "updated_at": updated_at,
                    }
                ]
            },
        )

    respx.post("http://onyx.test/api/admin/search").mock(side_effect=_search_response)

    payload = connector_readiness(onyx=onyx)

    rows = {row["connector_id"]: row for row in payload["connectors"]}
    assert rows["jira"]["status"] == "connected"
    assert rows["socure"]["status"] == "degraded"
    assert rows["klaviyo"]["status"] == "not_configured"


def test_seed_demo_data_is_idempotent_and_populates_review_loop(tmp_path: Path) -> None:
    session = _session(tmp_path)

    first = seed_demo_data(session)
    second = seed_demo_data(session)

    assert first == second
    assert session.query(ConsoleTopic).count() == 2
    assert session.query(EvalOutput).count() == 3
    assert session.query(ArtifactFeedback).count() == 2
    assert session.query(ProductionOutcome).count() == 1
    assert session.query(LearningProposal).count() == 1
    assert session.query(ReplaySchedule).count() == 1


@respx.mock
def test_ops_status_reports_degraded_until_connectors_are_live(tmp_path: Path) -> None:
    session = _session(tmp_path)
    seed_demo_data(session)
    onyx = OnyxClient(base_url="http://onyx.test", api_key="k")
    respx.get("http://onyx.test/api/health").mock(return_value=httpx.Response(200))
    respx.get("http://onyx.test/api/document-set").mock(
        return_value=httpx.Response(200, json={"document_sets": []})
    )

    payload = ops_status(session, onyx)

    assert payload["status"] == "degraded"
    assert "connectors" in payload["failures"]
    assert payload["database"]["status"] == "ok"
    assert payload["onyx"]["status"] == "reachable"
