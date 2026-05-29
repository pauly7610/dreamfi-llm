"""DreamFi source connector manifest.

This is the single place that defines the product evidence systems DreamFi
expects to see in Onyx. Setup scripts, readiness checks, and the console should
all derive connector expectations from this manifest.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


ConnectionMethod = Literal["onyx_native", "custom_ingestion"]
ONYX_NATIVE: ConnectionMethod = "onyx_native"
CUSTOM_INGESTION: ConnectionMethod = "custom_ingestion"
DEFAULT_CUSTOM_SETUP_DETAIL = (
    "Ingest through an Onyx File/Web/S3 source or a DreamFi source bridge. "
    "DreamFi validates the document set, required metadata, and freshness."
)
DEFAULT_REST_AUTH_HEADER = "Authorization"
DEFAULT_REST_AUTH_SCHEME = "Bearer"
DEFAULT_KLAVIYO_BASE_URL = "https://a.klaviyo.com"
DEFAULT_KLAVIYO_REVISION = "2025-10-15"
DEFAULT_POSTHOG_BASE_URL = "https://app.posthog.com"
DEFAULT_GA_BASE_URL = "https://analyticsdata.googleapis.com"
DEFAULT_GA_START_DATE = "30daysAgo"
DEFAULT_GA_END_DATE = "today"
DEFAULT_GA_DIMENSIONS = "date,sessionDefaultChannelGroup"
DEFAULT_GA_METRICS = "sessions,activeUsers,conversions"


@dataclass(frozen=True)
class ConnectorConfigField:
    key: str
    label: str
    required: bool = True
    placeholder: str = ""
    help_text: str = ""
    default: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "label": self.label,
            "required": self.required,
            "placeholder": self.placeholder,
            "help_text": self.help_text,
            "default": self.default,
        }


@dataclass(frozen=True)
class ConnectorSpec:
    connector_id: str
    name: str
    category: str
    purpose: str
    used_for: tuple[str, ...]
    expected_document_set: str
    href: str
    connection_method: ConnectionMethod = CUSTOM_INGESTION
    setup_method: str = "Custom/export ingestion"
    setup_detail: str = DEFAULT_CUSTOM_SETUP_DETAIL
    requires_dreamfi_secret: bool = False
    config_fields: tuple[ConnectorConfigField, ...] = ()
    default_config: dict[str, str] | None = None

    @property
    def required_config_keys(self) -> tuple[str, ...]:
        return tuple(field.key for field in self.config_fields if field.required)

    def as_console_integration(self) -> dict[str, object]:
        return {
            "id": self.connector_id,
            "name": self.name,
            "category": self.category,
            "purpose": self.purpose,
            "used_for": list(self.used_for),
            "status": "available",
            "href": self.href,
            "connection_method": self.connection_method,
            "setup_method": self.setup_method,
            "setup_detail": self.setup_detail,
            "requires_dreamfi_secret": self.requires_dreamfi_secret,
            "config_schema": [field.as_dict() for field in self.config_fields],
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


def _base_url_field(label: str, placeholder: str, *, required: bool = True, default: str | None = None) -> ConnectorConfigField:
    return ConnectorConfigField(
        key="base_url",
        label=label,
        placeholder=placeholder,
        required=required,
        default=default,
        help_text="Provider API root used by DreamFi sync jobs.",
    )


def _endpoints_field(placeholder: str, *, default: str | None = None) -> ConnectorConfigField:
    return ConnectorConfigField(
        key="endpoints",
        label="Endpoint paths",
        required=False,
        placeholder=placeholder,
        default=default,
        help_text="Comma-separated paths to pull during sync. Leave the defaults unless your tenant uses different routes.",
    )


def _auth_fields(
    *,
    header_default: str = DEFAULT_REST_AUTH_HEADER,
    scheme_default: str = DEFAULT_REST_AUTH_SCHEME,
) -> tuple[ConnectorConfigField, ConnectorConfigField]:
    return (
        ConnectorConfigField(
            key="auth_header",
            label="Auth header",
            required=False,
            placeholder=header_default,
            default=header_default,
            help_text="HTTP header that carries the saved API key.",
        ),
        ConnectorConfigField(
            key="auth_scheme",
            label="Auth scheme",
            required=False,
            placeholder=scheme_default or "leave blank for raw token",
            default=scheme_default,
            help_text="Prefix added before the API key. Clear this for providers that expect the raw token.",
        ),
    )


def _metadata_fields() -> tuple[ConnectorConfigField, ...]:
    return (
        ConnectorConfigField(
            key="product_area",
            label="Product area",
            required=False,
            placeholder="kyc, funding, lifecycle, payments",
            help_text="Optional default product area written into dreamfi_scope metadata.",
        ),
        ConnectorConfigField(
            key="topic_ids",
            label="Topic IDs",
            required=False,
            placeholder="kyc-conversion,onboarding-risk",
            help_text="Optional comma-separated topic IDs attached to pulled documents.",
        ),
        ConnectorConfigField(
            key="owner",
            label="Owner",
            required=False,
            placeholder="team-or-person@dreamfi.com",
            help_text="Optional accountable owner written into connector document metadata.",
        ),
    )


def _rest_default_config(
    *,
    endpoints: str,
    auth_header: str = DEFAULT_REST_AUTH_HEADER,
    auth_scheme: str = DEFAULT_REST_AUTH_SCHEME,
    base_url: str | None = None,
) -> dict[str, str]:
    values = {
        "endpoints": endpoints,
        "auth_header": auth_header,
        "auth_scheme": auth_scheme,
    }
    if base_url:
        values["base_url"] = base_url
    return values


CONNECTORS: tuple[ConnectorSpec, ...] = (
    ConnectorSpec(
        connector_id="jira",
        name="Jira",
        category="planning",
        purpose="Sprints, issues, and delivery state",
        used_for=("weekly-brief", "technical-prd", "risk-brd"),
        expected_document_set="dreamfi-source-jira",
        href="/console/integrations/jira",
        connection_method=ONYX_NATIVE,
        setup_method="Onyx native connector",
        setup_detail="Configure Jira credentials in Onyx, then let DreamFi validate the document set and freshness.",
    ),
    ConnectorSpec(
        connector_id="dragonboat",
        name="Dragonboat",
        category="planning",
        purpose="Roadmap, initiatives, and OKR alignment",
        used_for=("business-prd", "weekly-brief"),
        expected_document_set="dreamfi-source-dragonboat",
        href="/console/integrations/dragonboat",
        requires_dreamfi_secret=True,
        config_fields=(
            _base_url_field("Dragonboat base URL", "https://app.dragonboat.io"),
            _endpoints_field("/api/v1/initiatives,/api/v1/features,/api/v1/objectives"),
            *_auth_fields(),
            *_metadata_fields(),
        ),
        default_config=_rest_default_config(
            endpoints="/api/v1/initiatives,/api/v1/features,/api/v1/objectives"
        ),
    ),
    ConnectorSpec(
        connector_id="confluence",
        name="Confluence",
        category="docs",
        purpose="Source docs and publish target for PRDs and specs",
        used_for=("technical-prd", "business-prd", "risk-brd"),
        expected_document_set="dreamfi-source-confluence",
        href="/console/integrations/confluence",
        connection_method=ONYX_NATIVE,
        setup_method="Onyx native connector",
        setup_detail=(
            "Configure Confluence credentials in Onyx, then let DreamFi validate the document set, freshness, "
            "and publish evidence."
        ),
    ),
    ConnectorSpec(
        connector_id="metabase",
        name="Metabase",
        category="metrics",
        purpose="SQL-backed KPI and funnel dashboards",
        used_for=("weekly-brief", "business-prd"),
        expected_document_set="dreamfi-source-metabase",
        href="/console/integrations/metabase",
        requires_dreamfi_secret=True,
        config_fields=(
            _base_url_field("Metabase base URL", "https://metabase.company.com"),
            _endpoints_field("/api/card,/api/dashboard"),
            *_auth_fields(header_default="x-api-key", scheme_default=""),
            *_metadata_fields(),
        ),
        default_config=_rest_default_config(
            endpoints="/api/card,/api/dashboard",
            auth_header="x-api-key",
            auth_scheme="",
        ),
    ),
    ConnectorSpec(
        connector_id="posthog",
        name="PostHog",
        category="product_analytics",
        purpose="Product events, funnels, and session data",
        used_for=("weekly-brief", "technical-prd"),
        expected_document_set="dreamfi-source-posthog",
        href="/console/integrations/posthog",
        requires_dreamfi_secret=True,
        config_fields=(
            ConnectorConfigField(
                key="project_id",
                label="PostHog project ID",
                placeholder="12345",
            ),
            _base_url_field(
                "PostHog base URL",
                DEFAULT_POSTHOG_BASE_URL,
                required=False,
                default=DEFAULT_POSTHOG_BASE_URL,
            ),
            _endpoints_field("/api/projects/{project_id}/insights,/api/projects/{project_id}/dashboards"),
            *_metadata_fields(),
        ),
        default_config={"base_url": DEFAULT_POSTHOG_BASE_URL},
    ),
    ConnectorSpec(
        connector_id="ga",
        name="Google Analytics",
        category="marketing_analytics",
        purpose="Acquisition, traffic, and conversion signals",
        used_for=("business-prd",),
        expected_document_set="dreamfi-source-ga",
        href="/console/integrations/ga",
        requires_dreamfi_secret=True,
        config_fields=(
            ConnectorConfigField(
                key="property_id",
                label="GA4 property ID",
                placeholder="123456789",
            ),
            _base_url_field(
                "GA Data API base URL",
                DEFAULT_GA_BASE_URL,
                required=False,
                default=DEFAULT_GA_BASE_URL,
            ),
            ConnectorConfigField(
                key="start_date",
                label="Start date",
                required=False,
                placeholder=DEFAULT_GA_START_DATE,
                default=DEFAULT_GA_START_DATE,
                help_text="GA4 report start date, such as 30daysAgo or 2026-05-01.",
            ),
            ConnectorConfigField(
                key="end_date",
                label="End date",
                required=False,
                placeholder=DEFAULT_GA_END_DATE,
                default=DEFAULT_GA_END_DATE,
                help_text="GA4 report end date, such as today or 2026-05-07.",
            ),
            ConnectorConfigField(
                key="dimensions",
                label="Dimensions",
                required=False,
                placeholder=DEFAULT_GA_DIMENSIONS,
                default=DEFAULT_GA_DIMENSIONS,
                help_text="Comma-separated GA4 dimension names.",
            ),
            ConnectorConfigField(
                key="metrics",
                label="Metrics",
                required=False,
                placeholder=DEFAULT_GA_METRICS,
                default=DEFAULT_GA_METRICS,
                help_text="Comma-separated GA4 metric names.",
            ),
            *_metadata_fields(),
        ),
        default_config={
            "base_url": DEFAULT_GA_BASE_URL,
            "start_date": DEFAULT_GA_START_DATE,
            "end_date": DEFAULT_GA_END_DATE,
            "dimensions": DEFAULT_GA_DIMENSIONS,
            "metrics": DEFAULT_GA_METRICS,
        },
    ),
    ConnectorSpec(
        connector_id="klaviyo",
        name="Klaviyo",
        category="marketing",
        purpose="Lifecycle campaigns, audiences, and sends",
        used_for=("business-prd",),
        expected_document_set="dreamfi-source-klaviyo",
        href="/console/integrations/klaviyo",
        requires_dreamfi_secret=True,
        config_fields=(
            _base_url_field(
                "Klaviyo base URL",
                DEFAULT_KLAVIYO_BASE_URL,
                required=False,
                default=DEFAULT_KLAVIYO_BASE_URL,
            ),
            _endpoints_field("/api/campaigns,/api/flows,/api/segments"),
            ConnectorConfigField(
                key="revision",
                label="API revision",
                required=False,
                placeholder=DEFAULT_KLAVIYO_REVISION,
                default=DEFAULT_KLAVIYO_REVISION,
                help_text="Klaviyo API revision header.",
            ),
            *_metadata_fields(),
        ),
        default_config={
            "base_url": DEFAULT_KLAVIYO_BASE_URL,
            "endpoints": "/api/campaigns,/api/flows,/api/segments",
            "revision": DEFAULT_KLAVIYO_REVISION,
        },
    ),
    ConnectorSpec(
        connector_id="netxd",
        name="NetXD",
        category="payments",
        purpose="Payments and ledger transaction context",
        used_for=("risk-brd", "technical-prd"),
        expected_document_set="dreamfi-source-netxd",
        href="/console/integrations/netxd",
        requires_dreamfi_secret=True,
        config_fields=(
            _base_url_field("NetXD API base URL", "https://api.netxd.example"),
            _endpoints_field("/transactions,/accounts,/ledger-entries"),
            *_auth_fields(),
            *_metadata_fields(),
        ),
        default_config=_rest_default_config(endpoints="/transactions,/accounts,/ledger-entries"),
    ),
    ConnectorSpec(
        connector_id="sardine",
        name="Sardine",
        category="risk",
        purpose="Fraud and risk signal enrichment",
        used_for=("risk-brd",),
        expected_document_set="dreamfi-source-sardine",
        href="/console/integrations/sardine",
        requires_dreamfi_secret=True,
        config_fields=(
            _base_url_field("Sardine API base URL", "https://api.sardine.ai"),
            _endpoints_field("/v1/cases,/v1/transactions,/v1/customers"),
            *_auth_fields(),
            *_metadata_fields(),
        ),
        default_config=_rest_default_config(endpoints="/v1/cases,/v1/transactions,/v1/customers"),
    ),
    ConnectorSpec(
        connector_id="socure",
        name="Socure",
        category="identity",
        purpose="Identity verification and KYC signals",
        used_for=("risk-brd",),
        expected_document_set="dreamfi-source-socure",
        href="/console/integrations/socure",
        requires_dreamfi_secret=True,
        config_fields=(
            _base_url_field("Socure API base URL", "https://service.socure.com"),
            _endpoints_field("/api/3.0/reports,/api/3.0/decisions"),
            *_auth_fields(),
            *_metadata_fields(),
        ),
        default_config=_rest_default_config(endpoints="/api/3.0/reports,/api/3.0/decisions"),
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
