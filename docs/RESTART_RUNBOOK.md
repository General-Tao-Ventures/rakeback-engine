# Rakeback Engine – RESTART-PROOF RUNBOOK (Windows PowerShell)

---

## Simple steps (after reboot)

**Terminal 1 – backend**

```powershell
cd "c:\Users\-_-\Downloads\Rakeback Engine\backend"
.\.venv\Scripts\Activate.ps1
rakeback-api
```

**Terminal 2 – frontend**

```powershell
cd "c:\Users\-_-\Downloads\Rakeback Engine\frontend"
npm run dev
```

**Check:** Open http://localhost:5173 and hit http://localhost:8000/health — you should see `{"status":"ok"}`.

---

## A) Pre-requisites (only what is actually needed)

- **Node.js** – used for frontend (Vite). Check: `node -v` → should be **18+** (e.g. `v20.x`).
- **Python** – used for backend (FastAPI). Check: `python --version` → must be **3.11+**.
- **Package managers** – this repo uses **npm** for the frontend (see `frontend/package-lock.json`). No pnpm/yarn required.

Quick check (run in PowerShell):

```powershell
node -v
python --version
```

---

## B) One-time setup (do once per machine or after clone)

### Backend

1. **Create venv and install:**

```powershell
cd "c:\Users\-_-\Downloads\Rakeback Engine\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

2. **Create `.env`** in `backend/` (copy from project root `.env.example` or create). Exact variable names used by this repo:

| Variable | Required | Description |
|----------|----------|-------------|
| `DB_SQLITE_PATH` | No (default: `data/rakeback.db`) | SQLite path relative to `backend/`. Used when `DATABASE_URL` is not set. |
| `DATABASE_URL` | No | If set, use PostgreSQL instead of SQLite. |
| `CHAIN_RPC_URL` | No (has default) | Archive node WebSocket URL, e.g. `ws://185.189.45.20:9944`. Backend uses this for chain ingestion. |
| `TAOSTATS_API_KEY` | No | TaoStats API key for backend price fetches (optional). |
| `RAKEBACK_ENVIRONMENT` | No | e.g. `development`. |
| `RAKEBACK_DEBUG` | No | e.g. `true`. |

Example `backend/.env`:

```powershell
# Create from example (if .env.example exists at project root)
Copy-Item "c:\Users\-_-\Downloads\Rakeback Engine\.env.example" "c:\Users\-_-\Downloads\Rakeback Engine\backend\.env"
# Then edit backend\.env and set TAOSTATS_API_KEY=your_key_if_you_have_one
```

Minimal content:

```env
DB_SQLITE_PATH=data/rakeback.db
CHAIN_RPC_URL=ws://185.189.45.20:9944
TAOSTATS_API_KEY=
RAKEBACK_ENVIRONMENT=development
RAKEBACK_DEBUG=true
```

**SQLite:** The SQLite file lives at `backend/data/rakeback.db` (relative to backend root). To **reset** the DB: delete `backend/data/rakeback.db` and optionally `backend/data/rakeback.db-wal` and `backend/data/rakeback.db-shm`, then restart the backend (schema is created on startup).

### Frontend

1. **Install dependencies:**

```powershell
cd "c:\Users\-_-\Downloads\Rakeback Engine\frontend"
npm install
```

2. **Frontend `.env` (optional):** The app reads from `import.meta.env`. You can create `frontend/.env` with:

