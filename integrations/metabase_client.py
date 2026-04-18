"""Metabase integration — REST API via httpx."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from config import config as _cfg
from config import MetabaseConfig
from integrations.errors import DreamFiIntegrationError

log = logging.getLogger(__name__)


class MetabaseClient:
    """Async-first client for Metabase (with sync wrappers)."""

    def __init__(self, cfg: MetabaseConfig | None = None):
        self._cfg = cfg or _cfg.metabase
        self._base = self._cfg.url.rstrip("/") + "/api"
        self._session_token: str | None = self._cfg.session_token or None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self._session_token:
            h["X-Metabase-Session"] = self._session_token
        return h

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base, headers=self._headers(), timeout=60)

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        async with self._client() as client:
            resp = await client.request(method, path, **kwargs)
            if resp.status_code >= 400:
                raise DreamFiIntegrationError(
                    "metabase", f"{method.upper()} {path} failed",
                    status_code=resp.status_code, detail=resp.text,
                )
            # Some endpoints return raw bytes (PDF export).
            ct = resp.headers.get("content-type", "")
            if "application/json" in ct:
                return resp.json()
            return resp.content

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
    # Auth
    # ------------------------------------------------------------------

    async def async_authenticate(self) -> str:
        """Obtain a session token from Metabase using username/password."""
        payload = {"username": self._cfg.username, "password": self._cfg.password}
        async with httpx.AsyncClient(base_url=self._base, timeout=15) as client:
            resp = await client.post("/session", json=payload)
            if resp.status_code >= 400:
                raise DreamFiIntegrationError(
                    "metabase", "Authentication failed",
                    status_code=resp.status_code, detail=resp.text,
                )
            token = resp.json().get("id", "")
            self._session_token = token
            log.info("Metabase authenticated successfully")
            return token

    def authenticate(self) -> str:
        """Sync wrapper for :meth:`async_authenticate`."""
        return self._sync(self.async_authenticate())

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def async_run_query(self, database_id: int, native_query: str) -> dict[str, Any]:
        """Execute a native SQL query against *database_id*."""
        payload = {
            "database": database_id,
            "type": "native",
            "native": {"query": native_query},
        }
        log.info("Running native query on db %d", database_id)
        return await self._request("POST", "/dataset", json=payload)

    def run_query(self, database_id: int, native_query: str) -> dict[str, Any]:
        return self._sync(self.async_run_query(database_id, native_query))

    # ------------------------------------------------------------------
    # Cards (saved questions)
    # ------------------------------------------------------------------

    async def async_get_card(self, card_id: int) -> dict[str, Any]:
        """Get a saved question definition."""
        return await self._request("GET", f"/card/{card_id}")

    def get_card(self, card_id: int) -> dict[str, Any]:
        return self._sync(self.async_get_card(card_id))

    async def async_run_card(self, card_id: int, parameters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Execute a saved question and return results."""
        payload = {"parameters": parameters or []}
        return await self._request("POST", f"/card/{card_id}/query", json=payload)

    def run_card(self, card_id: int, parameters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return self._sync(self.async_run_card(card_id, parameters))

    async def async_create_card(
        self, name: str, dataset_query: dict[str, Any], visualization: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new saved question."""
        payload = {"name": name, "dataset_query": dataset_query, "display": visualization.get("display", "table"), "visualization_settings": visualization}
        result = await self._request("POST", "/card", json=payload)
        log.info("Created card '%s' (id=%s)", name, result.get("id"))
        return result

    def create_card(self, name: str, dataset_query: dict[str, Any], visualization: dict[str, Any]) -> dict[str, Any]:
        return self._sync(self.async_create_card(name, dataset_query, visualization))

    # ------------------------------------------------------------------
    # Dashboards
    # ------------------------------------------------------------------

    async def async_get_dashboard(self, dashboard_id: int) -> dict[str, Any]:
        """Get dashboard definition including cards."""
        return await self._request("GET", f"/dashboard/{dashboard_id}")

    def get_dashboard(self, dashboard_id: int) -> dict[str, Any]:
        return self._sync(self.async_get_dashboard(dashboard_id))

    async def async_export_dashboard_pdf(self, dashboard_id: int) -> bytes:
        """Export a dashboard as PDF bytes."""
        log.info("Exporting dashboard %d as PDF", dashboard_id)
        data = await self._request("POST", f"/dashboard/{dashboard_id}/pdf")
        if isinstance(data, bytes):
            return data
        raise DreamFiIntegrationError("metabase", f"Expected PDF bytes for dashboard {dashboard_id}")

    def export_dashboard_pdf(self, dashboard_id: int) -> bytes:
        return self._sync(self.async_export_dashboard_pdf(dashboard_id))
