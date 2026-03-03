# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

Bittensor Validator Rakeback Engine — monorepo with **backend** (Python/FastAPI, port 8000) and **frontend** (React/Vite, port 5173). See `LOCAL_SETUP.md` for general docs and `.cursor/rules/RakebackEngine_MAIN.mdc` for architecture context.

### Backend structure (post-PR #4 refactor)

The backend uses a flat, service-oriented layout at `backend/`:
- `app/` — FastAPI routes and Pydantic schemas
- `db/` — SQLAlchemy models, enums, connection management
- `rakeback/services/` — business logic (attribution, ingestion, aggregation, etc.)
- `config.py` — Pydantic-based settings (reads `.env`)
- `migrations/` — SQL migration runner (`python migrations/migrate.py`)
- `tests/` — 84 pytest tests
- `scripts/` — seed data, model generation
- `Makefile` — common dev commands (run from project root)

The entry point `rakeback-api` is defined in `pyproject.toml` as `app.main:start`. It must be run **from the `backend/` directory** so that `config`, `db`, `app`, and `rakeback` are importable. Use `python -c "from app.main import start; start()"` if the console script doesn't resolve `config` properly.

### Running services

**Backend API** (Terminal 1):
```bash
cd /workspace/backend && source .venv/bin/activate && python -c "from app.main import start; start()"
```
- Health check: `curl http://localhost:8000/health`
- Database: SQLite at `backend/data/rakeback.db` (auto-created by migrations on startup)
- Migrations run automatically on app startup via `_lifespan`
- The `.env` file in `backend/` is required — copy from `/workspace/.env.example` if missing

**Frontend dev server** (Terminal 2):
```bash
cd /workspace/frontend && npx vite --host 0.0.0.0
```
- Dashboard: `http://localhost:5173`
- Vite proxies `/api` and `/health` to the backend at `:8000`

### Makefile commands (run from project root)

See `Makefile` for the full list. Key targets:
- `make test` — run pytest (84 tests)
- `make lint` — ruff check
- `make fmt` — ruff fix + black
- `make migrate` — run SQL migrations
- `make api` — start backend (may need the `python -c` workaround above)

### Gotchas

- `python3.12-venv` must be installed at the system level before creating the venv.
- The `rakeback-api` console script may fail with `ModuleNotFoundError: No module named 'config'`. Use `python -c "from app.main import start; start()"` from the `backend/` directory as a workaround.
- External services (archive node, dRPC, TaoStats) are optional — the app runs without them.
- The frontend uses `package-lock.json` (npm), not pnpm or yarn.
- Real block ingestion from the Bittensor chain takes ~30-35s per block because the chain client scans up to 128 subnets per block. Emissions only happen at tempo boundaries (every ~99-360 blocks per subnet), so most blocks will have 0 yield even with successful snapshot ingestion.
- The `RAKEBACK_API_KEY` env var controls mutation endpoint auth; when empty/unset, auth is disabled.
