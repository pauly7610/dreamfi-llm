"""
conftest.py - Pytest configuration and fixtures.

Provides shared fixtures for database connections, API clients, and test data.
"""

import pytest
import os
import psycopg2
from psycopg2 import sql


@pytest.fixture(scope="session")
def db_connection():
    """
    Database connection fixture for integration tests.
    
    Uses DATABASE_URL environment variable or defaults to test DB.
    """
    db_url = os.getenv(
        'DATABASE_URL',
        'postgresql://test:test@localhost:5432/dreamfi_test'
    )
    
    # Parse connection string
    # Format: postgresql://user:password@host:port/dbname
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        yield conn
        conn.close()
    except psycopg2.OperationalError as e:
        pytest.skip(f"Cannot connect to database: {e}")


@pytest.fixture
def db_cursor(db_connection):
    """Database cursor fixture (auto-rollback after test)."""
    cursor = db_connection.cursor()
    yield cursor
    cursor.close()
    db_connection.rollback()


@pytest.fixture
def sample_eval_runner():
    """Sample eval runner for testing."""
    class SampleEval:
        def score_output(self, output, label):
            return {
                'pass_fail': 'pass' if len(output) > 0 else 'fail',
                'failed_criteria': [],
                'word_count': len(output.split()),
            }
        
        def score_round(self, outputs, labels):
            passed = sum(1 for o in outputs if len(o) > 0)
            return {
                'score_percent': (passed / len(outputs) * 100) if outputs else 0,
                'passes': passed,
                'failures': len(outputs) - passed,
            }
    
    return SampleEval()


def pytest_configure(config):
    """Pytest plugin hook for configuration."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "critical: Critical path tests (must pass before merge)"
    )
