"""RakebackLedgerEntry model."""

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
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from rakeback.models.base import Base, generate_uuid, utc_now
from rakeback.models.enums import CompletenessFlag, PaymentStatus, PeriodType, ParticipantType


class RakebackLedgerEntry(Base):
    """
    Final TAO obligation record.
    
    This is the aggregated record that finance uses to determine
    how much TAO is owed to each participant for a given period.
    """
    
    __tablename__ = "rakeback_ledger_entries"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    
    # Period specification
    period_type: Mapped[PeriodType] = mapped_column(
        Enum(PeriodType, name="period_type_enum"),
        nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Participant reference
    participant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    participant_type: Mapped[ParticipantType] = mapped_column(
        Enum(ParticipantType, name="participant_type_enum"),
        nullable=False
    )
    
    # Validator reference (for multi-validator support)
    validator_hotkey: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Aggregated amounts
    gross_dtao_attributed: Mapped[Decimal] = mapped_column(
        Numeric(38, 0),
        nullable=False,
        default=0
    )
    gross_tao_converted: Mapped[Decimal] = mapped_column(
        Numeric(38, 0),
        nullable=False,
        default=0
    )
    
    # Rakeback calculation
    rakeback_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),  # e.g., 0.5000 for 50%
        nullable=False
    )
    tao_owed: Mapped[Decimal] = mapped_column(
        Numeric(38, 0),
        nullable=False
    )
    
    # Payment tracking
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum"),
        nullable=False,
        default=PaymentStatus.UNPAID
    )
    payment_tx_hash: Mapped[Optional[str]] = mapped_column(String(66), nullable=True)
    payment_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Completeness tracking
    completeness_flag: Mapped[CompletenessFlag] = mapped_column(
        Enum(CompletenessFlag, name="completeness_flag_enum", create_type=False),
        nullable=False,
        default=CompletenessFlag.COMPLETE
    )
    completeness_details: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True
    )
    
    # Audit trail
    run_id: Mapped[str] = mapped_column(String(36), nullable=False)
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
    
    # Number of blocks/attributions included
    block_count: Mapped[int] = mapped_column(nullable=False, default=0)
    attribution_count: Mapped[int] = mapped_column(nullable=False, default=0)
    
    __table_args__ = (
        Index("ix_ledger_period", "period_type", "period_start", "period_end"),
        Index("ix_ledger_participant", "participant_id"),
        Index("ix_ledger_validator", "validator_hotkey"),
        Index("ix_ledger_payment_status", "payment_status"),
        Index("ix_ledger_run", "run_id"),
        # Unique constraint: one entry per participant per period per validator
        Index(
            "uq_ledger_participant_period",
            "participant_id",
            "period_type",
            "period_start",
            "validator_hotkey",
            unique=True
        ),
    )
    
    def __repr__(self) -> str:
        return (
            f"<RakebackLedgerEntry(participant={self.participant_id}, "
            f"period={self.period_start} to {self.period_end}, "
            f"tao_owed={self.tao_owed}, status={self.payment_status.value})>"
        )
