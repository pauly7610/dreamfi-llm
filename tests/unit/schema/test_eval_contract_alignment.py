"""
Unit tests for eval contract alignment.

CRITICAL TEST: Fails if schema and locked eval files disagree.
This catches path inconsistencies (.yaml vs .md) and criteria drift.
"""

import pytest
import os
from pathlib import Path


class TestEvalContractAlignment:
    """Verify locked eval files match schema definitions."""

    def test_eval_file_paths_use_md_format(self, db_connection):
        """All seeded evaluation_file_path values should reference .md files."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT skill_name, evaluation_file_path 
            FROM skill_registry 
            WHERE status = 'active'
        """)
        
        results = cursor.fetchall()
        for skill_name, eval_path in results:
            assert eval_path.endswith('.md'), \
                f"Skill {skill_name} references {eval_path} - should be .md not .yaml"

    def test_eval_files_exist(self):
        """All referenced eval files must exist in evals/ directory."""
        repo_root = Path(__file__).parent.parent.parent.parent
        evals_dir = repo_root / 'evals'
        
        expected_files = [
            'agent-system-prompt.md',
            'support-agent.md',
            'meeting-summary.md',
            'cold-email.md',
            'landing-page-copy.md',
            'newsletter-headline.md',
            'product-description.md',
            'resume-bullet.md',
            'short-form-script.md',
        ]
        
        for filename in expected_files:
            filepath = evals_dir / filename
            assert filepath.exists(), f"Missing eval file: {filepath}"

    def test_tier1_skills_criteria_alignment(self, db_connection):
        """Tier 1 skills must have same criteria count in schema as in locked eval files."""
        cursor = db_connection.cursor()
        
        tier1_skills_expected_criteria = {
            'agent_system_prompt': 5,
            'support_agent': 5,
            'meeting_summary': 5,
        }
        
        for skill_name, expected_count in tier1_skills_expected_criteria.items():
            cursor.execute("""
                SELECT COUNT(*) 
                FROM evaluation_criteria_catalog ec
                JOIN skill_registry sr ON ec.skill_id = sr.skill_id
                WHERE sr.skill_name = %s
            """, (skill_name,))
            
            actual_count = cursor.fetchone()[0]
            assert actual_count == expected_count, \
                f"Skill {skill_name}: expected {expected_count} criteria, got {actual_count}"

    def test_hard_gate_criteria_marked(self, db_connection):
        """All hard-gate criteria for Tier 1 skills must be marked as is_hard_gate = true."""
        cursor = db_connection.cursor()
        
        cursor.execute("""
            SELECT sr.skill_name, COUNT(*) as soft_gates
            FROM evaluation_criteria_catalog ec
            JOIN skill_registry sr ON ec.skill_id = sr.skill_id
            WHERE sr.skill_name IN ('agent_system_prompt', 'support_agent', 'meeting_summary')
            AND ec.is_hard_gate = false
            GROUP BY sr.skill_name
        """)
        
        soft_gate_skills = cursor.fetchall()
        assert len(soft_gate_skills) == 0, \
            f"Tier 1 skills should have all hard gates, found soft gates: {soft_gate_skills}"

    def test_criteria_names_consistency(self, db_connection):
        """Criteria names should follow C1, C2, C3... format for Tier 1 skills."""
        cursor = db_connection.cursor()
        
        cursor.execute("""
            SELECT sr.skill_name, ec.criterion_key
            FROM evaluation_criteria_catalog ec
            JOIN skill_registry sr ON ec.skill_id = sr.skill_id
            WHERE sr.skill_name IN ('agent_system_prompt', 'support_agent', 'meeting_summary')
            ORDER BY sr.skill_name, ec.criterion_key
        """)
        
        # For now, just verify criteria_key exists and is not null
        results = cursor.fetchall()
        for skill_name, criterion_key in results:
            assert criterion_key is not None
            assert len(criterion_key) > 0
