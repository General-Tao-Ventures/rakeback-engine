"""Repositories for ConversionEvent and TaoAllocation."""

from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import select, and_, func, update
from sqlalchemy.orm import joinedload

from rakeback.models import ConversionEvent, TaoAllocation, CompletenessFlag
from rakeback.repositories.base import BaseRepository


class ConversionEventRepository(BaseRepository[ConversionEvent]):
    """Repository for ConversionEvent operations."""
    
    model = ConversionEvent
    
    def get_by_tx_hash(self, transaction_hash: str) -> Optional[ConversionEvent]:
        """Get conversion event by transaction hash."""
        stmt = (
            select(ConversionEvent)
            .where(ConversionEvent.transaction_hash == transaction_hash)
            .options(joinedload(ConversionEvent.allocations))
        )
        return self.session.scalar(stmt)
    
    def get_by_block(self, block_number: int) -> Sequence[ConversionEvent]:
        """Get all conversion events for a block."""
        stmt = (
            select(ConversionEvent)
            .where(ConversionEvent.block_number == block_number)
            .order_by(ConversionEvent.id)
        )
        return self.session.scalars(stmt).all()
    
    def get_range(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: Optional[str] = None
    ) -> Sequence[ConversionEvent]:
        """Get conversion events in a block range."""
        conditions = [
            ConversionEvent.block_number >= start_block,
            ConversionEvent.block_number <= end_block,
        ]
        
        if validator_hotkey:
            conditions.append(ConversionEvent.validator_hotkey == validator_hotkey)
        
        stmt = (
            select(ConversionEvent)
            .where(and_(*conditions))
            .order_by(ConversionEvent.block_number)
        )
        return self.session.scalars(stmt).all()
    
    def get_unallocated(
        self,
        validator_hotkey: Optional[str] = None
    ) -> Sequence[ConversionEvent]:
        """Get conversion events that haven't been fully allocated."""
        conditions = [ConversionEvent.fully_allocated == False]
        
        if validator_hotkey:
            conditions.append(ConversionEvent.validator_hotkey == validator_hotkey)
        
        stmt = (
            select(ConversionEvent)
            .where(and_(*conditions))
            .order_by(ConversionEvent.block_number)
        )
        return self.session.scalars(stmt).all()
    
    def get_total_converted(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str
    ) -> tuple[Decimal, Decimal]:
        """Get total dTAO and TAO converted in a block range."""
        stmt = (
            select(
                func.sum(ConversionEvent.dtao_amount),
                func.sum(ConversionEvent.tao_amount)
            )
            .where(
                and_(
                    ConversionEvent.block_number >= start_block,
                    ConversionEvent.block_number <= end_block,
                    ConversionEvent.validator_hotkey == validator_hotkey
                )
            )
        )
        result = self.session.execute(stmt).one()
        return (result[0] or Decimal(0), result[1] or Decimal(0))
    
    def mark_allocated(self, conversion_id: str) -> None:
        """Mark a conversion event as fully allocated."""
        stmt = (
            update(ConversionEvent)
            .where(ConversionEvent.id == conversion_id)
            .values(fully_allocated=True)
        )
        self.session.execute(stmt)
        self.session.flush()
    
    def exists_for_tx(self, transaction_hash: str) -> bool:
        """Check if a conversion event exists for a transaction."""
        stmt = (
            select(func.count())
            .select_from(ConversionEvent)
            .where(ConversionEvent.transaction_hash == transaction_hash)
        )
        return (self.session.scalar(stmt) or 0) > 0


class TaoAllocationRepository(BaseRepository[TaoAllocation]):
    """Repository for TaoAllocation operations."""
    
    model = TaoAllocation
    
    def get_by_conversion(self, conversion_event_id: str) -> Sequence[TaoAllocation]:
        """Get all allocations for a conversion event."""
        stmt = (
            select(TaoAllocation)
            .where(TaoAllocation.conversion_event_id == conversion_event_id)
            .order_by(TaoAllocation.id)
        )
        return self.session.scalars(stmt).all()
    
    def get_by_attribution(self, block_attribution_id: str) -> Sequence[TaoAllocation]:
        """Get all allocations for a block attribution."""
        stmt = (
            select(TaoAllocation)
            .where(TaoAllocation.block_attribution_id == block_attribution_id)
            .order_by(TaoAllocation.created_at)
        )
        return self.session.scalars(stmt).all()
    
    def get_total_allocated_for_conversion(self, conversion_event_id: str) -> Decimal:
        """Get total TAO allocated for a conversion event."""
        stmt = (
            select(func.sum(TaoAllocation.tao_allocated))
            .where(TaoAllocation.conversion_event_id == conversion_event_id)
        )
        return self.session.scalar(stmt) or Decimal(0)
    
    def get_total_allocated_for_attribution(self, block_attribution_id: str) -> Decimal:
        """Get total TAO allocated for a block attribution."""
        stmt = (
            select(func.sum(TaoAllocation.tao_allocated))
            .where(TaoAllocation.block_attribution_id == block_attribution_id)
        )
        return self.session.scalar(stmt) or Decimal(0)
    
    def get_by_run(self, run_id: str) -> Sequence[TaoAllocation]:
        """Get all allocations created by a specific run."""
        stmt = (
            select(TaoAllocation)
            .where(TaoAllocation.run_id == run_id)
            .order_by(TaoAllocation.created_at)
        )
        return self.session.scalars(stmt).all()
    
    def get_allocations_with_incomplete_data(
        self,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None
    ) -> Sequence[TaoAllocation]:
        """Get allocations with incomplete completeness flags."""
        conditions = [
            TaoAllocation.completeness_flag.in_([
                CompletenessFlag.INCOMPLETE,
                CompletenessFlag.PARTIAL
            ])
        ]
        
        # Note: Would need to join with BlockAttribution for block filtering
        stmt = (
            select(TaoAllocation)
            .where(and_(*conditions))
            .order_by(TaoAllocation.created_at)
        )
        return self.session.scalars(stmt).all()
