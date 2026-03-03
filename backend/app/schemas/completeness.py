"""Data completeness response schemas."""

from app.schemas.common import CamelModel


class CoverageMetrics(CamelModel):
    total: int
    complete: int
    partial: int
    missing: int
    percentage: float


class ConversionMetrics(CamelModel):
    total: int
    allocated: int
    unallocated: int
    percentage: float


class LedgerMetrics(CamelModel):
    total: int
    complete: int
    incomplete: int
    percentage: float


class SystemMetrics(CamelModel):
    block_coverage: CoverageMetrics
    yield_data: CoverageMetrics
    conversion_events: ConversionMetrics
    ledger_entries: LedgerMetrics


class DataIssue(CamelModel):
    id: str
    type: str
    severity: str
    description: str
    affected_blocks: str | None = None
    detected_at: str
    requires_review: bool


class ActivityEntry(CamelModel):
    timestamp: str
    event: str
    details: str | None = None
    status: str


class CompletenessResponse(CamelModel):
    system_metrics: SystemMetrics
    issues: list[DataIssue]
    recent_activity: list[ActivityEntry]
