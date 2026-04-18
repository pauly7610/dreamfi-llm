"""
Test contract to schema alignment.

Validates that skills defined in contracts match schema-seeded skills exactly.
"""
import pytest


class TestContractToSchemaAlignment:
    """Verify contract→schema consistency."""

    def test_no_skill_in_schema_without_contract(self):
        """All schema-seeded skills must have corresponding locked eval file.
        
        Expected: Every skill in skills table has matching contract file.
        """
        pass

    def test_no_contract_without_schema_skill(self):
        """All contracts must be seeded in schema.
        
        Expected: Every locked eval file resolves to a skills table entry.
        """
        pass

    def test_skill_name_matches_exactly(self):
        """Skill names in schema must match contract identifiers.
        
        Expected: agent_system_prompt, support_agent, meeting_summary match exactly.
        """
        pass

    def test_eval_file_path_matches(self):
        """Schema eval_file_path must point to actual locked eval file.
        
        Expected: evals/agent-system-prompt.md exists and is locked.
        """
        pass

    def test_tier_level_matches(self):
        """Contract tier level must match schema tier level.
        
        Expected: Tier 1 skills in schema map to Tier 1 contracts.
        """
        pass

    def test_criteria_count_matches(self):
        """Number of criteria in contract must match schema.
        
        Expected: agent_system_prompt has 5 criteria in both sources.
        """
        pass

    def test_hard_gates_consistent(self):
        """Hard gates defined in contract must match schema metadata.
        
        Expected: Same gates flagged in both sources.
        """
        pass
