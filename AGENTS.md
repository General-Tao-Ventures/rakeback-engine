# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

Bittensor Validator Rakeback Engine — monorepo with **backend** (Python/FastAPI, port 8000) and **frontend** (React/Vite, port 5173). See `LOCAL_SETUP.md` for full setup docs and `.cursor/rules/RakebackEngine_MAIN.mdc` for architecture context.

### Running services

**Backend API** (Terminal 1):
```bash
cd /workspace/backend && source .venv/bin/activate && RAKEBACK_RELOAD=false rakeback-api
```
- Health check: `curl http://localhost:8000/health`
- Database: SQLite at `backend/data/rakeback.db` (auto-created on first run via `rakeback init-db`)
- The `.env` file in `backend/` is required — copy from `/workspace/.env.example` if missing.

**Frontend dev server** (Terminal 2):
```bash
cd /workspace/frontend && npx vite --host 0.0.0.0
```
- Dashboard: `http://localhost:5173`
- Vite proxies `/api` and `/health` to the backend at `:8000`.

### Gotchas

- `python3.12-venv` must be installed at the system level (`sudo apt-get install -y python3.12-venv`) before creating the backend virtualenv.
- The backend has no `tests/` directory yet — `pytest` will exit with code 4 (no tests collected). This is expected.
- Ruff reports ~1100 pre-existing lint warnings (mostly camelCase Pydantic fields for frontend compatibility and whitespace issues). Do not attempt to fix these unless asked.
- External services (archive node, dRPC, TaoStats) are optional — the app runs fully without them but chain-dependent features return empty/mock data.
- The frontend uses `package-lock.json` (npm), not pnpm or yarn.

### Lint / Build commands

| Service  | Command |
|----------|---------|
| Backend lint | `cd backend && source .venv/bin/activate && ruff check src/` |
| Frontend build | `cd frontend && npx vite build` |
