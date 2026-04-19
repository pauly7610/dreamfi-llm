"""Dragonboat integration — REST API via httpx."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from config import config as _cfg
from config import DragonboatConfig
from integrations.errors import DreamFiIntegrationError

log = logging.getLogger(__name__)


class DragonboatClient:
    """Async-first client for the Dragonboat REST API (with sync wrappers)."""

    def __init__(self, cfg: DragonboatConfig | None = None):
        c = cfg or _cfg.dragonboat
        self._base = c.api_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {c.api_key}",
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
                    "dragonboat", f"{method.upper()} {path} failed",
                    status_code=resp.status_code, detail=resp.text,
                )
            return resp.json()

    def _sync(self, coro):
        """Run an async coroutine synchronously."""
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
    # Async API
    # ------------------------------------------------------------------

    async def async_get_initiatives(self) -> list[dict[str, Any]]:
        """Fetch all initiatives."""
        log.info("Fetching Dragonboat initiatives")
        data = await self._request("GET", "/initiatives")
        return data if isinstance(data, list) else data.get("data", data.get("initiatives", []))

    async def async_get_features(self, initiative_id: str | None = None) -> list[dict[str, Any]]:
        """Fetch features, optionally scoped to an initiative."""
        params = {}
        if initiative_id:
            params["initiative_id"] = initiative_id
        data = await self._request("GET", "/features", params=params)
        return data if isinstance(data, list) else data.get("data", data.get("features", []))

    async def async_get_roadmap_items(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Fetch roadmap items with optional filters."""
        data = await self._request("GET", "/roadmap", params=filters or {})
        return data if isinstance(data, list) else data.get("data", data.get("items", []))

    async def async_update_initiative(self, initiative_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update an initiative."""
        result = await self._request("PUT", f"/initiatives/{initiative_id}", json=updates)
        log.info("Updated initiative %s", initiative_id)
        return result

    async def async_update_feature_status(self, feature_id: str, status: str, rag: str) -> dict[str, Any]:
        """Update a feature's status and RAG colour."""
        payload = {"status": status, "rag": rag}
        result = await self._request("PUT", f"/features/{feature_id}", json=payload)
        log.info("Updated feature %s -> status=%s rag=%s", feature_id, status, rag)
        return result

    async def async_create_feature(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new feature."""
        result = await self._request("POST", "/features", json=data)
        log.info("Created feature: %s", result.get("id", ""))
        return result

    async def async_get_saved_reports(self) -> list[dict[str, Any]]:
        """List saved reports."""
        data = await self._request("GET", "/reports")
        return data if isinstance(data, list) else data.get("data", data.get("reports", []))

    # ------------------------------------------------------------------
    # Sync wrappers
    # ------------------------------------------------------------------

    def get_initiatives(self) -> list[dict[str, Any]]:
        """Sync wrapper for :meth:`async_get_initiatives`."""
        return self._sync(self.async_get_initiatives())

    def get_features(self, initiative_id: str | None = None) -> list[dict[str, Any]]:
        """Sync wrapper for :meth:`async_get_features`."""
        return self._sync(self.async_get_features(initiative_id))

    def get_roadmap_items(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Sync wrapper for :meth:`async_get_roadmap_items`."""
        return self._sync(self.async_get_roadmap_items(filters))

    def update_initiative(self, initiative_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Sync wrapper for :meth:`async_update_initiative`."""
        return self._sync(self.async_update_initiative(initiative_id, updates))

    def update_feature_status(self, feature_id: str, status: str, rag: str) -> dict[str, Any]:
        """Sync wrapper for :meth:`async_update_feature_status`."""
        return self._sync(self.async_update_feature_status(feature_id, status, rag))

    def create_feature(self, data: dict[str, Any]) -> dict[str, Any]:
        """Sync wrapper for :meth:`async_create_feature`."""
        return self._sync(self.async_create_feature(data))

    def get_saved_reports(self) -> list[dict[str, Any]]:
        """Sync wrapper for :meth:`async_get_saved_reports`."""
        return self._sync(self.async_get_saved_reports())
