"""Worker: aggregate attributions into rakeback ledger entries.

Usage:
    python -m worker.run_aggregation --validator VHK --daily --date 2026-01-15
    python -m worker.run_aggregation --validator VHK --monthly --month 2026-01
"""

import argparse
from datetime import date

import structlog

from db.connection import get_session
from rakeback.services.aggregation import AggregationService

logger = structlog.get_logger(__name__)


def parse_month(raw: str) -> tuple[int, int]:
    try:
        parts = raw.split("-")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        raise argparse.ArgumentTypeError(
            f"Invalid month '{raw}'. Expected YYYY-MM (e.g. 2026-01)"
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Aggregate attributions into ledger entries")
    parser.add_argument(
        "--validator", "-v", required=True, help="Validator hotkey"
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--daily", action="store_true", help="Daily aggregation")
    mode.add_argument("--monthly", action="store_true", help="Monthly aggregation")

    parser.add_argument(
        "--date", "-d", type=date.fromisoformat,
        help="Date for daily aggregation (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--month", "-m", type=parse_month,
        help="Month for monthly aggregation (YYYY-MM)",
    )
    parser.add_argument(
        "--fail-on-incomplete", action="store_true", default=False,
        help="Fail if data is incomplete for the period",
    )
    args = parser.parse_args(argv)

    if args.daily and not args.date:
        parser.error("--date is required for daily aggregation")
    if args.monthly and not args.month:
        parser.error("--month is required for monthly aggregation")

    with get_session() as session:
        service = AggregationService(session)

        if args.daily:
            logger.info("Starting daily aggregation", date=str(args.date))
            result = service.aggregate_daily(
                args.date, args.validator, fail_on_incomplete=args.fail_on_incomplete,
            )
        else:
            year, month = args.month
            logger.info("Starting monthly aggregation", year=year, month=month)
            result = service.aggregate_monthly(
                year, month, args.validator,
                fail_on_incomplete=args.fail_on_incomplete,
            )

    logger.info(
        "Aggregation complete",
        run_id=result.run_id,
        period=f"{result.period_start} to {result.period_end}",
        entries_created=result.entries_created,
        total_tao_owed=str(result.total_tao_owed),
    )

    if result.warnings:
        for warn in result.warnings:
            logger.warning("aggregation_warning", detail=warn)


if __name__ == "__main__":
    main()
