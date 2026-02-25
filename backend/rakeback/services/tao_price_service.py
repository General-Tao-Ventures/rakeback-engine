"""Service for fetching and storing TAO price data."""

from datetime import UTC, datetime
from decimal import Decimal

import structlog
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from db.models import TaoPrices
from rakeback.services._helpers import new_id, now_iso

logger = structlog.get_logger(__name__)

TAOSTATS_PRICE_URL = "https://api.taostats.io/api/price/latest/v1"


class TaoPriceService:
    """Fetches TAO/USD prices from TaoStats and stores them locally."""

    def __init__(self, session: Session, api_key: str = "") -> None:
        self.session: Session = session
        self.api_key: str = api_key

    def fetch_and_store(self, block_number: int | None = None) -> Decimal | None:
        """Call TaoStats API and store the current price. Returns price_usd or None."""
        try:
            import json
            import urllib.request

            req: urllib.request.Request = urllib.request.Request(TAOSTATS_PRICE_URL)
            req.add_header("Content-Type", "application/json")
            if self.api_key:
                req.add_header("x-api-key", self.api_key)

            with urllib.request.urlopen(req, timeout=15) as resp:
                data: object = json.loads(resp.read().decode())

            price_usd: Decimal | None = None
            if isinstance(data, dict):
                items: object = data.get("data") or data.get("results") or []
                if isinstance(items, list) and items:
                    entry: object = items[0]
                    if isinstance(entry, dict):
                        price_usd = Decimal(
                            str(
                                entry.get("close")
                                or entry.get("price")
                                or entry.get("price_usd", 0)
                            )
                        )
                elif "price" in data:
                    price_usd = Decimal(str(data["price"]))

            if price_usd is None or price_usd <= 0:
                logger.warning("Could not parse TAO price from API response")
                return None

            now: datetime = datetime.now(UTC)
            price: TaoPrices = TaoPrices(
                id=new_id(),
                timestamp=now.isoformat(),
                price_usd=float(price_usd),
                source="taostats",
                block_number=block_number,
                created_at=now_iso(),
            )
            self.session.add(price)
            self.session.flush()

            logger.info("Stored TAO price", price_usd=str(price_usd))
            return price_usd

        except Exception:
            logger.exception("Failed to fetch TAO price from TaoStats")
            return None

    def get_price_at_timestamp(self, ts: datetime) -> Decimal | None:
        """Look up the closest stored price to a given timestamp."""
        ts_str: str = ts.isoformat()
        stmt_before: Select[tuple[TaoPrices]] = (
            select(TaoPrices)
            .where(TaoPrices.timestamp <= ts_str)
            .order_by(TaoPrices.timestamp.desc())
            .limit(1)
        )
        before: TaoPrices | None = self.session.scalar(stmt_before)

        stmt_after: Select[tuple[TaoPrices]] = (
            select(TaoPrices)
            .where(TaoPrices.timestamp >= ts_str)
            .order_by(TaoPrices.timestamp)
            .limit(1)
        )
        after: TaoPrices | None = self.session.scalar(stmt_after)

        if before and after:
            return Decimal(str(before.price_usd))
        record: TaoPrices | None = before or after
        return Decimal(str(record.price_usd)) if record else None

    def get_price_at_block(self, block_number: int) -> Decimal | None:
        """Look up the closest stored price to a given block."""
        stmt: Select[tuple[TaoPrices]] = (
            select(TaoPrices).where(TaoPrices.block_number == block_number).limit(1)
        )
        exact: TaoPrices | None = self.session.scalar(stmt)
        if exact:
            return Decimal(str(exact.price_usd))

        stmt_before: Select[tuple[TaoPrices]] = (
            select(TaoPrices)
            .where(TaoPrices.block_number.isnot(None), TaoPrices.block_number <= block_number)
            .order_by(TaoPrices.block_number.desc())
            .limit(1)
        )
        before: TaoPrices | None = self.session.scalar(stmt_before)

        stmt_after: Select[tuple[TaoPrices]] = (
            select(TaoPrices)
            .where(TaoPrices.block_number.isnot(None), TaoPrices.block_number >= block_number)
            .order_by(TaoPrices.block_number)
            .limit(1)
        )
        after: TaoPrices | None = self.session.scalar(stmt_after)

        if before and after and before.block_number is not None and after.block_number is not None:
            if (block_number - before.block_number) <= (after.block_number - block_number):
                return Decimal(str(before.price_usd))
            return Decimal(str(after.price_usd))
        record: TaoPrices | None = before or after
        return Decimal(str(record.price_usd)) if record else None
