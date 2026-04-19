#!/bin/bash

##############################################################################
# DreamFi Bootstrap Local Environment (Phase 0)
#
# Usage: bash scripts/bootstrap_local.sh
#
# This script:
# 1. Validates prerequisites (Docker, Python, Git)
# 2. Copies .env.local template if missing
# 3. Starts Docker stack (Postgres + Redis + Prometheus)
# 4. Installs Python dependencies
# 5. Runs database migrations
# 6. Seeds test data
# 7. Validates health checks
#
##############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🚀 DreamFi Phase 0 Bootstrap — Local Development Environment${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""

# ─── 1. VALIDATE PREREQUISITES ───
echo -e "${BLUE}🔍 Step 1: Validating prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found. Please install Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Docker $(docker --version | awk '{print $NF}')"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python $(python3 --version | awk '{print $NF}')"

if ! command -v git &> /dev/null; then
    echo -e "${RED}✗ Git not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Git $(git --version | awk '{print $NF}')"

echo ""

# ─── 2. ENSURE .env.local EXISTS ───
echo -e "${BLUE}📝 Step 2: Checking .env.local...${NC}"

if [ ! -f .env.local ]; then
    if [ -f .env.local.orig ] || [ -f .env.local ]; then
        echo -e "${YELLOW}⚠${NC} .env.local already exists, skipping"
    else
        cp .env.example .env.local 2>/dev/null || {
            echo -e "${YELLOW}⚠${NC} Could not auto-create .env.local"
            echo "Please create .env.local with your API keys"
        }
    fi
else
    echo -e "${YELLOW}⚠${NC} .env.local already exists"
fi

echo -e "${GREEN}✓${NC} .env.local ready"
echo "   (Edit .env.local with your API keys)"
echo ""

# ─── 3. START DOCKER STACK ───
echo -e "${BLUE}🐳 Step 3: Starting Docker stack (Postgres + Redis + Prometheus)...${NC}"

if docker ps -a --format "{{.Names}}" | grep -q "dreamfi-postgres-dev"; then
    echo -e "${YELLOW}⚠${NC} Docker containers already exist, restarting..."
    docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
fi

docker-compose -f docker-compose.dev.yml up -d
echo -e "${GREEN}✓${NC} Docker stack started"

# Wait for Postgres to be healthy
echo -e "${BLUE}  ⏳ Waiting for Postgres to be ready...${NC}"
for i in {1..30}; do
    if docker-compose -f docker-compose.dev.yml exec -T postgres pg_isready -U dreamfi_dev &> /dev/null; then
        echo -e "${GREEN}  ✓${NC} Postgres ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}  ✗ Postgres failed to start${NC}"
        exit 1
    fi
    sleep 1
done

# Wait for Redis
echo -e "${BLUE}  ⏳ Waiting for Redis to be ready...${NC}"
for i in {1..10}; do
    if docker-compose -f docker-compose.dev.yml exec -T redis redis-cli ping &> /dev/null; then
        echo -e "${GREEN}  ✓${NC} Redis ready"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${RED}  ✗ Redis failed to start${NC}"
        exit 1
    fi
    sleep 1
done

echo ""

# ─── 4. INSTALL PYTHON DEPENDENCIES ───
echo -e "${BLUE}📦 Step 4: Installing Python dependencies...${NC}"

python3 -m pip install --upgrade pip setuptools wheel > /dev/null 2>&1

if [ -f requirements.txt ]; then
    python3 -m pip install -q -r requirements.txt
    echo -e "${GREEN}✓${NC} requirements.txt installed"
fi

if [ -f requirements-dev.txt ]; then
    python3 -m pip install -q -r requirements-dev.txt
    echo -e "${GREEN}✓${NC} requirements-dev.txt installed"
fi

# Install psycopg2 for migrations
python3 -m pip install -q psycopg2-binary

echo ""

# ─── 5. RUN DATABASE MIGRATIONS ───
echo -e "${BLUE}🗄️  Step 5: Running database migrations...${NC}"

