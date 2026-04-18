"""
Unit tests for PostgreSQL schema validation.

Tests that all 11 canonical tables exist with correct structure.
"""

import pytest


class TestSchemaTables:
    """Verify all canonical tables exist in schema."""

    def test_all_11_tables_exist(self, db_connection):
        """All 11 canonical tables must exist."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = {row[0] for row in cursor.fetchall()}
        
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
        
        missing = required_tables - tables
        assert not missing, f"Missing tables: {missing}"

    def test_core_entities_table_structure(self, db_connection):
        """core_entities must have required columns."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'core_entities'
            ORDER BY column_name
        """)
        columns = {row[0]: row[1] for row in cursor.fetchall()}
        
        required_columns = {
            'entity_id',
            'entity_type',
            'name',
            'source_system',
            'source_object_id',
            'freshness_score',
            'confidence_score',
            'created_at',
            'updated_at',
        }
        
        missing = required_columns - set(columns.keys())
        assert not missing, f"Missing columns in core_entities: {missing}"

    def test_skill_registry_table_structure(self, db_connection):
        """skill_registry must have required columns."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'skill_registry'
        """)
        columns = {row[0] for row in cursor.fetchall()}
        
        required_columns = {
            'skill_id',
            'skill_name',
            'skill_family',
            'evaluation_file_path',
            'primary_output_type',
            'active_prompt_version_id',
            'status',
        }
        
        missing = required_columns - columns
        assert not missing, f"Missing columns in skill_registry: {missing}"
