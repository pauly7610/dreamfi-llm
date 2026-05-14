"""Types shared by custom connector adapters."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)


def stable_hash(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def compact_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


@dataclass(frozen=True)
class SourceDocument:
    connector_id: str
    external_id: str
    title: str
    text: str
    source_url: str | None = None
    updated_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        return stable_hash(self.title, self.text, compact_json(self.metadata))

    @property
    def onyx_document_id(self) -> str:
        return f"dreamfi:{self.connector_id}:{stable_hash(self.external_id)[:24]}"

    def onyx_metadata(self) -> dict[str, Any]:
        product_area = str(self.metadata.get("product_area") or self.connector_id)
        owner = str(self.metadata.get("owner") or "unassigned")
        topic_ids = self.metadata.get("topic_ids") or []
        if isinstance(topic_ids, str):
            topic_ids = [topic_ids]
        return {
            **self.metadata,
            "dreamfi_scope": {
                "source_ids": [self.connector_id],
                "product_area": product_area,
                "topic_ids": list(topic_ids),
                "owner": owner,
            },
            "doc_updated_at": as_utc(self.updated_at).isoformat(),
        }
