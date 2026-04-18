"""Socure integration — identity verification REST API via httpx."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from config import config as _cfg
from config import SocureConfig
from integrations.errors import DreamFiIntegrationError

log = logging.getLogger(__name__)


class SocureClient:
    """Async-first client for the Socure API (with sync wrappers)."""

    def __init__(self, cfg: SocureConfig | None = None):
        c = cfg or _cfg.socure
        self._base = c.api_url.rstrip("/")
        self._headers = {
            "Authorization": f"SocureApiKey {c.api_key}",
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
                    "socure", f"{method.upper()} {path} failed",
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
    # Identity verification
    # ------------------------------------------------------------------

    async def async_verify_identity(self, person_data: dict[str, Any]) -> dict[str, Any]:
        """Submit identity data for verification.

        *person_data* should include fields like ``firstName``, ``surName``,
        ``email``, ``dob``, ``address``, etc.
        """
        log.info("Submitting identity verification request")
        return await self._request("POST", "/api/3.0/EmailAuthScore", json=person_data)

    def verify_identity(self, person_data: dict[str, Any]):
        return self._sync(self.async_verify_identity(person_data))

    async def async_get_risk_score(self, reference_id: str) -> dict[str, Any]:
        """Retrieve detailed risk score for a previous verification."""
        return await self._request("GET", f"/api/3.0/risk/{reference_id}")

    def get_risk_score(self, reference_id: str):
        return self._sync(self.async_get_risk_score(reference_id))

    # ------------------------------------------------------------------
    # Decision history
    # ------------------------------------------------------------------

    async def async_get_decisions(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        """Fetch decision history within a date range."""
        params = {"start_date": date_from, "end_date": date_to}
        data = await self._request("GET", "/api/3.0/decisions", params=params)
        return data if isinstance(data, list) else data.get("data", data.get("decisions", []))

    def get_decisions(self, date_from: str, date_to: str):
        return self._sync(self.async_get_decisions(date_from, date_to))

    async def async_get_pass_fail_rates(self, date_from: str, date_to: str) -> dict[str, Any]:
        """Get aggregate pass/fail rates for a date range."""
        params = {"start_date": date_from, "end_date": date_to}
        log.info("Fetching Socure pass/fail rates %s to %s", date_from, date_to)
        return await self._request("GET", "/api/3.0/decisions/summary", params=params)

    def get_pass_fail_rates(self, date_from: str, date_to: str):
        return self._sync(self.async_get_pass_fail_rates(date_from, date_to))

    # ------------------------------------------------------------------
    # Modules
    # ------------------------------------------------------------------

    async def async_get_modules(self) -> list[dict[str, Any]]:
        """List available verification modules."""
        data = await self._request("GET", "/api/3.0/modules")
        return data if isinstance(data, list) else data.get("data", data.get("modules", []))

    def get_modules(self):
        return self._sync(self.async_get_modules())
