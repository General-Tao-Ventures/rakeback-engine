"""Typed dicts for service-layer return values.

Keeps route-facing methods explicit about their shape instead of returning bare dicts.
"""

import sys

if sys.version_info >= (3, 12):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

from rakeback.services._helpers import JsonDict

# -- Rules Engine ----------------------------------------------------------


class ParticipantSnapshot(TypedDict):
    id: str
    name: str
    type: str
    rakeback_percentage: str
    matching_rules: JsonDict
    aggregation_mode: str


class RulesSnapshot(TypedDict):
    as_of: str
    participants: list[ParticipantSnapshot]


# -- Participant Service ---------------------------------------------------


class RuleUI(TypedDict):
    id: str
    partnerId: str
    type: str
    config: JsonDict | None
    appliesFromBlock: int
    createdAt: str
    createdBy: str


class PartnerUI(TypedDict, total=False):
    id: str
    name: str
    type: str
    rakebackRate: float
    priority: int
    status: str
    createdBy: str
    createdDate: str
    walletAddress: object
    memoTag: object
    applyFromDate: str
    payoutAddress: str
    rules: list[RuleUI]


class ChangeLogEntry(TypedDict):
    timestamp: str
    user: str
    action: str
    partner: str
    details: str
    appliesFromBlock: int


# -- Attribution -----------------------------------------------------------


class AttributionDict(TypedDict):
    id: str
    block_number: int
    validator_hotkey: str
    delegator_address: str
    delegation_type: str
    subnet_id: int | None
    attributed_dtao: str
    delegation_proportion: str
    completeness_flag: str
    tao_allocated: str
    fully_allocated: bool


class AttributionStatsDict(TypedDict, total=False):
    total_blocks: int
    blocks_with_attributions: int
    total_attributions: int
    total_dtao_attributed: str
    unique_delegators: int


class BlockDetailDict(TypedDict):
    block_number: int
    timestamp: str | None
    validator_hotkey: str
    total_dtao: str
    delegator_count: int
    completeness_flag: str
    attributions: list[AttributionDict]


# -- Aggregation -----------------------------------------------------------


class LedgerEntryDict(TypedDict):
    id: str
    period_type: str
    period_start: str
    period_end: str
    participant_id: str
    participant_type: str
    validator_hotkey: str
    gross_dtao_attributed: float
    gross_tao_converted: float
    rakeback_percentage: float
    tao_owed: float
    payment_status: str
    payment_tx_hash: str | None
    payment_timestamp: str | None
    completeness_flag: str
    block_count: int | None
    attribution_count: int | None
    created_at: str
    updated_at: str


class LedgerSummaryDict(TypedDict):
    total_entries: int
    total_tao_owed: str
    total_tao_paid: str
    total_tao_outstanding: str
    complete_entries: int
    incomplete_entries: int


class CompletenessSummary(TypedDict):
    complete_entries: int
    incomplete_entries: int
    incomplete_blocks: list[int]
    missing_conversions: bool
    has_gaps: bool


def empty_completeness_summary(
    *,
    has_gaps: bool = False,
    complete_entries: int = 0,
    incomplete_entries: int = 0,
) -> CompletenessSummary:
    return {
        "complete_entries": complete_entries,
        "incomplete_entries": incomplete_entries,
        "incomplete_blocks": [],
        "missing_conversions": False,
        "has_gaps": has_gaps,
    }


class CompletenessDetails(TypedDict, total=False):
    reason: str


# -- Ingestion / Conversions -----------------------------------------------


class ConversionDict(TypedDict):
    id: str
    block_number: int
    transaction_hash: str
    validator_hotkey: str
    dtao_amount: str
    tao_amount: str
    conversion_rate: str
    subnet_id: int | None
    fully_allocated: bool
    tao_price: None


class AllocationDict(TypedDict):
    id: str
    conversion_event_id: str
    block_attribution_id: str
    tao_allocated: str
    allocation_method: str
    completeness_flag: str


class ConversionDetailDict(TypedDict):
    conversion: ConversionDict
    allocations: list[AllocationDict]


# -- Export ----------------------------------------------------------------


class ExportRunDict(TypedDict):
    id: str
    filename: str
    format: str
    period_start: str
    period_end: str
    record_count: int
    created_at: str


class ExportListDict(TypedDict):
    exports: list[ExportRunDict]


class ExportDataDict(TypedDict, total=False):
    format: str
    content: str
    data: list[dict[str, object]]
    record_count: int


class SummaryTotals(TypedDict):
    entries: int
    gross_dtao_attributed: str
    gross_tao_converted: str
    total_tao_owed: str


class SummaryPeriod(TypedDict):
    type: str
    start: str
    end: str


class SummaryReportDict(TypedDict):
    period: SummaryPeriod
    totals: SummaryTotals
    by_payment_status: dict[str, int]
    by_completeness: dict[str, int]
    by_participant: dict[str, dict[str, str]]


# -- Health ----------------------------------------------------------------


class DbInfoDict(TypedDict, total=False):
    backend_type: str
    database_url_or_path: str | None
    tables_present: list[str]
    tables_missing: list[str]
    schema_initialized: bool
    pid: int
    error: str
