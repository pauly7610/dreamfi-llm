"""High-level Jira fetcher for the Context Engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from dreamfi.connectors.base import TTLCache
from dreamfi.connectors.jira.client import JiraClient
from dreamfi.connectors.jira.models import JiraChangelog, JiraIssue


@dataclass
class JiraTopicBundle:
    issues: list[JiraIssue] = field(default_factory=list)
    changelogs: dict[str, JiraChangelog] = field(default_factory=dict)


def fetch_topic_jira(
    client: JiraClient,
    *,
    workspace_id: str,
    topic: str,
    epic_key: str | None = None,
    since: datetime | None = None,
    cache: TTLCache | None = None,
    changelog_for: int = 10,
) -> JiraTopicBundle:
    """Gather the Jira slice of context for a topic.

    If ``epic_key`` is supplied, we fetch that epic's children. Otherwise we
    fall back to a text search on ``summary ~ "topic"``. Changelogs are
    fetched for the first ``changelog_for`` issues to keep the round trip
    bounded.
    """
    since = since or (datetime.now(timezone.utc) - timedelta(days=30))
    cache_key = f"fetch_topic/{epic_key or topic}/{since.date().isoformat()}"
    if cache is not None:
        cached = cache.get(workspace_id=workspace_id, endpoint=cache_key)
        if cached is not None:
            assert isinstance(cached, JiraTopicBundle)
            return cached

    if epic_key:
        issues = client.get_epic_children(epic_key)
    else:
        escaped = topic.replace('"', '\\"')
        jql = f'summary ~ "{escaped}" AND updated >= "{since.date().isoformat()}"'
        issues = client.list_issues(jql)

    changelogs: dict[str, JiraChangelog] = {}
    for issue in issues[:changelog_for]:
        try:
            changelogs[issue.key] = client.get_changelog(issue.key)
        except Exception:  # noqa: BLE001 — best-effort; changelog is non-critical
            continue

    bundle = JiraTopicBundle(issues=issues, changelogs=changelogs)
    if cache is not None:
        cache.set(
            workspace_id=workspace_id,
            endpoint=cache_key,
            value=bundle,
            ttl_seconds=300.0,
        )
    return bundle
