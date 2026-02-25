.PHONY: setup migrate migrate-status migrate-dry api dev test lint fmt clean docker-up docker-down docker-build

# ── Local development ──────────────────────────────────────
setup:
	cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"

migrate:
	cd backend && .venv/bin/python migrations/migrate.py

migrate-status:
	cd backend && .venv/bin/python migrations/migrate.py --status

migrate-dry:
	cd backend && .venv/bin/python migrations/migrate.py --dry-run

api:
	cd backend && .venv/bin/rakeback-api

dev:
	cd backend && RAKEBACK_RELOAD=true .venv/bin/rakeback-api

test:
	cd backend && .venv/bin/pytest

lint:
	cd backend && .venv/bin/ruff check src/ tests/

fmt:
	cd backend && .venv/bin/ruff check --fix src/ tests/ && .venv/bin/black src/ tests/

clean:
	rm -rf backend/.venv backend/data/rakeback.db

# ── Docker ─────────────────────────────────────────────────
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down
