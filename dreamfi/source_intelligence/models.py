"""Typed source-intelligence records used by the console."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class InsightQuality:
    score: float
    checks: dict[str, bool]
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class SourcePacket:
    source_id: str
    source_name: str
    title: str
    finding: str
    evidence: str
    decision_relevance: str
    href: str
    owner: str
    source_status: str
    method: str
    topic_ids: tuple[str, ...] = ()
    metric: str | None = None
    gap: str | None = None
    updated_at: datetime | None = None
    sensitivity: str = "internal"
    redaction_profile: str = "summary"
    provenance_kind: str = "source_contract"
    connector_document_id: str | None = None
    sync_run_id: str | None = None
    output_id: str | None = None
    source_url: str | None = None
    is_demo: bool = False

    def serializable_updated_at(self) -> str | None:
        if self.updated_at is None:
            return None
        if self.updated_at.tzinfo is None:
            return self.updated_at.replace(tzinfo=timezone.utc).isoformat()
        return self.updated_at.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class SourceInsight:
    insight_id: str
    packet: SourcePacket
    quality: InsightQuality

    def as_dict(self) -> dict[str, object]:
        return {
            "insight_id": self.insight_id,
            "source_id": self.packet.source_id,
            "source_name": self.packet.source_name,
            "title": self.packet.title,
            "finding": self.packet.finding,
            "evidence": self.packet.evidence,
            "decision_relevance": self.packet.decision_relevance,
            "gap": self.packet.gap,
            "metric": self.packet.metric,
            "updated_at": self.packet.serializable_updated_at(),
            "topic_ids": list(self.packet.topic_ids),
            "owner": self.packet.owner,
            "quality": self.quality.as_dict(),
            "href": self.packet.href,
            "source_status": self.packet.source_status,
            "method": self.packet.method,
            "source_url": self.packet.source_url,
            "is_demo": self.packet.is_demo,
            "provenance": {
                "kind": self.packet.provenance_kind,
                "connector_document_id": self.packet.connector_document_id,
                "sync_run_id": self.packet.sync_run_id,
                "output_id": self.packet.output_id,
            },
        }
