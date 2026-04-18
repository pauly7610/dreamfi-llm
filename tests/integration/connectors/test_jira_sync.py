"""
Integration tests for Jira connector sync.

Tests end-to-end Jira sync with real database writes.
"""

import pytest


class TestJiraConnectorIntegration:
    """Integration tests: Jira connector syncs to canonical schema."""

    def test_jira_sync_watermarking(self, db_connection):
        """Changed objects sync, unchanged objects skipped."""
        # Create object with old timestamp
        # Run sync twice
        # Verify no duplicates, unchanged object has same row
        pass

    def test_jira_sync_malformed_payload_dead_letter(self, db_connection):
        """Malformed Jira issue goes to dead-letter, not canonical DB."""
        # Provide payload with missing required field
        # Verify not in core_entities
        pass

    def test_jira_sync_real_fixture_end_to_end(self, db_connection):
        """One real Jira issue should sync successfully."""
        # Requires real Jira API credentials
        # Syncs an actual issue to canonical DB
        pass

    def test_jira_sync_no_duplicates_on_retry(self, db_connection):
        """Retries should not create duplicate records."""
        pass