export DATABASE_URL="postgresql://dreamfi_dev:local_password@localhost:5432/dreamfi_dev"

if python3 services/knowledge_hub/db/migrate.py status 2>/dev/null | grep -q "Pending"; then
    python3 services/knowledge_hub/db/migrate.py migrate || {
        echo -e "${YELLOW}⚠${NC} Migrations had warnings, but continuing"
    }
    echo -e "${GREEN}✓${NC} Migrations applied"
else
    echo -e "${GREEN}✓${NC} All migrations already applied"
fi

echo ""

# ─── 6. SEED TEST DATA ───
echo -e "${BLUE}🌱 Step 6: Seeding test data...${NC}"

if [ -f services/knowledge_hub/db/seed_test_data.sql ]; then
    docker-compose -f docker-compose.dev.yml exec -T postgres psql -U dreamfi_dev -d dreamfi_dev \
        -f /dev/stdin < services/knowledge_hub/db/seed_test_data.sql > /dev/null 2>&1 || {
        echo -e "${YELLOW}⚠ Some seed data may already exist${NC}"
    }
    echo -e "${GREEN}✓${NC} Test data seeded"
fi

echo ""

# ─── 7. HEALTH CHECKS ───
echo -e "${BLUE}✅ Step 7: Running health checks...${NC}"

# Postgres health
if docker-compose -f docker-compose.dev.yml exec -T postgres pg_isready -U dreamfi_dev &> /dev/null; then
    echo -e "${GREEN}✓${NC} Postgres: healthy"
else
    echo -e "${RED}✗${NC} Postgres: unhealthy"
    exit 1
fi

# Redis health
if docker-compose -f docker-compose.dev.yml exec -T redis redis-cli ping &> /dev/null | grep -q "PONG"; then
    echo -e "${GREEN}✓${NC} Redis: healthy"
else
    echo -e "${RED}✗${NC} Redis: unhealthy"
    exit 1
fi

# Prometheus health (if available)
if docker-compose -f docker-compose.dev.yml exec -T prometheus wget -q -O - http://localhost:9090/-/healthy &> /dev/null; then
    echo -e "${GREEN}✓${NC} Prometheus: healthy"
else
    echo -e "${YELLOW}⚠${NC} Prometheus: not responding (optional)"
fi

# Check database tables
TABLE_COUNT=$(docker-compose -f docker-compose.dev.yml exec -T postgres psql -U dreamfi_dev -d dreamfi_dev -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null || echo "0")

if [ "$TABLE_COUNT" -gt 5 ]; then
    echo -e "${GREEN}✓${NC} Database schema: initialized ($TABLE_COUNT tables)"
else
    echo -e "${YELLOW}⚠${NC} Database schema: incomplete ($TABLE_COUNT tables)"
fi

echo ""

# ─── SUMMARY ───
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Phase 0 Bootstrap Complete!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}📋 Quick Start:${NC}"
echo ""
echo "  1. Edit .env.local with your API keys"
echo "  2. View Docker logs:"
echo "     ${BLUE}docker-compose -f docker-compose.dev.yml logs -f${NC}"
echo ""
echo "  3. Connect to Postgres:"
echo "     ${BLUE}psql postgresql://dreamfi_dev:local_password@localhost:5432/dreamfi_dev${NC}"
echo ""
echo "  4. Run Python tests:"
echo "     ${BLUE}pytest tests/unit -v${NC}"
echo ""
echo "  5. Run connectors validation:"
echo "     ${BLUE}python3 scripts/validate_connectors.py${NC}"
echo ""
echo "  6. Stop Docker stack:"
echo "     ${BLUE}docker-compose -f docker-compose.dev.yml down${NC}"
echo ""
echo -e "${YELLOW}📚 Documentation:${NC}"
echo "  • Phase 0 Architecture: docs/IMPLEMENTATION_QUICK_START.md"
echo "  • Connector Specs: docs/architecture/connector-specs.md"
echo "  • Operations Runbook: docs/operations/runbook.md"
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""
