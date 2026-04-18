"""
Integration tests for prompt version promotion.

Tests ADR-004 and ADR-008: keep improvements, revert regressions.
"""

import pytest


class TestPromptPromotion:
    """Tests for skill prompt version promotion and rollback logic."""

    def test_promotion_threshold_2_percent(self):
        """New prompt only promoted if score > previous + 2.0%."""
        pass

    def test_regression_blocks_activation(self):
        """Regression (score < previous - 2%) should not activate new version."""
        pass

    def test_regression_reverts_to_previous(self):
        """On regression, previous version reactivated."""
        pass

    def test_hard_gates_required_for_promotion(self):
        """All hard-gate criteria must pass for promotion."""
        pass

    def test_promotion_updates_active_prompt_version_id(self, db_connection):
        """Promotion should update skill_registry.active_prompt_version_id."""
        pass
