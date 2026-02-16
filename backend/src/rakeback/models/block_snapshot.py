"""BlockSnapshot and DelegationEntry models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import json

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rakeback.models.base import Base, generate_uuid, utc_now
from rakeback.models.enums import CompletenessFlag, DataSource, DelegationType


class BlockSnapshot(Base):
    """
    Immutable record of delegation state at a specific block.
    
    This is the source of truth for who was delegating to the validator
    at any given block height.
    """
    
    __tablename__ = "block_snapshots"
    
    # Primary key: block_number + validator_hotkey
    block_number: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    validator_hotkey: Mapped[str] = mapped_column(String(64), primary_key=True)
    
    # Block identification
    block_hash: Mapped[str] = mapped_column(String(66), nullable=False)  # 0x + 64 hex chars
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Metadata
    ingestion_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False,
        default=utc_now
    )
    data_source: Mapped[DataSource] = mapped_column(
        Enum(DataSource, name="data_source_enum"),
        nullable=False,
        default=DataSource.CHAIN
    )
    completeness_flag: Mapped[CompletenessFlag] = mapped_column(
        Enum(CompletenessFlag, name="completeness_flag_enum"),
        nullable=False,
        default=CompletenessFlag.COMPLETE
    )
    
    # Total stake for validation
    total_stake: Mapped[Decimal] = mapped_column(
        Numeric(38, 0),  # uint128 equivalent
        nullable=False,
        default=0
    )
    
    # Relationships
    delegations: Mapped[list["DelegationEntry"]] = relationship(
        "DelegationEntry",
        back_populates="snapshot",
        cascade="all, delete-orphan",
        order_by="DelegationEntry.delegator_address"
    )
    
    __table_args__ = (
        Index("ix_block_snapshots_timestamp", "timestamp"),
        Index("ix_block_snapshots_validator", "validator_hotkey"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<BlockSnapshot(block={self.block_number}, "
            f"validator={self.validator_hotkey[:16]}..., "
            f"delegations={len(self.delegations) if self.delegations else 0})>"
        )


class DelegationEntry(Base):
    """
    Individual delegation within a block snapshot.
    
    Records the stake of a single delegator at a specific block.
    """
    
    __tablename__ = "delegation_entries"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    
    # Foreign key to snapshot
    block_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    validator_hotkey: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Delegation details
    delegator_address: Mapped[str] = mapped_column(String(64), nullable=False)
    delegation_type: Mapped[DelegationType] = mapped_column(
        Enum(DelegationType, name="delegation_type_enum"),
        nullable=False
    )
    subnet_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Balances (stored as integers, representing smallest unit)
    balance_dtao: Mapped[Decimal] = mapped_column(
        Numeric(38, 0),  # uint128 equivalent
        nullable=False,
        default=0
    )
    balance_tao: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(38, 0),
        nullable=True
    )
    
    # Pre-calculated proportion (high precision)
    proportion: Mapped[Decimal] = mapped_column(
        Numeric(38, 18),  # 18 decimal places for precision
        nullable=False
    )
    
    # Relationship back to snapshot
    snapshot: Mapped["BlockSnapshot"] = relationship(
        "BlockSnapshot",
        back_populates="delegations"
    )
    
    __table_args__ = (
        ForeignKeyConstraint(
            ["block_number", "validator_hotkey"],
            ["block_snapshots.block_number", "block_snapshots.validator_hotkey"],
            ondelete="CASCADE"
        ),
        UniqueConstraint(
            "block_number", 
            "validator_hotkey", 
            "delegator_address",
            name="uq_delegation_per_block"
        ),
        Index("ix_delegation_entries_delegator", "delegator_address"),
        Index("ix_delegation_entries_block", "block_number", "validator_hotkey"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<DelegationEntry(block={self.block_number}, "
            f"delegator={self.delegator_address[:16]}..., "
            f"balance={self.balance_dtao}, proportion={self.proportion:.6f})>"
        )