| Variable | Description |
|----------|-------------|
| `VITE_TAOSTATS_API_KEY` | TaoStats API key (used if not set in API Settings UI / localStorage). |
| `VITE_RPC_NODE_URL` | RPC node URL (default: https://lb.drpc.live/bittensor/). |
| `VITE_RPC_NODE_API_KEY` | RPC node API key. |
| `VITE_BACKEND_API_URL` | Override backend URL (leave empty in dev so Vite proxies `/api` and `/health` to 8000). |

If you do not create `frontend/.env`, you can set the TaoStats key later in the UI (API Settings); it is stored in `localStorage` as `taostats_api_key`. Backend port is **8000**; frontend dev server is **5173** (Vite default; see `frontend/vite.config.ts` proxy).

---

## C) After-reboot quickstart (the main thing)

Use **two terminals**. Leave both running.

### Terminal 1 – Backend

```powershell
cd "c:\Users\-_-\Downloads\Rakeback Engine\backend"
.\.venv\Scripts\Activate.ps1
rakeback-api
```

- **Host/port:** Backend listens on **http://0.0.0.0:8000** (see `backend/src/rakeback/api/app.py`: `uvicorn.run(..., host="0.0.0.0", port=8000)`).
- **Confirm:** You should see a log line like: `DB: sqlite | C:/Users/.../Rakeback Engine/backend/data/rakeback.db` and no traceback.

### Terminal 2 – Frontend

```powershell
cd "c:\Users\-_-\Downloads\Rakeback Engine\frontend"
npm run dev
```

- **Port:** Frontend runs on **http://localhost:5173** (Vite default; see `frontend/vite.config.ts` – no custom `server.port`, so 5173).
- **Confirm:** You should see something like `Local: http://localhost:5173/`. The dev server proxies `/api` and `/health` to `http://localhost:8000`.

---

## D) Verification checklist (real endpoints and UI)

Run these **after** both backend and frontend are up. Every check is tied to real code in this repo.

### 1. Backend health (plain)

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

**Expected:** `{ "status": "ok" }` (see `backend/src/rakeback/api/app.py`).

### 2. Backend health (DB)

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health/db" | ConvertTo-Json -Depth 5
```

**Expected:** `backend_type` (e.g. `sqlite`), `database_url_or_path` (path to `rakeback.db`), `schema_initialized: true`, `tables_present` list (see `backend/src/rakeback/api/routes/health.py`).

### 3. Backend API (partners)

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/partners"
```

**Expected:** JSON array (e.g. `[]`). No 500.

### 4. Frontend loads and System status cards

- Open **http://localhost:5173** in a browser.
- Go to **System** (or dashboard that shows “Rakeback Dashboard” and API health).
- **Expected:** Page loads; summary metrics and API health status cards appear (see `frontend/src/app/pages/system-overview.tsx`). Backend card should show **Healthy** if backend is running.

### 5. TaoStats test connection (200 and UI “Healthy”)

- Go to **API Settings** (or equivalent settings page).
- Enter your **TaoStats API key** and click **Test Connection** (calls `taoStatsService.testConnection()` in `frontend/src/services/taostats-service.ts`; hits `https://api.taostats.io/api/stats/latest/v1` with `Authorization` header).
- **Expected:** Response 200 and UI shows “TaoStats API connection successful” / Healthy. If you get **401**, see Troubleshooting (TaoStats 401).

### 6. Current TAO Price (real number, no 401s)

- Go to a page that uses **Current TAO Price** (e.g. Conversion Events or any screen using `useTaoPrice()` from `frontend/src/hooks/use-tao-price.ts`). It calls TaoStats price endpoint.
- **Expected:** A numeric TAO price is shown; in browser DevTools → Network/Console there are no 401s. If key is missing or wrong, you may see fallback data or errors (see Troubleshooting).

---

## E) Common failure modes and fixes

| Failure | What to verify | Fix / reference |
|--------|----------------|------------------|
| **TaoStats 401 Unauthorized** | Frontend sends key in **Authorization** header (no “Bearer” prefix) in `frontend/src/services/taostats-service.ts`. API Settings stores key in `localStorage` as `taostats_api_key`. | Ensure API key is set in API Settings and saved (or in `VITE_TAOSTATS_API_KEY` / `frontend/.env`). 401 = invalid or missing key. |
| **Archive node ws:// connection errors** | Backend uses `CHAIN_RPC_URL` from `backend/.env` (e.g. `ws://185.189.45.20:9944`). Frontend uses `API_CONFIG.bittensor.archiveNode` or `localStorage` key `ARCHIVE_NODE_URL` in `frontend/src/config/api-config.ts` and `api-settings.tsx`. | Use `ws://` for non-TLS nodes; use `wss://` if the node has SSL. Do not mix `https://` with WebSocket clients (use `ws://` or `wss://`). |
| **Backend failing: env not loading / wrong DB path** | `.env` is loaded from **backend root** then project root in `backend/src/rakeback/config/settings.py` and `backend/src/rakeback/api/app.py` (`start()`). SQLite path is `DB_SQLITE_PATH` (default `data/rakeback.db`) relative to backend root. | Run backend from `backend/` after `cd` so cwd is backend root; or ensure `backend/.env` exists. Check startup log for `DB: sqlite | <path>` to confirm path. |
| **“no such table” (e.g. rakeback_participants)** | Multiple backend processes can point at different DB files or stale state. | Kill all Python processes: `Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force`. Then start a single backend. Optionally reset DB (delete `backend/data/rakeback.db`) and restart so schema is recreated. |
| **GET /health or /health/db returns 404** | Old process still bound to port 8000. | Kill Python processes (above), then start backend again. |

---

## Stopping everything (for cold-start test)

- **Backend:** In the backend terminal press `Ctrl+C`, or run:
  ```powershell
  Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
  ```
- **Frontend:** In the frontend terminal press `Ctrl+C`, or close the terminal. Optionally kill Node:
  ```powershell
  Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force
  ```

---

## Cold-start verification (summary)

1. **Stop** frontend and backend (see “Stopping everything” above).
2. **Start** backend in Terminal 1 (see “Terminal 1 – Backend”).
3. **Start** frontend in Terminal 2 (see “Terminal 2 – Frontend”).
4. Run **Verification checklist** items 1–4 (Invoke-RestMethod + open http://localhost:5173 and confirm System status cards).
5. If you have a TaoStats key, run checks 5–6 (TaoStats test connection and TAO price); otherwise note “skipped – no key”.

---

## Verification results (runbook validation)

The following was verified against this repo:

- **Backend cold start:** Stopped Python processes, started backend with the exact runbook commands (`cd backend`, activate venv, `rakeback-api`). Backend listened on http://0.0.0.0:8000. Startup log showed SQLite and table checks.
- **Check 1 – GET /health:** Returns `{ "status": "ok" }` (200).
- **Check 2 – GET /health/db:** Returns `backend_type: sqlite`, `database_url_or_path`, `schema_initialized: true`, `tables_present` list (200).
- **Check 3 – GET /api/partners:** Returns JSON array (200).
- **Frontend:** The command `cd frontend; npm run dev` is correct (Vite default port 5173). In an automated run, the frontend failed to start with `spawn EPERM` (esbuild) in the test environment; run the same commands locally to confirm the frontend and UI checks (4–6).

This runbook is documentation-only; no application code or features were changed.
