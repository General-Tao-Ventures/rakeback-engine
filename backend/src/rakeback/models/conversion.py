"""ConversionEvent and TaoAllocation models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rakeback.models.base import Base, generate_uuid, utc_now
from rakeback.models.enums import AllocationMethod, CompletenessFlag, DataSource


class ConversionEvent(Base):
    """
    dTAO → TAO conversion record.
    
    Records when the validator converts accumulated dTAO to TAO,
    including the exact conversion rate at the time.
    """
    
    __tablename__ = "conversion_events"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    
    # Block and transaction reference
    block_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    transaction_hash: Mapped[str] = mapped_column(String(66), nullable=False)  # 0x + 64 hex
    
    # Validator
    validator_hotkey: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Conversion amounts
    dtao_amount: Mapped[Decimal] = mapped_column(
        Numeric(38, 0),
        nullable=False
    )
    tao_amount: Mapped[Decimal] = mapped_column(
        Numeric(38, 0),
        nullable=False
    )
    conversion_rate: Mapped[Decimal] = mapped_column(
        Numeric(38, 18),  # High precision rate
        nullable=False
    )
    
    # Optional subnet specification
    subnet_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Metadata
    data_source: Mapped[DataSource] = mapped_column(
        Enum(DataSource, name="data_source_enum", create_type=False),
        nullable=False,
        default=DataSource.CHAIN
    )
    ingestion_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )
    
    # Allocation tracking
    fully_allocated: Mapped[bool] = mapped_column(
        default=False,
        nullable=False
    )
    
    # Relationships
    allocations: Mapped[list["TaoAllocation"]] = relationship(
        "TaoAllocation",
        back_populates="conversion_event",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("ix_conversion_events_block", "block_number"),
        Index("ix_conversion_events_validator", "validator_hotkey"),
        Index("ix_conversion_events_tx", "transaction_hash", unique=True),
    )
    
    def __repr__(self) -> str:
        return (
            f"<ConversionEvent(block={self.block_number}, "
            f"dtao={self.dtao_amount}, tao={self.tao_amount}, "
            f"rate={self.conversion_rate:.6f})>"
        )


class TaoAllocation(Base):
    """
    Links converted TAO back to attributed dTAO.
    
    When TAO is converted, this record allocates portions of the
    TAO to specific block attributions, creating the audit trail
    from dTAO attribution to TAO payment.
    """
    
    __tablename__ = "tao_allocations"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    
    # Foreign keys
    conversion_event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversion_events.id", ondelete="CASCADE"),
        nullable=False
    )
    block_attribution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("block_attributions.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Allocation details
    tao_allocated: Mapped[Decimal] = mapped_column(
        Numeric(38, 0),
        nullable=False
    )
    allocation_method: Mapped[AllocationMethod] = mapped_column(
        Enum(AllocationMethod, name="allocation_method_enum"),
        nullable=False,
        default=AllocationMethod.PRORATA
    )
    
    # Completeness inherited from sources
    completeness_flag: Mapped[CompletenessFlag] = mapped_column(
        Enum(CompletenessFlag, name="completeness_flag_enum", create_type=False),
        nullable=False,
        default=CompletenessFlag.COMPLETE
    )
    
    # Metadata
    run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )
    
    # Relationships
    conversion_event: Mapped["ConversionEvent"] = relationship(
        "ConversionEvent",
        back_populates="allocations"
    )
    
    __table_args__ = (
        Index("ix_tao_allocations_conversion", "conversion_event_id"),
        Index("ix_tao_allocations_attribution", "block_attribution_id"),
        Index("ix_tao_allocations_run", "run_id"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<TaoAllocation(conversion={self.conversion_event_id[:8]}..., "
            f"attribution={self.block_attribution_id[:8]}..., "
            f"tao={self.tao_allocated})>"
        )
