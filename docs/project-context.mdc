# Rakeback Engine — Full Project Context

## What This Is
Revenue attribution and rakeback calculation system for a Bittensor validator (GTV). Tracks how much yield each delegator's stake generates, identifies which delegators belong to rakeback partners, and calculates TAO owed monthly.

## The Players
| Entity | Role | Rakeback Rate |
|--------|------|---------------|
| Creative Builds (CB) | Named partner, known wallet | 33% |
| Talisman | Wallet provider, dynamic discovery via memos | 50% (new delegators) |
| WSL | VaaS provider | max(10% net rev, $20k) — out of scope |
| LVNA | Investor entity | Separate obligation — out of scope |
| GTV | Operator (us) | Remainder |

Priority: Named partner (CB) always wins over tagged wallet (Talisman).

## Revenue Streams
1. TAO staked to RT21 (root key) — 9% take
2. dTAO staked to RT21 — 9% take
3. dTAO staked to SNXX subnet keys — 18% take

Post-halving, all yield arrives as alpha (dTAO). Daily "nuke" script converts to TAO.

## The Math (Block-by-Block Attribution)
1. **Snapshot**: Record every delegator's stake per hotkey per subnet per block
2. **Attribution**: Split yield proportionally with floor rounding + remainder to largest holder
3. **Root Prop**: Split RT21 yield between TAO and dTAO stakers by effective weight (HARDEST PART - no code exists)
4. **Conversion**: Link dTAO→TAO nuke events back to delegators via pro-rata allocation
5. **Rakeback**: Sum by partner with Talisman FIFO partial attribution
6. ~~Distribution~~: Removed from scope — treasury management, not rakeback

Key invariant: SUM(attributed) == total earned, exactly. Nothing lost, nothing created.

## Phase Plan (Phases 0-8)

### Phase 0: Scaffold — DONE
New repo with engine backend + UI frontend. Stubs return empty arrays. Health endpoint works.

### Phase 1: API Layer + Partner Management — MOSTLY DONE
- Real FastAPI CRUD for partners (GET/POST/PUT + rules) — DONE
- Wire Partner Management page to real data instead of mock arrays — DONE
- Align RakebackParticipant model with UI expectations — DONE
- "Add Rule" button wired to API — DONE (fixed by Claude Code)
- Remaining: no Alembic migrations, applyFromDate not persisted, db files in git
- **No chain data yet**

### Phase 2: Conversion Pipeline + Block Attribution API
- Implement `get_conversion_events()` in chain_client.py (THE #1 BLOCKER)
- Build GET /api/attributions and GET /api/conversions endpoints
- Wire Block Attribution, Block Detail, Conversion Events pages to real data
- Add TAO price storage from TaoStats
- **First phase with real on-chain data**

### Phase 3: Rakeback Ledger + Exports
- Build GET /api/rakeback and GET /api/exports
- Wire Partner Ledger page
- JSON export alongside CSV
- Creative Builds rakeback end-to-end
- **First partner can be paid**

### Phase 4: Talisman Attribution
- Extrinsic memo parsing for "talisman" remarks
- FIFO stake/unstake tracking per wallet
- PER_WALLET aggregation mode
- Fix match_addresses for delegation context
- **Second partner live**

### Phase 5: Data Completeness + System Overview
- Wire Data Completeness page to DataGap records
- System Overview with real MTD/YTD metrics
- Real sync status tracking
- Rule change audit logging

### Phase 6: Payment Execution
- On-chain payment service (send TAO from distribution wallet)
- Wire Partner Ledger payment dialog to real transactions
- Record tx hashes against ledger entries

### Phase 7: Root Prop Decomposition
- Research chain storage for TAO/dTAO effective weights
- Per-block root prop fetching
- TAO/dTAO yield split calculation
- Update attribution with decomposed proportions on RT21

### Phase 8: Production Hardening
- Automated daily pipeline (cron)
- Alerting (Slack/email)
- Alembic migrations
- Parallel block processing
- Indexer integration
- Security (API auth, env vars for secrets)

## Engine Codebase — What Works vs What's Broken

### Works
- Block snapshot ingestion (chain + CSV override)
- Proportion calculation with 18-decimal precision
- Attribution with floor rounding + remainder to largest holder
- Exact-match invariant validation
- Rules engine for EXACT_ADDRESS and ALL matching
- Ledger entries with audit trail
- CSV export with payment status tracking
- Idempotent processing
- Data gap detection
- Partner CRUD API (Phase 1)
- ParticipantService with rule management and audit log (Phase 1)

### Broken/Missing
- `chain_client.py:534` — get_conversion_events() is TODO → all TAO values = 0
- `rules_engine.py:169` — RT21_AUTO_DELEGATION returns False always
- `rules_engine.py:110-132` — match_addresses only handles EXACT_ADDRESS and ALL
- `aggregation.py` — PER_WALLET enum exists but not implemented
- Root prop decomposition — no code anywhere
- Payment execution — no code
- TAO price tracking — engine doesn't store prices

## UI State (Post Phase 1)
- **Partner Management page**: LIVE — wired to real API (list, create, edit rules, audit log)
- All other pages: still hardcoded mock data
- Live connections: Archive node WebSocket (block number), TaoStats price API, Health check, Partner CRUD API
- Backend service (`backend-service.ts`): typed client with all endpoints defined, stubs for Phase 2+ endpoints

## Key Architecture Decisions
- `matching_rules` JSON on RakebackParticipant is now a **derived cache** from the `eligibility_rules` table
- EligibilityRule is the source of truth for rules; synced to matching_rules on create/add_rule
- Vite proxy forwards `/api` and `/health` to `:8000` in dev (empty baseUrl trick avoids CORS)
- `app.py` has global exception handler returning JSON with CORS headers even on 500s
- `RAKEBACK_RELOAD` env var controls uvicorn hot-reload (disabled by default on Windows)
- `createdBy` is always "system" — no auth/user context yet
