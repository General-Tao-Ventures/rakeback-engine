"""Worker: fetch and store the current TAO/USD price.

Usage:
    python -m worker.fetch_prices
    python -m worker.fetch_prices --block 4500000
"""

import argparse
from decimal import Decimal

import structlog

from config import Settings, get_settings
from db.connection import get_session
from rakeback.services.tao_price_service import TaoPriceService

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


def main(argv: list[str] | None = None) -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Fetch current TAO/USD price",
    )
    parser.add_argument(
        "--block",
        type=int,
        default=None,
        help="Associate the price with a specific block number",
    )
    args: argparse.Namespace = parser.parse_args(argv)

    settings: Settings = get_settings()
    api_key: str = getattr(settings, "taostats_api_key", "")

    with get_session() as session:
        service: TaoPriceService = TaoPriceService(session, api_key=api_key)
        price: Decimal | None = service.fetch_and_store(block_number=args.block)

    if price is not None:
        logger.info("Stored TAO price", price_usd=str(price), block=args.block)
    else:
        logger.error("Failed to fetch TAO price")


if __name__ == "__main__":
    main()
