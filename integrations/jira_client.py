"""Jira integration — wraps atlassian-python-api."""

from __future__ import annotations

import logging
from typing import Any

from atlassian import Jira

from config import config as _cfg
from config import JiraConfig
from integrations.errors import DreamFiIntegrationError

log = logging.getLogger(__name__)


class JiraClient:
    """Thin wrapper around the Jira REST API via atlassian-python-api."""

    def __init__(self, cfg: JiraConfig | None = None):
        c = cfg or _cfg.jira
        try:
            self._jira = Jira(url=c.url, username=c.email, password=c.api_token)
        except Exception as exc:
            raise DreamFiIntegrationError("jira", "Failed to initialise Jira client") from exc

    # ------------------------------------------------------------------
    # Epics
    # ------------------------------------------------------------------

    def get_epics(self, project_key: str, status_filter: str | None = None) -> list[dict[str, Any]]:
        """Return all epics in a project, optionally filtered by status."""
        jql = f'project = {project_key} AND issuetype = Epic'
        if status_filter:
            jql += f' AND status = "{status_filter}"'
        return self.search_issues(jql)

    def get_epic_stories(self, epic_key: str) -> list[dict[str, Any]]:
        """Return all stories linked to *epic_key*."""
        jql = f'"Epic Link" = {epic_key}'
        return self.search_issues(jql)

    # ------------------------------------------------------------------
    # Sprints
    # ------------------------------------------------------------------

    def get_sprint_data(self, board_id: int) -> dict[str, Any]:
        """Return the current active sprint and its velocity for *board_id*."""
        try:
            sprints = self._jira.get_all_sprint(board_id, state="active")
            if not sprints:
                return {"board_id": board_id, "active_sprint": None}
            sprint = sprints[0]
            sprint_id = sprint["id"]
            issues = self._jira.get_sprint_issues(sprint_id, start=0, limit=500)
            total_sp = 0
            completed_sp = 0
            for issue in issues.get("issues", []):
                sp = issue["fields"].get("story_points") or issue["fields"].get("customfield_10028") or 0
                total_sp += sp
                if issue["fields"].get("status", {}).get("statusCategory", {}).get("key") == "done":
                    completed_sp += sp
            log.info("Sprint %s: %s/%s SP completed", sprint["name"], completed_sp, total_sp)
            return {
                "board_id": board_id,
                "sprint": sprint,
                "total_story_points": total_sp,
                "completed_story_points": completed_sp,
            }
        except Exception as exc:
            raise DreamFiIntegrationError("jira", f"Failed to get sprint data for board {board_id}") from exc

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

    def create_epic(
        self, project_key: str, summary: str, description: str, fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new epic in *project_key*."""
        try:
            payload: dict[str, Any] = {
                "project": {"key": project_key},
                "issuetype": {"name": "Epic"},
                "summary": summary,
                "description": description,
            }
            if fields:
                payload.update(fields)
            result = self._jira.issue_create(fields=payload)
            log.info("Created epic %s in %s", result.get("key"), project_key)
            return result
        except Exception as exc:
            raise DreamFiIntegrationError("jira", f"Failed to create epic in {project_key}") from exc

    def search_issues(self, jql: str, max_results: int = 200) -> list[dict[str, Any]]:
        """Execute a JQL query and return matching issues."""
        try:
            data = self._jira.jql(jql, limit=max_results)
            return data.get("issues", [])
        except Exception as exc:
            raise DreamFiIntegrationError("jira", f"JQL query failed: {jql}") from exc

    def get_issue(self, key: str) -> dict[str, Any]:
        """Fetch a single issue by key."""
        try:
            return self._jira.issue(key)
        except Exception as exc:
            raise DreamFiIntegrationError("jira", f"Failed to get issue {key}") from exc

    def update_issue(self, key: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Update fields on an existing issue."""
        try:
            self._jira.issue_update(key, fields)
            log.info("Updated issue %s", key)
            return self.get_issue(key)
        except Exception as exc:
            raise DreamFiIntegrationError("jira", f"Failed to update issue {key}") from exc

    def get_fields_for_issue(self, key: str) -> list[dict[str, Any]]:
        """Return the field metadata for *key* (useful for auditing custom fields)."""
        try:
            issue = self._jira.issue(key)
            fields = issue.get("fields", {})
            return [{"key": k, "value_type": type(v).__name__} for k, v in fields.items()]
        except Exception as exc:
            raise DreamFiIntegrationError("jira", f"Failed to list fields for {key}") from exc
