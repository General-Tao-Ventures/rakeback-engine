"""BlockAttribution model."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from rakeback.models.base import Base, generate_uuid, utc_now
from rakeback.models.enums import CompletenessFlag, DelegationType


class BlockAttribution(Base):
    """
    Attributed dTAO per delegator per block.
    
    This is the core attribution record that links a delegator's stake
    proportion to their share of the block's yield.
    """
    
    __tablename__ = "block_attributions"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    
    # Block and validator reference
    block_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    validator_hotkey: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Delegator details
    delegator_address: Mapped[str] = mapped_column(String(64), nullable=False)
    delegation_type: Mapped[DelegationType] = mapped_column(
        Enum(DelegationType, name="delegation_type_enum", create_type=False),
        nullable=False
    )
    subnet_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Attribution calculation
    attributed_dtao: Mapped[Decimal] = mapped_column(
        Numeric(38, 0),  # uint128 equivalent - actual dTAO amount
        nullable=False
    )
    delegation_proportion: Mapped[Decimal] = mapped_column(
        Numeric(38, 18),  # High precision proportion used
        nullable=False
    )
    
    # Metadata
    completeness_flag: Mapped[CompletenessFlag] = mapped_column(
        Enum(CompletenessFlag, name="completeness_flag_enum", create_type=False),
        nullable=False,
        default=CompletenessFlag.COMPLETE
    )
    computation_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )
    run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    
    # Allocation tracking (updated when TAO is allocated)
    tao_allocated: Mapped[Decimal] = mapped_column(
        Numeric(38, 0),
        nullable=False,
        default=0
    )
    fully_allocated: Mapped[bool] = mapped_column(
        default=False,
        nullable=False
    )
    
    __table_args__ = (
        Index("ix_block_attributions_block", "block_number", "validator_hotkey"),
        Index("ix_block_attributions_delegator", "delegator_address"),
        Index("ix_block_attributions_run", "run_id"),
        Index("ix_block_attributions_unallocated", "fully_allocated", "validator_hotkey"),
        # Unique constraint: one attribution per delegator per block per validator
        Index(
            "uq_attribution_per_block_delegator",
            "block_number",
            "validator_hotkey",
            "delegator_address",
            unique=True
        ),
    )
    
    def __repr__(self) -> str:
        return (
            f"<BlockAttribution(block={self.block_number}, "
            f"delegator={self.delegator_address[:16]}..., "
            f"dtao={self.attributed_dtao})>"
        )
