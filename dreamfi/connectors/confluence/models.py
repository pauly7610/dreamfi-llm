"""Typed views over Confluence REST v2 responses."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConfluencePage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    space_id: str | None = None
    parent_id: str | None = None
    body_storage: str | None = None
    updated_at: datetime | None = None
    author_account_id: str | None = None
    url: str | None = None


class ConfluenceHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: int
    when: datetime | None = None
    by_account_id: str | None = None
    message: str | None = Field(default=None)
