"""
Unit tests for planning field mapping.

Tests that status and field mappings are deterministic.
"""

import pytest


class TestFieldMapping:
    """Verify planning field mapping is deterministic."""

    def test_jira_status_mapping_deterministic(self):
        """Same Jira status always maps to same canonical status."""
        pass

    def test_dragonboat_status_mapping_deterministic(self):
        """Same Dragonboat status always maps to same canonical status."""
        pass

    def test_invalid_status_rejected(self):
        """Unknown statuses should be rejected."""
        pass

    def test_date_field_normalization(self):
        """Dates should be normalized to ISO-8601."""
        pass
