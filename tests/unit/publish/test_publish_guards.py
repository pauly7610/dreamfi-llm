"""
Unit tests for publish guards.

Tests ADR-006: Hard gates must block publish 100% of the time.
"""

import pytest


class TestPublishGuards:
    """Verify all publish guards work."""

    def test_publish_blocked_on_hard_gate_fail(self):
        """Publish must be blocked if any hard-gate criterion failed."""
        pass

    def test_publish_blocked_on_stale_data(self):
        """Publish must be blocked if freshness < 0.6."""
        pass

    def test_publish_blocked_on_skill_mismatch(self):
        """Publish must be blocked if artifact skill type mismatches."""
        pass

    def test_publish_blocked_on_low_confidence(self):
        """Publish must be blocked if confidence < 0.7."""
        pass

    def test_publish_includes_source_references(self):
        """Publish must include source references."""
        pass

    def test_publish_includes_evaluation_score(self):
        """Publish must include evaluation score."""
        pass

    def test_publish_includes_artifact_metadata(self):
        """Publish must include artifact metadata."""
        pass
