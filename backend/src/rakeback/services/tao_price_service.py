"""Service for fetching and storing TAO price data."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy.orm import Session

from rakeback.repositories.tao_price import TaoPriceRepository

logger = structlog.get_logger(__name__)

# TaoStats price endpoint
TAOSTATS_PRICE_URL = "https://api.taostats.io/api/price/latest/v1"


class TaoPriceService:
    """Fetches TAO/USD prices from TaoStats and stores them locally."""

    def __init__(self, session: Session, api_key: str = ""):
        self.session = session
        self.repo = TaoPriceRepository(session)
        self.api_key = api_key

    def fetch_and_store(self, block_number: Optional[int] = None) -> Optional[Decimal]:
        """
        Call TaoStats API to get the current TAO price and store it.

        Returns the price_usd on success, None on failure.
        """
        try:
            import urllib.request
            import json

            req = urllib.request.Request(TAOSTATS_PRICE_URL)
            req.add_header("Content-Type", "application/json")
            if self.api_key:
                req.add_header("x-api-key", self.api_key)

            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            # TaoStats returns {"data": [{"close": "...", ...}]} or similar
            price_usd = None
            if isinstance(data, dict):
                items = data.get("data") or data.get("results") or []
                if isinstance(items, list) and items:
                    entry = items[0]
                    price_usd = Decimal(str(
                        entry.get("close") or entry.get("price") or entry.get("price_usd", 0)
                    ))
                elif "price" in data:
                    price_usd = Decimal(str(data["price"]))

            if price_usd is None or price_usd <= 0:
                logger.warning("Could not parse TAO price from API response")
                return None

            now = datetime.now(timezone.utc)
            self.repo.create(
                timestamp=now,
                price_usd=price_usd,
                source="taostats",
                block_number=block_number,
            )
            self.session.flush()

            logger.info("Stored TAO price", price_usd=str(price_usd), block_number=block_number)
            return price_usd

        except Exception:
            logger.exception("Failed to fetch TAO price from TaoStats")
            return None

    def get_price_at_time(self, ts: datetime) -> Optional[Decimal]:
        """Look up the closest stored price to a given timestamp."""
        record = self.repo.get_closest_to_timestamp(ts)
        return record.price_usd if record else None

    def get_price_at_block(self, block_number: int) -> Optional[Decimal]:
        """Look up the closest stored price to a given block."""
        record = self.repo.get_closest_to_block(block_number)
        return record.price_usd if record else None
