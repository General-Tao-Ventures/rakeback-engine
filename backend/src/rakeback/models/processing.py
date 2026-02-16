"""ProcessingRun and DataGap models."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from rakeback.models.base import Base, generate_uuid, utc_now
from rakeback.models.enums import GapType, ResolutionStatus, RunStatus, RunType


class ProcessingRun(Base):
    """
    Audit log for each processing execution.
    
    Tracks every run of ingestion, attribution, aggregation, or export
    for full traceability and idempotency support.
    """
    
    __tablename__ = "processing_runs"
    
    # Primary key
    run_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    
    # Run type
    run_type: Mapped[RunType] = mapped_column(
        Enum(RunType, name="run_type_enum"),
        nullable=False
    )
    
    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Status
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status_enum"),
        nullable=False,
        default=RunStatus.RUNNING
    )
    
    # Scope - block range
    block_range_start: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    block_range_end: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # Scope - period
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Validator filter
    validator_hotkey: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Error details (if failed)
    error_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Completeness summary
    completeness_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Snapshot of configuration at time of run
    config_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Statistics
    records_processed: Mapped[int] = mapped_column(nullable=False, default=0)
    records_created: Mapped[int] = mapped_column(nullable=False, default=0)
    records_skipped: Mapped[int] = mapped_column(nullable=False, default=0)
    
    # Reference to parent run (for re-runs)
    parent_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    __table_args__ = (
        Index("ix_processing_runs_type", "run_type"),
        Index("ix_processing_runs_status", "status"),
        Index("ix_processing_runs_started", "started_at"),
        Index("ix_processing_runs_validator", "validator_hotkey"),
    )
    
    def mark_completed(self, status: RunStatus = RunStatus.SUCCESS) -> None:
        """Mark the run as completed."""
        self.completed_at = utc_now()
        self.status = status
    
    def mark_failed(self, error: Exception) -> None:
        """Mark the run as failed with error details."""
        self.completed_at = utc_now()
        self.status = RunStatus.FAILED
        self.error_details = {
            "type": type(error).__name__,
            "message": str(error),
        }
    
    def __repr__(self) -> str:
        return (
            f"<ProcessingRun(id={self.run_id[:8]}..., "
            f"type={self.run_type.value}, status={self.status.value})>"
        )


class DataGap(Base):
    """
    Tracks known missing data.
    
    When data cannot be fetched or is detected as missing, a gap
    is recorded for later resolution or explicit marking as unrecoverable.
    """
    
    __tablename__ = "data_gaps"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    
    # Gap type
    gap_type: Mapped[GapType] = mapped_column(
        Enum(GapType, name="gap_type_enum"),
        nullable=False
    )
    
    # Block range
    block_start: Mapped[int] = mapped_column(BigInteger, nullable=False)
    block_end: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    # Optional validator specificity
    validator_hotkey: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Reason for gap
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    
    # Resolution status
    resolution_status: Mapped[ResolutionStatus] = mapped_column(
        Enum(ResolutionStatus, name="resolution_status_enum"),
        nullable=False,
        default=ResolutionStatus.OPEN
    )
    
    # Resolution details
    resolution_notes: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    resolved_by_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )
    
    # Run that detected this gap
    detected_by_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    
    __table_args__ = (
        Index("ix_data_gaps_type", "gap_type"),
        Index("ix_data_gaps_status", "resolution_status"),
        Index("ix_data_gaps_blocks", "block_start", "block_end"),
        Index("ix_data_gaps_validator", "validator_hotkey"),
    )
    
    def mark_resolved(self, status: ResolutionStatus, run_id: str, notes: Optional[str] = None) -> None:
        """Mark the gap as resolved."""
        self.resolution_status = status
        self.resolved_at = utc_now()
        self.resolved_by_run_id = run_id
        self.resolution_notes = notes
    
    def __repr__(self) -> str:
        return (
            f"<DataGap(type={self.gap_type.value}, "
            f"blocks={self.block_start}-{self.block_end}, "
            f"status={self.resolution_status.value})>"
        )
