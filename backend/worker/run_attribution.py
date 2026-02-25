"""Worker: compute attributions for a block range.

Usage:
    python -m worker.run_attribution --validator VHK --block-range 1000:2000
    python -m worker.run_attribution --validator VHK --block-range 1000:2000 --dry-run
"""

import argparse
import sys

import structlog

from db.connection import get_session
from rakeback.services.attribution import AttributionService

logger = structlog.get_logger(__name__)


def parse_block_range(raw: str) -> tuple[int, int]:
    try:
        parts = raw.split(":")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        raise argparse.ArgumentTypeError(
            f"Invalid block range '{raw}'. Expected START:END (e.g. 1000:2000)"
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run attribution for a block range")
    parser.add_argument(
        "--validator", "-v", required=True, help="Validator hotkey"
    )
    parser.add_argument(
        "--block-range", "-b", required=True, type=parse_block_range,
        help="Block range START:END (e.g. 1000:2000)",
    )
    parser.add_argument(
        "--skip-existing", action="store_true", default=True,
        help="Skip blocks already attributed (default: true)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=False,
        help="Compute without persisting",
    )
    args = parser.parse_args(argv)
    start_block, end_block = args.block_range

    logger.info(
        "Starting attribution",
        validator=args.validator[:16],
        start=start_block,
        end=end_block,
        dry_run=args.dry_run,
    )

    with get_session() as session:
        service = AttributionService(session)

        result = service.run_attribution(
            start_block=start_block,
            end_block=end_block,
            validator_hotkey=args.validator,
            skip_existing=args.skip_existing,
            dry_run=args.dry_run,
        )

    logger.info(
        "Attribution complete",
        run_id=result.run_id,
        blocks_processed=result.blocks_processed,
        attributions_created=result.attributions_created,
        blocks_skipped=result.blocks_skipped,
        blocks_incomplete=result.blocks_incomplete,
        total_dtao=str(result.total_dtao_attributed),
    )

    if result.errors:
        for err in result.errors[:10]:
            logger.error("attribution_error", detail=err)
        sys.exit(1)


if __name__ == "__main__":
    main()
