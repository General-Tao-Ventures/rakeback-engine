# Rakeback Engine — Build Plan

Revenue attribution and rakeback calculation for a Bittensor validator. Block-by-block attribution is the canonical approach — balance-delta formulas do not work for this setup.

## Partners

| Partner | Type | Discovery | Rakeback |
|---------|------|-----------|----------|
| **Creative Builds (CB)** | Named | Known wallet address (EXACT_ADDRESS) | 33% |
| **Talisman** | Tag-based | Extrinsic memo "talisman" on stake/unstake | 50% (new delegators only) |

**Note:** CB = Creative Builds, not Coinbase. Named partners (CB) always win over tagged wallets (Talisman) for attribution.

## Phase Status

| Phase | Status | Deliverable |
|-------|--------|-------------|
| 0 | ✅ Done | Scaffold — both API and UI run locally, health check works |
| 1 | In progress | API Layer + Partner Management |
| 2 | Pending | Conversion Pipeline + Block Attribution |
| 3 | Pending | Rakeback Ledger + Exports |
| 4 | Pending | Talisman Attribution |
| 5 | Pending | Data Completeness + System Overview |
| 6 | Pending | Payment Execution |
| 7 | Pending | Root Prop Decomposition |
| 8 | Pending | Production Hardening |

---

## Phase 0: Scaffold (DONE)

Set up repo with engine backend (FastAPI) + UI frontend (React/Vite). Both run locally. Backend responds to `/health`. UI still shows mock data.

---

## Phase 1: API Layer + Partner Management

- Implement real FastAPI routes the UI expects
- Wire Partner Management page to real CRUD (create, edit, view partners in DB)
- Align `RakebackParticipant` model with UI (add partner type, split `matching_rules` into separate rule entities for audit log)

**Deliverable:** Partner Management page works with real data. Create, edit, view partners — persisted to DB.

---

## Phase 2: Conversion Pipeline + Block Attribution API

- Implement `get_conversion_events()` in chain client (**#1 engine blocker**)
- Build `GET /api/attributions?start=&end=` and `GET /api/conversions?from=&to=`
- Wire Block Attribution, Block Detail, and Conversion Events pages to real data
- Add TAO price storage (from TaoStats at conversion time, store with conversion event)

**Deliverable:** Block Attribution and Conversion Events pages show real chain data. TAO figures are non-zero.

---

## Phase 3: Rakeback Ledger + Exports

- Build `GET /api/rakeback?partnerId=` and `GET /api/exports`
- Wire Partner Ledger page to real data
- Add JSON export alongside existing CSV
- Implement Creative Builds rakeback end-to-end (known address, 33%)

**Deliverable:** Partner Ledger shows real rakeback obligations. Exports work. First partner can be paid.

---

## Phase 4: Talisman Attribution

- Implement RT21 auto-delegation detection (extrinsic memo parsing for "talisman")
- Build FIFO stake/unstake tracking per wallet per platform
- Implement PER_WALLET aggregation mode
- Fix `match_addresses` to pass delegation context for non-address rules

**Deliverable:** Talisman wallets are discovered and attributed. Second partner live.

---

## Phase 5: Data Completeness + System Overview

- Wire Data Completeness page to real `DataGap` records
- Wire System Overview metrics to real aggregated data (MTD/YTD from ledger entries)
- Build real sync status tracking (replace "Last sync: 2m ago" hardcode)
- Add rule change audit logging

**Deliverable:** Dashboard shows real operational health. Data quality is monitored.

---

## Phase 6: Payment Execution

- Build on-chain payment service (send TAO from distribution wallet to partner payout address)
- Wire Partner Ledger payment dialog to real transactions (replace simulated 2.5s fake)
- Record transaction hashes against ledger entries

**Deliverable:** Payments can be initiated from the dashboard and tracked on-chain.

---

## Phase 7: Root Prop Decomposition

- Research chain storage format for TAO/dTAO effective weights
- Implement per-block root prop fetching
- Build TAO/dTAO yield split calculation
- Update attribution to use decomposed proportions on RT21

**Deliverable:** Attribution accuracy is complete. All math from the spec is implemented.

---

## Phase 8: Production Hardening

- Automated daily ingestion/attribution pipeline (cron)
- Alerting (Slack/email on failures or anomalies)
- Alembic migrations for schema evolution
- Parallel block processing
- Indexer integration
- Security (API auth, env vars for secrets, remove embedded TaoStats key from UI)

**Deliverable:** System runs unattended. Monitoring and alerts in place.

---

## Key Technical Constraints

### Engine Blockers (from original analysis)

1. **Conversion events** — `ChainClient.get_conversion_events()` returns empty list (TODO). All TAO calculations return 0 until fixed.
2. **RT21 auto-delegation** — `RulesEngine._check_rt21_auto_delegation()` returns False always (stub). Talisman attribution broken.
3. **match_addresses** — Only handles EXACT_ADDRESS and ALL. DELEGATION_TYPE and SUBNET rules need delegation context.
4. **PER_WALLET aggregation** — Enum exists but not implemented. All participants get single ledger entry.
5. **Root prop decomposition** — Not implemented. Hardest math problem.

### Repo Structure

```
Rakeback Engine/
├── backend/          # Python/FastAPI + engine (models, repos, services)
├── frontend/         # React/Vite dashboard
├── docs/
└── .cursor/rules/
```
