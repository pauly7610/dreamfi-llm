#!/bin/bash

##############################################################################
# Reset Test Database
#
# Drops and recreates test database for clean state.
#
##############################################################################

set -e

PSQL_USER="${POSTGRES_USER:-postgres}"
PSQL_HOST="${POSTGRES_HOST:-localhost}"
PSQL_PORT="${POSTGRES_PORT:-5432}"
TEST_DB="dreamfi_test"

echo "🔄 Resetting test database..."

# Drop existing DB
psql -U "$PSQL_USER" -h "$PSQL_HOST" -p "$PSQL_PORT" -c "DROP DATABASE IF EXISTS $TEST_DB;" || true

# Create fresh DB
psql -U "$PSQL_USER" -h "$PSQL_HOST" -p "$PSQL_PORT" -c "CREATE DATABASE $TEST_DB;"

echo "✅ Test database reset complete"
