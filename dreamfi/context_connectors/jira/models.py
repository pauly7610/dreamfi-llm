"""Typed Pydantic views over Jira REST v3 responses (subset DreamFi needs)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JiraUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    account_id: str = Field(alias="accountId")
    display_name: str = Field(alias="displayName")
    email_address: str | None = Field(default=None, alias="emailAddress")


class JiraIssueLink(BaseModel):
    model_config = ConfigDict(extra="ignore")

    link_type: str
    target_key: str
    direction: str  # "outward" | "inward"


class JiraIssue(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key: str
    summary: str
    status: str
    issue_type: str
    assignee: JiraUser | None = None
    reporter: JiraUser | None = None
    parent_key: str | None = None
    labels: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None
    created_at: datetime | None = None
    sprint_ids: list[int] = Field(default_factory=list)
    links: list[JiraIssueLink] = Field(default_factory=list)


class JiraChangelog(BaseModel):
    model_config = ConfigDict(extra="ignore")

    issue_key: str
    entries: list[dict[str, Any]] = Field(default_factory=list)


class JiraSprint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    state: str  # "active" | "closed" | "future"
    board_id: int
    start_date: datetime | None = None
    end_date: datetime | None = None
