"""
Database migrations runner.

Automatically runs migrations on schema initialization.
Idempotent: safe to run multiple times.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional


class MigrationsRunner:
    """Runs SQL migrations in order."""
    
    def __init__(self, db_path: Optional[str] = None, migrations_dir: Optional[str] = None):
        self.db_path = db_path or os.getenv('KNOWLEDGE_HUB_DB', ':memory:')
        
        # Default migrations dir
        if migrations_dir is None:
            # Assuming this file is in services/knowledge-hub/src/
            base = Path(__file__).parent.parent
            migrations_dir = base / 'db' / 'migrations'
        
        self.migrations_dir = Path(migrations_dir)
        self.connection = None
    
    def connect(self):
        """Connect to database."""
        if not self.connection:
            self.connection = sqlite3.connect(self.db_path)
    
    def disconnect(self):
        """Close connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def run_migrations(self):
        """
        Run all migrations in order.
        
        Migrations are SQL files named: NNN_description.sql
        They are executed in alphabetical order.
        """
        self.connect()
        
        try:
            # List all migration files
            migration_files = sorted(self.migrations_dir.glob('*.sql'))
            
            if not migration_files:
                print("No migrations found")
                return
            
            for migration_file in migration_files:
                self._run_migration(migration_file)
            
            if self.connection:
                self.connection.commit()
        
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            raise e
        finally:
            self.disconnect()
    
    def _run_migration(self, migration_file: Path):
        """Execute a single migration file."""
        
        print(f"Running migration: {migration_file.name}")
        
        try:
            with open(migration_file, 'r') as f:
                sql = f.read()
            
            cursor = self.connection.cursor()
            
            # Split by semicolon to handle multiple statements
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            
            for statement in statements:
                cursor.execute(statement)
            
            self.connection.commit()
            print(f"✓ {migration_file.name} completed")
        
        except Exception as e:
            print(f"✗ {migration_file.name} FAILED: {e}")
            raise


def run_migrations(db_path: Optional[str] = None, migrations_dir: Optional[str] = None):
    """Convenience function to run migrations."""
    runner = MigrationsRunner(db_path, migrations_dir)
    runner.run_migrations()


# Global singleton
_runner: Optional[MigrationsRunner] = None


def get_migrations_runner(db_path: Optional[str] = None) -> MigrationsRunner:
    """Get or create global migrations runner."""
    global _runner
    if _runner is None:
        _runner = MigrationsRunner(db_path)
    return _runner
