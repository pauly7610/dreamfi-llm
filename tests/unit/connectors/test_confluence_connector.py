"""
Unit tests for Confluence connector.

Tests authentication, page normalization, and pagination.
"""

import pytest


class TestConfluenceConnectorUnit:
    """Unit tests for Confluence connector."""

    def test_confluence_auth_from_env(self):
        """Confluence should parse auth from environment."""
        # CONFLUENCE_BASE_URL, CONFLUENCE_API_TOKEN
        pass

    def test_confluence_page_normalization(self):
        """Confluence page should normalize to NormalizedEntity."""
        pass

    def test_confluence_pagination_cql_search(self):
        """Should handle CQL search pagination."""
        pass

    def test_confluence_freshness_calculation(self):
        """Confluence freshness based on last modified date."""
        pass
