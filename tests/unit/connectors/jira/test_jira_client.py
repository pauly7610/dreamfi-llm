"""C2a: JiraClient contract tests — all HTTP respx-mocked."""
from __future__ import annotations

import re

import httpx
import pytest
import respx

from dreamfi.connectors import (
    ConnectorAuthError,
    ConnectorNotFoundError,
    ConnectorServerError,
    TTLCache,
)
from dreamfi.connectors.jira import JiraClient, fetch_topic_jira

BASE_URL = "https://acme.atlassian.net"


def _client() -> JiraClient:
    return JiraClient(base_url=BASE_URL, email="pm@acme.test", api_token="t0k3n")


@respx.mock
def test_ping_returns_reachable_when_myself_200() -> None:
    respx.get(f"{BASE_URL}/rest/api/3/myself").mock(
        return_value=httpx.Response(200, json={"accountId": "abc"})
    )
    assert _client().ping() == "reachable"


@respx.mock
def test_ping_returns_unreachable_when_5xx() -> None:
    respx.get(f"{BASE_URL}/rest/api/3/myself").mock(
        return_value=httpx.Response(503, text="down")
    )
    assert _client().ping() == "unreachable"


@respx.mock
def test_auth_failure_raises_connector_auth_error() -> None:
    respx.get(re.compile(f"{BASE_URL}/rest/api/3/issue/.*")).mock(
        return_value=httpx.Response(401, json={"error": "bad token"})
    )
    with pytest.raises(ConnectorAuthError):
        _client().get_issue("ACT-1")


@respx.mock
def test_get_issue_not_found_raises() -> None:
    respx.get(re.compile(f"{BASE_URL}/rest/api/3/issue/.*")).mock(
        return_value=httpx.Response(404, json={})
    )
    with pytest.raises(ConnectorNotFoundError):
        _client().get_issue("ACT-404")


@respx.mock
def test_list_issues_paginates() -> None:
    # First page: 2 issues of total 3.
    route = respx.get(f"{BASE_URL}/rest/api/3/search")
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "issues": [
                    {
                        "key": "ACT-1",
                        "fields": {
                            "summary": "Beta launch",
                            "status": {"name": "In Progress"},
                            "issuetype": {"name": "Story"},
                            "updated": "2026-04-18T10:00:00.000+0000",
                        },
                    },
                    {
                        "key": "ACT-2",
                        "fields": {
                            "summary": "Design review",
                            "status": {"name": "Blocked"},
                            "issuetype": {"name": "Task"},
                            "updated": "2026-04-19T09:00:00.000+0000",
                        },
                    },
                ],
                "total": 3,
            },
        ),
        httpx.Response(
            200,
            json={
                "issues": [
                    {
                        "key": "ACT-3",
                        "fields": {
                            "summary": "Pricing copy",
                            "status": {"name": "Done"},
                            "issuetype": {"name": "Task"},
                        },
                    }
                ],
                "total": 3,
            },
        ),
    ]

    issues = _client().list_issues('summary ~ "beta"', max_results=2)
    assert [i.key for i in issues] == ["ACT-1", "ACT-2", "ACT-3"]
    assert issues[0].status == "In Progress"
    assert issues[1].status == "Blocked"
    assert route.call_count == 2


@respx.mock
def test_get_epic_children_uses_parent_jql() -> None:
    route = respx.get(f"{BASE_URL}/rest/api/3/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "issues": [
                    {
                        "key": "ACT-42",
                        "fields": {
                            "summary": "Child task",
                            "status": {"name": "To Do"},
                            "issuetype": {"name": "Task"},
                            "parent": {"key": "ACT-321"},
                        },
                    }
                ],
                "total": 1,
            },
        )
    )

    issues = _client().get_epic_children("ACT-321")
    assert len(issues) == 1
    assert issues[0].parent_key == "ACT-321"
    # The JQL must reference the epic — either as parent or Epic Link.
    sent_jql = route.calls.last.request.url.params["jql"]
    assert "ACT-321" in sent_jql


@respx.mock
def test_current_sprint_picks_active() -> None:
    respx.get(f"{BASE_URL}/rest/agile/1.0/board/7/sprint").mock(
        return_value=httpx.Response(
            200,
            json={
                "values": [
                    {"id": 1, "name": "Sprint 7", "state": "closed"},
                    {"id": 2, "name": "Sprint 8", "state": "active"},
                    {"id": 3, "name": "Sprint 9", "state": "future"},
                ]
            },
        )
    )
    sprint = _client().current_sprint(7)
    assert sprint is not None
    assert sprint.id == 2
    assert sprint.state == "active"


@respx.mock
def test_changelog_returns_entries() -> None:
    respx.get(f"{BASE_URL}/rest/api/3/issue/ACT-1/changelog").mock(
        return_value=httpx.Response(
            200,
            json={
                "values": [
                    {"id": "1", "created": "2026-04-18T10:00:00.000+0000"},
                    {"id": "2", "created": "2026-04-19T10:00:00.000+0000"},
                ]
            },
        )
    )
    cl = _client().get_changelog("ACT-1")
    assert cl.issue_key == "ACT-1"
    assert len(cl.entries) == 2


@respx.mock
def test_server_error_retries_and_eventually_surfaces() -> None:
    route = respx.get(re.compile(f"{BASE_URL}/rest/api/3/issue/.*")).mock(
        return_value=httpx.Response(503, text="upstream down")
    )
    with pytest.raises(ConnectorServerError):
        _client().get_issue("ACT-1")
    # 3 attempts per the connector retry envelope.
    assert route.call_count == 3


@respx.mock
def test_fetch_topic_jira_uses_epic_when_provided(tmp_path: None = None) -> None:
    respx.get(f"{BASE_URL}/rest/api/3/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "issues": [
                    {
                        "key": "ACT-10",
                        "fields": {
                            "summary": "Child",
                            "status": {"name": "To Do"},
                            "issuetype": {"name": "Task"},
                            "parent": {"key": "ACT-321"},
                        },
                    }
                ],
                "total": 1,
            },
        )
    )
    respx.get(re.compile(f"{BASE_URL}/rest/api/3/issue/.*/changelog")).mock(
        return_value=httpx.Response(200, json={"values": []})
    )
    bundle = fetch_topic_jira(
        _client(),
        workspace_id="w1",
        topic="onboarding",
        epic_key="ACT-321",
    )
    assert [i.key for i in bundle.issues] == ["ACT-10"]
    assert "ACT-10" in bundle.changelogs


@respx.mock
def test_fetch_topic_jira_uses_cache_on_second_call() -> None:
    route = respx.get(f"{BASE_URL}/rest/api/3/search").mock(
        return_value=httpx.Response(200, json={"issues": [], "total": 0})
    )
    cache = TTLCache(default_ttl_seconds=60.0)
    fetch_topic_jira(
        _client(), workspace_id="w1", topic="x", epic_key="E-1", cache=cache
    )
    fetch_topic_jira(
        _client(), workspace_id="w1", topic="x", epic_key="E-1", cache=cache
    )
    assert route.call_count == 1  # second call hit the cache
