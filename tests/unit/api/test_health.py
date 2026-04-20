"""Health endpoint tests."""
from __future__ import annotations

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from dreamfi.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@respx.mock
def test_health_reports_onyx_reachable(client: TestClient) -> None:
    respx.get("http://localhost:8080/api/health").mock(return_value=httpx.Response(200))
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["onyx"] == "reachable"


@respx.mock
def test_health_reports_onyx_unreachable_on_5xx(client: TestClient) -> None:
    respx.get("http://localhost:8080/api/health").mock(
        side_effect=httpx.ConnectError("boom")
    )
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["onyx"] == "unreachable"
