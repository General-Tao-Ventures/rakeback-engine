# Rakeback Engine — Demo Script

> Walkthrough script for demonstrating the Bittensor Validator Rakeback Engine dashboard.
> Estimated time: 8–12 minutes.

## Prerequisites

Start both services before the demo:

```bash
# Terminal 1 — Backend API
cd backend && source .venv/bin/activate && RAKEBACK_RELOAD=false rakeback-api

# Terminal 2 — Frontend
cd frontend && npx vite --host 0.0.0.0
```

Open **http://localhost:5173** in Chrome.

> **Note on data:** Block Attribution and Conversion Events pages require seeded data in the database. If you're starting fresh after `rakeback init-db`, the attribution/conversion tables will be empty. The System Overview, Partner Ledger, and Data Completeness pages show hardcoded mock data and always display content. Partner Management pulls from the real database — create a partner first if the registry is empty.

---

## Page 1: System Overview

**Navigate to:** System Overview tab (default landing page)

### What to show

**Top-level metrics** (above the fold):
- **Total Rakeback (MTD):** 1,847.32 TAO (+12.4% vs last month)
- **Total Rakeback (YTD):** 18,392.58 TAO (+24.8% vs last year)
- **Active Partners:** 2 (Creative Builds + Talisman)
- **Tracked Wallets:** 1,247 (+89 this month)

**API health indicators** — five status badges in a row:
- Archive Node, RPC Node, TaoStats API, Backend API, Indexer API
- Highlight that Backend API shows **Healthy** (green) — this is a live health check against the running API server

**Financial summaries** — two side-by-side cards:
- February 2026 (MTD): Total Yield 12,315.47, Rakeback 1,847.32, Net Yield 10,468.15 TAO
- 2026 (YTD): Total Yield 122,617.28, Rakeback 18,392.58, Net Yield 104,224.62 TAO

### Scroll down to reveal

**Partner Performance table:**

| Partner | Type | Rakeback MTD | Rakeback YTD | Wallets | Avg Yield/Wallet |
|---------|------|-------------|-------------|---------|-----------------|
| Creative Builds | Named | 1,124.85 TAO | 11,523.44 TAO | 1 | 1,124.85 TAO |
| Talisman | Tag-based | 722.47 TAO | 6,869.14 TAO | 1,246 | 0.58 TAO |

> **Talking point:** "Creative Builds is a named partner — one known wallet, high yield per wallet. Talisman is tag-based — dynamically discovered wallets via extrinsic memos, many wallets but lower individual yield."

**Recent Activity log** — daily settlement entries for both partners with block ranges

**System Health table** — pipeline component status:
- Block Ingestion → Active, processing block 4,527,342
- Attribution Engine → Active, processing block 4,527,341
- Conversion Tracker → Active, last conversion block 4,527,289
- Partner Ledger → Active, daily settlement complete

> **Talking point:** "This gives us a single-pane-of-glass view of the entire rakeback pipeline. Every component is monitored and shows its last activity."

---

## Page 2: Block Attribution

**Navigate to:** Block Attribution tab

### What to show first

**Header cards:**
- Current Block number (live from archive node if connected, otherwise fallback ~4,527,342)
- Today's Block Range (Predicted)
- Yesterday's Block Range (24h)

**Filters section:**
- Block Range dropdown (Latest 100, Latest 1000, Latest 10000, Custom)
- Subnet filter (All Subnets, ROOT, SN8, SN21, etc.)
- Hotkey filter (text input)

**Ingest Block Data section** (below filters):
- Start Block, End Block, Validator Hotkey inputs
- Warning banner about ~5–30s per block RPC latency
- "Ingest Blocks" button

> **Talking point:** "This page is where real on-chain data meets our attribution engine. You can either query existing attribution data, or trigger new ingestion directly from the UI."

### Load the seeded data

1. Change **Block Range** dropdown to **Custom**
2. Enter **Start Block:** `4527000`
3. Enter **End Block:** `4527024`
4. Click **Search**

