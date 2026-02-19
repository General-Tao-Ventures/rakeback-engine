"""TAO price tracking model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from rakeback.models.base import Base, generate_uuid, utc_now


class TaoPrice(Base):
    """Stores historical TAO/USD price snapshots."""

    __tablename__ = "tao_prices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price_usd: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="taostats")
    block_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    __table_args__ = (
        Index("ix_tao_prices_timestamp", "timestamp"),
        Index("ix_tao_prices_block_number", "block_number"),
    )
