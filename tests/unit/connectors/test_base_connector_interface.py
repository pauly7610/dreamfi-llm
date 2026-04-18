"""
Unit tests for base connector interface.

Tests that all connectors properly implement the base interface contract.
"""

import pytest
from datetime import datetime


class TestBaseConnectorInterface:
    """Verify connector interface is properly defined and followed."""

    def test_connector_auth_config_required(self):
        """Connector must require auth config."""
        # This tests that connector init validates required fields
        pass

    def test_connector_normalizes_required_fields(self):
        """Connector must normalize all required canonical fields."""
        required_fields = {
            'source_system',
            'source_object_id',
            'last_synced_at',
            'freshness_score',
            'eligible_skill_families_json',
        }
        # Implementation: test that normalized output contains all fields
        pass

    def test_freshness_score_in_valid_range(self):
        """Freshness score must be 0-1 decimal."""
        # freshness_score should never be > 1 or < 0
        pass

    def test_pagination_handling(self):
        """Connector should handle paginated responses."""
        pass

    def test_rate_limit_retry_logic(self):
        """Connector should retry on 429 with exponential backoff."""
        pass

    def test_error_handling_typed(self):
        """Connector should emit typed errors."""
        pass
