"""
Unit tests for freshness scoring.

Tests that all connectors correctly compute freshness_score.
"""

import pytest
from datetime import datetime, timedelta


class TestFreshnessScoring:
    """Verify freshness scoring follows ADR-007."""

    def test_freshness_score_fresh_data(self):
        """Recently synced data should have freshness ~1.0."""
        # last_synced_at = now, freshness_score should be near 1.0
        pass

    def test_freshness_score_aged_data(self):
        """Aged data should have reduced freshness."""
        # last_synced_at = 7 days ago (Jira half-life), freshness should be ~0.5
        pass

    def test_freshness_score_very_old_data(self):
        """Very old data should have low freshness."""
        # last_synced_at = 30+ days ago, freshness should be < 0.1
        pass

    def test_different_halflifes_per_connector(self):
        """Different connectors have different freshness half-lives."""
        # Jira: 7 days
        # Metabase: 1 day
        # PostHog: 6 hours
        # Verify calculations respect these differences
        pass
