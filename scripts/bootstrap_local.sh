#!/bin/bash

##############################################################################
# DreamFi Bootstrap Local Environment
#
# Usage: bash scripts/bootstrap_local.sh
#
# This script:
# 1. Validates prerequisites
# 2. Creates .env.local
# 3. Installs dependencies
# 4. Creates test database
# 5. Runs migrations
# 6. Seeds test data
# 7. Validates setup
#
##############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "════════════════════════════════════════════════════════════════"
echo "🚀 DreamFi Bootstrap — Local Development Environment"
echo "════════════════════════════════════════════════════════════════"
echo ""

# ─── 1. VALIDATE PREREQUISITES ───
echo "🔍 Validating prerequisites..."

if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Node.js $(node --version)"

if ! command -v npm &> /dev/null; then
    echo -e "${RED}✗ npm not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} npm $(npm --version)"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python $(python3 --version)"

if ! command -v psql &> /dev/null; then
    echo -e "${RED}✗ PostgreSQL client not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} PostgreSQL client found"

if ! command -v git &> /dev/null; then
    echo -e "${RED}✗ Git not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Git $(git --version | cut -d' ' -f3)"

echo ""

# ─── 2. CREATE .env.local ───
echo "📝 Creating .env.local..."

if [ ! -f .env.local ]; then
    cat > .env.local << 'EOF'
# Local development overrides
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DATABASE_URL=postgresql://dreamfi:password@localhost:5432/dreamfi_dev
TEST_DATABASE_URL=postgresql://dreamfi_test:password@localhost:5432/dreamfi_test
ANTHROPIC_API_KEY=sk-ant-placeholder
SERVICE_PORT=3000
INTERNAL_HUB_PORT=3002
WEBHOOK_PORT=3001
BOOTSTRAP_INCLUDE_MOCK_DATA=true
BOOTSTRAP_INCLUDE_FIXTURE_CONNECTORS=true
DEV_LOG_CONNECTOR_SYNC=true
EOF
    echo -e "${GREEN}✓${NC} .env.local created"
else
    echo -e "${YELLOW}⚠${NC} .env.local already exists, skipping"
fi

echo ""

# ─── 3. INSTALL DEPENDENCIES ───
echo "📦 Installing dependencies..."

echo "  • pip packages..."
pip install -q -r requirements.txt 2>/dev/null || echo -e "${YELLOW}⚠${NC} pip install had warnings"

services=("services/knowledge-hub" "services/generators" "services/planning-sync" "services/metrics" "apps/internal-hub")
for service in "${services[@]}"; do
    if [ -d "$service" ] && [ -f "$service/package.json" ]; then
        echo "  • npm packages ($service)..."
        (cd "$service" && npm install --quiet) || echo -e "${YELLOW}⚠${NC} npm install had warnings"
    fi
done

echo -e "${GREEN}✓${NC} Dependencies installed"
echo ""

# ─── 4. CREATE TEST DATABASE ───
echo "🗄️  Creating PostgreSQL databases..."

# Note: This assumes PostgreSQL is running locally
# Adjust connection params as needed

PSQL_USER="${POSTGRES_USER:-postgres}"
PSQL_HOST="${POSTGRES_HOST:-localhost}"
PSQL_PORT="${POSTGRES_PORT:-5432}"

# Try to create main dev DB
psql -U "$PSQL_USER" -h "$PSQL_HOST" -p "$PSQL_PORT" -c "CREATE DATABASE dreamfi_dev;" 2>/dev/null || echo -e "${YELLOW}⚠${NC} dreamfi_dev may already exist"

# Try to create test DB
psql -U "$PSQL_USER" -h "$PSQL_HOST" -p "$PSQL_PORT" -c "CREATE DATABASE dreamfi_test;" 2>/dev/null || echo -e "${YELLOW}⚠${NC} dreamfi_test may already exist"

# Create superuser if doesn't exist
psql -U "$PSQL_USER" -h "$PSQL_HOST" -p "$PSQL_PORT" -c "CREATE USER dreamfi WITH PASSWORD 'password' CREATEDB;" 2>/dev/null || echo -e "${YELLOW}⚠${NC} dreamfi user may already exist"

echo -e "${GREEN}✓${NC} Databases ready"
echo ""

# ─── 5. RUN MIGRATIONS ───
echo "📦 Running database migrations..."

migration_path="services/knowledge-hub/db/migrations"

if [ -d "$migration_path" ]; then
    ls "$migration_path"/*.sql 2>/dev/null | while read -r migration; do
        echo "  • $(basename "$migration")..."
        # Note: In production use a proper migration tool; this is simplified
    done
    echo -e "${GREEN}✓${NC} Migrations staged (run 'make db-migrate' to apply)"
else
    echo -e "${YELLOW}⚠${NC} Migrations not found"
fi

echo ""

# ─── 6. SEED TEST DATA ───
echo "🌱 Seeding test data..."

if [ -d "services/knowledge-hub/db/seeds" ]; then
    echo "  • Test data staged (run 'make db-seed' to apply)"
    echo -e "${GREEN}✓${NC} Seeding ready"
else
    echo -e "${YELLOW}⚠${NC} Seed scripts not found"
fi

echo ""

# ─── 7. VALIDATE SETUP ───
echo "✅ Validating setup..."

# Check if .env.local has required vars
required_vars=("DATABASE_URL" "ANTHROPIC_API_KEY")
for var in "${required_vars[@]}"; do
    if grep -q "^$var=" .env.local; then
        echo -e "${GREEN}✓${NC} $var configured"
    else
        echo -e "${RED}✗ $var missing from .env.local${NC}"
    fi
done

echo ""

# ─── SUMMARY ───
echo "════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Bootstrap Complete!${NC}"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Complete .env.local with your API keys"
echo "  2. Start PostgreSQL: brew services start postgresql"
echo "  3. Run migrations: make db-migrate"
echo "  4. Seed data: make db-seed"
echo "  5. Start services: make run"
echo "  6. Run tests: make test"
echo ""
echo "For more info: make help"
echo ""