### What appears

A table with **25 rows** — one per block:

| Column | Example value |
|--------|--------------|
| Block Number | 4,527,024 … 4,527,000 (descending) |
| Timestamp | — |
| Subnet | SN21 |
| Hotkey | 5FTyhanHHs… |
| Total dTAO | varies per block (e.g., 81000000000000000.0000) |
| Delegators | 7 (every block) |
| Status | Complete (green badge) |

> **Talking point:** "Each row is a block where our validator earned emissions. 7 delegators are staked across this validator's hotkeys. The dTAO amounts vary block-to-block because emission tempo and staker balances fluctuate."

### Subnet filter demo (optional)

- Change Subnet to **SN8** or **ROOT** — the table re-fetches and filters
- Change back to **All Subnets**

---

## Page 3: Block Detail

**Navigate to:** Click any block row (e.g., block **4,527,012**)

### What appears

**Block header:**
- Block number with **Complete** status badge
- Timestamp (e.g., 2/26/2026, 3:58:57 PM)
- Total Attributed dTAO
- TAO Allocated (0.0000 — not yet linked to conversions in this view)

**Block Metadata:**
- Full validator hotkey
- Total Delegators: 7
- Attribution Status: Complete

**Delegator Attribution Breakdown** table — the core of the engine:

| Delegator Wallet | Delegation Type | Subnet | Proportion | Attributed dTAO | TAO Allocated | Status |
|-----------------|----------------|--------|-----------|----------------|--------------|--------|
| 5GrwvaEF… | dTAO | SN21 | ~31% | largest share | 0.0000 | Unallocated |
| 5FHneW46… | dTAO | SN21 | ~22% | | 0.0000 | Unallocated |
| 5HGjWAeF… | TAO | — | ~19% | | 0.0000 | Unallocated |
| 5CiPPseX… | dTAO | SN8 | ~10% | | 0.0000 | Unallocated |
| 5DAAnrj7… | TAO | — | ~8% | | 0.0000 | Unallocated |
| 5HpG9w8E… | dTAO | SN21 | ~5% | | 0.0000 | Unallocated |
| 5Ew3MyB1… | dTAO | SN8 | ~3% | | 0.0000 | Unallocated |

> **Talking points:**
> - "This is the forensic view — every delegator's exact share of the block's yield."
> - "Proportions are calculated from on-chain stake balances at this block height."
> - "Notice we have both TAO stakers (root delegators, no subnet) and dTAO stakers (subnet-specific). The engine handles both."
> - "The sum of all attributed dTAO exactly equals the block's total yield — nothing lost, nothing created. That's the core invariant."

Click **← Back to Block Attribution** to return.

---

## Page 4: Conversion Events

**Navigate to:** Conversion Events tab

### What appears

**Summary cards:**
- Current TAO Price (from TaoStats or fallback)
- Total Conversions: **3**
- Total dTAO Sold
- Total TAO Received
- Avg Conversion Rate (e.g., ~0.93τ per dTAO)

**Conversion Event Timeline** — 3 events:

| Event ID | Block | Subnet | dTAO Sold | TAO Received | Rate | TAO Price | Status |
|----------|-------|--------|-----------|-------------|------|-----------|--------|
| a2843071… | 4,527,005 | SN21 | 1.325×10¹⁸ | 1.244×10¹⁸ | 0.9389 | $412.35 | Allocated |
| ff292d2a… | 4,527,012 | SN21 | 1.631×10¹⁸ | 1.569×10¹⁸ | 0.9622 | $415.80 | Allocated |
| 96a488bd… | 4,527,020 | SN21 | 1.187×10¹⁸ | 1.056×10¹⁸ | 0.8896 | $418.22 | Allocated |

> **Talking point:** "These are the daily 'nuke' events — dTAO subnet alpha converted to TAO. Each event records the exact swap rate and the TAO price at conversion time."

### Show allocation detail

Click the **arrow (→)** on any conversion event row to open the **Allocation Details** dialog:

