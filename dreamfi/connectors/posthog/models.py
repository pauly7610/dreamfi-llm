"""Typed shapes for PostHog."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PostHogResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    query_id: str
    result: list[dict[str, Any]] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)


class PostHogFeatureFlag(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key: str
    active: bool
    rollout_percentage: float | None = None
