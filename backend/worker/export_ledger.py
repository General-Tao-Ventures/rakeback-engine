"""Worker: export rakeback ledger entries to CSV.

Usage:
    python -m worker.export_ledger --period-type DAILY --start 2026-01-01 --end 2026-01-31
    python -m worker.export_ledger --period-type MONTHLY \
        --start 2026-01-01 --end 2026-01-31 -o report.csv
"""

import argparse
from datetime import date
from pathlib import Path

import structlog

from db.connection import get_session
from db.enums import PeriodType
from rakeback.services.export import ExportResult, ExportService

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def main(argv: list[str] | None = None) -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Export ledger entries to CSV",
    )
    parser.add_argument(
        "--period-type",
        "-t",
        required=True,
        choices=[e.value for e in PeriodType],
        help="Period type (DAILY or MONTHLY)",
    )
    parser.add_argument(
        "--start",
        "-s",
        required=True,
        type=date.fromisoformat,
        help="Period start (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        "-e",
        required=True,
        type=date.fromisoformat,
        help="Period end (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output file path (auto-generated if omitted)",
    )
    parser.add_argument(
        "--include-incomplete",
        action="store_true",
        default=True,
        help="Include entries with incomplete data (default: true)",
    )
    args: argparse.Namespace = parser.parse_args(argv)

    period_type: PeriodType = PeriodType(args.period_type)

    logger.info(
        "Starting ledger export",
        period_type=period_type.value,
        start=str(args.start),
        end=str(args.end),
    )

    with get_session() as session:
        service: ExportService = ExportService(session)
        result: ExportResult = service.export_ledger_csv(
            period_type=period_type,
            period_start=args.start,
            period_end=args.end,
            output_path=args.output,
            include_incomplete=args.include_incomplete,
        )

    logger.info(
        "Export complete",
        run_id=result.run_id,
        output=str(result.output_path),
        rows=result.row_count,
        total_tao=str(result.total_tao),
    )

    if result.warnings:
        for warn in result.warnings:
            logger.warning("export_warning", detail=warn)


if __name__ == "__main__":
    main()
