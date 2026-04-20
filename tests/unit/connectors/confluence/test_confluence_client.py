"""C2b: ConfluenceClient contract tests."""
from __future__ import annotations

import re

import httpx
import pytest
import respx

from dreamfi.connectors import ConnectorAuthError
from dreamfi.connectors.confluence import ConfluenceClient

BASE_URL = "https://acme.atlassian.net"


def _client() -> ConfluenceClient:
    return ConfluenceClient(base_url=BASE_URL, email="pm@acme.test", api_token="t")


@respx.mock
def test_get_page_returns_body_storage() -> None:
    respx.get(f"{BASE_URL}/wiki/api/v2/pages/18432").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 18432,
                "title": "Onboarding v3",
                "spaceId": 7,
                "parentId": "123",
                "body": {"storage": {"value": "<p>Context</p>"}},
                "version": {
                    "authorId": "laila",
                    "createdAt": "2026-04-15T09:00:00Z",
                    "number": 4,
                },
                "_links": {"webui": "/display/PM/Onboarding+v3"},
            },
        )
    )
    page = _client().get_page("18432")
    assert page.title == "Onboarding v3"
    assert page.body_storage == "<p>Context</p>"
    assert page.author_account_id == "laila"
    assert page.url == "/display/PM/Onboarding+v3"


@respx.mock
def test_search_skips_non_page_hits() -> None:
    respx.get(f"{BASE_URL}/wiki/rest/api/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"content": {"id": "1", "type": "page", "title": "P1"}},
                    {"content": {"id": "2", "type": "blogpost", "title": "B1"}},
                ]
            },
        )
    )
    pages = _client().search("text ~ onboarding")
    assert [p.id for p in pages] == ["1"]


@respx.mock
def test_list_children_returns_pages() -> None:
    respx.get(f"{BASE_URL}/wiki/api/v2/pages/18432/children").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"id": 18433, "title": "Child A", "spaceId": 7},
                    {"id": 18434, "title": "Child B", "spaceId": 7},
                ]
            },
        )
    )
    children = _client().list_children("18432")
    assert [c.title for c in children] == ["Child A", "Child B"]


@respx.mock
def test_history_parses_versions() -> None:
    respx.get(f"{BASE_URL}/wiki/api/v2/pages/18432/versions").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "number": 1,
                        "createdAt": "2026-04-10T09:00:00Z",
                        "authorId": "laila",
                    },
                    {
                        "number": 2,
                        "createdAt": "2026-04-15T09:00:00Z",
                        "authorId": "sam",
                        "message": "clarified EU rollout",
                    },
                ]
            },
        )
    )
    hist = _client().get_page_history("18432")
    assert [h.version for h in hist] == [1, 2]
    assert hist[1].message == "clarified EU rollout"


@respx.mock
def test_auth_failure_raises() -> None:
    respx.get(re.compile(f"{BASE_URL}/wiki/api/v2/pages/.*")).mock(
        return_value=httpx.Response(401, json={})
    )
    with pytest.raises(ConnectorAuthError):
        _client().get_page("1")


@respx.mock
def test_ping_reachable_when_spaces_200() -> None:
    respx.get(f"{BASE_URL}/wiki/api/v2/spaces").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    assert _client().ping() == "reachable"
