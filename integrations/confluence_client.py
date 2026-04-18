"""Confluence integration — wraps atlassian-python-api."""

from __future__ import annotations

import logging
from typing import Any

from atlassian import Confluence

from config import config as _cfg
from config import ConfluenceConfig
from integrations.errors import DreamFiIntegrationError

log = logging.getLogger(__name__)


class ConfluenceClient:
    """Thin wrapper around the Confluence REST API."""

    def __init__(self, cfg: ConfluenceConfig | None = None):
        c = cfg or _cfg.confluence
        try:
            self._confluence = Confluence(url=c.url, username=c.email, password=c.api_token)
        except Exception as exc:
            raise DreamFiIntegrationError("confluence", "Failed to initialise Confluence client") from exc

    def create_page(
        self,
        space_key: str,
        title: str,
        body_html: str,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new page in *space_key*."""
        try:
            result = self._confluence.create_page(
                space=space_key,
                title=title,
                body=body_html,
                parent_id=parent_id,
                type="page",
                representation="storage",
            )
            log.info("Created page '%s' in %s (id=%s)", title, space_key, result.get("id"))
            return result
        except Exception as exc:
            raise DreamFiIntegrationError("confluence", f"Failed to create page '{title}'") from exc

    def update_page(self, page_id: str, title: str, body_html: str) -> dict[str, Any]:
        """Update an existing page's title and body."""
        try:
            result = self._confluence.update_page(
                page_id=page_id,
                title=title,
                body=body_html,
                representation="storage",
            )
            log.info("Updated page %s", page_id)
            return result
        except Exception as exc:
            raise DreamFiIntegrationError("confluence", f"Failed to update page {page_id}") from exc

    def get_page(self, page_id: str) -> dict[str, Any]:
        """Fetch a page by ID, including body content."""
        try:
            return self._confluence.get_page_by_id(page_id, expand="body.storage,version")
        except Exception as exc:
            raise DreamFiIntegrationError("confluence", f"Failed to get page {page_id}") from exc

    def search(self, query: str, space_key: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        """Run a CQL search across Confluence."""
        try:
            cql = f'text ~ "{query}"'
            if space_key:
                cql += f' AND space = "{space_key}"'
            results = self._confluence.cql(cql, limit=limit)
            return results.get("results", [])
        except Exception as exc:
            raise DreamFiIntegrationError("confluence", f"CQL search failed: {query}") from exc

    def export_page_pdf(self, page_id: str) -> bytes:
        """Export a single page as PDF and return the raw bytes."""
        try:
            pdf = self._confluence.export_page(page_id)
            log.info("Exported page %s as PDF (%d bytes)", page_id, len(pdf))
            return pdf
        except Exception as exc:
            raise DreamFiIntegrationError("confluence", f"Failed to export page {page_id} as PDF") from exc

    def get_all_pages(self, space_key: str, limit: int = 500) -> list[dict[str, Any]]:
        """List all pages in a space."""
        try:
            return self._confluence.get_all_pages_from_space(space_key, start=0, limit=limit)
        except Exception as exc:
            raise DreamFiIntegrationError("confluence", f"Failed to list pages in {space_key}") from exc
