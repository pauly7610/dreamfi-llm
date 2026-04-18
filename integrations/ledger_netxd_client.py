"""NetXD ledger integration — REST API via httpx."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from config import config as _cfg
from config import NetXDConfig
from integrations.errors import DreamFiIntegrationError

log = logging.getLogger(__name__)


class NetXDClient:
    """Async-first client for the NetXD ledger API (with sync wrappers)."""

    def __init__(self, cfg: NetXDConfig | None = None):
        c = cfg or _cfg.netxd
        self._base = c.api_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {c.api_key}",
            "X-Client-Id": c.client_id,
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base, headers=self._headers, timeout=30)

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        async with self._client() as client:
            resp = await client.request(method, path, **kwargs)
            if resp.status_code >= 400:
                raise DreamFiIntegrationError(
                    "netxd", f"{method.upper()} {path} failed",
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
        """Fetch ledger transactions within a date range."""
        params: dict[str, Any] = {"start_date": date_from, "end_date": date_to}
        if filters:
            params.update(filters)
        data = await self._request("GET", "/api/v1/transactions", params=params)
        return data if isinstance(data, list) else data.get("data", data.get("transactions", []))

    def get_transactions(self, date_from: str, date_to: str, filters=None):
        return self._sync(self.async_get_transactions(date_from, date_to, filters))

    # ------------------------------------------------------------------
    # Balances
    # ------------------------------------------------------------------

    async def async_get_balances(self, account_ids: list[str] | None = None) -> list[dict[str, Any]]:
        """Fetch account balances, optionally scoped to specific accounts."""
        params: dict[str, Any] = {}
        if account_ids:
            params["account_ids"] = ",".join(account_ids)
        data = await self._request("GET", "/api/v1/balances", params=params)
        return data if isinstance(data, list) else data.get("data", data.get("balances", []))

    def get_balances(self, account_ids: list[str] | None = None):
        return self._sync(self.async_get_balances(account_ids))

    # ------------------------------------------------------------------
    # Settlements
    # ------------------------------------------------------------------

    async def async_get_settlements(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        """Fetch settlement data within a date range."""
        params = {"start_date": date_from, "end_date": date_to}
        data = await self._request("GET", "/api/v1/settlements", params=params)
        return data if isinstance(data, list) else data.get("data", data.get("settlements", []))

    def get_settlements(self, date_from: str, date_to: str):
        return self._sync(self.async_get_settlements(date_from, date_to))

    # ------------------------------------------------------------------
    # Reconciliation
    # ------------------------------------------------------------------

    async def async_get_reconciliation_status(self) -> dict[str, Any]:
        """Fetch current reconciliation status."""
        log.info("Fetching NetXD reconciliation status")
        return await self._request("GET", "/api/v1/reconciliation/status")

    def get_reconciliation_status(self):
        return self._sync(self.async_get_reconciliation_status())

    # ------------------------------------------------------------------
    # Journal entries
    # ------------------------------------------------------------------

    async def async_get_journal_entries(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        """Fetch journal entries within a date range."""
        params = {"start_date": date_from, "end_date": date_to}
        data = await self._request("GET", "/api/v1/journal-entries", params=params)
        return data if isinstance(data, list) else data.get("data", data.get("entries", []))

    def get_journal_entries(self, date_from: str, date_to: str):
        return self._sync(self.async_get_journal_entries(date_from, date_to))
