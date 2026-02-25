"""SQLAlchemy ORM models — auto-generated from migrated schema.

DO NOT EDIT by hand. Re-generate with:
    python scripts/generate_models.py
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    ForeignKey,
    ForeignKeyConstraint,
    MetaData,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)

    def to_dict(self) -> dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


def generate_uuid() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class BlockAttributions(Base):
    __tablename__ = "block_attributions"

    id: Mapped[str] = mapped_column(primary_key=True)
    block_number: Mapped[int] = mapped_column(nullable=False)
    validator_hotkey: Mapped[str] = mapped_column(nullable=False)
    delegator_address: Mapped[str] = mapped_column(nullable=False)
    delegation_type: Mapped[str] = mapped_column(nullable=False)
    subnet_id: Mapped[int | None] = mapped_column()
    attributed_dtao: Mapped[float] = mapped_column(nullable=False)
    delegation_proportion: Mapped[float] = mapped_column(nullable=False)
    completeness_flag: Mapped[str] = mapped_column(nullable=False, default="COMPLETE")
    computation_timestamp: Mapped[str] = mapped_column(nullable=False)
    run_id: Mapped[str] = mapped_column(nullable=False)
    tao_allocated: Mapped[float] = mapped_column(nullable=False, default="0")
    fully_allocated: Mapped[int] = mapped_column(nullable=False, default="0")

    __table_args__ = (UniqueConstraint("block_number", "validator_hotkey", "delegator_address"),)


class BlockSnapshots(Base):
    __tablename__ = "block_snapshots"

    block_number: Mapped[int] = mapped_column(primary_key=True)
    validator_hotkey: Mapped[str] = mapped_column(primary_key=True)
    block_hash: Mapped[str] = mapped_column(nullable=False)
    timestamp: Mapped[str] = mapped_column(nullable=False)
    ingestion_timestamp: Mapped[str] = mapped_column(nullable=False)
    data_source: Mapped[str] = mapped_column(nullable=False, default="CHAIN")
    completeness_flag: Mapped[str] = mapped_column(nullable=False, default="COMPLETE")
    total_stake: Mapped[float] = mapped_column(nullable=False, default="0")
    delegations = relationship(
        "DelegationEntries",
        back_populates="snapshot",
        cascade="all, delete-orphan",
        order_by="DelegationEntries.delegator_address",
    )


class BlockYields(Base):
    __tablename__ = "block_yields"

    block_number: Mapped[int] = mapped_column(primary_key=True)
    validator_hotkey: Mapped[str] = mapped_column(primary_key=True)
    total_dtao_earned: Mapped[float] = mapped_column(nullable=False, default="0")
    data_source: Mapped[str] = mapped_column(nullable=False, default="CHAIN")
    completeness_flag: Mapped[str] = mapped_column(nullable=False, default="COMPLETE")
    ingestion_timestamp: Mapped[str] = mapped_column(nullable=False)
    yield_sources = relationship(
        "YieldSources",
        back_populates="block_yield",
        cascade="all, delete-orphan",
        order_by="YieldSources.subnet_id",
    )


class ConversionEvents(Base):
    __tablename__ = "conversion_events"

    id: Mapped[str] = mapped_column(primary_key=True)
    block_number: Mapped[int] = mapped_column(nullable=False)
    transaction_hash: Mapped[str] = mapped_column(nullable=False)
    validator_hotkey: Mapped[str] = mapped_column(nullable=False)
    dtao_amount: Mapped[float] = mapped_column(nullable=False)
    tao_amount: Mapped[float] = mapped_column(nullable=False)
    conversion_rate: Mapped[float] = mapped_column(nullable=False)
    subnet_id: Mapped[int | None] = mapped_column()
    data_source: Mapped[str] = mapped_column(nullable=False, default="CHAIN")
    ingestion_timestamp: Mapped[str] = mapped_column(nullable=False)
    fully_allocated: Mapped[int] = mapped_column(nullable=False, default="0")

    __table_args__ = (UniqueConstraint("transaction_hash"),)
    allocations = relationship(
        "TaoAllocations",
        back_populates="conversion_event",
        cascade="all, delete-orphan",
    )


class DataGaps(Base):
    __tablename__ = "data_gaps"

    id: Mapped[str] = mapped_column(primary_key=True)
    gap_type: Mapped[str] = mapped_column(nullable=False)
    block_start: Mapped[int] = mapped_column(nullable=False)
    block_end: Mapped[int] = mapped_column(nullable=False)
    validator_hotkey: Mapped[str | None] = mapped_column()
    reason: Mapped[str] = mapped_column(nullable=False)
    resolution_status: Mapped[str] = mapped_column(nullable=False, default="OPEN")
    resolution_notes: Mapped[str | None] = mapped_column()
    resolved_at: Mapped[str | None] = mapped_column()
    resolved_by_run_id: Mapped[str | None] = mapped_column()
    created_at: Mapped[str] = mapped_column(nullable=False)
    detected_by_run_id: Mapped[str | None] = mapped_column()


class DelegationEntries(Base):
    __tablename__ = "delegation_entries"

    id: Mapped[str] = mapped_column(primary_key=True)
    block_number: Mapped[int] = mapped_column(nullable=False)
    validator_hotkey: Mapped[str] = mapped_column(nullable=False)
    delegator_address: Mapped[str] = mapped_column(nullable=False)
    delegation_type: Mapped[str] = mapped_column(nullable=False)
    subnet_id: Mapped[int | None] = mapped_column()
    balance_dtao: Mapped[float] = mapped_column(nullable=False, default="0")
    balance_tao: Mapped[float | None] = mapped_column()
    proportion: Mapped[float] = mapped_column(nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["block_number", "validator_hotkey"],
            ["block_snapshots.block_number", "block_snapshots.validator_hotkey"],
        ),
        UniqueConstraint("block_number", "validator_hotkey", "delegator_address"),
    )
    snapshot = relationship("BlockSnapshots", back_populates="delegations")


class EligibilityRules(Base):
    __tablename__ = "eligibility_rules"

    id: Mapped[str] = mapped_column(primary_key=True)
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("rakeback_participants.id"),
        nullable=False,
    )
    rule_type: Mapped[str] = mapped_column(nullable=False)
    config: Mapped[str] = mapped_column(nullable=False)
    applies_from_block: Mapped[int | None] = mapped_column()
    created_at: Mapped[str] = mapped_column(nullable=False)
    created_by: Mapped[str] = mapped_column(nullable=False, default="system")
    participant = relationship("RakebackParticipants", back_populates="eligibility_rules")


class ProcessingRuns(Base):
    __tablename__ = "processing_runs"

    run_id: Mapped[str] = mapped_column(primary_key=True)
    run_type: Mapped[str] = mapped_column(nullable=False)
    started_at: Mapped[str] = mapped_column(nullable=False)
    completed_at: Mapped[str | None] = mapped_column()
    status: Mapped[str] = mapped_column(nullable=False, default="RUNNING")
    block_range_start: Mapped[int | None] = mapped_column()
    block_range_end: Mapped[int | None] = mapped_column()
    period_start: Mapped[str | None] = mapped_column()
    period_end: Mapped[str | None] = mapped_column()
    validator_hotkey: Mapped[str | None] = mapped_column()
    error_details: Mapped[str | None] = mapped_column()
    completeness_summary: Mapped[str | None] = mapped_column()
    config_snapshot: Mapped[str | None] = mapped_column()
    records_processed: Mapped[int] = mapped_column(nullable=False, default="0")
    records_created: Mapped[int] = mapped_column(nullable=False, default="0")
    records_skipped: Mapped[int] = mapped_column(nullable=False, default="0")
    parent_run_id: Mapped[str | None] = mapped_column()


class RakebackLedgerEntries(Base):
    __tablename__ = "rakeback_ledger_entries"

    id: Mapped[str] = mapped_column(primary_key=True)
    period_type: Mapped[str] = mapped_column(nullable=False)
    period_start: Mapped[str] = mapped_column(nullable=False)
    period_end: Mapped[str] = mapped_column(nullable=False)
    participant_id: Mapped[str] = mapped_column(nullable=False)
    participant_type: Mapped[str] = mapped_column(nullable=False)
    validator_hotkey: Mapped[str] = mapped_column(nullable=False)
    gross_dtao_attributed: Mapped[float] = mapped_column(nullable=False, default="0")
    gross_tao_converted: Mapped[float] = mapped_column(nullable=False, default="0")
    rakeback_percentage: Mapped[float] = mapped_column(nullable=False)
    tao_owed: Mapped[float] = mapped_column(nullable=False)
    payment_status: Mapped[str] = mapped_column(nullable=False, default="UNPAID")
    payment_tx_hash: Mapped[str | None] = mapped_column()
    payment_timestamp: Mapped[str | None] = mapped_column()
    completeness_flag: Mapped[str] = mapped_column(nullable=False, default="COMPLETE")
    completeness_details: Mapped[str | None] = mapped_column()
    run_id: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)
    block_count: Mapped[int] = mapped_column(nullable=False, default="0")
    attribution_count: Mapped[int] = mapped_column(nullable=False, default="0")

    __table_args__ = (
        UniqueConstraint("participant_id", "period_type", "period_start", "validator_hotkey"),
    )


class RakebackParticipants(Base):
    __tablename__ = "rakeback_participants"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    partner_type: Mapped[str | None] = mapped_column(default="NAMED")
    priority: Mapped[int] = mapped_column(nullable=False, default="1")
    type: Mapped[str] = mapped_column(nullable=False)
    matching_rules: Mapped[str] = mapped_column(nullable=False, default='{"rules": []}')
    rakeback_percentage: Mapped[float] = mapped_column(nullable=False)
    effective_from: Mapped[str] = mapped_column(nullable=False)
    effective_to: Mapped[str | None] = mapped_column()
    payout_address: Mapped[str] = mapped_column(nullable=False)
    aggregation_mode: Mapped[str] = mapped_column(nullable=False, default="LUMP_SUM")
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)
    notes: Mapped[str | None] = mapped_column()
    eligibility_rules = relationship(
        "EligibilityRules",
        back_populates="participant",
        cascade="all, delete-orphan",
        order_by="EligibilityRules.created_at",
    )


class RuleChangeLog(Base):
    __tablename__ = "rule_change_log"

    id: Mapped[str] = mapped_column(primary_key=True)
    timestamp: Mapped[str] = mapped_column(nullable=False)
    user: Mapped[str] = mapped_column(nullable=False, default="system")
    action: Mapped[str] = mapped_column(nullable=False)
    partner_id: Mapped[str] = mapped_column(nullable=False)
    partner_name: Mapped[str] = mapped_column(nullable=False)
    details: Mapped[str] = mapped_column(nullable=False)
    applies_from_block: Mapped[int] = mapped_column(nullable=False)


class TaoAllocations(Base):
    __tablename__ = "tao_allocations"

    id: Mapped[str] = mapped_column(primary_key=True)
    conversion_event_id: Mapped[str] = mapped_column(
        ForeignKey("conversion_events.id"),
        nullable=False,
    )
    block_attribution_id: Mapped[str] = mapped_column(
        ForeignKey("block_attributions.id"),
        nullable=False,
    )
    tao_allocated: Mapped[float] = mapped_column(nullable=False)
    allocation_method: Mapped[str] = mapped_column(nullable=False, default="PRORATA")
    completeness_flag: Mapped[str] = mapped_column(nullable=False, default="COMPLETE")
    run_id: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[str] = mapped_column(nullable=False)
    conversion_event = relationship("ConversionEvents", back_populates="allocations")


class TaoPrices(Base):
    __tablename__ = "tao_prices"

    id: Mapped[str] = mapped_column(primary_key=True)
    timestamp: Mapped[str] = mapped_column(nullable=False)
    price_usd: Mapped[float] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(nullable=False, default="taostats")
    block_number: Mapped[int | None] = mapped_column()
    created_at: Mapped[str] = mapped_column(nullable=False)


class YieldSources(Base):
    __tablename__ = "yield_sources"

    id: Mapped[str] = mapped_column(primary_key=True)
    block_number: Mapped[int] = mapped_column(nullable=False)
    validator_hotkey: Mapped[str] = mapped_column(nullable=False)
    subnet_id: Mapped[int] = mapped_column(nullable=False)
    dtao_amount: Mapped[float] = mapped_column(nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["block_number", "validator_hotkey"],
            ["block_yields.block_number", "block_yields.validator_hotkey"],
        ),
        UniqueConstraint("block_number", "validator_hotkey", "subnet_id"),
    )
    block_yield = relationship("BlockYields", back_populates="yield_sources")
