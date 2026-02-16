"""Repositories for ProcessingRun and DataGap."""

from datetime import date, datetime
from typing import Optional, Sequence

from sqlalchemy import select, and_, update

from rakeback.models import ProcessingRun, DataGap, RunType, RunStatus, GapType, ResolutionStatus
from rakeback.repositories.base import BaseRepository


class ProcessingRunRepository(BaseRepository[ProcessingRun]):
    """Repository for ProcessingRun operations."""
    
    model = ProcessingRun
    
    def get_by_id(self, run_id: str) -> Optional[ProcessingRun]:
        """Get processing run by ID."""
        return self.session.get(ProcessingRun, run_id)
    
    def get_latest(
        self,
        run_type: Optional[RunType] = None,
        validator_hotkey: Optional[str] = None,
        status: Optional[RunStatus] = None
    ) -> Optional[ProcessingRun]:
        """Get the most recent processing run."""
        conditions = []
        
        if run_type:
            conditions.append(ProcessingRun.run_type == run_type)
        if validator_hotkey:
            conditions.append(ProcessingRun.validator_hotkey == validator_hotkey)
        if status:
            conditions.append(ProcessingRun.status == status)
        
        stmt = (
            select(ProcessingRun)
            .order_by(ProcessingRun.started_at.desc())
            .limit(1)
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        return self.session.scalar(stmt)
    
    def get_by_type(
        self,
        run_type: RunType,
        limit: int = 100
    ) -> Sequence[ProcessingRun]:
        """Get processing runs by type."""
        stmt = (
            select(ProcessingRun)
            .where(ProcessingRun.run_type == run_type)
            .order_by(ProcessingRun.started_at.desc())
            .limit(limit)
        )
        return self.session.scalars(stmt).all()
    
    def get_running(self) -> Sequence[ProcessingRun]:
        """Get all currently running processes."""
        stmt = (
            select(ProcessingRun)
            .where(ProcessingRun.status == RunStatus.RUNNING)
            .order_by(ProcessingRun.started_at)
        )
        return self.session.scalars(stmt).all()
    
    def get_failed(
        self,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> Sequence[ProcessingRun]:
        """Get failed processing runs."""
        conditions = [ProcessingRun.status == RunStatus.FAILED]
        
        if since:
            conditions.append(ProcessingRun.started_at >= since)
        
        stmt = (
            select(ProcessingRun)
            .where(and_(*conditions))
            .order_by(ProcessingRun.started_at.desc())
            .limit(limit)
        )
        return self.session.scalars(stmt).all()
    
    def get_by_block_range(
        self,
        start_block: int,
        end_block: int,
        run_type: Optional[RunType] = None
    ) -> Sequence[ProcessingRun]:
        """Get runs that processed a specific block range."""
        conditions = [
            ProcessingRun.block_range_start <= end_block,
            ProcessingRun.block_range_end >= start_block,
        ]
        
        if run_type:
            conditions.append(ProcessingRun.run_type == run_type)
        
        stmt = (
            select(ProcessingRun)
            .where(and_(*conditions))
            .order_by(ProcessingRun.started_at.desc())
        )
        return self.session.scalars(stmt).all()
    
    def create_run(
        self,
        run_type: RunType,
        validator_hotkey: Optional[str] = None,
        block_range: Optional[tuple[int, int]] = None,
        period: Optional[tuple[date, date]] = None,
        config_snapshot: Optional[dict] = None
    ) -> ProcessingRun:
        """Create a new processing run."""
        run = ProcessingRun(
            run_type=run_type,
            validator_hotkey=validator_hotkey,
            config_snapshot=config_snapshot,
        )
        
        if block_range:
            run.block_range_start = block_range[0]
            run.block_range_end = block_range[1]
        
        if period:
            run.period_start = period[0]
            run.period_end = period[1]
        
        self.session.add(run)
        self.session.flush()
        return run


class DataGapRepository(BaseRepository[DataGap]):
    """Repository for DataGap operations."""
    
    model = DataGap
    
    def get_open(
        self,
        gap_type: Optional[GapType] = None,
        validator_hotkey: Optional[str] = None
    ) -> Sequence[DataGap]:
        """Get open (unresolved) data gaps."""
        conditions = [DataGap.resolution_status == ResolutionStatus.OPEN]
        
        if gap_type:
            conditions.append(DataGap.gap_type == gap_type)
        if validator_hotkey:
            conditions.append(DataGap.validator_hotkey == validator_hotkey)
        
        stmt = (
            select(DataGap)
            .where(and_(*conditions))
            .order_by(DataGap.block_start)
        )
        return self.session.scalars(stmt).all()
    
    def get_by_block_range(
        self,
        start_block: int,
        end_block: int,
        gap_type: Optional[GapType] = None
    ) -> Sequence[DataGap]:
        """Get gaps overlapping a block range."""
        conditions = [
            DataGap.block_start <= end_block,
            DataGap.block_end >= start_block,
        ]
        
        if gap_type:
            conditions.append(DataGap.gap_type == gap_type)
        
        stmt = (
            select(DataGap)
            .where(and_(*conditions))
            .order_by(DataGap.block_start)
        )
        return self.session.scalars(stmt).all()
    
    def create_gap(
        self,
        gap_type: GapType,
        block_start: int,
        block_end: int,
        reason: str,
        validator_hotkey: Optional[str] = None,
        detected_by_run_id: Optional[str] = None
    ) -> DataGap:
        """Create a new data gap record."""
        gap = DataGap(
            gap_type=gap_type,
            block_start=block_start,
            block_end=block_end,
            reason=reason,
            validator_hotkey=validator_hotkey,
            detected_by_run_id=detected_by_run_id,
        )
        self.session.add(gap)
        self.session.flush()
        return gap
    
    def mark_resolved(
        self,
        gap_id: str,
        status: ResolutionStatus,
        run_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """Mark a gap as resolved."""
        gap = self.get_by_id(gap_id)
        if not gap:
            return False
        
        gap.mark_resolved(status, run_id, notes)
        self.session.flush()
        return True
    
    def merge_overlapping(
        self,
        gap_type: GapType,
        validator_hotkey: Optional[str] = None
    ) -> int:
        """
        Merge overlapping or adjacent gaps of the same type.
        Returns count of gaps after merging.
        """
        # Get all open gaps of this type
        gaps = list(self.get_open(gap_type, validator_hotkey))
        if len(gaps) <= 1:
            return len(gaps)
        
        # Sort by start block
        gaps.sort(key=lambda g: g.block_start)
        
        merged = []
        current = gaps[0]
        
        for gap in gaps[1:]:
            # If overlapping or adjacent
            if gap.block_start <= current.block_end + 1:
                # Extend current gap
                current.block_end = max(current.block_end, gap.block_end)
                current.reason = f"{current.reason}; {gap.reason}"
                # Delete the merged gap
                self.session.delete(gap)
            else:
                merged.append(current)
                current = gap
        
        merged.append(current)
        self.session.flush()
        return len(merged)
    
    def has_gaps_in_range(
        self,
        start_block: int,
        end_block: int,
        gap_type: Optional[GapType] = None,
        validator_hotkey: Optional[str] = None
    ) -> bool:
        """Check if there are any open gaps in a block range."""
        gaps = self.get_by_block_range(start_block, end_block, gap_type)
        
        for gap in gaps:
            if gap.resolution_status == ResolutionStatus.OPEN:
                if validator_hotkey is None or gap.validator_hotkey == validator_hotkey:
                    return True
        
        return False
