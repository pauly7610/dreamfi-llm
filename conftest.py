"""
conftest.py - Pytest configuration and fixtures.

Provides shared fixtures for database connections, API clients, and test data.
"""

import pytest
import os
import psycopg2
from psycopg2 import sql
from services.knowledge_hub.db.migrations import run_migrations


@pytest.fixture(scope="session", autouse=True)
def run_db_migrations():
    """Auto-run database migrations at session start."""
    db_url = os.getenv(
        'DATABASE_URL',
        'postgresql://test:test@localhost:5432/dreamfi_test'
    )
    
    # For SQLite (local testing)
    if 'sqlite' in db_url.lower():
        try:
            run_migrations(db_url)
            print("✓ Migrations completed")
        except Exception as e:
            print(f"✗ Migrations failed: {e}")
            raise
    # For PostgreSQL, migrations may run in CI or via Alembic
    # This is placeholder for future integration


@pytest.fixture(scope="session")
def db_connection():
    """
    Database connection fixture for integration tests.
    
    Uses DATABASE_URL environment variable or defaults to test DB.
    Uses savepoints per test to prevent data pollution.
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
    """
    Database cursor fixture - uses savepoint to prevent test pollution.
    
    Each test gets its own savepoint; rolled back after test completes.
    Prevents issues where one test's data affects another.
    """
    try:
        savepoint_id = f"sp_test_{id(db_connection)}"
        cursor = db_connection.cursor()
        
        # Create savepoint before test
        cursor.execute(f"SAVEPOINT {savepoint_id}")
        db_connection.commit()
        
        yield cursor
        
        # Rollback to savepoint after test
        cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id}")
        db_connection.commit()
        cursor.close()
    
    except Exception as e:
        # If something fails, attempt rollback anyway
        try:
            db_connection.rollback()
        except:
            pass
        raise


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
