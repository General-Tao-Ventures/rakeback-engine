-- 001_initial_schema.sql
-- Initial schema for the Validator Rakeback Attribution Engine.
-- Tables listed in dependency order.

-- ============================================================
-- 1. rakeback_participants
-- ============================================================
CREATE TABLE IF NOT EXISTS rakeback_participants (
    id              TEXT        PRIMARY KEY,
    name            TEXT        NOT NULL,
    partner_type    TEXT        DEFAULT 'NAMED'
                                CHECK (partner_type IN ('NAMED', 'TAG_BASED', 'HYBRID')),
    priority        INTEGER     NOT NULL DEFAULT 1,
    type            TEXT        NOT NULL
                                CHECK (type IN ('PARTNER', 'DELEGATOR_GROUP', 'SUBNET')),
    matching_rules  TEXT        NOT NULL DEFAULT '{"rules": []}',   -- JSON
    rakeback_percentage NUMERIC(5, 4) NOT NULL,
    effective_from  DATE        NOT NULL,
    effective_to    DATE,
    payout_address  TEXT        NOT NULL,
    aggregation_mode TEXT       NOT NULL DEFAULT 'LUMP_SUM'
                                CHECK (aggregation_mode IN ('LUMP_SUM', 'PER_WALLET')),
    created_at      TEXT        NOT NULL,  -- ISO-8601 UTC
    updated_at      TEXT        NOT NULL,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS ix_participants_type ON rakeback_participants (type);
CREATE INDEX IF NOT EXISTS ix_participants_effective ON rakeback_participants (effective_from, effective_to);

-- ============================================================
-- 2. eligibility_rules
-- ============================================================
CREATE TABLE IF NOT EXISTS eligibility_rules (
    id                  TEXT    PRIMARY KEY,
    participant_id      TEXT    NOT NULL
                                REFERENCES rakeback_participants (id) ON DELETE CASCADE,
    rule_type           TEXT    NOT NULL,
    config              TEXT    NOT NULL,  -- JSON
    applies_from_block  INTEGER,
    created_at          TEXT    NOT NULL,
    created_by          TEXT    NOT NULL DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS ix_eligibility_rules_participant ON eligibility_rules (participant_id);

-- ============================================================
-- 3. rule_change_log
-- ============================================================
CREATE TABLE IF NOT EXISTS rule_change_log (
    id                  TEXT    PRIMARY KEY,
    timestamp           TEXT    NOT NULL,
    user                TEXT    NOT NULL DEFAULT 'system',
    action              TEXT    NOT NULL,
    partner_id          TEXT    NOT NULL,
    partner_name        TEXT    NOT NULL,
    details             TEXT    NOT NULL,
    applies_from_block  INTEGER NOT NULL
);

-- ============================================================
-- 4. block_snapshots  (composite PK)
-- ============================================================
CREATE TABLE IF NOT EXISTS block_snapshots (
    block_number        INTEGER NOT NULL,
    validator_hotkey    TEXT    NOT NULL,
    block_hash          TEXT    NOT NULL,
    timestamp           TEXT    NOT NULL,
    ingestion_timestamp TEXT    NOT NULL,
    data_source         TEXT    NOT NULL DEFAULT 'CHAIN'
                                CHECK (data_source IN ('CHAIN', 'CSV_OVERRIDE', 'BACKFILL')),
    completeness_flag   TEXT    NOT NULL DEFAULT 'COMPLETE'
                                CHECK (completeness_flag IN ('COMPLETE', 'PARTIAL', 'MISSING', 'INCOMPLETE')),
    total_stake         NUMERIC(38, 0) NOT NULL DEFAULT 0,
    PRIMARY KEY (block_number, validator_hotkey)
);

CREATE INDEX IF NOT EXISTS ix_block_snapshots_timestamp ON block_snapshots (timestamp);
CREATE INDEX IF NOT EXISTS ix_block_snapshots_validator ON block_snapshots (validator_hotkey);

-- ============================================================
-- 5. delegation_entries  (composite FK to block_snapshots)
-- ============================================================
CREATE TABLE IF NOT EXISTS delegation_entries (
    id                  TEXT    PRIMARY KEY,
    block_number        INTEGER NOT NULL,
    validator_hotkey    TEXT    NOT NULL,
    delegator_address   TEXT    NOT NULL,
    delegation_type     TEXT    NOT NULL
                                CHECK (delegation_type IN ('ROOT_TAO', 'SUBNET_DTAO', 'CHILD_HOTKEY')),
    subnet_id           INTEGER,
    balance_dtao        NUMERIC(38, 0) NOT NULL DEFAULT 0,
    balance_tao         NUMERIC(38, 0),
    proportion          NUMERIC(38, 18) NOT NULL,
    FOREIGN KEY (block_number, validator_hotkey)
        REFERENCES block_snapshots (block_number, validator_hotkey) ON DELETE CASCADE,
    UNIQUE (block_number, validator_hotkey, delegator_address)
);

CREATE INDEX IF NOT EXISTS ix_delegation_entries_delegator ON delegation_entries (delegator_address);
CREATE INDEX IF NOT EXISTS ix_delegation_entries_block ON delegation_entries (block_number, validator_hotkey);

-- ============================================================
-- 6. block_yields  (composite PK)
-- ============================================================
CREATE TABLE IF NOT EXISTS block_yields (
    block_number        INTEGER NOT NULL,
    validator_hotkey    TEXT    NOT NULL,
    total_dtao_earned   NUMERIC(38, 0) NOT NULL DEFAULT 0,
    data_source         TEXT    NOT NULL DEFAULT 'CHAIN'
                                CHECK (data_source IN ('CHAIN', 'CSV_OVERRIDE', 'BACKFILL')),
    completeness_flag   TEXT    NOT NULL DEFAULT 'COMPLETE'
                                CHECK (completeness_flag IN ('COMPLETE', 'PARTIAL', 'MISSING', 'INCOMPLETE')),
    ingestion_timestamp TEXT    NOT NULL,
    PRIMARY KEY (block_number, validator_hotkey)
);

CREATE INDEX IF NOT EXISTS ix_block_yields_block ON block_yields (block_number);
CREATE INDEX IF NOT EXISTS ix_block_yields_validator ON block_yields (validator_hotkey);

-- ============================================================
-- 7. yield_sources  (composite FK to block_yields)
-- ============================================================
CREATE TABLE IF NOT EXISTS yield_sources (
    id                  TEXT    PRIMARY KEY,
    block_number        INTEGER NOT NULL,
    validator_hotkey    TEXT    NOT NULL,
    subnet_id           INTEGER NOT NULL,
    dtao_amount         NUMERIC(38, 0) NOT NULL,
    FOREIGN KEY (block_number, validator_hotkey)
        REFERENCES block_yields (block_number, validator_hotkey) ON DELETE CASCADE,
    UNIQUE (block_number, validator_hotkey, subnet_id)
);

CREATE INDEX IF NOT EXISTS ix_yield_sources_subnet ON yield_sources (subnet_id);

-- ============================================================
-- 8. block_attributions
-- ============================================================
CREATE TABLE IF NOT EXISTS block_attributions (
    id                      TEXT    PRIMARY KEY,
    block_number            INTEGER NOT NULL,
    validator_hotkey        TEXT    NOT NULL,
    delegator_address       TEXT    NOT NULL,
    delegation_type         TEXT    NOT NULL
                                    CHECK (delegation_type IN ('ROOT_TAO', 'SUBNET_DTAO', 'CHILD_HOTKEY')),
    subnet_id               INTEGER,
    attributed_dtao         NUMERIC(38, 0) NOT NULL,
    delegation_proportion   NUMERIC(38, 18) NOT NULL,
    completeness_flag       TEXT    NOT NULL DEFAULT 'COMPLETE'
                                    CHECK (completeness_flag IN ('COMPLETE', 'PARTIAL', 'MISSING', 'INCOMPLETE')),
    computation_timestamp   TEXT    NOT NULL,
    run_id                  TEXT    NOT NULL,
    tao_allocated           NUMERIC(38, 0) NOT NULL DEFAULT 0,
    fully_allocated         INTEGER NOT NULL DEFAULT 0,  -- boolean
    UNIQUE (block_number, validator_hotkey, delegator_address)
);

CREATE INDEX IF NOT EXISTS ix_block_attributions_block ON block_attributions (block_number, validator_hotkey);
CREATE INDEX IF NOT EXISTS ix_block_attributions_delegator ON block_attributions (delegator_address);
CREATE INDEX IF NOT EXISTS ix_block_attributions_run ON block_attributions (run_id);
CREATE INDEX IF NOT EXISTS ix_block_attributions_unallocated ON block_attributions (fully_allocated, validator_hotkey);

-- ============================================================
-- 9. conversion_events
-- ============================================================
CREATE TABLE IF NOT EXISTS conversion_events (
    id                  TEXT    PRIMARY KEY,
    block_number        INTEGER NOT NULL,
    transaction_hash    TEXT    NOT NULL UNIQUE,
    validator_hotkey    TEXT    NOT NULL,
    dtao_amount         NUMERIC(38, 0) NOT NULL,
    tao_amount          NUMERIC(38, 0) NOT NULL,
    conversion_rate     NUMERIC(38, 18) NOT NULL,
    subnet_id           INTEGER,
    data_source         TEXT    NOT NULL DEFAULT 'CHAIN'
                                CHECK (data_source IN ('CHAIN', 'CSV_OVERRIDE', 'BACKFILL')),
    ingestion_timestamp TEXT    NOT NULL,
    fully_allocated     INTEGER NOT NULL DEFAULT 0  -- boolean
);

CREATE INDEX IF NOT EXISTS ix_conversion_events_block ON conversion_events (block_number);
CREATE INDEX IF NOT EXISTS ix_conversion_events_validator ON conversion_events (validator_hotkey);

-- ============================================================
-- 10. tao_allocations  (FK to conversions + attributions)
-- ============================================================
CREATE TABLE IF NOT EXISTS tao_allocations (
    id                      TEXT    PRIMARY KEY,
    conversion_event_id     TEXT    NOT NULL
                                    REFERENCES conversion_events (id) ON DELETE CASCADE,
    block_attribution_id    TEXT    NOT NULL
                                    REFERENCES block_attributions (id) ON DELETE CASCADE,
    tao_allocated           NUMERIC(38, 0) NOT NULL,
    allocation_method       TEXT    NOT NULL DEFAULT 'PRORATA'
                                    CHECK (allocation_method IN ('FIFO', 'PRORATA', 'EXPLICIT')),
    completeness_flag       TEXT    NOT NULL DEFAULT 'COMPLETE'
                                    CHECK (completeness_flag IN ('COMPLETE', 'PARTIAL', 'MISSING', 'INCOMPLETE')),
    run_id                  TEXT    NOT NULL,
    created_at              TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_tao_allocations_conversion ON tao_allocations (conversion_event_id);
CREATE INDEX IF NOT EXISTS ix_tao_allocations_attribution ON tao_allocations (block_attribution_id);
CREATE INDEX IF NOT EXISTS ix_tao_allocations_run ON tao_allocations (run_id);

-- ============================================================
-- 11. rakeback_ledger_entries
-- ============================================================
CREATE TABLE IF NOT EXISTS rakeback_ledger_entries (
    id                      TEXT    PRIMARY KEY,
    period_type             TEXT    NOT NULL
                                    CHECK (period_type IN ('DAILY', 'MONTHLY')),
    period_start            DATE    NOT NULL,
    period_end              DATE    NOT NULL,
    participant_id          TEXT    NOT NULL,
    participant_type        TEXT    NOT NULL
                                    CHECK (participant_type IN ('PARTNER', 'DELEGATOR_GROUP', 'SUBNET')),
    validator_hotkey        TEXT    NOT NULL,
    gross_dtao_attributed   NUMERIC(38, 0) NOT NULL DEFAULT 0,
    gross_tao_converted     NUMERIC(38, 0) NOT NULL DEFAULT 0,
    rakeback_percentage     NUMERIC(5, 4) NOT NULL,
    tao_owed                NUMERIC(38, 0) NOT NULL,
    payment_status          TEXT    NOT NULL DEFAULT 'UNPAID'
                                    CHECK (payment_status IN ('UNPAID', 'PAID', 'DISPUTED')),
    payment_tx_hash         TEXT,
    payment_timestamp       TEXT,
    completeness_flag       TEXT    NOT NULL DEFAULT 'COMPLETE'
                                    CHECK (completeness_flag IN ('COMPLETE', 'PARTIAL', 'MISSING', 'INCOMPLETE')),
    completeness_details    TEXT,   -- JSON
    run_id                  TEXT    NOT NULL,
    created_at              TEXT    NOT NULL,
    updated_at              TEXT    NOT NULL,
    block_count             INTEGER NOT NULL DEFAULT 0,
    attribution_count       INTEGER NOT NULL DEFAULT 0,
    UNIQUE (participant_id, period_type, period_start, validator_hotkey)
);

CREATE INDEX IF NOT EXISTS ix_ledger_period ON rakeback_ledger_entries (period_type, period_start, period_end);
CREATE INDEX IF NOT EXISTS ix_ledger_participant ON rakeback_ledger_entries (participant_id);
CREATE INDEX IF NOT EXISTS ix_ledger_validator ON rakeback_ledger_entries (validator_hotkey);
CREATE INDEX IF NOT EXISTS ix_ledger_payment_status ON rakeback_ledger_entries (payment_status);
CREATE INDEX IF NOT EXISTS ix_ledger_run ON rakeback_ledger_entries (run_id);

-- ============================================================
-- 12. tao_prices
-- ============================================================
CREATE TABLE IF NOT EXISTS tao_prices (
    id              TEXT    PRIMARY KEY,
    timestamp       TEXT    NOT NULL,
    price_usd       NUMERIC(18, 6) NOT NULL,
    source          TEXT    NOT NULL DEFAULT 'taostats',
    block_number    INTEGER,
    created_at      TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_tao_prices_timestamp ON tao_prices (timestamp);
CREATE INDEX IF NOT EXISTS ix_tao_prices_block_number ON tao_prices (block_number);

-- ============================================================
-- 13. processing_runs
-- ============================================================
CREATE TABLE IF NOT EXISTS processing_runs (
    run_id                  TEXT    PRIMARY KEY,
    run_type                TEXT    NOT NULL
                                    CHECK (run_type IN ('INGESTION', 'ATTRIBUTION', 'AGGREGATION', 'EXPORT', 'RERUN')),
    started_at              TEXT    NOT NULL,
    completed_at            TEXT,
    status                  TEXT    NOT NULL DEFAULT 'RUNNING'
                                    CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED', 'PARTIAL')),
    block_range_start       INTEGER,
    block_range_end         INTEGER,
    period_start            DATE,
    period_end              DATE,
    validator_hotkey        TEXT,
    error_details           TEXT,   -- JSON
    completeness_summary    TEXT,   -- JSON
    config_snapshot         TEXT,   -- JSON
    records_processed       INTEGER NOT NULL DEFAULT 0,
    records_created         INTEGER NOT NULL DEFAULT 0,
    records_skipped         INTEGER NOT NULL DEFAULT 0,
    parent_run_id           TEXT
);

CREATE INDEX IF NOT EXISTS ix_processing_runs_type ON processing_runs (run_type);
CREATE INDEX IF NOT EXISTS ix_processing_runs_status ON processing_runs (status);
CREATE INDEX IF NOT EXISTS ix_processing_runs_started ON processing_runs (started_at);
CREATE INDEX IF NOT EXISTS ix_processing_runs_validator ON processing_runs (validator_hotkey);

-- ============================================================
-- 14. data_gaps
-- ============================================================
CREATE TABLE IF NOT EXISTS data_gaps (
    id                  TEXT    PRIMARY KEY,
    gap_type            TEXT    NOT NULL
                                CHECK (gap_type IN ('SNAPSHOT', 'YIELD', 'CONVERSION')),
    block_start         INTEGER NOT NULL,
    block_end           INTEGER NOT NULL,
    validator_hotkey    TEXT,
    reason              TEXT    NOT NULL,
    resolution_status   TEXT    NOT NULL DEFAULT 'OPEN'
                                CHECK (resolution_status IN ('OPEN', 'BACKFILLED', 'UNRECOVERABLE')),
    resolution_notes    TEXT,
    resolved_at         TEXT,
    resolved_by_run_id  TEXT,
    created_at          TEXT    NOT NULL,
    detected_by_run_id  TEXT
);

CREATE INDEX IF NOT EXISTS ix_data_gaps_type ON data_gaps (gap_type);
CREATE INDEX IF NOT EXISTS ix_data_gaps_status ON data_gaps (resolution_status);
CREATE INDEX IF NOT EXISTS ix_data_gaps_blocks ON data_gaps (block_start, block_end);
CREATE INDEX IF NOT EXISTS ix_data_gaps_validator ON data_gaps (validator_hotkey);

-- ============================================================
-- _migrations tracking table (used by migrate.py)
-- ============================================================
CREATE TABLE IF NOT EXISTS _migrations (
    filename    TEXT    PRIMARY KEY,
    applied_at  TEXT    NOT NULL
);
