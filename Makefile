.PHONY: setup migrate migrate-status migrate-dry generate-models api dev test lint typecheck fmt clean docker-up docker-down docker-build

DIRS = app/ db/ rakeback/ worker/ scripts/ tests/

# ── Local development ──────────────────────────────────────
setup:
	cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"

migrate:
	cd backend && .venv/bin/python migrations/migrate.py

migrate-status:
	cd backend && .venv/bin/python migrations/migrate.py --status

migrate-dry:
	cd backend && .venv/bin/python migrations/migrate.py --dry-run

generate-models:
	cd backend && .venv/bin/python scripts/generate_models.py
	cd backend && .venv/bin/ruff check --fix db/models.py || true
	cd backend && .venv/bin/black db/models.py

api:
	cd backend && .venv/bin/rakeback-api

dev:
	cd backend && RAKEBACK_RELOAD=true .venv/bin/rakeback-api

test:
	cd backend && .venv/bin/pytest

lint:
	cd backend && .venv/bin/ruff check $(DIRS) config.py

typecheck:
	cd backend && .venv/bin/mypy $(DIRS) config.py --ignore-missing-imports

fmt:
	cd backend && .venv/bin/ruff check --fix $(DIRS) config.py && .venv/bin/black $(DIRS) config.py

clean:
	rm -rf backend/.venv backend/data/rakeback.db

# ── Workers (run from backend/) ───────────────────────────
ingest:
	cd backend && .venv/bin/python -m worker.ingest_blocks $(ARGS)

attribute:
	cd backend && .venv/bin/python -m worker.run_attribution $(ARGS)

aggregate:
	cd backend && .venv/bin/python -m worker.run_aggregation $(ARGS)

export:
	cd backend && .venv/bin/python -m worker.export_ledger $(ARGS)

fetch-prices:
	cd backend && .venv/bin/python -m worker.fetch_prices $(ARGS)

# ── Docker ─────────────────────────────────────────────────
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down
