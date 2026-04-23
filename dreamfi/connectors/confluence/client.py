"""Confluence REST v2 client (read-only slice we actually need)."""
from __future__ import annotations

import base64
from datetime import datetime
from typing import Any

import httpx

from dreamfi.connectors.base import HttpConnector, connector_retry
from dreamfi.connectors.confluence.models import ConfluenceHistoryEntry, ConfluencePage


def _parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _page_from_json(obj: dict[str, Any]) -> ConfluencePage:
    body = obj.get("body") or {}
    storage = body.get("storage") or {}
    version = obj.get("version") or {}
    links = obj.get("_links") or {}
    return ConfluencePage(
        id=str(obj.get("id", "")),
        title=obj.get("title", ""),
        space_id=str(obj["spaceId"]) if obj.get("spaceId") is not None else None,
        parent_id=str(obj["parentId"]) if obj.get("parentId") else None,
        body_storage=storage.get("value"),
        updated_at=_parse_dt(version.get("createdAt") or obj.get("updatedAt")),
        author_account_id=version.get("authorId"),
        url=links.get("webui"),
    )


class ConfluenceClient(HttpConnector):
    """Read-only Confluence client. Atlassian cloud REST v2 shapes."""

    health_path = "/wiki/api/v2/spaces"

    def __init__(
        self,
        base_url: str,
        *,
        email: str,
        api_token: str,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._email = email
        self._api_token = api_token
        super().__init__(base_url, timeout=timeout, transport=transport)

    def _auth_headers(self) -> dict[str, str]:
        token = base64.b64encode(
            f"{self._email}:{self._api_token}".encode("utf-8")
        ).decode("ascii")
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {token}",
        }

    @connector_retry
    def get_page(self, page_id: str, *, include_body: bool = True) -> ConfluencePage:
        params: dict[str, Any] = {}
        if include_body:
            params["body-format"] = "storage"
        resp = self._get(f"/wiki/api/v2/pages/{page_id}", params=params)
        return _page_from_json(resp.json())

    @connector_retry
    def search(self, cql: str, *, limit: int = 25) -> list[ConfluencePage]:
        resp = self._get(
            "/wiki/rest/api/search", params={"cql": cql, "limit": limit}
        )
        data = resp.json()
        out: list[ConfluencePage] = []
        for hit in data.get("results") or []:
            content = hit.get("content") or {}
            if content.get("type") != "page":
                continue
            out.append(
                ConfluencePage(
                    id=str(content.get("id", "")),
                    title=content.get("title", ""),
                    url=((hit.get("url")) or None),
                    updated_at=_parse_dt(
                        (hit.get("lastModified") or hit.get("friendlyLastModified"))
                    ),
                )
            )
        return out

    @connector_retry
    def list_children(self, parent_id: str) -> list[ConfluencePage]:
        resp = self._get(f"/wiki/api/v2/pages/{parent_id}/children")
        data = resp.json()
        return [_page_from_json(o) for o in (data.get("results") or [])]

    @connector_retry
    def get_page_history(self, page_id: str) -> list[ConfluenceHistoryEntry]:
        resp = self._get(f"/wiki/api/v2/pages/{page_id}/versions")
        data = resp.json()
        out: list[ConfluenceHistoryEntry] = []
        for v in data.get("results") or []:
            out.append(
                ConfluenceHistoryEntry(
                    version=int(v.get("number", 0)),
                    when=_parse_dt(v.get("createdAt")),
                    by_account_id=v.get("authorId"),
                    message=v.get("message"),
                )
            )
        return out
