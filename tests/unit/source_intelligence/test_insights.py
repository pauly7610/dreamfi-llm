from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from dreamfi.source_intelligence import (
    build_source_insights,
    detect_source_contradictions,
    score_source_packet,
    serialize_source_packets,
)
from dreamfi.source_intelligence.models import SourcePacket


def test_score_source_packet_blocks_sensitive_unredacted_evidence() -> None:
    packet = SourcePacket(
        source_id="socure",
        source_name="Socure",
        title="Identity verification",
        finding="Approval rate moved 4 percent after retry policy changes.",
        evidence="KYC decision summary includes user-level PII.",
        metric="approval rate moved 4 percent",
        decision_relevance="Use this to decide whether retry policy should change.",
        href="/console/integrations/socure",
        owner="Risk",
        source_status="connected",
        method="custom_ingestion",
        topic_ids=("kyc-conversion",),
        updated_at=datetime.now(timezone.utc),
        sensitivity="pii",
        redaction_profile="raw",
    )

    quality = score_source_packet(packet)

    assert quality.score < 1
    assert "passes_redaction_policy" in quality.blockers


def test_build_source_insights_prefers_source_scoped_artifacts() -> None:
    output = SimpleNamespace(
        output_id="artifact-1",
        test_input_label="KYC conversion",
        pass_fail="pass",
        confidence=Decimal("0.880"),
        export_readiness=Decimal("0.910"),
        created_at=datetime(2026, 5, 13, 14, 30, tzinfo=timezone.utc),
        criteria_json={
            "source_id": "posthog",
            "workflow_slug": "technical-prd",
            "workflow_title": "Technical PRD",
            "question": "Why are users stalling after upload?",
            "citation_count": 3,
            "meets_min_citations": True,
            "review_checklist_resolved": True,
        },
    )

    insights = build_source_insights(
        integrations=[
            {
                "id": "posthog",
                "name": "PostHog",
                "href": "/console/integrations/posthog",
                "status": "connected",
                "connection_method": "custom_ingestion",
            }
        ],
        outputs=[output],
        topics=[{"id": "kyc-conversion", "source_ids": ["posthog"], "owner": "Product Analytics"}],
    )

    insight = insights[0]
    assert insight["title"] == "PostHog influenced Technical PRD"
    assert "Why are users stalling" in insight["finding"]
    assert "3 citations" in insight["evidence"]
    assert insight["updated_at"] == "2026-05-13T14:30:00+00:00"
    assert insight["owner"] == "Product Analytics"
    assert insight["quality"]["score"] == 1


def test_build_source_insights_declares_gaps_for_unconfigured_sources() -> None:
    insights = build_source_insights(
        integrations=[
            {
                "id": "klaviyo",
                "name": "Klaviyo",
                "href": "/console/integrations/klaviyo",
                "status": "not_configured",
                "connection_method": "custom_ingestion",
            }
        ],
        outputs=[],
        topics=[],
    )

    insight = insights[0]
    assert insight["source_id"] == "klaviyo"
    assert insight["gap"] is not None
    assert "has_freshness_timestamp" in insight["quality"]["blockers"]


def test_build_source_insights_uses_persisted_connector_documents() -> None:
    document = SimpleNamespace(
        connector_document_id="doc-42",
        connector_id="metabase",
        external_id="card-42",
        title="Funding funnel dashboard",
        body_text="Completion fell 7 percent while start volume stayed flat for returning users.",
        doc_updated_at=datetime(2026, 5, 13, 12, 0, tzinfo=timezone.utc),
        metadata_json={
            "dreamfi_scope": {
                "owner": "Data",
                "product_area": "funding",
                "topic_ids": ["funding"],
            }
        },
        sync_run_id="sync-1",
        source_url="https://metabase.example/card/42",
        last_ingested_at=datetime(2026, 5, 13, 12, 5, tzinfo=timezone.utc),
    )

    insights = build_source_insights(
        integrations=[
            {
                "id": "metabase",
                "name": "Metabase",
                "href": "/console/integrations/metabase",
                "status": "connected",
                "connection_method": "custom_ingestion",
            }
        ],
        outputs=[],
        topics=[],
        documents=[document],
    )

    insight = insights[0]
    assert insight["title"] == "Metabase: Funding funnel dashboard"
    assert "Completion fell 7 percent" in insight["finding"]
    assert insight["metric"] == "1 persisted context packet for funding"
    assert insight["owner"] == "Data"
    assert insight["topic_ids"] == ["funding"]
    assert insight["gap"] is None
    assert insight["source_url"] == "https://metabase.example/card/42"
    assert insight["provenance"] == {
        "kind": "connector_document",
        "connector_document_id": "doc-42",
        "sync_run_id": "sync-1",
        "output_id": None,
    }


