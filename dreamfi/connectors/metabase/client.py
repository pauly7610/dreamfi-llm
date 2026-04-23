"""Metabase client (session-based auth)."""
from __future__ import annotations

from typing import Any

import httpx

from dreamfi.connectors.base import HttpConnector, connector_retry
from dreamfi.connectors.metabase.models import MetabaseCardResult, MetabaseDatasetResult


def _extract_rows(data: dict[str, Any]) -> tuple[list[list[Any]], list[str]]:
    payload = data.get("data") or {}
    rows = list(payload.get("rows") or [])
    cols_raw = payload.get("cols") or []
    columns = [str(c.get("name", "")) for c in cols_raw]
    return rows, columns


class MetabaseClient(HttpConnector):
    health_path = "/api/user/current"

    def __init__(
        self,
        base_url: str,
        *,
        session_token: str,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._session_token = session_token
        super().__init__(base_url, timeout=timeout, transport=transport)

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Metabase-Session": self._session_token,
        }

    @connector_retry
    def query_card(self, card_id: int) -> MetabaseCardResult:
        resp = self._post(f"/api/card/{card_id}/query")
        rows, columns = _extract_rows(resp.json())
        return MetabaseCardResult(card_id=card_id, rows=rows, columns=columns)

    @connector_retry
    def dataset(self, database_id: int, native_query: str) -> MetabaseDatasetResult:
        resp = self._post(
            "/api/dataset",
            json={
                "database": database_id,
                "type": "native",
                "native": {"query": native_query},
            },
        )
        rows, columns = _extract_rows(resp.json())
        return MetabaseDatasetResult(
            database_id=database_id, rows=rows, columns=columns
        )