- Shows Total dTAO Sold, Total TAO Received, number of Allocations
- **Allocation table** — how the converted TAO was distributed back to delegators:
  - Each row: Allocation ID, TAO Allocated, Method (prorata), Status (Complete)
- **Sum Check** at the bottom: ✓ Σ TAO Allocated = [exact total] — proves no rounding loss

> **Talking point:** "The allocation links conversions back to block attributions. Every TAO received from a conversion is traced to specific delegators using pro-rata allocation. The sum check at the bottom proves the math is exact."

Close the dialog.

---

## Page 5: Partner Ledger

**Navigate to:** Partner Ledger tab

### What appears

**Summary cards:**
- Total Entries: 6
- Pending Payments: 1,653.82 τ
- Total Paid: 4,769.82 τ
- Active Partners: 2

**Ledger Entries table** — monthly rakeback obligations:

| Entry ID | Partner | Period | Gross TAO | Rate | TAO Owed | Status | Payment Tx |
|----------|---------|--------|-----------|------|----------|--------|-----------|
| PL-CB-2026-02 | Creative Builds | Feb 2026 | 8,432.58 | 15% | 1,264.89 | Pending | [Send] |
| PL-TL-2026-02 | Talisman | Feb 2026 | 3,241.90 | 12% | 388.93 | Pending | [Send] |
| PL-CB-2026-01 | Creative Builds | Jan 2026 | 12,567.35 | 15% | 1,885.10 | Paid | 0x8F3d… |
| PL-TL-2026-01 | Talisman | Jan 2026 | 4,893.20 | 12% | 587.18 | Paid | 0x7e2c… |
| PL-CB-2025-12 | Creative Builds | Dec 2025 | 11,234.89 | 15% | 1,685.23 | Paid | 0x6d1f… |
| PL-TL-2025-12 | Talisman | Dec 2025 | 5,102.48 | 12% | 612.30 | Paid | 0x5c0e… |

> **Talking points:**
> - "This is the finance view — what we owe each partner and what we've already paid."
> - "February is pending — the Send button will trigger an on-chain TAO transfer (Phase 6)."
> - "Paid entries have on-chain transaction hashes for audit."
> - "Note: this page currently uses mock data — Phase 3 will wire it to real ledger calculations."

### Optional: Click a row to expand

Clicking the arrow (→) on any entry opens a **Breakdown Dialog** showing:
- Period details, block range
- Per-delegator breakdown with individual TAO amounts
- Subtotal that matches the TAO Owed figure

---

## Page 6: Partner Management

**Navigate to:** Partner Management tab

### What appears

**Partner Registry** table showing configured partners (e.g., Creative Builds if already created):

| Partner Name | Type | Wallet / Tag | Rakeback Rate | Priority | Apply From | Status |
|-------------|------|-------------|--------------|----------|-----------|--------|
| Creative Builds | Named | 5GrwvaEF5z… | 33% | 1 | 2026-02-25 | Active |

**Conflict Resolution Rules** — explains priority-based resolution:
- "When a wallet matches multiple partners, the partner with the lowest priority number wins."
- Shows priority ladder (e.g., Priority 1: Creative Builds (33%))

**Audit & Safety Guarantees** — four green checkmarks:
- ✓ Forward-Only Application — rule changes only affect future blocks
- ✓ Block-Height Tracking — every rule specifies exact block height
- ✓ Complete Audit Trail — all changes logged
- ✓ Chain-Reproducible — verifiable from on-chain data

### Scroll down to the Rule Change Log

Immutable audit history of all configuration changes:
- "Created partner — Creative Builds, named partner at 33.0% rakeback, by system, applies from block 4,527,352"

> **Talking point:** "Every rule change is immutable and block-stamped. You can always reproduce exactly which rules were active at any block height. This is critical for audit."

### Optional: Create a second partner live

