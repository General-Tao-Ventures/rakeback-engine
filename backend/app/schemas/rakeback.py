"""Rakeback ledger schemas."""

from app.schemas.common import CamelModel


class LedgerEntryResponse(CamelModel):
    id: str
    period_type: str
    period_start: str
    period_end: str
    participant_id: str
    participant_type: str
    validator_hotkey: str
    gross_dtao_attributed: str
    gross_tao_converted: str
    rakeback_percentage: float
    tao_owed: str
    payment_status: str
    payment_tx_hash: str | None
    payment_timestamp: str | None
    completeness_flag: str
    block_count: int
    attribution_count: int
    created_at: str
    updated_at: str


class LedgerSummaryResponse(CamelModel):
    total_entries: int
    total_tao_owed: str
    total_tao_paid: str
    total_tao_outstanding: str
    complete_entries: int
    incomplete_entries: int


class AggregationResultResponse(CamelModel):
    run_id: str
    period_type: str
    period_start: str
    period_end: str
    entries_created: int
    entries_updated: int
    errors: list[str]
