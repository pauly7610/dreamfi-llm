"""Klaviyo integration — REST API v2024 via httpx."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from config import config as _cfg
from config import KlaviyoConfig
from integrations.errors import DreamFiIntegrationError

log = logging.getLogger(__name__)

_KLAVIYO_BASE = "https://a.klaviyo.com/api"


class KlaviyoClient:
    """Async-first client for the Klaviyo API (with sync wrappers)."""

    def __init__(self, cfg: KlaviyoConfig | None = None):
        c = cfg or _cfg.klaviyo
        self._headers = {
            "Authorization": f"Klaviyo-API-Key {c.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "revision": "2024-10-15",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=_KLAVIYO_BASE, headers=self._headers, timeout=30)

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        async with self._client() as client:
            resp = await client.request(method, path, **kwargs)
            if resp.status_code >= 400:
                raise DreamFiIntegrationError(
                    "klaviyo", f"{method.upper()} {path} failed",
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
    # Campaigns
    # ------------------------------------------------------------------

    async def async_get_campaigns(self, status: str | None = None) -> list[dict[str, Any]]:
        """List campaigns, optionally filtered by status (draft, scheduled, sent)."""
        params: dict[str, str] = {}
        if status:
            params["filter"] = f'equals(messages.channel,"email"),equals(status,"{status}")'
        data = await self._request("GET", "/campaigns", params=params)
        return data.get("data", [])

    def get_campaigns(self, status: str | None = None):
        return self._sync(self.async_get_campaigns(status))

    async def async_get_campaign_metrics(self, campaign_id: str) -> dict[str, Any]:
        """Retrieve open/click/conversion rates for a campaign."""
        data = await self._request(
            "GET",
            f"/campaigns/{campaign_id}",
            params={"fields[campaign]": "send_time,status"},
        )
        campaign = data.get("data", {})
        # Fetch associated metrics via the campaign-values endpoint
        metrics = await self._request(
            "GET",
            f"/campaign-values-reports",
            params={
                "filter": f'equals(campaign_id,"{campaign_id}")',
                "fields[campaign-values-report]": "statistics",
            },
        )
        log.info("Fetched metrics for campaign %s", campaign_id)
        return {"campaign": campaign, "metrics": metrics.get("data", [])}

    def get_campaign_metrics(self, campaign_id: str):
        return self._sync(self.async_get_campaign_metrics(campaign_id))

    # ------------------------------------------------------------------
    # Flows
    # ------------------------------------------------------------------

    async def async_get_flows(self) -> list[dict[str, Any]]:
        """List all flows."""
        data = await self._request("GET", "/flows")
        return data.get("data", [])

    def get_flows(self):
        return self._sync(self.async_get_flows())

    async def async_get_flow_metrics(self, flow_id: str) -> dict[str, Any]:
        """Fetch performance metrics for a flow."""
        data = await self._request(
            "GET",
            f"/flow-values-reports",
            params={
                "filter": f'equals(flow_id,"{flow_id}")',
                "fields[flow-values-report]": "statistics",
            },
        )
        log.info("Fetched metrics for flow %s", flow_id)
        return data.get("data", {})

    def get_flow_metrics(self, flow_id: str):
        return self._sync(self.async_get_flow_metrics(flow_id))

    # ------------------------------------------------------------------
    # Lists
    # ------------------------------------------------------------------

    async def async_get_lists(self) -> list[dict[str, Any]]:
        """List all subscriber lists."""
        data = await self._request("GET", "/lists")
        return data.get("data", [])

    def get_lists(self):
        return self._sync(self.async_get_lists())
