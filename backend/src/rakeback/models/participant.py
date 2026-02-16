"""RakebackParticipant model."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Index,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from rakeback.models.base import Base, utc_now
from rakeback.models.enums import AggregationMode, ParticipantType


class RakebackParticipant(Base):
    """
    Rakeback-eligible entity definition.
    
    Configuration record that defines who is eligible for rakebacks,
    how to identify their delegations, and what percentage they receive.
    """
    
    __tablename__ = "rakeback_participants"
    
    # Primary key - human-readable identifier
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    
    # Display name
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # Participant type
    type: Mapped[ParticipantType] = mapped_column(
        Enum(ParticipantType, name="participant_type_enum", create_type=False),
        nullable=False
    )
    
    # Matching rules (JSON structure)
    # Example:
    # {
    #   "rules": [
    #     {"type": "EXACT_ADDRESS", "addresses": ["5Cabc...", "5Cdef..."]},
    #     {"type": "DELEGATION_TYPE", "delegation_types": ["SUBNET_DTAO"], "subnet_ids": [21, 22]}
    #   ]
    # }
    matching_rules: Mapped[dict] = mapped_column(
        JSON,
        nullable=False
    )
    
    # Rakeback percentage (e.g., 0.5000 for 50%)
    rakeback_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False
    )
    
    # Validity period
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Payout destination
    payout_address: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # How to aggregate rakeback (lump sum vs per-wallet)
    aggregation_mode: Mapped[AggregationMode] = mapped_column(
        Enum(AggregationMode, name="aggregation_mode_enum"),
        nullable=False,
        default=AggregationMode.LUMP_SUM
    )
    
    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now
    )
    
    # Optional notes
    notes: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    
    __table_args__ = (
        Index("ix_participants_type", "type"),
        Index("ix_participants_effective", "effective_from", "effective_to"),
    )
    
    def is_active(self, as_of: date) -> bool:
        """Check if participant is active as of a given date."""
        if as_of < self.effective_from:
            return False
        if self.effective_to is not None and as_of > self.effective_to:
            return False
        return True
    
    def __repr__(self) -> str:
        return (
            f"<RakebackParticipant(id={self.id}, name={self.name}, "
            f"rakeback={self.rakeback_percentage:.2%})>"
        )
