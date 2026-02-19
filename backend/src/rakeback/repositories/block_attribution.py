"""Repository for BlockAttribution."""

from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import select, and_, func, update
from sqlalchemy.orm import Session

from rakeback.models import BlockAttribution, CompletenessFlag, DelegationType
from rakeback.repositories.base import BaseRepository


class BlockAttributionRepository(BaseRepository[BlockAttribution]):
    """Repository for BlockAttribution operations."""
    
    model = BlockAttribution
    
    def get_by_block_and_delegator(
        self,
        block_number: int,
        validator_hotkey: str,
        delegator_address: str
    ) -> Optional[BlockAttribution]:
        """Get attribution for a specific block, validator, and delegator."""
        stmt = (
            select(BlockAttribution)
            .where(
                and_(
                    BlockAttribution.block_number == block_number,
                    BlockAttribution.validator_hotkey == validator_hotkey,
                    BlockAttribution.delegator_address == delegator_address
                )
            )
        )
        return self.session.scalar(stmt)
    
    def get_by_block(
        self,
        block_number: int,
        validator_hotkey: Optional[str] = None
    ) -> Sequence[BlockAttribution]:
        """Get all attributions for a block."""
        conditions = [BlockAttribution.block_number == block_number]
        if validator_hotkey is not None:
            conditions.append(BlockAttribution.validator_hotkey == validator_hotkey)

        stmt = (
            select(BlockAttribution)
            .where(and_(*conditions))
            .order_by(BlockAttribution.delegator_address)
        )
        return self.session.scalars(stmt).all()
    
    def get_range(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: Optional[str] = None
    ) -> Sequence[BlockAttribution]:
        """Get attributions for a block range."""
        conditions = [
            BlockAttribution.block_number >= start_block,
            BlockAttribution.block_number <= end_block,
        ]
        if validator_hotkey is not None:
            conditions.append(BlockAttribution.validator_hotkey == validator_hotkey)

        stmt = (
            select(BlockAttribution)
            .where(and_(*conditions))
            .order_by(BlockAttribution.block_number, BlockAttribution.delegator_address)
        )
        return self.session.scalars(stmt).all()
    
    def get_by_delegator(
        self,
        delegator_address: str,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None,
        validator_hotkey: Optional[str] = None
    ) -> Sequence[BlockAttribution]:
        """Get attributions for a specific delegator."""
        conditions = [BlockAttribution.delegator_address == delegator_address]
        
        if start_block is not None:
            conditions.append(BlockAttribution.block_number >= start_block)
        if end_block is not None:
            conditions.append(BlockAttribution.block_number <= end_block)
        if validator_hotkey is not None:
            conditions.append(BlockAttribution.validator_hotkey == validator_hotkey)
        
        stmt = (
            select(BlockAttribution)
            .where(and_(*conditions))
            .order_by(BlockAttribution.block_number)
        )
        return self.session.scalars(stmt).all()
    
    def get_unallocated(
        self,
        validator_hotkey: str,
        subnet_id: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Sequence[BlockAttribution]:
        """Get attributions that haven't been fully allocated TAO."""
        conditions = [
            BlockAttribution.validator_hotkey == validator_hotkey,
            BlockAttribution.fully_allocated == False,
        ]
        
        if subnet_id is not None:
            conditions.append(BlockAttribution.subnet_id == subnet_id)
        
        stmt = (
            select(BlockAttribution)
            .where(and_(*conditions))
            .order_by(BlockAttribution.block_number)  # FIFO ordering
        )
        
        if limit:
            stmt = stmt.limit(limit)
        
        return self.session.scalars(stmt).all()
    
    def get_total_attributed(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str,
        delegator_address: Optional[str] = None
    ) -> Decimal:
        """Get total attributed dTAO in a block range."""
        conditions = [
            BlockAttribution.block_number >= start_block,
            BlockAttribution.block_number <= end_block,
            BlockAttribution.validator_hotkey == validator_hotkey,
        ]
        
        if delegator_address:
            conditions.append(BlockAttribution.delegator_address == delegator_address)
        
        stmt = (
            select(func.sum(BlockAttribution.attributed_dtao))
            .where(and_(*conditions))
        )
        return self.session.scalar(stmt) or Decimal(0)
    
    def get_attributed_by_delegator(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str
    ) -> dict[str, Decimal]:
        """Get total attributed dTAO per delegator in a block range."""
        stmt = (
            select(
                BlockAttribution.delegator_address,
                func.sum(BlockAttribution.attributed_dtao)
            )
            .where(
                and_(
                    BlockAttribution.block_number >= start_block,
                    BlockAttribution.block_number <= end_block,
                    BlockAttribution.validator_hotkey == validator_hotkey
                )
            )
            .group_by(BlockAttribution.delegator_address)
        )
        results = self.session.execute(stmt).all()
        return {delegator: amount for delegator, amount in results}
    
    def exists_for_block(
        self,
        block_number: int,
        validator_hotkey: str
    ) -> bool:
        """Check if attributions exist for a block."""
        stmt = (
            select(func.count())
            .select_from(BlockAttribution)
            .where(
                and_(
                    BlockAttribution.block_number == block_number,
                    BlockAttribution.validator_hotkey == validator_hotkey
                )
            )
        )
        return (self.session.scalar(stmt) or 0) > 0
    
    def get_by_run(self, run_id: str) -> Sequence[BlockAttribution]:
        """Get all attributions created by a specific run."""
        stmt = (
            select(BlockAttribution)
            .where(BlockAttribution.run_id == run_id)
            .order_by(BlockAttribution.block_number)
        )
        return self.session.scalars(stmt).all()
    
    def update_allocation(
        self,
        attribution_id: str,
        tao_allocated: Decimal,
        fully_allocated: bool
    ) -> None:
        """Update allocation status for an attribution."""
        stmt = (
            update(BlockAttribution)
            .where(BlockAttribution.id == attribution_id)
            .values(
                tao_allocated=BlockAttribution.tao_allocated + tao_allocated,
                fully_allocated=fully_allocated
            )
        )
        self.session.execute(stmt)
        self.session.flush()
    
    def count_by_completeness(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str
    ) -> dict[CompletenessFlag, int]:
        """Count attributions by completeness flag."""
        stmt = (
            select(BlockAttribution.completeness_flag, func.count())
            .where(
                and_(
                    BlockAttribution.block_number >= start_block,
                    BlockAttribution.block_number <= end_block,
                    BlockAttribution.validator_hotkey == validator_hotkey
                )
            )
            .group_by(BlockAttribution.completeness_flag)
        )
        results = self.session.execute(stmt).all()
        return {flag: count for flag, count in results}
    
    def find_missing_blocks(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str
    ) -> Sequence[int]:
        """Find block numbers without attributions in range."""
        stmt = (
            select(BlockAttribution.block_number)
            .where(
                and_(
                    BlockAttribution.block_number >= start_block,
                    BlockAttribution.block_number <= end_block,
                    BlockAttribution.validator_hotkey == validator_hotkey
                )
            )
            .distinct()
        )
        existing = set(self.session.scalars(stmt).all())
        all_blocks = set(range(start_block, end_block + 1))
        return sorted(all_blocks - existing)
