.PHONY: help bootstrap bootstrap-ci test test-unit test-integration test-e2e test-critical build run serve-internal clean db-reset db-migrate db-seed lint format check all phase1 phase2 phase3 phase4 phase5

help:
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "DreamFi Massive Upgrade — Makefile"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Core Targets:"
	@echo "  make bootstrap          Bootstrap local dev environment (<15 min)"
	@echo "  make test               Run all tests"
	@echo "  make test-unit          Run unit tests only"
	@echo "  make test-integration   Run integration tests only"
	@echo "  make test-critical      Run critical path tests only"
	@echo "  make build              Build all services"
	@echo "  make run                Start all services locally"
	@echo ""
	@echo "Database:"
	@echo "  make db-reset           Drop and recreate test DB"
	@echo "  make db-migrate         Run all pending migrations"
	@echo "  make db-seed            Seed test data"
	@echo ""
	@echo "Quality:"
	@echo "  make lint               Run linters (Python + TypeScript)"
	@echo "  make format             Format code (black, prettier)"
	@echo "  make check              Run all checks (test + lint)"
	@echo ""
	@echo "Phase Gates (Enforce Build Order):"
	@echo "  make phase1             Run Phase 1 tests (contracts, schema, health)"
	@echo "  make phase2             Run Phase 2 tests (connectors, generation)"
	@echo "  make phase3             Run Phase 3 tests (planning, sync)"
	@echo "  make phase4             Run Phase 4 tests (metrics, narrative)"
	@echo "  make phase5             Run Phase 5 tests (UI, publish)"
	@echo ""
	@echo "Operators:"
	@echo "  make serve-internal     Start internal operator console"
	@echo "  make logs               Tail service logs"
	@echo "  make clean              Clean build artifacts and caches"
	@echo ""

bootstrap:
	@echo "🚀 Bootstrapping DreamFi local environment..."
	bash scripts/bootstrap_local.sh
	@echo "✅ Bootstrap complete!"

bootstrap-ci:
	@echo "🚀 Bootstrapping CI environment..."
	bash scripts/bootstrap_ci.sh
	@echo "✅ CI Bootstrap complete!"

test:
	pytest -v --tb=short

test-unit:
	pytest tests/unit -v --tb=short

test-integration:
	pytest tests/integration -v --tb=short

test-e2e:
	pytest tests/e2e -v --tb=short

test-critical:
	pytest -m critical -v --tb=short

db-reset:
	@echo "🔄 Resetting test database..."
	bash scripts/db/reset_test_db.sh
	@echo "✅ Database reset complete!"

db-migrate:
	@echo "📦 Running migrations..."
	psql $(TEST_DATABASE_URL) -f services/knowledge-hub/db/migrations/001_initial_schema.sql
	psql $(TEST_DATABASE_URL) -f services/knowledge-hub/db/migrations/002_add_artifact_versioning.sql
	@echo "✅ Migrations complete!"

db-seed:
	@echo "🌱 Seeding test data..."
	ts-node services/knowledge-hub/db/seeds/seed_skills.ts
	ts-node services/knowledge-hub/db/seeds/seed_eval_criteria.ts
	ts-node services/knowledge-hub/db/seeds/seed_test_inputs.ts
	@echo "✅ Seeding complete!"

build:
	@echo "🔨 Building services..."
	cd services/knowledge-hub && npm run build
	cd services/generators && npm run build
	cd services/planning-sync && npm run build
	cd services/metrics && npm run build
	cd apps/internal-hub && npm run build
	@echo "✅ Build complete!"

run:
	@echo "▶️  Starting all services..."
	docker-compose up -d
	@echo "✅ Services started!"

run-local:
	@echo "▶️  Starting services locally (no Docker)..."
	concurrently \
		"cd services/knowledge-hub && npm run dev" \
		"cd services/generators && npm run dev" \
		"cd services/planning-sync && npm run dev" \
		"cd services/metrics && npm run dev" \
		"cd apps/internal-hub && npm run dev"

serve-internal:
	@echo "🎛️  Starting operator console..."
	cd apps/internal-hub && npm run dev

lint:
	@echo "🔍 Linting Python..."
	pylint tests/ | head -20
	@echo ""
	@echo "🔍 Linting TypeScript..."
	cd services/knowledge-hub && npx eslint src --max-warnings=0

format:
	@echo "🎨 Formatting Python..."
	black tests/ --line-length=100
	@echo ""
	@echo "🎨 Formatting TypeScript..."
	cd services/knowledge-hub && npx prettier --write src

check: lint test
	@echo "✅ All checks passed!"

logs:
	docker-compose logs -f

clean:
	@echo "🧹 Cleaning build artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name build -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned!"

phase1:
	@echo "🔴 Running Phase 1 Tests (Core Platform Hardening)..."
	pytest -m critical tests/unit/contracts tests/unit/schema tests/unit/config tests/api/test_health -v

phase2:
	@echo "🟠 Running Phase 2 Tests (Connector Maturity + Generation)..."
	pytest -m critical tests/unit/connectors tests/integration/connectors tests/unit/generators tests/integration/evals -v

phase3:
	@echo "🟡 Running Phase 3 Tests (Planning + Sync)..."
	pytest -m critical tests/unit/planning tests/integration/planning tests/e2e/test_phase3 -v

phase4:
	@echo "🟢 Running Phase 4 Tests (Metrics + Narrative)..."
	pytest -m critical tests/unit/metrics tests/integration/metrics tests/e2e/test_phase4 -v

phase5:
	@echo "🟠 Running Phase 5 Tests (UI + Publish)..."
	pytest -m critical tests/unit/ui tests/integration/ui tests/unit/publish tests/e2e/test_phase5 -v

all: clean bootstrap check build

.DEFAULT_GOAL := help
