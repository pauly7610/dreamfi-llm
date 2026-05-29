"""Typed shapes for Metabase."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MetabaseCardResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    card_id: int
    rows: list[list[Any]] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)


class MetabaseDatasetResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    database_id: int
    rows: list[list[Any]] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
