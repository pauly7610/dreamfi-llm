"""Source packet history, provenance, and evidence-risk summaries."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from dreamfi.source_intelligence.insights import SOURCE_SIGNAL_CATALOG


DEMO_PACKET_TEMPLATES: dict[str, dict[str, object]] = {
    "jira": {
        "title": "Demo delivery blocker digest",
        "snippet": "Two funding-completion tickets are blocked behind error classification work; the oldest issue is six days past target.",
        "metric": "2 blockers, 6 day oldest age",
        "topic_ids": ("funding",),
        "product_area": "funding",
    },
    "dragonboat": {
        "title": "Demo roadmap commitment packet",
        "snippet": "Funding completion remains committed for the quarter, but the dependency on payment-retry diagnostics moved one sprint.",
        "metric": "1 committed initiative, 1 date movement",
        "topic_ids": ("funding",),
        "product_area": "funding",
    },
    "confluence": {
        "title": "Demo decision record packet",
        "snippet": "The latest PRD keeps retry copy, analytics tagging, and review-owner signoff as launch requirements.",
        "metric": "3 open review items",
        "topic_ids": ("funding", "kyc-conversion"),
        "product_area": "product",
    },
    "metabase": {
        "title": "Demo funding funnel dashboard",
        "snippet": "Funding-start volume is flat, but completion fell 7 percent for returning users over the latest 30-day window.",
        "metric": "7 percent completion decline",
        "topic_ids": ("funding",),
        "product_area": "funding",
    },
    "posthog": {
        "title": "Demo KYC upload funnel",
        "snippet": "Mobile users recover after the first upload retry, then drop sharply when the second retry fails without a clear next step.",
        "metric": "11 point drop after second retry",
        "topic_ids": ("kyc-conversion", "onboarding"),
        "product_area": "onboarding",
    },
    "ga": {
        "title": "Demo acquisition quality packet",
        "snippet": "Paid traffic is steady, but returning organic users complete onboarding at a higher rate than first-time paid sessions.",
        "metric": "organic conversion outperforms paid",
        "topic_ids": ("lifecycle-messaging",),
        "product_area": "growth",
    },
    "klaviyo": {
        "title": "Demo lifecycle flow packet",
        "snippet": "Funding reminder clicks increased after the second message, but downstream completion did not improve.",
        "metric": "click lift without completion lift",
        "topic_ids": ("lifecycle-messaging", "funding"),
        "product_area": "lifecycle",
    },
    "netxd": {
        "title": "Demo payment exception packet",
        "snippet": "ACH retry failures cluster around one return-code family, while card funding remains stable.",
        "metric": "ACH failures concentrated in one reason family",
        "topic_ids": ("funding",),
        "product_area": "payments",
    },
    "sardine": {
        "title": "Demo fraud pressure packet",
        "snippet": "Manual review pressure increased for medium-risk funding attempts, but high-risk blocks are steady.",
        "metric": "manual review pressure increased",
        "topic_ids": ("kyc-conversion", "funding"),
        "product_area": "risk",
    },
    "socure": {
        "title": "Demo identity retry packet",
        "snippet": "Identity approval is steady overall, while retry volume is concentrated in address mismatch reason codes.",
        "metric": "retry volume concentrated in address mismatch",
        "topic_ids": ("kyc-conversion",),
        "product_area": "identity",
    },
}

POSITIVE_TERMS = (
    "approved",
    "complete",
    "committed",
    "flat",
    "higher",
    "improve",
    "increased",
    "lift",
    "recovery",
    "recover",
    "stable",
    "steady",
)
NEGATIVE_TERMS = (
    "blocked",
    "decline",
    "drop",
    "fail",
    "fell",
    "lag",
    "mismatch",
    "moved",
    "not improve",
    "past target",
    "pressure",
    "retry",
    "risk",
    "underperform",
)


def _text(value: object, fallback: str = "") -> str:
    return value if isinstance(value, str) else fallback


def _tuple_texts(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    normalized = _as_utc(value)
    return normalized.isoformat() if normalized else None


def _snippet(value: str, limit: int = 260) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."


def _metadata_scope(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    scope = value.get("dreamfi_scope")
    return scope if isinstance(scope, Mapping) else {}


def _metadata_topics(value: object) -> tuple[str, ...]:
    scope = _metadata_scope(value)
    topics = scope.get("topic_ids")
    if not topics and isinstance(value, Mapping):
        topics = value.get("topic_ids")
    return _tuple_texts(topics)


def _metadata_value(value: object, key: str) -> str:
    return _text(value.get(key)) if isinstance(value, Mapping) else ""


def _source_name(integrations_by_id: Mapping[str, Mapping[str, object]], source_id: str) -> str:
    integration = integrations_by_id.get(source_id, {})
    return _text(integration.get("name"), source_id)


def _source_href(integrations_by_id: Mapping[str, Mapping[str, object]], source_id: str) -> str:
    integration = integrations_by_id.get(source_id, {})
    return _text(integration.get("href"), f"/console/integrations/{source_id}")


def _source_status(integrations_by_id: Mapping[str, Mapping[str, object]], source_id: str) -> str:
    integration = integrations_by_id.get(source_id, {})
    return _text(integration.get("status"), "not_configured")


def _source_method(integrations_by_id: Mapping[str, Mapping[str, object]], source_id: str) -> str:
    integration = integrations_by_id.get(source_id, {})
    return _text(integration.get("connection_method"), "custom_ingestion")


def _catalog_owner(source_id: str) -> str:
    catalog = SOURCE_SIGNAL_CATALOG.get(source_id, {})
    return _text(catalog.get("owner"), "Product Ops")


def _packet_status(
    *,
    doc_updated_at: datetime | None,
    last_ingested_at: datetime | None,
    now: datetime,
    stale_after_days: int,
) -> str:
    updated = _as_utc(doc_updated_at)
    if updated is None:
        return "missing_freshness"
    if updated < now - timedelta(days=stale_after_days):
        return "stale"
    if last_ingested_at is None:
        return "not_ingested"
    return "live"


def serialize_source_packets(
    *,
    integrations: Iterable[Mapping[str, object]],
    documents: Iterable[Any],
    max_per_source: int,
    stale_after_days: int,
    include_demo_packets: bool,
    now: datetime | None = None,
) -> list[dict[str, object]]:
    """Return the source packet history used by the console and evidence export."""
    current_time = _as_utc(now) or datetime.now(timezone.utc)
    integrations_by_id = {_text(item.get("id")): item for item in integrations if _text(item.get("id"))}
    grouped_documents: dict[str, list[Any]] = defaultdict(list)
    for document in documents:
        source_id = _text(getattr(document, "connector_id", ""))
        if source_id in integrations_by_id:
            grouped_documents[source_id].append(document)

    packets: list[dict[str, object]] = []
    for source_id, integration in integrations_by_id.items():
        source_documents = sorted(
            grouped_documents.get(source_id, []),
            key=lambda row: _as_utc(getattr(row, "doc_updated_at", None)) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        for document in source_documents[:max_per_source]:
            metadata = getattr(document, "metadata_json", {}) or {}
            scope = _metadata_scope(metadata)
            updated_at = _as_utc(getattr(document, "doc_updated_at", None))
            last_ingested_at = _as_utc(getattr(document, "last_ingested_at", None))
            status = _packet_status(
                doc_updated_at=updated_at,
                last_ingested_at=last_ingested_at,
                now=current_time,
                stale_after_days=stale_after_days,
            )
            changed_since_last_sync = (
                updated_at is not None
                and (last_ingested_at is None or updated_at > last_ingested_at)
            )
            connector_document_id = _text(getattr(document, "connector_document_id", ""))
            sync_run_id = _text(getattr(document, "sync_run_id", ""))
            packets.append(
                {
                    "packet_id": f"document:{connector_document_id or getattr(document, 'external_id', source_id)}",
                    "source_id": source_id,
                    "source_name": _text(integration.get("name"), source_id),
                    "title": _text(getattr(document, "title", None), f"{_source_name(integrations_by_id, source_id)} packet"),
                    "snippet": _snippet(_text(getattr(document, "body_text", None))),
                    "metric": _metadata_value(metadata, "metric") or _metadata_value(scope, "metric"),
                    "source_url": _text(getattr(document, "source_url", None)) or _source_href(integrations_by_id, source_id),
                    "doc_updated_at": _iso(updated_at),
                    "persisted_at": _iso(getattr(document, "created_at", None)),
                    "last_seen_at": _iso(getattr(document, "last_seen_at", None)),
                    "last_ingested_at": _iso(last_ingested_at),
                    "connector_document_id": connector_document_id or None,
                    "sync_run_id": sync_run_id or None,
                    "onyx_document_id": _text(getattr(document, "onyx_document_id", None)) or None,
                    "external_id": _text(getattr(document, "external_id", None)) or None,
                    "topic_ids": list(_metadata_topics(metadata)),
                    "owner": _metadata_value(scope, "owner") or _metadata_value(metadata, "owner") or _catalog_owner(source_id),
                    "product_area": _metadata_value(scope, "product_area") or _metadata_value(metadata, "product_area"),
                    "sensitivity": _metadata_value(metadata, "sensitivity") or "internal",
                    "redaction_profile": _metadata_value(metadata, "redaction_profile") or "summary",
                    "status": status,
                    "source_status": _source_status(integrations_by_id, source_id),
                    "method": _source_method(integrations_by_id, source_id),
                    "stale": status == "stale",
                    "changed_since_last_sync": changed_since_last_sync,
                    "is_demo": False,
                    "provenance": {
                        "kind": "connector_document",
                        "connector_document_id": connector_document_id or None,
                        "sync_run_id": sync_run_id or None,
                        "output_id": None,
                    },
                }
            )

        if include_demo_packets and not source_documents:
            packets.append(_demo_packet(source_id=source_id, integrations_by_id=integrations_by_id, now=current_time))

    return packets


def _demo_packet(
    *,
    source_id: str,
    integrations_by_id: Mapping[str, Mapping[str, object]],
    now: datetime,
) -> dict[str, object]:
    catalog = SOURCE_SIGNAL_CATALOG.get(source_id, {})
    template = DEMO_PACKET_TEMPLATES.get(source_id, {})
    topic_ids = _tuple_texts(template.get("topic_ids")) or _tuple_texts(catalog.get("topic_ids"))
    title = _text(template.get("title"), f"Demo {_source_name(integrations_by_id, source_id)} packet")
    snippet = _text(template.get("snippet"), _text(catalog.get("evidence"), "Demo source packet awaiting real data."))
    return {
        "packet_id": f"demo:{source_id}",
        "source_id": source_id,
        "source_name": _source_name(integrations_by_id, source_id),
        "title": title,
        "snippet": snippet,
        "metric": _text(template.get("metric"), _text(catalog.get("metric"), "demo signal")),
        "source_url": _source_href(integrations_by_id, source_id),
        "doc_updated_at": _iso(now - timedelta(hours=2)),
        "persisted_at": None,
        "last_seen_at": None,
        "last_ingested_at": None,
        "connector_document_id": None,
        "sync_run_id": None,
        "onyx_document_id": None,
        "external_id": f"demo-{source_id}",
        "topic_ids": list(topic_ids),
        "owner": _text(catalog.get("owner"), "Product Ops"),
        "product_area": _text(template.get("product_area"), ""),
        "sensitivity": "internal",
        "redaction_profile": "summary",
        "status": "demo",
        "source_status": _source_status(integrations_by_id, source_id),
        "method": _source_method(integrations_by_id, source_id),
        "stale": False,
        "changed_since_last_sync": False,
        "is_demo": True,
        "provenance": {
            "kind": "demo_packet",
            "connector_document_id": None,
            "sync_run_id": None,
            "output_id": None,
        },
    }


def detect_source_contradictions(
    *,
    source_packets: Sequence[Mapping[str, object]],
    max_count: int,
) -> list[dict[str, object]]:
    """Flag places where source packets appear to point in different directions."""
    packets_by_topic: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for packet in source_packets:
        for topic_id in _tuple_texts(packet.get("topic_ids")):
            packets_by_topic[topic_id].append(packet)

    contradictions: list[dict[str, object]] = []
    for topic_id, packets in packets_by_topic.items():
        positive = [packet for packet in packets if _sentiment(packet) == "positive"]
        negative = [packet for packet in packets if _sentiment(packet) == "negative"]
        for positive_packet in positive:
            negative_packet = next(
                (
                    packet
                    for packet in negative
                    if _text(packet.get("source_id")) != _text(positive_packet.get("source_id"))
                ),
                None,
            )
            if negative_packet is None:
                continue
            contradictions.append(
                {
                    "contradiction_id": (
                        f"{topic_id}:{positive_packet.get('packet_id')}:{negative_packet.get('packet_id')}"
                    ),
                    "topic_id": topic_id,
                    "title": f"{topic_id.replace('-', ' ').title()} evidence points in different directions",
                    "summary": (
                        f"{positive_packet.get('source_name')} shows stability or improvement, while "
                        f"{negative_packet.get('source_name')} shows friction or decline."
                    ),
                    "severity": "warning",
                    "source_ids": [
                        _text(positive_packet.get("source_id")),
                        _text(negative_packet.get("source_id")),
                    ],
                    "packet_ids": [
                        _text(positive_packet.get("packet_id")),
                        _text(negative_packet.get("packet_id")),
                    ],
                    "evidence": [
                        _text(positive_packet.get("snippet")),
                        _text(negative_packet.get("snippet")),
                    ],
                    "recommended_action": (
                        "Open the linked packets, verify the date windows and cohorts, then decide which signal "
                        "should govern the product recommendation."
                    ),
                    "updated_at": positive_packet.get("doc_updated_at") or negative_packet.get("doc_updated_at"),
                    "is_demo": bool(positive_packet.get("is_demo")) or bool(negative_packet.get("is_demo")),
                }
            )
            break
        if len(contradictions) >= max_count:
            break
    return contradictions[:max_count]


def build_source_refresh_summary(
    *,
    schedules: Sequence[Any],
    sync_runs: Sequence[Any],
    integrations: Sequence[Mapping[str, object]],
    source_packets: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    active_schedule = next((schedule for schedule in schedules if bool(getattr(schedule, "is_active", False))), None)
    latest_sync = sync_runs[0] if sync_runs else None
    real_packets = [packet for packet in source_packets if not bool(packet.get("is_demo"))]
    failed_source_ids = {
        _text(getattr(run, "connector_id", ""))
        for run in sync_runs
        if _text(getattr(run, "status", "")) == "failed"
    }
    stale_source_ids = {
        _text(packet.get("source_id"))
        for packet in real_packets
        if bool(packet.get("stale")) or _text(packet.get("status")) in {"not_ingested", "missing_freshness"}
    }
    active_sources = [
        integration
        for integration in integrations
        if _text(integration.get("status")) in {"connected", "degraded"}
    ]
    return {
        "configured": active_schedule is not None,
        "schedule_id": getattr(active_schedule, "schedule_id", None) if active_schedule else None,
        "cadence_days": getattr(active_schedule, "cadence_days", None) if active_schedule else None,
        "next_run_at": _iso(getattr(active_schedule, "next_run_at", None)) if active_schedule else None,
        "last_run_at": _iso(getattr(active_schedule, "last_run_at", None)) if active_schedule else None,
        "active_source_count": len(active_sources),
        "packet_count": len(real_packets),
        "demo_packet_count": len(source_packets) - len(real_packets),
        "failed_source_count": len(failed_source_ids),
        "stale_source_count": len(stale_source_ids),
        "latest_sync_status": _text(getattr(latest_sync, "status", None)) if latest_sync else None,
        "latest_sync_at": _iso(getattr(latest_sync, "started_at", None)) if latest_sync else None,
        "href": "/api/console/source-refresh/schedule",
    }


def _sentiment(packet: Mapping[str, object]) -> str:
    haystack = f"{packet.get('title', '')} {packet.get('snippet', '')} {packet.get('metric', '')}".lower()
    has_negative = any(term in haystack for term in NEGATIVE_TERMS)
    has_positive = any(term in haystack for term in POSITIVE_TERMS)
    if has_negative and not has_positive:
        return "negative"
    if has_positive and not has_negative:
        return "positive"
    if has_negative and has_positive:
        return "mixed"
    return "neutral"
