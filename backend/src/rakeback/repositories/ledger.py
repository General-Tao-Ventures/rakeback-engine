"""Repository for RakebackLedgerEntry."""

from datetime import date
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import select, and_, func, update

from rakeback.models import RakebackLedgerEntry, CompletenessFlag, PaymentStatus, PeriodType
from rakeback.repositories.base import BaseRepository


class RakebackLedgerRepository(BaseRepository[RakebackLedgerEntry]):
    """Repository for RakebackLedgerEntry operations."""
    
    model = RakebackLedgerEntry
    
    def get_by_period_and_participant(
        self,
        period_type: PeriodType,
        period_start: date,
        participant_id: str,
        validator_hotkey: str
    ) -> Optional[RakebackLedgerEntry]:
        """Get ledger entry for a specific period and participant."""
        stmt = (
            select(RakebackLedgerEntry)
            .where(
                and_(
                    RakebackLedgerEntry.period_type == period_type,
                    RakebackLedgerEntry.period_start == period_start,
                    RakebackLedgerEntry.participant_id == participant_id,
                    RakebackLedgerEntry.validator_hotkey == validator_hotkey
                )
            )
        )
        return self.session.scalar(stmt)
    
    def get_by_period(
        self,
        period_type: PeriodType,
        period_start: date,
        period_end: date,
        validator_hotkey: Optional[str] = None
    ) -> Sequence[RakebackLedgerEntry]:
        """Get all ledger entries for a period."""
        conditions = [
            RakebackLedgerEntry.period_type == period_type,
            RakebackLedgerEntry.period_start >= period_start,
            RakebackLedgerEntry.period_end <= period_end,
        ]
        
        if validator_hotkey:
            conditions.append(RakebackLedgerEntry.validator_hotkey == validator_hotkey)
        
        stmt = (
            select(RakebackLedgerEntry)
            .where(and_(*conditions))
            .order_by(RakebackLedgerEntry.participant_id)
        )
        return self.session.scalars(stmt).all()
    
    def get_by_participant(
        self,
        participant_id: str,
        period_type: Optional[PeriodType] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Sequence[RakebackLedgerEntry]:
        """Get ledger entries for a participant."""
        conditions = [RakebackLedgerEntry.participant_id == participant_id]
        
        if period_type:
            conditions.append(RakebackLedgerEntry.period_type == period_type)
        if start_date:
            conditions.append(RakebackLedgerEntry.period_start >= start_date)
        if end_date:
            conditions.append(RakebackLedgerEntry.period_end <= end_date)
        
        stmt = (
            select(RakebackLedgerEntry)
            .where(and_(*conditions))
            .order_by(RakebackLedgerEntry.period_start.desc())
        )
        return self.session.scalars(stmt).all()
    
    def get_unpaid(
        self,
        participant_id: Optional[str] = None,
        validator_hotkey: Optional[str] = None
    ) -> Sequence[RakebackLedgerEntry]:
        """Get unpaid ledger entries."""
        conditions = [RakebackLedgerEntry.payment_status == PaymentStatus.UNPAID]
        
        if participant_id:
            conditions.append(RakebackLedgerEntry.participant_id == participant_id)
        if validator_hotkey:
            conditions.append(RakebackLedgerEntry.validator_hotkey == validator_hotkey)
        
        stmt = (
            select(RakebackLedgerEntry)
            .where(and_(*conditions))
            .order_by(RakebackLedgerEntry.period_start)
        )
        return self.session.scalars(stmt).all()
    
    def get_total_owed(
        self,
        participant_id: Optional[str] = None,
        validator_hotkey: Optional[str] = None,
        unpaid_only: bool = True
    ) -> Decimal:
        """Get total TAO owed."""
        conditions = []
        
        if unpaid_only:
            conditions.append(RakebackLedgerEntry.payment_status == PaymentStatus.UNPAID)
        if participant_id:
            conditions.append(RakebackLedgerEntry.participant_id == participant_id)
        if validator_hotkey:
            conditions.append(RakebackLedgerEntry.validator_hotkey == validator_hotkey)
        
        stmt = select(func.sum(RakebackLedgerEntry.tao_owed))
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        return self.session.scalar(stmt) or Decimal(0)
    
    def mark_paid(
        self,
        entry_ids: Sequence[str],
        payment_tx_hash: str,
        payment_timestamp: date
    ) -> int:
        """Mark entries as paid. Returns count updated."""
        stmt = (
            update(RakebackLedgerEntry)
            .where(RakebackLedgerEntry.id.in_(entry_ids))
            .values(
                payment_status=PaymentStatus.PAID,
                payment_tx_hash=payment_tx_hash,
                payment_timestamp=payment_timestamp
            )
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount
    
    def get_incomplete(
        self,
        period_type: Optional[PeriodType] = None
    ) -> Sequence[RakebackLedgerEntry]:
        """Get entries with incomplete data flags."""
        conditions = [
            RakebackLedgerEntry.completeness_flag.in_([
                CompletenessFlag.INCOMPLETE,
                CompletenessFlag.PARTIAL
            ])
        ]
        
        if period_type:
            conditions.append(RakebackLedgerEntry.period_type == period_type)
        
        stmt = (
            select(RakebackLedgerEntry)
            .where(and_(*conditions))
            .order_by(RakebackLedgerEntry.period_start.desc())
        )
        return self.session.scalars(stmt).all()
    
    def get_by_run(self, run_id: str) -> Sequence[RakebackLedgerEntry]:
        """Get all entries created by a specific run."""
        stmt = (
            select(RakebackLedgerEntry)
            .where(RakebackLedgerEntry.run_id == run_id)
            .order_by(RakebackLedgerEntry.period_start)
        )
        return self.session.scalars(stmt).all()
    
    def count_by_status(
        self,
        period_type: Optional[PeriodType] = None
    ) -> dict[PaymentStatus, int]:
        """Count entries by payment status."""
        conditions = []
        if period_type:
            conditions.append(RakebackLedgerEntry.period_type == period_type)
        
        stmt = (
            select(RakebackLedgerEntry.payment_status, func.count())
            .group_by(RakebackLedgerEntry.payment_status)
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        results = self.session.execute(stmt).all()
        return {status: count for status, count in results}
