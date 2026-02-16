"""BlockYield and YieldSource models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rakeback.models.base import Base, generate_uuid, utc_now
from rakeback.models.enums import CompletenessFlag, DataSource


class BlockYield(Base):
    """
    dTAO yield earned by validator at a specific block.
    
    Records the total dTAO minted to the validator at this block,
    optionally broken down by source subnet.
    """
    
    __tablename__ = "block_yields"
    
    # Primary key: block_number + validator_hotkey
    block_number: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    validator_hotkey: Mapped[str] = mapped_column(String(64), primary_key=True)
    
    # Total yield
    total_dtao_earned: Mapped[Decimal] = mapped_column(
        Numeric(38, 0),  # uint128 equivalent
        nullable=False,
        default=0
    )
    
    # Metadata
    data_source: Mapped[DataSource] = mapped_column(
        Enum(DataSource, name="data_source_enum", create_type=False),
        nullable=False,
        default=DataSource.CHAIN
    )
    completeness_flag: Mapped[CompletenessFlag] = mapped_column(
        Enum(CompletenessFlag, name="completeness_flag_enum", create_type=False),
        nullable=False,
        default=CompletenessFlag.COMPLETE
    )
    ingestion_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )
    
    # Relationships
    yield_sources: Mapped[list["YieldSource"]] = relationship(
        "YieldSource",
        back_populates="block_yield",
        cascade="all, delete-orphan",
        order_by="YieldSource.subnet_id"
    )
    
    __table_args__ = (
        Index("ix_block_yields_block", "block_number"),
        Index("ix_block_yields_validator", "validator_hotkey"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<BlockYield(block={self.block_number}, "
            f"validator={self.validator_hotkey[:16]}..., "
            f"dtao={self.total_dtao_earned})>"
        )


class YieldSource(Base):
    """
    Subnet-level yield breakdown.
    
    Records how much of the block yield came from each subnet.
    """
    
    __tablename__ = "yield_sources"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    
    # Foreign key to block yield
    block_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    validator_hotkey: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Subnet identification
    subnet_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Amount from this subnet
    dtao_amount: Mapped[Decimal] = mapped_column(
        Numeric(38, 0),
        nullable=False
    )
    
    # Relationship back to block yield
    block_yield: Mapped["BlockYield"] = relationship(
        "BlockYield",
        back_populates="yield_sources"
    )
    
    __table_args__ = (
        ForeignKeyConstraint(
            ["block_number", "validator_hotkey"],
            ["block_yields.block_number", "block_yields.validator_hotkey"],
            ondelete="CASCADE"
        ),
        UniqueConstraint(
            "block_number",
            "validator_hotkey",
            "subnet_id",
            name="uq_yield_source_per_subnet"
        ),
        Index("ix_yield_sources_subnet", "subnet_id"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<YieldSource(block={self.block_number}, "
            f"subnet={self.subnet_id}, dtao={self.dtao_amount})>"
        )
