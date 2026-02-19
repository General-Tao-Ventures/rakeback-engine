# Rakeback Engine – Windows PowerShell Runbook

## Prerequisites

- Python 3.11+, Node 18+
- `.env` in `backend/` or project root:
  - `DB_SQLITE_PATH=data/rakeback.db` (default, SQLite)
  - Or `DATABASE_URL=postgresql://...` (explicit Postgres). **If absent, always SQLite.**

---

## 0. Kill any existing backend (prevents "no such table" with multiple processes)

If you see `no such table: rakeback_participants`, kill duplicate backends first:

```powershell
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
```

---

## 1. Reset DB (delete sqlite file)

Use the path reported by `GET /health/db` → `database_url_or_path`, or:

```powershell
cd "c:\Users\-_-\Downloads\Rakeback Engine\backend"
Remove-Item "data\rakeback.db" -ErrorAction SilentlyContinue
Remove-Item "data\rakeback.db-wal" -ErrorAction SilentlyContinue
Remove-Item "data\rakeback.db-shm" -ErrorAction SilentlyContinue
```

---

## 2. Start backend

```powershell
cd "c:\Users\-_-\Downloads\Rakeback Engine\backend"
.\.venv\Scripts\Activate.ps1
rakeback-api
```

**Expected startup logs:**
```
DB: sqlite | C:/Users/.../Rakeback Engine/backend/data/rakeback.db
Schema init: created tables []   (or list of tables if fresh)
```

---

## 3. Start frontend (separate terminal)

```powershell
cd "c:\Users\-_-\Downloads\Rakeback Engine\frontend"
npm run dev
```

---

## 4. Sanity checks (curl / Invoke-RestMethod)

```powershell
# Health
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Health/DB (shows path, tables)
Invoke-RestMethod -Uri "http://localhost:8000/health/db" | ConvertTo-Json

# Partners list (should return [])
Invoke-RestMethod -Uri "http://localhost:8000/api/partners"

# Create partner
$body = @{
  name = "Test Partner"
  type = "named"
  rakebackRate = 33
  priority = 1
  payoutAddress = ""
  walletAddress = "5DywxdtESjskgPZrDXL86qV44SpPgJuqs9X6noyJJwX9PaSA"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/partners" -Method Post -Body $body -ContentType "application/json"
```

---

## 5. UI verification

1. Open http://localhost:5173
2. Go to Partner Management
3. Click "Add Partner", fill form, Create
4. Should see success toast, dialog closes, partner in list. No 500.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `GET /health/db` → 404 | Kill all backend processes (Step 0), then restart. Old processes may still be bound to port 8000. |
| `no such table: rakeback_participants` on POST | Run **Step 0** to kill duplicate backends. Then Step 1 + 2 to reset and restart. Or: `cd backend; rakeback init-db` then restart. |
| GET /api/partners returns data but POST fails | Classic sign of multiple backend processes using different DB files. Kill all Python processes and start one backend. |
