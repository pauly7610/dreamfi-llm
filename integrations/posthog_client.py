"""PostHog integration — REST API via httpx."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from config import config as _cfg
from config import PostHogConfig
from integrations.errors import DreamFiIntegrationError

log = logging.getLogger(__name__)


class PostHogClient:
    """Async-first client for the PostHog API (with sync wrappers)."""

    def __init__(self, cfg: PostHogConfig | None = None):
        c = cfg or _cfg.posthog
        self._base = c.host.rstrip("/") + "/api"
        self._project_id = c.project_id
        self._headers = {
            "Authorization": f"Bearer {c.api_key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base, headers=self._headers, timeout=30)

    def _proj(self, path: str) -> str:
        """Prefix path with /projects/<id>."""
        return f"/projects/{self._project_id}{path}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        async with self._client() as client:
            resp = await client.request(method, path, **kwargs)
            if resp.status_code >= 400:
                raise DreamFiIntegrationError(
                    "posthog", f"{method.upper()} {path} failed",
                    status_code=resp.status_code, detail=resp.text,
                )
            return resp.json()

    def _sync(self, coro):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        return asyncio.run(coro)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    async def async_get_events(
        self,
        event_name: str,
        filters: dict[str, Any] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch events by name with optional property filters and date range."""
        params: dict[str, Any] = {"event": event_name}
        if date_from:
            params["after"] = date_from
        if date_to:
            params["before"] = date_to
        if filters:
            params["properties"] = filters
        data = await self._request("GET", self._proj("/events"), params=params)
        return data.get("results", [])

    def get_events(self, event_name: str, filters=None, date_from=None, date_to=None):
        return self._sync(self.async_get_events(event_name, filters, date_from, date_to))

    # ------------------------------------------------------------------
    # Funnels & trends
    # ------------------------------------------------------------------

    async def async_get_funnel(self, funnel_id: int) -> dict[str, Any]:
        """Fetch conversion funnel data for a saved funnel insight."""
        return await self._request("GET", self._proj(f"/insights/{funnel_id}"))

    def get_funnel(self, funnel_id: int) -> dict[str, Any]:
        return self._sync(self.async_get_funnel(funnel_id))

    async def async_get_trends(
        self,
        events: list[dict[str, Any]],
        date_from: str,
        date_to: str,
    ) -> dict[str, Any]:
        """Compute trend data for the given events and date range."""
        payload = {
            "insight": "TRENDS",
            "events": events,
            "date_from": date_from,
            "date_to": date_to,
        }
        return await self._request("POST", self._proj("/insights/trend"), json=payload)

    def get_trends(self, events, date_from, date_to):
        return self._sync(self.async_get_trends(events, date_from, date_to))

    # ------------------------------------------------------------------
    # Insights & feature flags
    # ------------------------------------------------------------------

    async def async_get_insights(self, insight_id: int) -> dict[str, Any]:
        """Fetch a saved insight by ID."""
        return await self._request("GET", self._proj(f"/insights/{insight_id}"))

    def get_insights(self, insight_id: int) -> dict[str, Any]:
        return self._sync(self.async_get_insights(insight_id))

    async def async_get_feature_flags(self) -> list[dict[str, Any]]:
        """List all feature flags."""
        data = await self._request("GET", self._proj("/feature_flags"))
        return data.get("results", [])

    def get_feature_flags(self):
        return self._sync(self.async_get_feature_flags())

    # ------------------------------------------------------------------
    # Persons
    # ------------------------------------------------------------------

    async def async_get_persons(self, properties_filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Fetch persons, optionally filtered by properties."""
        params = {}
        if properties_filter:
            params["properties"] = properties_filter
        data = await self._request("GET", self._proj("/persons"), params=params)
        return data.get("results", [])

    def get_persons(self, properties_filter=None):
        return self._sync(self.async_get_persons(properties_filter))
