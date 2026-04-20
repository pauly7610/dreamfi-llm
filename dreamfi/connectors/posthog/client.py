"""PostHog client (project-scoped, personal-API-key auth)."""
from __future__ import annotations

from typing import Any

import httpx

from dreamfi.connectors.base import HttpConnector, connector_retry
from dreamfi.connectors.posthog.models import PostHogFeatureFlag, PostHogResult


class PostHogClient(HttpConnector):
    health_path = "/api/users/@me/"

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str,
        project_id: int,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._project_id = project_id
        super().__init__(base_url, timeout=timeout, transport=transport)

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

    @connector_retry
    def query_funnel(self, definition: dict[str, Any]) -> PostHogResult:
        resp = self._post(
            f"/api/projects/{self._project_id}/insights/funnel/",
            json=definition,
        )
        data = resp.json()
        return PostHogResult(
            query_id=str(data.get("id") or data.get("query_id") or "funnel"),
            result=list(data.get("result") or []),
            columns=list(data.get("columns") or []),
        )

    @connector_retry
    def query_trend(self, definition: dict[str, Any]) -> PostHogResult:
        resp = self._post(
            f"/api/projects/{self._project_id}/insights/trend/",
            json=definition,
        )
        data = resp.json()
        return PostHogResult(
            query_id=str(data.get("id") or "trend"),
            result=list(data.get("result") or []),
            columns=list(data.get("columns") or []),
        )

    @connector_retry
    def events_for_user(
        self, distinct_id: str, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        resp = self._get(
            f"/api/projects/{self._project_id}/events/",
            params={"distinct_id": distinct_id, "limit": limit},
        )
        data = resp.json()
        return list(data.get("results") or [])

    @connector_retry
    def feature_flag_state(self, key: str) -> PostHogFeatureFlag | None:
        resp = self._get(
            f"/api/projects/{self._project_id}/feature_flags/",
            params={"search": key},
        )
        data = resp.json()
        for flag in data.get("results") or []:
            if flag.get("key") == key:
                return PostHogFeatureFlag(
                    key=flag["key"],
                    active=bool(flag.get("active", False)),
                    rollout_percentage=flag.get("rollout_percentage"),
                )
        return None
