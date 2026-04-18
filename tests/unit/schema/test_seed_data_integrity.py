"""
Unit tests for seed data integrity.

Tests that all 9 seeded skills are inserted correctly.
"""

import pytest


class TestSeedData:
    """Verify seed data is loaded correctly."""

    def test_all_9_skills_seeded(self, db_connection):
        """All 9 skills must be seeded into skill_registry."""
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM skill_registry WHERE status = 'active'")
        count = cursor.fetchone()[0]
        assert count >= 9, f"Expected at least 9 seeded skills, got {count}"

    def test_seeded_skills_have_criteria(self, db_connection):
        """Every seeded skill must have evaluation criteria."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT sr.skill_name, COUNT(ec.criterion_id)
            FROM skill_registry sr
            LEFT JOIN evaluation_criteria_catalog ec ON sr.skill_id = ec.skill_id
            WHERE sr.status = 'active'
            GROUP BY sr.skill_name
        """)
        
        results = cursor.fetchall()
        for skill_name, criterion_count in results:
            assert criterion_count > 0, f"Skill {skill_name} has no evaluation criteria"

    def test_no_duplicate_skills(self, db_connection):
        """No duplicate skill entries."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT skill_name, COUNT(*) 
            FROM skill_registry 
            GROUP BY skill_name 
            HAVING COUNT(*) > 1
        """)
        
        duplicates = cursor.fetchall()
        assert len(duplicates) == 0, f"Found duplicate skills: {duplicates}"

    def test_seeded_skills_have_correct_families(self, db_connection):
        """Skills should be in correct families."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT skill_name, skill_family 
            FROM skill_registry 
            WHERE status = 'active'
            ORDER BY skill_name
        """)
        
        skill_families = dict(cursor.fetchall())
        
        # Verify tier 1 agent skills
        assert skill_families.get('agent_system_prompt') == 'agent'
        assert skill_families.get('support_agent') == 'agent'
        assert skill_families.get('meeting_summary') == 'summarization'
