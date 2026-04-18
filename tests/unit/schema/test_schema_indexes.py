"""
Unit tests for schema indexes.

Tests that performance-critical indexes exist.
"""

import pytest


class TestSchemaIndexes:
    """Verify all critical performance indexes are present."""

    def test_core_entities_indexes(self, db_connection):
        """core_entities must have critical indexes."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'core_entities'
            ORDER BY indexname
        """)
        indexes = {row[0] for row in cursor.fetchall()}
        
        # Verify key indexes exist
        required_indexes = {
            'idx_core_entities_type',
            'idx_core_entities_status',
            'idx_core_entities_source',
            'idx_core_entities_freshness',
        }
        
        missing = required_indexes - indexes
        assert not missing, f"Missing indexes on core_entities: {missing}"

    def test_evaluation_outputs_indexes(self, db_connection):
        """evaluation_outputs must have critical indexes."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'evaluation_outputs'
            ORDER BY indexname
        """)
        indexes = {row[0] for row in cursor.fetchall()}
        
        # Verify key indexes exist
        required_indexes = {
            'idx_eval_outputs_round',
            'idx_eval_outputs_test_input',
            'idx_eval_outputs_pass_fail',
        }
        
        missing = required_indexes - indexes
        assert not missing, f"Missing indexes on evaluation_outputs: {missing}"

    def test_full_text_search_indexes(self, db_connection):
        """core_entities should have trigram indexes for search."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'core_entities' 
            AND indexname LIKE '%trgm%'
        """)
        trgm_indexes = [row[0] for row in cursor.fetchall()]
        
        assert len(trgm_indexes) >= 1, "Missing trigram indexes for full-text search"
