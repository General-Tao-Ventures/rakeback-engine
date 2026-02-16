# Running the Project Locally

Quick reference for standing up the Rakeback Engine on your machine.

## Prerequisites

- **Python 3.11+** (backend)
- **Node.js** (frontend)
- Run all commands from the project root unless noted.

## One-time setup (already done if you ran the stand-up)

1. **Environment**
   - `.env` exists at project root (from `.env.example`).
   - `backend/.env` exists so the API uses SQLite when run from `backend/`.

2. **Backend**
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e .
   rakeback init-db
   ```

3. **Frontend**
   ```powershell
   cd frontend
   npm install
   ```

## Running the app

Use **two terminals**.

### Terminal 1 – Backend API

```powershell
cd "c:\Users\-_-\Downloads\Rakeback Engine\backend"
.\.venv\Scripts\Activate.ps1
rakeback-api
```

- API: **http://localhost:8000**
- Health: **http://localhost:8000/health**
- Reload is off by default on Windows. To enable: `$env:RAKEBACK_RELOAD="true"; rakeback-api`

### Terminal 2 – Frontend

```powershell
cd "c:\Users\-_-\Downloads\Rakeback Engine\frontend"
npm run dev
```

- Dashboard: **http://localhost:5173**
- Vite proxies `/api` and `/health` to the backend.

## On-chain data: archive node, RPC, TaoStats

To get **real on-chain numbers** you need at least one of these working.

### 1. Archive node (WebSocket) – best for full chain state

- **URL:** `ws://185.189.45.20:9944` (no API key)
- **Frontend:** Dashboard → **API Settings** → “Bittensor archive node”. Default is already this URL. Click **Connect** to test.
- **Backend:** In `backend/.env` set:
  ```env
  CHAIN_RPC_URL=ws://185.189.45.20:9944
  ```
  Backend uses this for ingestion (`rakeback ingest-blocks`, etc.). Restart the API after changing.

**If archive node fails in the browser:** Browsers block `ws://` on HTTPS pages (mixed content). Use **http://localhost:5173** for dev so `ws://` is allowed. If the node is only reachable from your server, use the backend for all chain reads and keep the frontend on HTTP in dev.

### 2. RPC node (dRPC HTTP) – for health checks and JSON-RPC

- **URL:** `https://lb.drpc.live/bittensor/`
- **API key:** Your dRPC key (e.g. from dRPC dashboard). Sent as **Drpc-Key** header (not Bearer).
- **Frontend:** API Settings → “RPC node” → set URL and “RPC node API key” → **Test connection**. Values are stored in `localStorage` and used on System Overview for RPC health.

The app now uses the **Drpc-Key** header for dRPC; no need to put the key in the URL.

### 3. TaoStats API – price, validators, network stats

- **API key:** From [dash.taostats.io](https://dash.taostats.io) (full key format e.g. `tao-xxx-xxx:yyy`).
- **Frontend:** API Settings → “TaoStats API key” → Save. Used for TAO price and (if you add it) validators/network.
- **Backend (optional):** For live yield/TAO in backend, set `TAOSTATS_API_KEY` in `backend/.env`.

### Quick test

1. **Archive:** API Settings → Connect to archive node. You should see “Connected” and a current block number.
2. **RPC:** API Settings → RPC URL `https://lb.drpc.live/bittensor/`, API key your dRPC key → Test connection. Should show “RPC node connection successful”.
3. **TaoStats:** API Settings → TaoStats API key → Save. System Overview or any page that uses TAO price should load without “Using fallback data”.

### Summary

| Source       | Purpose              | Where to set                          |
|-------------|----------------------|----------------------------------------|
| Archive node| Blocks, state, ingest| Frontend: API Settings; Backend: `CHAIN_RPC_URL` |
| dRPC RPC    | HTTP RPC / health    | Frontend: API Settings (URL + Drpc-Key) |
| TaoStats    | Price, validators    | Frontend: API Settings; Backend: `TAOSTATS_API_KEY` |