1. Click **+ Add Partner**
2. Fill in:
   - Name: **Talisman**
   - Type: **Tag-based (dynamic discovery)**
   - Rakeback Rate: **50**
   - Tag/Memo: **talisman**
   - Priority: **2**
3. Click **Create Partner Rule**
4. Show it appears in the registry and the Rule Change Log updates

> **Talking point:** "Named partners always win over tag-based in attribution conflicts — that's why Creative Builds is Priority 1."

---

## Page 7: Data Completeness

**Navigate to:** Data Completeness tab

### What appears

**Coverage metrics** — four cards:
- Block Coverage: **99.894%** (98,894 / 100,000)
- Yield Data: **99.895%**
- Conversions: **98.718%**
- Ledger Entries: **100.0%** (48 / 48)

**Active Issues** — 3 issues requiring review:

| Issue ID | Type | Severity | Description | Affected | Status |
|----------|------|---------|-------------|----------|--------|
| ISS-2026-02-14-003 | missing-block | Critical 🔴 | Block snapshot missing for block 4521887 | ROOT | Requires Review |
| ISS-2026-02-14-002 | missing-yield | Warning 🟡 | Partial yield data for blocks 4521890–4521892 | SN8 | Requires Review |
| ISS-2026-02-13-001 | missing-conversion | Warning 🟡 | Conversion event not fully allocated | ROOT | Requires Review |

**Recent Activity** timeline — system events with timestamps

> **Talking points:**
> - "This page is about operational confidence. We monitor every data gap and surface them proactively."
> - "The critical missing-block issue means we didn't get a snapshot for block 4,521,887 — likely an archive node timeout. We can backfill that."
> - "99.9% coverage sounds great, but the 0.1% matters when money is on the line. That's why we track every gap."
> - "Note: this page currently uses mock data — Phase 5 will wire it to real DataGap records."

---

## Page 8: API Settings

**Navigate to:** API Settings tab

### What appears

**Bittensor Archive Node** section:
- URL: `ws://185.189.45.20:9944`
- Status: Connected / Healthy (green badge) — shows current block number
- Connect/Disconnect button
- Notes about `ws://` vs `wss://` for mixed content

**RPC Node** section:
- URL: `https://lb.drpc.live/bittensor/`
- API Key field (optional, uses Drpc-Key header)
- Test Connection button

**TaoStats API** section (scroll down):
- API key input
- Used for TAO price data and validator info

**Backend API** section:
- Health check status

**Indexer API** section:
- URL + status

> **Talking points:**
> - "All external connections are configurable from the UI — no env file editing needed."
> - "The archive node is the primary data source for block ingestion. When connected, you can see the live block number updating."
> - "API keys are stored in localStorage for the frontend; backend uses env vars."

---

## Wrap-up

> "To summarize: the Rakeback Engine does block-by-block yield attribution for our Bittensor validator. It tracks every delegator's proportional share, links dTAO-to-TAO conversions back to individual delegators, and calculates exactly how much we owe each partner.
>
> **What's live today:** Partner CRUD, block attribution, conversion tracking, and the dashboard.
> **Coming next:** Phase 3 wires the Partner Ledger to real calculations, Phase 4 adds Talisman's dynamic wallet discovery, and Phase 7 tackles root prop decomposition — the hardest math problem."

---

## Quick Reference: What's Real vs Mock

| Page | Data Source | Status |
|------|-----------|--------|
| System Overview | Hardcoded mock | Phase 5 will wire to real metrics |
| Block Attribution | **Real API** (needs seeded/ingested data) | ✅ Phase 2 complete |
| Block Detail | **Real API** | ✅ Phase 2 complete |
| Conversion Events | **Real API** (needs seeded/ingested data) | ✅ Phase 2 complete |
| Partner Ledger | Hardcoded mock | Phase 3 will wire to real ledger |
| Partner Management | **Real API** | ✅ Phase 1 complete |
| Data Completeness | Hardcoded mock | Phase 5 will wire to DataGap records |
| API Settings | **Live health checks** | ✅ Working |
