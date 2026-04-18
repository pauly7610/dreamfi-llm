"""
Unit tests for schema constraints validation.

Tests that primary keys, unique constraints, and foreign keys are enforced.
"""

import pytest
import psycopg2


class TestSchemaConstraints:
    """Verify schema constraints are properly defined."""

    def test_primary_keys_exist(self, db_connection):
        """All tables must have primary keys."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT table_name
            FROM information_schema.table_constraints
            WHERE constraint_type = 'PRIMARY KEY'
            AND table_schema = 'public'
            ORDER BY table_name
        """)
        
        pk_tables = {row[0] for row in cursor.fetchall()}
        required_tables = {
            'core_entities',
            'relationships',
            'citations',
            'skill_registry',
            'prompt_versions',
            'evaluation_criteria_catalog',
            'test_input_registry',
            'evaluation_rounds',
            'evaluation_outputs',
            'gold_example_registry',
            'skill_failure_patterns',
        }
        
        missing = required_tables - pk_tables
        assert not missing, f"Tables without primary keys: {missing}"

    def test_skill_name_unique_constraint(self, db_connection):
        """skill_registry.skill_name must be unique."""
        cursor = db_connection.cursor()
        
        try:
            # Try inserting duplicate skill_name
            cursor.execute("INSERT INTO skill_registry (skill_name, skill_family, status) VALUES (%s, %s, %s)",
                          ('test_skill_unique', 'test', 'active'))
            db_connection.commit()
            
            try:
                cursor.execute("INSERT INTO skill_registry (skill_name, skill_family, status) VALUES (%s, %s, %s)",
                              ('test_skill_unique', 'test', 'active'))
                db_connection.commit()
                assert False, "Should have raised unique constraint violation"
            except psycopg2.IntegrityError:
                db_connection.rollback()
        finally:
            # Cleanup: remove test data
            cursor.execute("DELETE FROM skill_registry WHERE skill_name = %s", ('test_skill_unique',))
            db_connection.commit()

    def test_foreign_key_enforcement(self, db_connection):
        """Foreign keys must enforce referential integrity."""
        cursor = db_connection.cursor()
        
        # Try inserting evaluation_criteria_catalog with non-existent skill_id
        fake_skill_id = '00000000-0000-0000-0000-000000000000'
        
        try:
            cursor.execute("""
                INSERT INTO evaluation_criteria_catalog 
                (skill_id, criterion_key, criterion_text, is_hard_gate) 
                VALUES (%s, %s, %s, %s)
            """, (fake_skill_id, 'test_criterion', 'Test', True))
            db_connection.commit()
            assert False, "Should have raised foreign key violation"
        except psycopg2.IntegrityError:
            db_connection.rollback()

    def test_deletion_cascade(self, db_connection):
        """Foreign keys should cascade on delete."""
        cursor = db_connection.cursor()
        
        # Insert a skill
        skill_id = '11111111-1111-1111-1111-111111111111'
        cursor.execute("""
            INSERT INTO skill_registry (skill_id, skill_name, skill_family, status) 
            VALUES (%s, %s, %s, %s)
        """, (skill_id, 'test_cascade_skill', 'test', 'active'))
        
        # Insert evaluation criteria for that skill
        cursor.execute("""
            INSERT INTO evaluation_criteria_catalog 
            (skill_id, criterion_key, criterion_text, is_hard_gate) 
            VALUES (%s, %s, %s, %s)
        """, (skill_id, 'test_criterion', 'Test', True))
        
        db_connection.commit()
        
        # Delete the skill
        cursor.execute("DELETE FROM skill_registry WHERE skill_id = %s", (skill_id,))
        db_connection.commit()
        
        # Criteria should be gone too
        cursor.execute("SELECT COUNT(*) FROM evaluation_criteria_catalog WHERE skill_id = %s", (skill_id,))
        count = cursor.fetchone()[0]
        assert count == 0, "Criteria should be deleted when skill is deleted"

    def test_check_constraints_on_ranges(self, db_connection):
        """Numeric fields should have CHECK constraints."""
        cursor = db_connection.cursor()
        
        # Try inserting invalid freshness_score (should be 0-1)
        try:
            cursor.execute("""
                INSERT INTO core_entities 
                (entity_type, name, freshness_score, status) 
                VALUES (%s, %s, %s, %s)
            """, ('test', 'test', 1.5, 'active'))
            db_connection.commit()
            assert False, "Should reject freshness_score > 1"
        except psycopg2.IntegrityError:
            db_connection.rollback()
