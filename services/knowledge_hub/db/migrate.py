#!/usr/bin/env python3
"""
Database migration runner for PostgreSQL.
Applies pending migrations in order, tracks applied migrations.
Supports rollback and idempotent re-runs.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import AUTOCOMMIT
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

class PostgresMigrator:
    def __init__(self, db_url: str = None):
        """Initialize migrator with database connection string."""
        self.db_url = db_url or os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        self.migrations_dir = Path(__file__).parent / 'migrations'
        self.conn = None

    def connect(self):
        """Connect to PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.conn.set_isolation_level(AUTOCOMMIT)
            print(f"✅ Connected to database: {self.db_url.split('@')[1] if '@' in self.db_url else 'unknown'}")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP DEFAULT NOW(),
                    rollback_sql TEXT
                );
            """)
        print("✅ Migrations table ready")

    def get_applied_migrations(self) -> List[str]:
        """Get list of already-applied migration versions."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT version FROM schema_migrations ORDER BY version")
            return [row[0] for row in cur.fetchall()]

    def get_pending_migrations(self) -> List[Tuple[str, str, str]]:
        """Get list of pending migrations. Returns (version, name, path)."""
        applied = self.get_applied_migrations()
        pending = []
        
        for migration_file in sorted(self.migrations_dir.glob('*.sql')):
            if migration_file.name.startswith('_'):
                continue  # Skip . files
            
            # Extract version (e.g., "001" from "001_initial.sql")
            version = migration_file.stem.split('_')[0]
            name = migration_file.stem
            
            if version not in applied:
                pending.append((version, name, str(migration_file)))
        
        return pending

    def apply_migration(self, version: str, name: str, filepath: str):
        """Apply a single migration."""
        try:
            with open(filepath, 'r') as f:
                migration_sql = f.read()
            
            # Read rollback if available
            rollback_file = filepath.replace('.sql', '.rollback.sql')
            rollback_sql = None
            if os.path.exists(rollback_file):
                with open(rollback_file, 'r') as f:
                    rollback_sql = f.read()
            
            with self.conn.cursor() as cur:
                # Execute migration
                cur.execute(migration_sql)
                
                # Track migration
                cur.execute("""
                    INSERT INTO schema_migrations (version, name, rollback_sql)
                    VALUES (%s, %s, %s)
                """, (version, name, rollback_sql))
            
            print(f"✅ Applied migration {version}: {name}")
            return True
        except Exception as e:
            print(f"❌ Failed to apply migration {version} ({name}): {e}")
            return False

    def rollback_migration(self, version: str):
        """Rollback a migration."""
        try:
            with self.conn.cursor() as cur:
                # Get rollback SQL
                cur.execute("""
                    SELECT rollback_sql FROM schema_migrations
                    WHERE version = %s
                """, (version,))
                result = cur.fetchone()
                
                if not result or not result[0]:
                    print(f"❌ No rollback SQL found for migration {version}")
                    return False
                
                rollback_sql = result[0]
                
                # Execute rollback
                cur.execute(rollback_sql)
                
                # Remove migration record
                cur.execute("DELETE FROM schema_migrations WHERE version = %s", (version,))
            
            print(f"✅ Rolled back migration {version}")
            return True
        except Exception as e:
            print(f"❌ Failed to rollback migration {version}: {e}")
            return False

    def migrate(self):
        """Apply all pending migrations."""
        self.connect()
        self.ensure_migrations_table()
        
        pending = self.get_pending_migrations()
        if not pending:
            print("✅ No pending migrations")
            self.disconnect()
            return True
        
        print(f"\n📋 Found {len(pending)} pending migration(s)")
        for version, name, filepath in pending:
            if not self.apply_migration(version, name, filepath):
                self.disconnect()
                return False
        
        print("\n✅ All migrations applied successfully")
        self.disconnect()
        return True

    def status(self):
        """Show migration status."""
        self.connect()
        self.ensure_migrations_table()
        
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        print(f"\n📊 Migration Status")
        print(f"Applied: {len(applied)}")
        for m in applied:
            print(f"  ✅ {m}")
        
        print(f"\nPending: {len(pending)}")
        for version, name, _ in pending:
            print(f"  ⏳ {version}: {name}")
        
        self.disconnect()

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='PostgreSQL migration runner')
    parser.add_argument('--db-url', default=None, help='Database URL')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    subparsers.add_parser('migrate', help='Apply pending migrations')
    rollback_parser = subparsers.add_parser('rollback', help='Rollback a migration')
    rollback_parser.add_argument('version', help='Migration version to rollback')
    subparsers.add_parser('status', help='Show migration status')
    
    args = parser.parse_args()
    
    migrator = PostgresMigrator(args.db_url)
    
    if args.command == 'migrate':
        success = migrator.migrate()
        sys.exit(0 if success else 1)
    elif args.command == 'rollback':
        migrator.connect()
        migrator.ensure_migrations_table()
        success = migrator.rollback_migration(args.version)
        migrator.disconnect()
        sys.exit(0 if success else 1)
    elif args.command == 'status':
        migrator.status()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
