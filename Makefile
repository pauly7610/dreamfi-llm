.PHONY: help bootstrap onyx-up dreamfi-up test test-live lint format migrate seed seed-local seed-demo setup-env-check setup-docsets validate-connectors run-replay backup-db ops-status run-round console

help:
	@echo "bootstrap        - one-shot: bring up Onyx + DreamFi"
	@echo "onyx-up          - launch Onyx via its installer"
	@echo "dreamfi-up       - start DreamFi API + Postgres"
	@echo "dreamfi-down     - stop DreamFi API + Postgres"
	@echo "test             - all unit + mocked integration tests"
	@echo "test-live        - tests that require a live Onyx"
	@echo "migrate          - alembic upgrade head"
	@echo "seed             - register skills + create Onyx personas"
	@echo "seed-local       - register skills + active prompt versions without Onyx"
	@echo "seed-demo        - add realistic demo topics/artifacts/feedback/outcomes"
	@echo "setup-env-check  - validate env/secrets placeholders"
	@echo "setup-docsets    - APPLY=1 creates expected Onyx source doc sets"
	@echo "validate-connectors - verify source doc-set/retrieval readiness"
	@echo "run-replay       - run due learning replay schedules"
	@echo "backup-db        - write a compressed logical DB snapshot"
	@echo "ops-status       - print operational readiness payload"
	@echo "run-round        - SKILL=... [N=10] run one eval round"
	@echo "lint / format    - ruff"

bootstrap: onyx-up dreamfi-up migrate seed

onyx-up:
	bash scripts/bootstrap_local.sh

dreamfi-up:
	docker compose -f deployment/docker-compose.dreamfi.yml up -d --build

dreamfi-down:
	docker compose -f deployment/docker-compose.dreamfi.yml down

test:
	pytest -m "not live_onyx" -q

test-live:
	pytest -m live_onyx -q

migrate:
	alembic upgrade head

seed:
	python -m scripts.onyx_seed

seed-local:
	python -m scripts.dreamfi_setup seed-local

seed-demo:
	python -m scripts.dreamfi_setup seed-demo

setup-env-check:
	python -m scripts.dreamfi_setup env-check

setup-docsets:
	python -m scripts.dreamfi_setup bootstrap-docsets $(if $(APPLY),--apply,)

validate-connectors:
	python -m scripts.dreamfi_setup validate-connectors

run-replay:
	python -m scripts.dreamfi_setup run-replay --limit=$(or $(LIMIT),10)

backup-db:
	python -m scripts.dreamfi_setup backup-db

ops-status:
	python -m scripts.dreamfi_setup ops-status

run-round:
	python -m scripts.run_eval_round --skill=$(SKILL) --n=$(or $(N),10)

console:
	uvicorn dreamfi.api.app:app --host 0.0.0.0 --port 5001

lint:
	ruff check dreamfi scripts tests

format:
	ruff format dreamfi scripts tests
