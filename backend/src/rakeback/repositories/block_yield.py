"""Repository for BlockYield and YieldSource."""

from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import select, and_, func, delete
from sqlalchemy.orm import joinedload

from rakeback.models import BlockYield, YieldSource, CompletenessFlag, DataSource
from rakeback.repositories.base import BaseRepository


class BlockYieldRepository(BaseRepository[BlockYield]):
    """Repository for BlockYield operations."""
    
    model = BlockYield
    
    def get_by_block_and_validator(
        self,
        block_number: int,
        validator_hotkey: str
    ) -> Optional[BlockYield]:
        """Get yield for a specific block and validator."""
        stmt = (
            select(BlockYield)
            .where(
                and_(
                    BlockYield.block_number == block_number,
                    BlockYield.validator_hotkey == validator_hotkey
                )
            )
            .options(joinedload(BlockYield.yield_sources))
        )
        return self.session.scalar(stmt)
    
    def get_range(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str,
        include_sources: bool = False
    ) -> Sequence[BlockYield]:
        """Get yields for a block range."""
        stmt = (
            select(BlockYield)
            .where(
                and_(
                    BlockYield.block_number >= start_block,
                    BlockYield.block_number <= end_block,
                    BlockYield.validator_hotkey == validator_hotkey
                )
            )
            .order_by(BlockYield.block_number)
        )
        if include_sources:
            stmt = stmt.options(joinedload(BlockYield.yield_sources))
        return self.session.scalars(stmt).unique().all()
    
    def exists_for_block(self, block_number: int, validator_hotkey: str) -> bool:
        """Check if yield exists for block and validator."""
        stmt = (
            select(func.count())
            .select_from(BlockYield)
            .where(
                and_(
                    BlockYield.block_number == block_number,
                    BlockYield.validator_hotkey == validator_hotkey
                )
            )
        )
        return (self.session.scalar(stmt) or 0) > 0
    
    def find_missing_blocks(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str
    ) -> Sequence[int]:
        """Find block numbers without yields in range."""
        stmt = (
            select(BlockYield.block_number)
            .where(
                and_(
                    BlockYield.block_number >= start_block,
                    BlockYield.block_number <= end_block,
                    BlockYield.validator_hotkey == validator_hotkey
                )
            )
        )
        existing = set(self.session.scalars(stmt).all())
        all_blocks = set(range(start_block, end_block + 1))
        return sorted(all_blocks - existing)
    
    def get_total_yield(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str
    ) -> Decimal:
        """Get total dTAO earned in a block range."""
        stmt = (
            select(func.sum(BlockYield.total_dtao_earned))
            .where(
                and_(
                    BlockYield.block_number >= start_block,
                    BlockYield.block_number <= end_block,
                    BlockYield.validator_hotkey == validator_hotkey
                )
            )
        )
        return self.session.scalar(stmt) or Decimal(0)
    
    def get_yield_by_subnet(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str
    ) -> dict[int, Decimal]:
        """Get total yield by subnet in a block range."""
        stmt = (
            select(YieldSource.subnet_id, func.sum(YieldSource.dtao_amount))
            .join(BlockYield, and_(
                YieldSource.block_number == BlockYield.block_number,
                YieldSource.validator_hotkey == BlockYield.validator_hotkey
            ))
            .where(
                and_(
                    BlockYield.block_number >= start_block,
                    BlockYield.block_number <= end_block,
                    BlockYield.validator_hotkey == validator_hotkey
                )
            )
            .group_by(YieldSource.subnet_id)
        )
        results = self.session.execute(stmt).all()
        return {subnet_id: amount for subnet_id, amount in results}
    
    def create_yield(
        self,
        block_number: int,
        validator_hotkey: str,
        total_dtao_earned: Decimal,
        yield_sources: Optional[list[dict]] = None,
        data_source: DataSource = DataSource.CHAIN,
        completeness_flag: CompletenessFlag = CompletenessFlag.COMPLETE
    ) -> BlockYield:
        """Create a new block yield with optional source breakdown."""
        block_yield = BlockYield(
            block_number=block_number,
            validator_hotkey=validator_hotkey,
            total_dtao_earned=total_dtao_earned,
            data_source=data_source,
            completeness_flag=completeness_flag,
        )
        
        if yield_sources:
            for source in yield_sources:
                ys = YieldSource(
                    block_number=block_number,
                    validator_hotkey=validator_hotkey,
                    subnet_id=source["subnet_id"],
                    dtao_amount=Decimal(source["dtao_amount"]),
                )
                block_yield.yield_sources.append(ys)
        
        self.session.add(block_yield)
        self.session.flush()
        return block_yield
    
    def delete_range(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str
    ) -> int:
        """Delete yields in a block range. Returns count deleted."""
        stmt = (
            delete(BlockYield)
            .where(
                and_(
                    BlockYield.block_number >= start_block,
                    BlockYield.block_number <= end_block,
                    BlockYield.validator_hotkey == validator_hotkey
                )
            )
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount
