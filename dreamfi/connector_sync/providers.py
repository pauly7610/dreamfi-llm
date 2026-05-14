"""Provider adapters for custom DreamFi evidence sources."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import urljoin

import httpx

from dreamfi.config import get_settings
from dreamfi.connectors import (
    DEFAULT_GA_BASE_URL,
    DEFAULT_GA_DIMENSIONS,
    DEFAULT_GA_END_DATE,
    DEFAULT_GA_METRICS,
    DEFAULT_GA_START_DATE,
    DEFAULT_KLAVIYO_BASE_URL,
    DEFAULT_KLAVIYO_REVISION,
    ConnectorSpec,
)
from dreamfi.connector_sync.types import SourceDocument, utc_now


class ConnectorAdapter(Protocol):
    def fetch_documents(
        self,
        *,
        connector: ConnectorSpec,
        config: dict[str, str],
        secret: str,
        limit: int,
        transport: httpx.BaseTransport | None = None,
    ) -> list[SourceDocument]:
        ...


class ConnectorAdapterError(RuntimeError):
    """Raised when a custom provider cannot be read."""


def _client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        timeout=get_settings().dreamfi_connector_http_timeout_seconds,
        transport=transport,
    )


def _clean_base_url(value: str) -> str:
    stripped = value.strip().rstrip("/")
    if not stripped:
        raise ConnectorAdapterError("base_url is required")
    return stripped


def _paths(config: dict[str, str], defaults: tuple[str, ...]) -> tuple[str, ...]:
    configured = config.get("endpoints", "").strip()
    if not configured:
        return defaults
    return tuple(path.strip() for path in configured.split(",") if path.strip())


def _csv_values(value: str | None, defaults: tuple[str, ...] = ()) -> tuple[str, ...]:
    configured = (value or "").strip()
    if not configured:
        return defaults
    return tuple(item.strip() for item in configured.split(",") if item.strip())


def _configured_metadata(config: dict[str, str]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for key in ("product_area", "owner"):
        value = config.get(key, "").strip()
        if value:
            metadata[key] = value
    topic_ids = _csv_values(config.get("topic_ids"))
    if topic_ids:
        metadata["topic_ids"] = list(topic_ids)
    return metadata


def _join(base_url: str, path: str) -> str:
    return urljoin(f"{base_url}/", path.lstrip("/"))


def _items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "results", "items", "dashboards", "cards", "campaigns", "flows", "segments"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return [payload]


def _nested_value(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        current: Any = payload
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current[part]
        if current not in (None, ""):
            return current
    return None


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return utc_now()
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return utc_now()


def _title(item: dict[str, Any], fallback: str) -> str:
    value = _nested_value(item, "attributes.name", "attributes.title", "name", "title", "label", "id")
    return str(value or fallback)


def _external_id(item: dict[str, Any], *, connector_id: str, path: str, index: int) -> str:
    value = _nested_value(item, "id", "uuid", "key", "attributes.id", "attributes.external_id")
    return f"{path}:{value}" if value not in (None, "") else f"{path}:{connector_id}:{index}"


def _updated_at(item: dict[str, Any]) -> datetime:
    return _parse_datetime(
        _nested_value(
            item,
            "updated_at",
            "updatedAt",
            "last_updated",
            "lastUpdated",
            "attributes.updated_at",
            "attributes.updated",
            "created_at",
            "attributes.created_at",
        )
    )


def _source_url(item: dict[str, Any], base_url: str) -> str | None:
    value = _nested_value(item, "url", "link", "attributes.url", "attributes.web_url")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return base_url


def _document(
    *,
    connector: ConnectorSpec,
    config: dict[str, str],
    path: str,
    item: dict[str, Any],
    index: int,
    base_url: str,
) -> SourceDocument:
    title = _title(item, f"{connector.name} item {index + 1}")
    external_id = _external_id(item, connector_id=connector.connector_id, path=path, index=index)
    text = json.dumps(item, indent=2, sort_keys=True, ensure_ascii=False, default=str)
    return SourceDocument(
        connector_id=connector.connector_id,
        external_id=external_id,
        title=title,
        text=f"{connector.name} evidence: {title}\n\n{text}",
        source_url=_source_url(item, base_url),
        updated_at=_updated_at(item),
        metadata={
            **_configured_metadata(config),
            "provider": connector.name,
            "endpoint_path": path,
            "record_type": path.strip("/").replace("/", "_") or connector.connector_id,
        },
    )


class RestPullAdapter:
    default_paths: tuple[str, ...] = ()
    auth_header = "Authorization"
    auth_scheme = "Bearer"

    def headers(self, *, config: dict[str, str], secret: str) -> dict[str, str]:
        configured_header = config.get("auth_header")
        header = configured_header.strip() if configured_header and configured_header.strip() else self.auth_header
        scheme = config["auth_scheme"].strip() if "auth_scheme" in config else self.auth_scheme
        value = f"{scheme} {secret}" if scheme else secret
        return {header: value, "Accept": "application/json"}

    def fetch_documents(
        self,
        *,
        connector: ConnectorSpec,
        config: dict[str, str],
        secret: str,
        limit: int,
        transport: httpx.BaseTransport | None = None,
    ) -> list[SourceDocument]:
        base_url = _clean_base_url(config.get("base_url", ""))
        docs: list[SourceDocument] = []
        with _client(transport) as client:
            for path in _paths(config, self.default_paths):
                response = client.get(_join(base_url, path), headers=self.headers(config=config, secret=secret))
                response.raise_for_status()
                for index, item in enumerate(_items(response.json())):
                    docs.append(
                        _document(
                            connector=connector,
                            config=config,
                            path=path,
                            item=item,
                            index=index,
                            base_url=base_url,
                        )
                    )
                    if len(docs) >= limit:
                        return docs
        return docs


class DragonboatAdapter(RestPullAdapter):
    default_paths = ("/api/v1/initiatives", "/api/v1/features", "/api/v1/objectives")


class MetabaseAdapter(RestPullAdapter):
    default_paths = ("/api/card", "/api/dashboard")
    auth_header = "x-api-key"
    auth_scheme = ""


class NetxdAdapter(RestPullAdapter):
    default_paths = ("/transactions", "/accounts", "/ledger-entries")


class SardineAdapter(RestPullAdapter):
    default_paths = ("/v1/cases", "/v1/transactions", "/v1/customers")


class SocureAdapter(RestPullAdapter):
    default_paths = ("/api/3.0/reports", "/api/3.0/decisions")


class PostHogAdapter(RestPullAdapter):
    def fetch_documents(
        self,
        *,
        connector: ConnectorSpec,
        config: dict[str, str],
        secret: str,
        limit: int,
        transport: httpx.BaseTransport | None = None,
    ) -> list[SourceDocument]:
        project_id = config["project_id"].strip()
        base_url = _clean_base_url(config.get("base_url", "https://app.posthog.com"))
        paths = tuple(
            path.replace("{project_id}", project_id)
            for path in _paths(
                config,
                (
                    f"/api/projects/{project_id}/insights",
                    f"/api/projects/{project_id}/dashboards",
                ),
            )
        )
        return _fetch_paths(
            connector=connector,
            config={**config, "base_url": base_url, "endpoints": ",".join(paths)},
            secret=secret,
            limit=limit,
            transport=transport,
            headers={"Authorization": f"Bearer {secret}", "Accept": "application/json"},
        )


class KlaviyoAdapter(RestPullAdapter):
    def fetch_documents(
        self,
        *,
        connector: ConnectorSpec,
        config: dict[str, str],
        secret: str,
        limit: int,
        transport: httpx.BaseTransport | None = None,
    ) -> list[SourceDocument]:
        revision = config.get("revision", DEFAULT_KLAVIYO_REVISION)
        base_url = config.get("base_url", DEFAULT_KLAVIYO_BASE_URL)
        endpoints = ",".join(_paths(config, ("/api/campaigns", "/api/flows", "/api/segments")))
        return _fetch_paths(
            connector=connector,
            config={**config, "base_url": base_url, "endpoints": endpoints},
            secret=secret,
            limit=limit,
            transport=transport,
            headers={
                "Authorization": f"Klaviyo-API-Key {secret}",
                "Accept": "application/json",
                "revision": revision,
            },
        )


class GoogleAnalyticsAdapter:
    def fetch_documents(
        self,
        *,
        connector: ConnectorSpec,
        config: dict[str, str],
        secret: str,
        limit: int,
        transport: httpx.BaseTransport | None = None,
    ) -> list[SourceDocument]:
        property_id = config["property_id"].strip()
        base_url = _clean_base_url(config.get("base_url", DEFAULT_GA_BASE_URL))
        dimensions = _csv_values(
            config.get("dimensions"),
            tuple(item.strip() for item in DEFAULT_GA_DIMENSIONS.split(",") if item.strip()),
        )
        metrics = _csv_values(
            config.get("metrics"),
            tuple(item.strip() for item in DEFAULT_GA_METRICS.split(",") if item.strip()),
        )
        start_date = config.get("start_date", DEFAULT_GA_START_DATE).strip() or DEFAULT_GA_START_DATE
        end_date = config.get("end_date", DEFAULT_GA_END_DATE).strip() or DEFAULT_GA_END_DATE
        url = _join(base_url, f"/v1beta/properties/{property_id}:runReport")
        body = {
            "dateRanges": [{"startDate": start_date, "endDate": end_date}],
            "dimensions": [{"name": name} for name in dimensions],
            "metrics": [{"name": name} for name in metrics],
            "limit": str(limit),
        }
        headers = {"Authorization": f"Bearer {secret}", "Accept": "application/json"}
        with _client(transport) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
        payload = response.json()
        rows = payload.get("rows", []) if isinstance(payload, dict) else []
        docs = []
        for index, row in enumerate(item for item in rows if isinstance(item, dict)):
            dimension_values = [value.get("value") for value in row.get("dimensionValues", []) if isinstance(value, dict)]
            metric_values = [value.get("value") for value in row.get("metricValues", []) if isinstance(value, dict)]
            title = f"GA4 {property_id} {' / '.join(str(value) for value in dimension_values if value)}"
            docs.append(
                SourceDocument(
                    connector_id=connector.connector_id,
                    external_id=f"ga4:{property_id}:{index}:{':'.join(str(value) for value in dimension_values)}",
                    title=title,
                    text=json.dumps(row, indent=2, sort_keys=True, ensure_ascii=False, default=str),
                    source_url=f"https://analytics.google.com/analytics/web/#/p{property_id}",
                    updated_at=utc_now(),
                    metadata={
                        **_configured_metadata(config),
                        "provider": connector.name,
                        "record_type": "ga4_report_row",
                        "property_id": property_id,
                        "dimensions": dimension_values,
                        "metrics": metric_values,
                    },
                )
            )
        return docs


def _fetch_paths(
    *,
    connector: ConnectorSpec,
    config: dict[str, str],
    secret: str,
    limit: int,
    headers: dict[str, str],
    transport: httpx.BaseTransport | None,
) -> list[SourceDocument]:
    base_url = _clean_base_url(config.get("base_url", ""))
    docs: list[SourceDocument] = []
    with _client(transport) as client:
        for path in _paths(config, ()):
            response = client.get(_join(base_url, path), headers=headers)
            response.raise_for_status()
            for index, item in enumerate(_items(response.json())):
                docs.append(
                    _document(
                        connector=connector,
                        config=config,
                        path=path,
                        item=item,
                        index=index,
                        base_url=base_url,
                    )
                )
                if len(docs) >= limit:
                    return docs
    return docs


ADAPTERS: dict[str, ConnectorAdapter] = {
    "dragonboat": DragonboatAdapter(),
    "metabase": MetabaseAdapter(),
    "posthog": PostHogAdapter(),
    "ga": GoogleAnalyticsAdapter(),
    "klaviyo": KlaviyoAdapter(),
    "netxd": NetxdAdapter(),
    "sardine": SardineAdapter(),
    "socure": SocureAdapter(),
}


def adapter_for(connector_id: str) -> ConnectorAdapter:
    try:
        return ADAPTERS[connector_id]
    except KeyError as exc:
        raise ConnectorAdapterError(f"no custom adapter registered for {connector_id}") from exc
