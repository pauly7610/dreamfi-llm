.PHONY: help bootstrap onyx-up dreamfi-up test test-live lint format migrate seed run-round console

help:
	@echo "bootstrap        - one-shot: bring up Onyx + DreamFi"
	@echo "onyx-up          - launch Onyx via its installer"
	@echo "dreamfi-up       - start DreamFi API + Postgres"
	@echo "dreamfi-down     - stop DreamFi API + Postgres"
	@echo "test             - all unit + mocked integration tests"
	@echo "test-live        - tests that require a live Onyx"
	@echo "migrate          - alembic upgrade head"
	@echo "seed             - register skills + create Onyx personas"
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

run-round:
	python -m scripts.run_eval_round --skill=$(SKILL) --n=$(or $(N),10)

console:
	uvicorn dreamfi.api.app:app --host 0.0.0.0 --port 5001

lint:
	ruff check dreamfi scripts tests

format:
	ruff format dreamfi scripts tests
