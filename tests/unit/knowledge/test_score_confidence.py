"""
Unit tests for confidence score calculation.

Tests ADR-005: confidence = eval_score × freshness × citation_count × hard_gate
"""

import pytest


class TestScoreConfidence:
    """Verify confidence scoring follows ADR-005."""

    def test_confidence_deterministic(self):
        """Same input always produces same confidence output."""
        # No randomness
        pass

    def test_confidence_reduces_with_stale_data(self):
        """Confidence reduced when freshness < 0.8."""
        pass

    def test_confidence_reduces_with_low_citations(self):
        """Confidence reduced when citation_count < 1."""
        pass

    def test_confidence_reduces_on_hard_gate_fail(self):
        """Confidence reduced when hard-gate criteria fail."""
        pass

    def test_confidence_never_high_with_stale(self):
        """Never return high confidence (>0.8) with freshness < threshold."""
        pass

    def test_confidence_breakdown_included(self):
        """Response includes breakdown of what affected score."""
        pass
