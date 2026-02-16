"""Repository for BlockSnapshot and DelegationEntry."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import select, and_, func, delete
from sqlalchemy.orm import Session, joinedload

from rakeback.models import BlockSnapshot, DelegationEntry, CompletenessFlag, DataSource, DelegationType
from rakeback.repositories.base import BaseRepository


class BlockSnapshotRepository(BaseRepository[BlockSnapshot]):
    """Repository for BlockSnapshot operations."""
    
    model = BlockSnapshot
    
    def get_by_block_and_validator(
        self,
        block_number: int,
        validator_hotkey: str
    ) -> Optional[BlockSnapshot]:
        """Get snapshot for a specific block and validator."""
        stmt = (
            select(BlockSnapshot)
            .where(
                and_(
                    BlockSnapshot.block_number == block_number,
                    BlockSnapshot.validator_hotkey == validator_hotkey
                )
            )
            .options(joinedload(BlockSnapshot.delegations))
        )
        return self.session.scalar(stmt)
    
    def get_range(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str,
        include_delegations: bool = False
    ) -> Sequence[BlockSnapshot]:
        """Get snapshots for a block range."""
        stmt = (
            select(BlockSnapshot)
            .where(
                and_(
                    BlockSnapshot.block_number >= start_block,
                    BlockSnapshot.block_number <= end_block,
                    BlockSnapshot.validator_hotkey == validator_hotkey
                )
            )
            .order_by(BlockSnapshot.block_number)
        )
        if include_delegations:
            stmt = stmt.options(joinedload(BlockSnapshot.delegations))
        return self.session.scalars(stmt).unique().all()
    
    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        validator_hotkey: str
    ) -> Sequence[BlockSnapshot]:
        """Get snapshots within a date range."""
        stmt = (
            select(BlockSnapshot)
            .where(
                and_(
                    BlockSnapshot.timestamp >= start_date,
                    BlockSnapshot.timestamp < end_date,
                    BlockSnapshot.validator_hotkey == validator_hotkey
                )
            )
            .order_by(BlockSnapshot.block_number)
        )
        return self.session.scalars(stmt).all()
    
    def exists_for_block(self, block_number: int, validator_hotkey: str) -> bool:
        """Check if snapshot exists for block and validator."""
        stmt = (
            select(func.count())
            .select_from(BlockSnapshot)
            .where(
                and_(
                    BlockSnapshot.block_number == block_number,
                    BlockSnapshot.validator_hotkey == validator_hotkey
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
        """Find block numbers without snapshots in range."""
        # Get all existing block numbers
        stmt = (
            select(BlockSnapshot.block_number)
            .where(
                and_(
                    BlockSnapshot.block_number >= start_block,
                    BlockSnapshot.block_number <= end_block,
                    BlockSnapshot.validator_hotkey == validator_hotkey
                )
            )
        )
        existing = set(self.session.scalars(stmt).all())
        
        # Find missing
        all_blocks = set(range(start_block, end_block + 1))
        return sorted(all_blocks - existing)
    
    def get_latest_block(self, validator_hotkey: str) -> Optional[int]:
        """Get the latest block number for a validator."""
        stmt = (
            select(func.max(BlockSnapshot.block_number))
            .where(BlockSnapshot.validator_hotkey == validator_hotkey)
        )
        return self.session.scalar(stmt)
    
    def count_by_completeness(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str
    ) -> dict[CompletenessFlag, int]:
        """Count snapshots by completeness flag."""
        stmt = (
            select(BlockSnapshot.completeness_flag, func.count())
            .where(
                and_(
                    BlockSnapshot.block_number >= start_block,
                    BlockSnapshot.block_number <= end_block,
                    BlockSnapshot.validator_hotkey == validator_hotkey
                )
            )
            .group_by(BlockSnapshot.completeness_flag)
        )
        results = self.session.execute(stmt).all()
        return {flag: count for flag, count in results}
    
    def create_snapshot(
        self,
        block_number: int,
        validator_hotkey: str,
        block_hash: str,
        timestamp: datetime,
        delegations: list[dict],
        data_source: DataSource = DataSource.CHAIN,
        completeness_flag: CompletenessFlag = CompletenessFlag.COMPLETE
    ) -> BlockSnapshot:
        """Create a new block snapshot with delegations."""
        # Calculate total stake and proportions
        total_stake = sum(Decimal(d.get("balance_dtao", 0)) for d in delegations)
        
        snapshot = BlockSnapshot(
            block_number=block_number,
            validator_hotkey=validator_hotkey,
            block_hash=block_hash,
            timestamp=timestamp,
            data_source=data_source,
            completeness_flag=completeness_flag,
            total_stake=total_stake,
        )
        
        # Create delegation entries with calculated proportions
        for d in delegations:
            balance = Decimal(d.get("balance_dtao", 0))
            proportion = balance / total_stake if total_stake > 0 else Decimal(0)
            
            entry = DelegationEntry(
                block_number=block_number,
                validator_hotkey=validator_hotkey,
                delegator_address=d["delegator_address"],
                delegation_type=DelegationType(d["delegation_type"]),
                subnet_id=d.get("subnet_id"),
                balance_dtao=balance,
                balance_tao=d.get("balance_tao"),
                proportion=proportion,
            )
            snapshot.delegations.append(entry)
        
        self.session.add(snapshot)
        self.session.flush()
        return snapshot
    
    def delete_range(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str
    ) -> int:
        """Delete snapshots in a block range. Returns count deleted."""
        # Delegations cascade delete
        stmt = (
            delete(BlockSnapshot)
            .where(
                and_(
                    BlockSnapshot.block_number >= start_block,
                    BlockSnapshot.block_number <= end_block,
                    BlockSnapshot.validator_hotkey == validator_hotkey
                )
            )
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount
