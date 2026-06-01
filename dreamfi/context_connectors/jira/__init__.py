"""Jira connector (C2a).

This package is the ONLY allowed import path for Jira. Nothing else in
DreamFi may import ``httpx`` to talk to Jira directly.
"""

from dreamfi.context_connectors.jira.client import JiraClient
from dreamfi.context_connectors.jira.fetcher import JiraTopicBundle, fetch_topic_jira
from dreamfi.context_connectors.jira.models import (
    JiraChangelog,
    JiraIssue,
    JiraIssueLink,
    JiraSprint,
    JiraUser,
)

__all__ = [
    "JiraChangelog",
    "JiraClient",
    "JiraIssue",
    "JiraIssueLink",
    "JiraSprint",
    "JiraTopicBundle",
    "JiraUser",
    "fetch_topic_jira",
]
