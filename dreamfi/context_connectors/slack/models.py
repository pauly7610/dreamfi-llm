"""Typed Slack shapes."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SlackChannel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    is_archived: bool = False


class SlackMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    channel_id: str
    ts: str
    user_id: str | None = None
    text: str = ""
    thread_ts: str | None = None
