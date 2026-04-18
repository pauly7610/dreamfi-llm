"""Sardine integration — fraud monitoring REST API via httpx."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from config import config as _cfg
from config import SardineConfig
from integrations.errors import DreamFiIntegrationError

log = logging.getLogger(__name__)


class SardineClient:
    """Async-first client for the Sardine API (with sync wrappers)."""

    def __init__(self, cfg: SardineConfig | None = None):
        c = cfg or _cfg.sardine
        self._base = c.api_url.rstrip("/")
        self._headers = {
            "Content-Type": "application/json",
        }
        self._auth = (c.client_id, c.secret_key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base,
            headers=self._headers,
            auth=self._auth,
            timeout=30,
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        async with self._client() as client:
            resp = await client.request(method, path, **kwargs)
            if resp.status_code >= 400:
                raise DreamFiIntegrationError(
                    "sardine", f"{method.upper()} {path} failed",
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
    # Transactions
    # ------------------------------------------------------------------

    async def async_get_transactions(
        self, date_from: str, date_to: str, filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch transactions within a date range."""
        params: dict[str, Any] = {"start_date": date_from, "end_date": date_to}
        if filters:
            params.update(filters)
        data = await self._request("GET", "/v1/transactions", params=params)
        return data if isinstance(data, list) else data.get("data", data.get("transactions", []))

    def get_transactions(self, date_from: str, date_to: str, filters=None):
        return self._sync(self.async_get_transactions(date_from, date_to, filters))

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    async def async_get_alerts(
        self, status: str | None = None, date_from: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch fraud alerts, optionally filtered by status and start date."""
        params: dict[str, str] = {}
        if status:
            params["status"] = status
        if date_from:
            params["start_date"] = date_from
        data = await self._request("GET", "/v1/alerts", params=params)
        return data if isinstance(data, list) else data.get("data", data.get("alerts", []))

    def get_alerts(self, status=None, date_from=None):
        return self._sync(self.async_get_alerts(status, date_from))

    # ------------------------------------------------------------------
    # Risk
    # ------------------------------------------------------------------

    async def async_get_risk_scores(self, transaction_ids: list[str]) -> list[dict[str, Any]]:
        """Get risk assessment for one or more transactions."""
        payload = {"transaction_ids": transaction_ids}
        data = await self._request("POST", "/v1/risk/scores", json=payload)
        return data if isinstance(data, list) else data.get("data", data.get("scores", []))

    def get_risk_scores(self, transaction_ids: list[str]):
        return self._sync(self.async_get_risk_scores(transaction_ids))

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    async def async_get_rules(self) -> list[dict[str, Any]]:
        """List all monitoring rules."""
        data = await self._request("GET", "/v1/rules")
        return data if isinstance(data, list) else data.get("data", data.get("rules", []))

    def get_rules(self):
        return self._sync(self.async_get_rules())

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    async def async_get_summary(self, date_from: str, date_to: str) -> dict[str, Any]:
        """Aggregated fraud summary for a date range."""
        params = {"start_date": date_from, "end_date": date_to}
        log.info("Fetching Sardine summary %s to %s", date_from, date_to)
        return await self._request("GET", "/v1/summary", params=params)

    def get_summary(self, date_from: str, date_to: str):
        return self._sync(self.async_get_summary(date_from, date_to))
