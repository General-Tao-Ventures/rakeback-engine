"""Worker: ingest blocks, yields, and conversions from the chain.

Usage:
    python -m worker.ingest_blocks --validator VHK --block-range 1000:2000
    python -m worker.ingest_blocks --validator VHK --block-range 1000:2000 --skip-existing
"""

import argparse
import sys

import structlog

from db.connection import get_session
from rakeback.services.chain_client import ChainClient
from rakeback.services.ingestion import IngestionResult, IngestionService

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def parse_block_range(raw: str) -> tuple[int, int]:
    try:
        parts: list[str] = raw.split(":")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError) as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid block range '{raw}'. Expected START:END (e.g. 1000:2000)"
        ) from exc


def main(argv: list[str] | None = None) -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Ingest blocks from the chain",
    )
    parser.add_argument("--validator", "-v", required=True, help="Validator hotkey")
    parser.add_argument(
        "--block-range",
        "-b",
        required=True,
        type=parse_block_range,
        help="Block range START:END (e.g. 1000:2000)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip blocks already ingested (default: true)",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        default=False,
        help="Abort on first block error",
    )
    args: argparse.Namespace = parser.parse_args(argv)
    start_block: int
    end_block: int
    start_block, end_block = args.block_range

    logger.info(
        "Starting block ingestion",
        validator=args.validator[:16],
        start=start_block,
        end=end_block,
    )

    with get_session() as session:
        chain_client: ChainClient = ChainClient()
        service: IngestionService = IngestionService(session, chain_client)

        result: IngestionResult = service.ingest_block_range(
            start_block=start_block,
            end_block=end_block,
            validator_hotkey=args.validator,
            skip_existing=args.skip_existing,
            fail_on_error=args.fail_on_error,
        )

    logger.info(
        "Ingestion complete",
        run_id=result.run_id,
        blocks_processed=result.blocks_processed,
        blocks_created=result.blocks_created,
        blocks_skipped=result.blocks_skipped,
        gaps=len(result.gaps_detected),
        errors=len(result.errors),
    )

    if result.errors:
        for err in result.errors[:10]:
            logger.error("ingestion_error", detail=err)
        if len(result.errors) > 10:
            logger.warning("truncated_errors", remaining=len(result.errors) - 10)
        sys.exit(1)


if __name__ == "__main__":
    main()
