"""DreamFi source connector manifest.

This is the single place that defines the product evidence systems DreamFi
expects to see in Onyx. Setup scripts, readiness checks, and the console should
all derive connector expectations from this manifest.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectorSpec:
    connector_id: str
    name: str
    category: str
    purpose: str
    used_for: tuple[str, ...]
    expected_document_set: str
    href: str

    def as_console_integration(self) -> dict[str, object]:
        return {
            "id": self.connector_id,
            "name": self.name,
            "category": self.category,
            "purpose": self.purpose,
            "used_for": list(self.used_for),
            "status": "available",
            "href": self.href,
        }


def normalize_document_set_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def connector_document_set_aliases(connector: ConnectorSpec) -> set[str]:
    normalized_name = normalize_document_set_name(connector.name)
    return {
        connector.connector_id,
        connector.expected_document_set,
        normalized_name,
        f"dreamfi-{connector.connector_id}",
        f"dreamfi-{normalized_name}",
        f"dreamfi-source-{connector.connector_id}",
        f"dreamfi-source-{normalized_name}",
    }


CONNECTORS: tuple[ConnectorSpec, ...] = (
    ConnectorSpec(
        connector_id="jira",
        name="Jira",
        category="planning",
        purpose="Sprints, issues, and delivery state",
        used_for=("weekly-brief", "technical-prd", "risk-brd"),
        expected_document_set="dreamfi-source-jira",
        href="/console/integrations/jira",
    ),
    ConnectorSpec(
        connector_id="dragonboat",
        name="Dragonboat",
        category="planning",
        purpose="Roadmap, initiatives, and OKR alignment",
        used_for=("business-prd", "weekly-brief"),
        expected_document_set="dreamfi-source-dragonboat",
        href="/console/integrations/dragonboat",
    ),
    ConnectorSpec(
        connector_id="confluence",
        name="Confluence",
        category="docs",
        purpose="Source docs and publish target for PRDs and specs",
        used_for=("technical-prd", "business-prd", "risk-brd"),
        expected_document_set="dreamfi-source-confluence",
        href="/console/integrations/confluence",
    ),
    ConnectorSpec(
        connector_id="metabase",
        name="Metabase",
        category="metrics",
        purpose="SQL-backed KPI and funnel dashboards",
        used_for=("weekly-brief", "business-prd"),
        expected_document_set="dreamfi-source-metabase",
        href="/console/integrations/metabase",
    ),
    ConnectorSpec(
        connector_id="posthog",
        name="PostHog",
        category="product_analytics",
        purpose="Product events, funnels, and session data",
        used_for=("weekly-brief", "technical-prd"),
        expected_document_set="dreamfi-source-posthog",
        href="/console/integrations/posthog",
    ),
    ConnectorSpec(
        connector_id="ga",
        name="Google Analytics",
        category="marketing_analytics",
        purpose="Acquisition, traffic, and conversion signals",
        used_for=("business-prd",),
        expected_document_set="dreamfi-source-ga",
        href="/console/integrations/ga",
    ),
    ConnectorSpec(
        connector_id="klaviyo",
        name="Klaviyo",
        category="marketing",
        purpose="Lifecycle campaigns, audiences, and sends",
        used_for=("business-prd",),
        expected_document_set="dreamfi-source-klaviyo",
        href="/console/integrations/klaviyo",
    ),
    ConnectorSpec(
        connector_id="netxd",
        name="NetXD",
        category="payments",
        purpose="Payments and ledger transaction context",
        used_for=("risk-brd", "technical-prd"),
        expected_document_set="dreamfi-source-netxd",
        href="/console/integrations/netxd",
    ),
    ConnectorSpec(
        connector_id="sardine",
        name="Sardine",
        category="risk",
        purpose="Fraud and risk signal enrichment",
        used_for=("risk-brd",),
        expected_document_set="dreamfi-source-sardine",
        href="/console/integrations/sardine",
    ),
    ConnectorSpec(
        connector_id="socure",
        name="Socure",
        category="identity",
        purpose="Identity verification and KYC signals",
        used_for=("risk-brd",),
        expected_document_set="dreamfi-source-socure",
        href="/console/integrations/socure",
    ),
)


CONNECTOR_BY_ID = {connector.connector_id: connector for connector in CONNECTORS}

REQUIRED_METADATA_KEYS = (
    "dreamfi_scope.source_ids",
    "dreamfi_scope.product_area",
    "dreamfi_scope.topic_ids",
    "dreamfi_scope.owner",
    "doc_updated_at",
)
