.PHONY: setup migrate migrate-status migrate-dry generate-models api dev test lint fmt clean docker-up docker-down docker-build

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
	cd backend && .venv/bin/ruff check src/ db/ scripts/ tests/

fmt:
	cd backend && .venv/bin/ruff check --fix src/ db/ scripts/ tests/ && .venv/bin/black src/ db/ scripts/ tests/

clean:
	rm -rf backend/.venv backend/data/rakeback.db

# ── Docker ─────────────────────────────────────────────────
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down
