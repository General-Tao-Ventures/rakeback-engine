# Validator Rakeback Attribution Engine

Revenue attribution and rakeback calculation system for dTAO-based validator revenue model. Combines a Python backend (FastAPI + SQLAlchemy) with a React/Vite dashboard UI.

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .\.venv\Scripts\Activate.ps1 on Windows
pip install -e .
```

Copy `backend/.env` from `.env.example` if needed. Default uses SQLite at `data/rakeback.db`.

Start the API server (schema is created on startup):

```bash
rakeback-api
```

The API will be available at `http://localhost:8000`. Check `http://localhost:8000/health` to verify.

To reset DB: delete `backend/data/rakeback.db` and restart `rakeback-api`. See [docs/RUNBOOK.md](docs/RUNBOOK.md) for full Windows PowerShell commands.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard will be available at `http://localhost:5173`. The Vite dev server proxies `/api` and `/health` requests to the backend.

### CLI

The existing CLI still works:

```bash
rakeback status
rakeback --help
```

## Environment Variables

Copy `.env.example` to `.env` and fill in values. See the example file for available options.
