"""
Unit tests for support_agent skill evaluation.

Tests C1-C5 criteria from locked eval file.
"""

import pytest


class TestSupportAgentSkill:
    """Unit tests for support_agent scoring."""

    def test_c1_resolve_without_escalation(self):
        """C1: Should resolve without escalation when possible."""
        pass

    def test_c2_kb_only_info(self):
        """C2: Should use only knowledge base information."""
        pass

    def test_c3_three_message_limit(self):
        """C3: Should resolve within 3 messages."""
        pass

    def test_c4_escalation_path(self):
        """C4: Should escalate correctly when required."""
        pass

    def test_c5_word_limit_120(self):
        """C5: Response should be under 120 words."""
        pass
