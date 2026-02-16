# Validator Rakeback Attribution Engine

Revenue attribution and rakeback calculation system for dTAO-based validator revenue model. Combines a Python backend (FastAPI + SQLAlchemy) with a React/Vite dashboard UI.

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e .
```

Initialize the database:

```bash
DB_SQLITE_PATH=data/dev.db rakeback init-db
```

Start the API server:

```bash
DB_SQLITE_PATH=data/dev.db rakeback-api
```

The API will be available at `http://localhost:8000`. Check `http://localhost:8000/health` to verify.

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
