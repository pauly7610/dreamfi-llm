from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from dreamfi.api.app import create_app
from dreamfi.config import get_settings


def _basic(username: str, password: str) -> dict[str, str]:
    encoded = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {encoded}"}


def test_auth_exempts_health_checks(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DREAMFI_AUTH_ENABLED", "true")
    monkeypatch.setenv("DREAMFI_AUTH_PASSWORD", "secret")
    get_settings.cache_clear()
    client = TestClient(create_app())

    assert client.get("/ready").status_code == 200


def test_auth_blocks_console_without_credentials(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DREAMFI_AUTH_ENABLED", "true")
    monkeypatch.setenv("DREAMFI_AUTH_PASSWORD", "secret")
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.get("/llms.txt")

    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


def test_auth_rejects_placeholder_secrets(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DREAMFI_AUTH_ENABLED", "true")
    monkeypatch.setenv("DREAMFI_AUTH_PASSWORD", "change-me-before-deploy")
    monkeypatch.setenv("DREAMFI_API_TOKEN", "change-me-before-deploy")
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.get("/llms.txt")

    assert response.status_code == 503


def test_auth_allows_basic_credentials(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DREAMFI_AUTH_ENABLED", "true")
    monkeypatch.setenv("DREAMFI_AUTH_USERNAME", "dreamfi")
    monkeypatch.setenv("DREAMFI_AUTH_PASSWORD", "secret")
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.get("/llms.txt", headers=_basic("dreamfi", "secret"))

    assert response.status_code == 200


def test_auth_allows_bearer_token(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DREAMFI_AUTH_ENABLED", "true")
    monkeypatch.delenv("DREAMFI_AUTH_PASSWORD", raising=False)
    monkeypatch.setenv("DREAMFI_API_TOKEN", "token-secret")
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.get(
        "/llms.txt",
        headers={"Authorization": "Bearer token-secret"},
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("authorization", "expected_header"),
    [
        ("Basic !!!not-base64!!!", "Basic"),
        ("Basic bm8tc2VwYXJhdG9y", "Basic"),
        ("Bearer wrong-token", "Bearer"),
    ],
)
def test_auth_rejects_malformed_or_invalid_authorization(
    authorization: str,
    expected_header: str,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DREAMFI_AUTH_ENABLED", "true")
    monkeypatch.setenv("DREAMFI_AUTH_USERNAME", "dreamfi")
    monkeypatch.setenv("DREAMFI_AUTH_PASSWORD", "secret")
    monkeypatch.setenv("DREAMFI_API_TOKEN", "token-secret")
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.get("/llms.txt", headers={"Authorization": authorization})

    assert response.status_code == 401
    assert expected_header in response.headers["WWW-Authenticate"]
