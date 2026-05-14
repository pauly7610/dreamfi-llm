"""Build source-intelligence cards from source catalog and generated artifacts."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from dreamfi.source_intelligence.models import SourceInsight, SourcePacket
from dreamfi.source_intelligence.quality import score_source_packet


SOURCE_SIGNAL_CATALOG: dict[str, dict[str, object]] = {
    "jira": {
        "title": "Delivery state",
        "finding": "Use ticket movement, ownership, and blocked work to see where execution is slowing.",
        "evidence": "Expected packets include issues, sprint state, blockers, owners, and recent status changes.",
        "metric": "Blocked count, cycle-time movement, and issue aging",
        "decision_relevance": "Prioritize the smallest product or engineering move that removes delivery drag.",
        "topic_ids": ("onboarding", "funding", "kyc-conversion"),
        "owner": "Product Ops",
    },
    "dragonboat": {
        "title": "Roadmap commitment",
        "finding": "Use initiative, roadmap, and OKR context to compare current work against committed priorities.",
        "evidence": "Expected packets include initiatives, feature plans, objectives, target dates, and dependency notes.",
        "metric": "Committed initiative count and roadmap date movement",
        "decision_relevance": "Escalate scope, sequencing, or tradeoff decisions before teams discover them late.",
        "topic_ids": ("onboarding", "funding"),
        "owner": "Product Ops",
    },
    "confluence": {
        "title": "Decision record",
        "finding": "Use specs, PRDs, and decision logs to anchor generated artifacts in the current written record.",
        "evidence": "Expected packets include PRDs, technical specs, decision pages, launch notes, and review comments.",
        "metric": "Spec freshness, decision count, and unresolved review items",
        "decision_relevance": "Keep recommendations aligned with the latest documented product and engineering intent.",
        "topic_ids": ("onboarding", "funding", "kyc-conversion", "lifecycle-messaging"),
        "owner": "Product Ops",
    },
    "metabase": {
        "title": "KPI movement",
        "finding": "Use dashboards and saved questions to separate real metric movement from anecdotal noise.",
        "evidence": "Expected packets include KPI cards, dashboard exports, SQL result summaries, and dashboard links.",
        "metric": "Funnel rate, KPI delta, cohort trend, and query timestamp",
        "decision_relevance": "Rank product opportunities by observed business impact and metric confidence.",
        "topic_ids": ("funding", "kyc-conversion", "lifecycle-messaging"),
        "owner": "Data",
    },
    "posthog": {
        "title": "Behavior signal",
        "finding": "Use product events, funnels, and cohorts to see where users actually stall or recover.",
        "evidence": "Expected packets include funnel snapshots, cohorts, event summaries, and session pointers.",
        "metric": "Conversion drop, recovery rate, and event-volume movement",
        "decision_relevance": "Choose experiments and fixes from observed behavior instead of internal opinion.",
        "topic_ids": ("onboarding", "funding", "kyc-conversion"),
        "owner": "Product Analytics",
    },
    "ga": {
        "title": "Acquisition signal",
        "finding": "Use traffic and conversion reports to see whether top-of-funnel quality is helping product outcomes.",
        "evidence": "Expected packets include channel reports, conversion events, landing pages, and date-windowed summaries.",
        "metric": "Sessions, active users, conversion count, and channel mix",
        "decision_relevance": "Separate acquisition mix problems from product experience problems.",
        "topic_ids": ("lifecycle-messaging", "kyc-conversion"),
        "owner": "Growth",
    },
    "klaviyo": {
        "title": "Lifecycle performance",
        "finding": "Use campaigns, flows, and segments to see which lifecycle messages are creating or losing momentum.",
        "evidence": "Expected packets include campaign sends, flows, audiences, segment changes, and performance summaries.",
        "metric": "Open rate, click rate, conversion rate, and audience movement",
        "decision_relevance": "Tune lifecycle work against actual customer response before adding more campaigns.",
        "topic_ids": ("lifecycle-messaging", "funding"),
        "owner": "Lifecycle",
    },
    "netxd": {
        "title": "Payment movement",
        "finding": "Use payment and ledger records to connect customer experience issues to transaction outcomes.",
        "evidence": "Expected packets include transactions, accounts, ledger events, exceptions, and operational status.",
        "metric": "Transaction count, failure rate, ledger exception count, and settlement timing",
        "decision_relevance": "Protect money movement decisions with operational evidence and exception context.",
        "topic_ids": ("funding",),
        "owner": "Payments",
    },
    "sardine": {
        "title": "Fraud pressure",
        "finding": "Use risk enrichment and case context to see where fraud pressure is changing user experience.",
        "evidence": "Expected packets include cases, transaction risk events, customer risk tags, and decision outcomes.",
        "metric": "Case volume, risk-tier mix, manual-review rate, and approval movement",
        "decision_relevance": "Balance conversion speed against the observed fraud and review pressure.",
        "topic_ids": ("kyc-conversion", "funding"),
        "owner": "Risk",
    },
    "socure": {
        "title": "Identity verification",
        "finding": "Use KYC and identity-decision evidence to see where verification policy is helping or blocking users.",
        "evidence": "Expected packets include verification reports, decisions, retry outcomes, and policy reason codes.",
        "metric": "Approval rate, retry rate, decline reason mix, and manual-review volume",
        "decision_relevance": "Make identity-policy tradeoffs with conversion and risk evidence in the same frame.",
        "topic_ids": ("kyc-conversion",),
        "owner": "Risk",
    },
}

STATUS_RANK = {"connected": 0, "available": 1, "degraded": 2, "not_configured": 3}
WORKFLOW_LABELS = {
    "weekly-brief": "Weekly PM brief",
    "technical-prd": "Technical PRD",
    "business-prd": "Business PRD",
    "risk-brd": "Risk BRD",
}


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


def _criteria_source_ids(criteria: Mapping[str, Any]) -> tuple[str, ...]:
    raw_values: list[object] = []
    for key in ("source_id", "source_ids", "sourceIds"):
        if key in criteria:
            raw_values.append(criteria[key])
    scope = criteria.get("dreamfi_scope")
    if isinstance(scope, Mapping):
        for key in ("source_id", "source_ids", "sourceIds"):
            if key in scope:
                raw_values.append(scope[key])

    source_ids: list[str] = []
    for value in raw_values:
        if isinstance(value, str) and value.strip():
            source_ids.append(value.strip())
        elif isinstance(value, (list, tuple)):
            source_ids.extend(str(item).strip() for item in value if str(item).strip())
    return tuple(dict.fromkeys(source_ids))


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


def _metadata_owner(value: object) -> str:
    scope = _metadata_scope(value)
    owner = _text(scope.get("owner"))
    if owner:
        return owner
    return _text(value.get("owner")) if isinstance(value, Mapping) else ""


def _metadata_value(value: object, key: str) -> str:
    return _text(value.get(key)) if isinstance(value, Mapping) else ""


def _snippet(value: str, limit: int = 240) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."


def _topics_by_source(topics: Iterable[Mapping[str, object]]) -> dict[str, tuple[str, ...]]:
    mapped: dict[str, list[str]] = defaultdict(list)
    for topic in topics:
        topic_id = _text(topic.get("id"))
        if not topic_id:
            continue
        for source_id in _tuple_texts(topic.get("source_ids")):
            mapped[source_id].append(topic_id)
    return {source_id: tuple(dict.fromkeys(topic_ids)) for source_id, topic_ids in mapped.items()}


def _owners_by_source(topics: Iterable[Mapping[str, object]]) -> dict[str, str]:
    owners: dict[str, str] = {}
    for topic in topics:
        owner = _text(topic.get("owner"))
        if not owner or owner == "unassigned":
            continue
        for source_id in _tuple_texts(topic.get("source_ids")):
            owners.setdefault(source_id, owner)
    return owners


def _output_packet(
    *,
    integration: Mapping[str, object],
    output: Any,
    topic_ids: tuple[str, ...],
    owner: str,
) -> SourcePacket:
    criteria = getattr(output, "criteria_json", {}) or {}
    workflow_slug = _text(criteria.get("workflow_slug"), "artifact")
    workflow_title = _text(
        criteria.get("workflow_title"),
        WORKFLOW_LABELS.get(workflow_slug, "Generated artifact"),
    )
    question = _text(criteria.get("question"), getattr(output, "test_input_label", "recent artifact"))
    citation_count = criteria.get("citation_count")
    readiness = getattr(output, "export_readiness", None)
    confidence = getattr(output, "confidence", None)
    source_name = _text(integration.get("name"), _text(integration.get("id"), "Source"))
    source_status = _text(integration.get("status"), "available")
    metric_parts = []
    if readiness is not None:
        metric_parts.append(f"readiness {float(readiness):.2f}")
    if confidence is not None:
        metric_parts.append(f"confidence {float(confidence):.2f}")
    if isinstance(citation_count, int):
        metric_parts.append(f"{citation_count} citations")

    gap = None
    if getattr(output, "pass_fail", "") != "pass":
        gap = "Generated artifact failed one or more locked gates and needs review before reuse."
    elif criteria.get("review_checklist_resolved") is False:
        gap = "Review checklist still has unresolved items."
    elif criteria.get("meets_min_citations") is False:
        gap = "Citation coverage is below the workflow minimum."
    elif source_status != "connected":
        gap = "Latest artifact is source-scoped, but connector freshness still needs operational validation."

    return SourcePacket(
        source_id=_text(integration.get("id")),
        source_name=source_name,
        title=f"{source_name} influenced {workflow_title}",
        finding=f"{workflow_title} has recent source-scoped output for: {question}",
        evidence=(
            f"Latest artifact {getattr(output, 'output_id', 'unknown')} "
            f"was {getattr(output, 'pass_fail', 'unknown')} with {citation_count or 0} citations."
        ),
        metric=", ".join(metric_parts) if metric_parts else "artifact quality movement",
        decision_relevance="Review this artifact when deciding whether the source supports action or needs more evidence.",
        href=f"/console/review?focus={getattr(output, 'output_id', '')}",
        owner=owner,
        source_status=source_status,
        method=_text(integration.get("connection_method"), "unknown"),
        topic_ids=topic_ids,
        gap=gap,
        updated_at=_as_utc(getattr(output, "created_at", None)),
        provenance_kind="artifact",
        output_id=_text(getattr(output, "output_id", None)),
    )


def _document_packet(
    *,
    integration: Mapping[str, object],
    document: Any,
    topic_ids: tuple[str, ...],
    owner: str,
) -> SourcePacket:
    source_id = _text(integration.get("id"))
    source_name = _text(integration.get("name"), source_id)
    source_status = _text(integration.get("status"), "available")
    catalog = SOURCE_SIGNAL_CATALOG.get(source_id, {})
    metadata = getattr(document, "metadata_json", {}) or {}
    metadata_topic_ids = _metadata_topics(metadata)
    effective_topic_ids = tuple(dict.fromkeys((*topic_ids, *metadata_topic_ids)))
    owner_value = owner or _metadata_owner(metadata) or _text(catalog.get("owner"), "Product Ops")
    sensitivity = _metadata_value(metadata, "sensitivity") or "internal"
    redaction_profile = _metadata_value(metadata, "redaction_profile") or "summary"
    is_sensitive = sensitivity.strip().lower() in {"pii", "restricted", "secret"} and redaction_profile.strip().lower() not in {
        "aggregate",
        "masked",
        "redacted",
        "summary",
    }
    title = _text(getattr(document, "title", None), f"{source_name} context packet")
    body_text = _text(getattr(document, "body_text", None))
    if is_sensitive:
        finding = f"Latest persisted {source_name} packet is available but needs redaction before content is shown."
    else:
        finding = f"Latest persisted packet says: {_snippet(body_text) or title}"

    last_ingested_at = getattr(document, "last_ingested_at", None)
    gap = None
    if last_ingested_at is None:
        gap = "This packet is persisted locally but has not been confirmed ingested into Onyx."
    elif source_status != "connected":
        gap = "Persisted context exists, but connector freshness still needs operational validation."

    product_area = _metadata_value(_metadata_scope(metadata), "product_area") or _metadata_value(metadata, "product_area")
    return SourcePacket(
        source_id=source_id,
        source_name=source_name,
        title=f"{source_name}: {title}",
        finding=finding,
        evidence=(
            f"Persisted connector document {getattr(document, 'external_id', 'unknown')} "
            f"updated {getattr(document, 'doc_updated_at', None)}."
        ),
        metric=f"1 persisted context packet{f' for {product_area}' if product_area else ''}",
        decision_relevance=_text(
            catalog.get("decision_relevance"),
            "Use this persisted context packet to ground product and engineering decisions.",
        ),
        href=_text(integration.get("href"), "/console/integrations"),
        owner=owner_value,
        source_status=source_status,
        method=_text(integration.get("connection_method"), "unknown"),
        topic_ids=effective_topic_ids,
        gap=gap,
        updated_at=_as_utc(getattr(document, "doc_updated_at", None)),
        sensitivity=sensitivity,
        redaction_profile=redaction_profile,
        provenance_kind="connector_document",
        connector_document_id=_text(getattr(document, "connector_document_id", None)) or None,
        sync_run_id=_text(getattr(document, "sync_run_id", None)) or None,
        source_url=_text(getattr(document, "source_url", None)) or None,
    )


def _catalog_packet(
    *,
    integration: Mapping[str, object],
    topic_ids: tuple[str, ...],
    owner: str,
) -> SourcePacket:
    source_id = _text(integration.get("id"))
    source_name = _text(integration.get("name"), source_id)
    status = _text(integration.get("status"), "available")
    catalog = SOURCE_SIGNAL_CATALOG.get(source_id, {})
    catalog_topic_ids = _tuple_texts(catalog.get("topic_ids"))
    effective_topic_ids = topic_ids or catalog_topic_ids
    owner_value = owner or _text(catalog.get("owner"), "Product Ops")
    gap = None
    if status == "not_configured":
        gap = "No source packet is usable yet because the document set or bridge has not been configured."
    elif status == "degraded":
        gap = "Evidence exists, but freshness or retrieval quality needs review before high-stakes use."
    elif status == "available":
        gap = "Connector probing is not proving freshness yet, so treat this as an available source contract."

    return SourcePacket(
        source_id=source_id,
        source_name=source_name,
        title=_text(catalog.get("title"), f"{source_name} signal"),
        finding=_text(catalog.get("finding"), _text(integration.get("purpose"))),
        evidence=_text(catalog.get("evidence"), "Expected packets depend on this source's configured document set."),
        metric=_text(catalog.get("metric"), "source-specific movement"),
        decision_relevance=_text(
            catalog.get("decision_relevance"),
            "Use this source to ground product and engineering decisions with traceable evidence.",
        ),
        href=_text(integration.get("href"), "/console/integrations"),
        owner=owner_value,
        source_status=status,
        method=_text(integration.get("connection_method"), "unknown"),
        topic_ids=effective_topic_ids,
        gap=gap,
        updated_at=None,
        provenance_kind="source_contract",
    )


def build_source_insights(
    *,
    integrations: Iterable[Mapping[str, object]],
    outputs: Iterable[Any],
    topics: Iterable[Mapping[str, object]],
    documents: Iterable[Any] = (),
) -> list[dict[str, object]]:
    """Return source-centered insight cards for the console payload."""
    integrations_by_id = {_text(item.get("id")): item for item in integrations if _text(item.get("id"))}
    topic_ids_by_source = _topics_by_source(topics)
    owners_by_source = _owners_by_source(topics)
    latest_output_by_source: dict[str, Any] = {}
    for output in outputs:
        criteria = getattr(output, "criteria_json", {}) or {}
        if not isinstance(criteria, Mapping):
            continue
        for source_id in _criteria_source_ids(criteria):
            if source_id in integrations_by_id and source_id not in latest_output_by_source:
                latest_output_by_source[source_id] = output
    latest_document_by_source: dict[str, Any] = {}
    for document in documents:
        source_id = _text(getattr(document, "connector_id", ""))
        if source_id in integrations_by_id and source_id not in latest_document_by_source:
            latest_document_by_source[source_id] = document

    insights: list[SourceInsight] = []
    for source_id, integration in integrations_by_id.items():
        topic_ids = topic_ids_by_source.get(source_id, ())
        owner = owners_by_source.get(source_id, "")
        output = latest_output_by_source.get(source_id)
        if output is not None:
            packet = _output_packet(
                integration=integration,
                output=output,
                topic_ids=topic_ids,
                owner=owner or "Product Ops",
            )
        elif source_id in latest_document_by_source:
            packet = _document_packet(
                integration=integration,
                document=latest_document_by_source[source_id],
                topic_ids=topic_ids,
                owner=owner,
            )
        else:
            packet = _catalog_packet(integration=integration, topic_ids=topic_ids, owner=owner)
        insights.append(
            SourceInsight(
                insight_id=f"{packet.source_id}:{packet.title.lower().replace(' ', '-')}",
                packet=packet,
                quality=score_source_packet(packet),
            )
        )

    insights.sort(
        key=lambda insight: (
            STATUS_RANK.get(insight.packet.source_status, 1),
            -insight.quality.score,
            insight.packet.source_name,
        )
    )
    return [insight.as_dict() for insight in insights]
