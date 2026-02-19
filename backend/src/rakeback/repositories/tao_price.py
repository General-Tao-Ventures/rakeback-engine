"""Repository for TAO price data."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from rakeback.models.tao_price import TaoPrice
from rakeback.repositories.base import BaseRepository


class TaoPriceRepository(BaseRepository[TaoPrice]):
    """Data access for tao_prices table."""

    model = TaoPrice

    def get_latest(self) -> Optional[TaoPrice]:
        """Get the most recent price record."""
        stmt = select(TaoPrice).order_by(TaoPrice.timestamp.desc()).limit(1)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_date_range(
        self, start: datetime, end: datetime
    ) -> Sequence[TaoPrice]:
        """Get all prices within a date range, ordered by timestamp."""
        stmt = (
            select(TaoPrice)
            .where(TaoPrice.timestamp >= start, TaoPrice.timestamp <= end)
            .order_by(TaoPrice.timestamp)
        )
        return self.session.execute(stmt).scalars().all()

    def get_closest_to_block(self, block_number: int) -> Optional[TaoPrice]:
        """Get the price record closest to a given block number."""
        # Try exact match first
        stmt = select(TaoPrice).where(TaoPrice.block_number == block_number).limit(1)
        exact = self.session.execute(stmt).scalar_one_or_none()
        if exact:
            return exact

        # Find nearest by block_number (prefer the one just before)
        stmt_before = (
            select(TaoPrice)
            .where(TaoPrice.block_number.isnot(None), TaoPrice.block_number <= block_number)
            .order_by(TaoPrice.block_number.desc())
            .limit(1)
        )
        before = self.session.execute(stmt_before).scalar_one_or_none()

        stmt_after = (
            select(TaoPrice)
            .where(TaoPrice.block_number.isnot(None), TaoPrice.block_number >= block_number)
            .order_by(TaoPrice.block_number)
            .limit(1)
        )
        after = self.session.execute(stmt_after).scalar_one_or_none()

        if before and after:
            if (block_number - before.block_number) <= (after.block_number - block_number):
                return before
            return after
        return before or after

    def get_closest_to_timestamp(self, ts: datetime) -> Optional[TaoPrice]:
        """Get the price record closest to a given timestamp."""
        stmt_before = (
            select(TaoPrice)
            .where(TaoPrice.timestamp <= ts)
            .order_by(TaoPrice.timestamp.desc())
            .limit(1)
        )
        before = self.session.execute(stmt_before).scalar_one_or_none()

        stmt_after = (
            select(TaoPrice)
            .where(TaoPrice.timestamp >= ts)
            .order_by(TaoPrice.timestamp)
            .limit(1)
        )
        after = self.session.execute(stmt_after).scalar_one_or_none()

        if before and after:
            if (ts - before.timestamp) <= (after.timestamp - ts):
                return before
            return after
        return before or after

    def create(
        self,
        timestamp: datetime,
        price_usd: Decimal,
        source: str = "taostats",
        block_number: Optional[int] = None,
    ) -> TaoPrice:
        """Create a new price record."""
        price = TaoPrice(
            timestamp=timestamp,
            price_usd=price_usd,
            source=source,
            block_number=block_number,
        )
        self.session.add(price)
        self.session.flush()
        return price