def test_serialize_source_packets_prefers_real_documents_and_marks_provenance() -> None:
    document = SimpleNamespace(
        connector_document_id="doc-1",
        connector_id="metabase",
        external_id="funding-funnel",
        title="Funding funnel dashboard",
        body_text="Completion fell 7 percent while start volume stayed flat.",
        source_url="https://metabase.example/card/42",
        doc_updated_at=datetime(2026, 5, 13, 12, 0, tzinfo=timezone.utc),
        created_at=datetime(2026, 5, 13, 12, 1, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 5, 13, 12, 2, tzinfo=timezone.utc),
        last_ingested_at=datetime(2026, 5, 13, 12, 5, tzinfo=timezone.utc),
        sync_run_id="sync-1",
        onyx_document_id="onyx-1",
        metadata_json={
            "dreamfi_scope": {
                "owner": "Data",
                "product_area": "funding",
                "topic_ids": ["funding"],
            },
            "sensitivity": "internal",
            "redaction_profile": "summary",
        },
    )

    packets = serialize_source_packets(
        integrations=[
            {
                "id": "metabase",
                "name": "Metabase",
                "href": "/console/integrations/metabase",
                "status": "connected",
                "connection_method": "custom_ingestion",
            },
            {
                "id": "posthog",
                "name": "PostHog",
                "href": "/console/integrations/posthog",
                "status": "available",
                "connection_method": "custom_ingestion",
            },
        ],
        documents=[document],
        max_per_source=3,
        stale_after_days=14,
        include_demo_packets=True,
        now=datetime(2026, 5, 13, 13, 0, tzinfo=timezone.utc),
    )

    real_packet = next(packet for packet in packets if packet["source_id"] == "metabase")
    demo_packet = next(packet for packet in packets if packet["source_id"] == "posthog")
    assert real_packet["is_demo"] is False
    assert real_packet["status"] == "live"
    assert real_packet["connector_document_id"] == "doc-1"
    assert real_packet["sync_run_id"] == "sync-1"
    assert real_packet["provenance"]["kind"] == "connector_document"
    assert demo_packet["is_demo"] is True
    assert demo_packet["status"] == "demo"
    assert demo_packet["provenance"]["kind"] == "demo_packet"


def test_detect_source_contradictions_groups_topic_conflicts() -> None:
    contradictions = detect_source_contradictions(
        source_packets=[
            {
                "packet_id": "demo:dragonboat",
                "source_id": "dragonboat",
                "source_name": "Dragonboat",
                "title": "Roadmap commitment",
                "snippet": "Funding completion remains committed and steady.",
                "metric": "1 committed initiative",
                "topic_ids": ["funding"],
                "doc_updated_at": "2026-05-13T12:00:00+00:00",
                "is_demo": True,
            },
            {
                "packet_id": "demo:metabase",
                "source_id": "metabase",
                "source_name": "Metabase",
                "title": "Funding funnel",
                "snippet": "Completion fell 7 percent and is underperforming.",
                "metric": "7 percent decline",
                "topic_ids": ["funding"],
                "doc_updated_at": "2026-05-13T12:30:00+00:00",
                "is_demo": True,
            },
        ],
        max_count=5,
    )

    assert len(contradictions) == 1
    assert contradictions[0]["topic_id"] == "funding"
    assert contradictions[0]["is_demo"] is True
