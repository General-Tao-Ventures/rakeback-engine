"""Result dataclasses returned by service operations."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from db.enums import PeriodType
from rakeback.services._types import CompletenessSummary


@dataclass
class IngestionResult:
    run_id: str
    blocks_processed: int
    blocks_created: int
    blocks_skipped: int
    gaps_detected: list[tuple[int, int]]
    completeness_summary: dict[str, int]
    errors: list[str]


@dataclass
class AttributionResult:
    run_id: str
    blocks_processed: int
    attributions_created: int
    blocks_skipped: int
    blocks_incomplete: int
    total_dtao_attributed: Decimal
    completeness_summary: dict[str, int]
    errors: list[str]


@dataclass
class AggregationResult:
    run_id: str
    period_type: PeriodType
    period_start: date
    period_end: date
    entries_created: int
    total_tao_owed: Decimal
    completeness_summary: CompletenessSummary
    warnings: list[str]


@dataclass
class ExportResult:
    run_id: str
    output_path: Path
    row_count: int
    complete_entries: int
    incomplete_entries: int
    total_tao: Decimal
    warnings: list[str]
