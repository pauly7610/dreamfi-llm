"""Typed Jira REST v3 client.

Covers the narrow read-only surface the Context Engine needs:

- ``list_issues(jql)`` / ``get_issue(key)`` / ``get_epic_children(epic_key)``
- ``get_changelog(key)`` / ``list_sprints(board_id)`` / ``current_sprint(board_id)``

Nothing writes to Jira (PM reads only, for now).
"""
from __future__ import annotations

import base64
from datetime import datetime
from typing import Any

import httpx

from dreamfi.connectors.base import HttpConnector, connector_retry
from dreamfi.connectors.jira.models import (
    JiraChangelog,
    JiraIssue,
    JiraIssueLink,
    JiraSprint,
    JiraUser,
)


def _parse_dt(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _issue_from_json(obj: dict[str, Any]) -> JiraIssue:
    fields = obj.get("fields") or {}
    assignee = JiraUser(**fields["assignee"]) if fields.get("assignee") else None
    reporter = JiraUser(**fields["reporter"]) if fields.get("reporter") else None
    status_obj = fields.get("status") or {}
    issue_type_obj = fields.get("issuetype") or {}
    parent = fields.get("parent") or {}

    links: list[JiraIssueLink] = []
    for link in fields.get("issuelinks") or []:
        link_type = (link.get("type") or {}).get("name", "related")
        if "outwardIssue" in link:
            links.append(
                JiraIssueLink(
                    link_type=link_type,
                    target_key=link["outwardIssue"].get("key", ""),
                    direction="outward",
                )
            )
        elif "inwardIssue" in link:
            links.append(
                JiraIssueLink(
                    link_type=link_type,
                    target_key=link["inwardIssue"].get("key", ""),
                    direction="inward",
                )
            )

    # Sprints are commonly at customfield_10020; Jira clouds vary.
    sprint_ids: list[int] = []
    for cf in ("customfield_10020", "customfield_10010"):
        raw_sprints = fields.get(cf) or []
        if isinstance(raw_sprints, list):
            for s in raw_sprints:
                if isinstance(s, dict) and isinstance(s.get("id"), int):
                    sprint_ids.append(s["id"])

    return JiraIssue(
        key=obj.get("key", ""),
        summary=fields.get("summary") or "",
        status=status_obj.get("name") or "",
        issue_type=issue_type_obj.get("name") or "",
        assignee=assignee,
        reporter=reporter,
        parent_key=parent.get("key"),
        labels=list(fields.get("labels") or []),
        updated_at=_parse_dt(fields.get("updated")),
        created_at=_parse_dt(fields.get("created")),
        sprint_ids=sprint_ids,
        links=links,
    )


class JiraClient(HttpConnector):
    """Read-only Jira client. Workspace-scoped auth is the caller's concern."""

    health_path = "/rest/api/3/myself"

    def __init__(
        self,
        base_url: str,
        *,
        email: str,
        api_token: str,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._email = email
        self._api_token = api_token
        super().__init__(base_url, timeout=timeout, transport=transport)

    def _auth_headers(self) -> dict[str, str]:
        token = base64.b64encode(
            f"{self._email}:{self._api_token}".encode("utf-8")
        ).decode("ascii")
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {token}",
        }

    # --- issues --------------------------------------------------------------

    @connector_retry
    def list_issues(
        self,
        jql: str,
        *,
        fields: list[str] | None = None,
        max_results: int = 50,
    ) -> list[JiraIssue]:
        out: list[JiraIssue] = []
        start_at = 0
        field_param = ",".join(
            fields
            or [
                "summary",
                "status",
                "issuetype",
                "assignee",
                "reporter",
                "parent",
                "labels",
                "updated",
                "created",
                "issuelinks",
                "customfield_10020",
            ]
        )
        while True:
            resp = self._get(
                "/rest/api/3/search",
                params={
                    "jql": jql,
                    "startAt": start_at,
                    "maxResults": max_results,
                    "fields": field_param,
                },
            )
            data = resp.json()
            issues = data.get("issues") or []
            for obj in issues:
                out.append(_issue_from_json(obj))
            total = int(data.get("total", len(out)))
            start_at += len(issues)
            if start_at >= total or not issues:
                break
        return out

    @connector_retry
    def get_issue(self, key: str) -> JiraIssue:
        resp = self._get(f"/rest/api/3/issue/{key}")
        return _issue_from_json(resp.json())

    @connector_retry
    def get_epic_children(self, epic_key: str) -> list[JiraIssue]:
        jql = f'parent = "{epic_key}" OR "Epic Link" = "{epic_key}"'
        return self.list_issues(jql)

    @connector_retry
    def get_changelog(self, key: str) -> JiraChangelog:
        resp = self._get(f"/rest/api/3/issue/{key}/changelog")
        data = resp.json()
        return JiraChangelog(issue_key=key, entries=list(data.get("values") or []))

    # --- sprints -------------------------------------------------------------

    @connector_retry
    def list_sprints(self, board_id: int) -> list[JiraSprint]:
        resp = self._get(f"/rest/agile/1.0/board/{board_id}/sprint")
        data = resp.json()
        values = data.get("values") or []
        out: list[JiraSprint] = []
        for s in values:
            out.append(
                JiraSprint(
                    id=int(s.get("id", 0)),
                    name=s.get("name", ""),
                    state=s.get("state", "future"),
                    board_id=board_id,
                    start_date=_parse_dt(s.get("startDate")),
                    end_date=_parse_dt(s.get("endDate")),
                )
            )
        return out

    def current_sprint(self, board_id: int) -> JiraSprint | None:
        for s in self.list_sprints(board_id):
            if s.state == "active":
                return s
        return None
