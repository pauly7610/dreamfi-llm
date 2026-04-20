"""Pydantic mirrors of Onyx request/response shapes we use."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Persona(BaseModel):
    id: int
    name: str
    description: str | None = None
    document_set_ids: list[int] = Field(default_factory=list)
    tool_ids: list[int] = Field(default_factory=list)


class ChatSession(BaseModel):
    id: str
    persona_id: int | None = None
    description: str | None = None


class SearchHit(BaseModel):
    document_id: str
    semantic_identifier: str
    blurb: str
    score: float
    link: str | None = None
    updated_at: datetime | None = None


class ChatResult(BaseModel):
    text: str
    citations: dict[int, str] = Field(default_factory=dict)
    documents: list[dict[str, Any]] = Field(default_factory=list)
    message_id: int | None = None


class IngestResult(BaseModel):
    document_id: str
    already_existed: bool = False


class DocSet(BaseModel):
    id: int
    name: str
    description: str | None = None
