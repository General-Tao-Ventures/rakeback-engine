"""Aggregation service for daily/monthly rakeback calculations."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, Sequence

import structlog
from sqlalchemy.orm import Session

from rakeback.models import (
    RakebackLedgerEntry,
    RakebackParticipant,
    CompletenessFlag,
    PaymentStatus,
    PeriodType,
    ParticipantType,
    RunType,
    RunStatus,
)
from rakeback.repositories import (
    BlockSnapshotRepository,
    BlockAttributionRepository,
    ConversionEventRepository,
    TaoAllocationRepository,
    RakebackLedgerRepository,
    ParticipantRepository,
    ProcessingRunRepository,
    DataGapRepository,
)
from rakeback.services.rules_engine import RulesEngine

logger = structlog.get_logger(__name__)


class AggregationError(Exception):
    """Base exception for aggregation errors."""
    pass


class IncompleteDataError(AggregationError):
    """Required data is incomplete."""
    pass


class NoParticipantsError(AggregationError):
    """No active rakeback participants found."""
    pass


@dataclass
class AggregationResult:
    """Result of an aggregation run."""
    run_id: str
    period_type: PeriodType
    period_start: date
    period_end: date
    entries_created: int
    total_tao_owed: Decimal
    completeness_summary: dict
    warnings: list[str]


class AggregationService:
    """
    Service for aggregating attributions into rakeback ledger entries.
    
    This service:
    1. Collects attributions for a period (daily/monthly)
    2. Matches attributions to rakeback participants
    3. Applies rakeback percentages
    4. Creates ledger entries with TAO obligations
    """
    
    def __init__(self, session: Session, rules_engine: Optional[RulesEngine] = None):
        """Initialize the aggregation service."""
        self.session = session
        self.rules_engine = rules_engine or RulesEngine(session)
        
        # Repositories
        self.snapshot_repo = BlockSnapshotRepository(session)
        self.attribution_repo = BlockAttributionRepository(session)
        self.conversion_repo = ConversionEventRepository(session)
        self.allocation_repo = TaoAllocationRepository(session)
        self.ledger_repo = RakebackLedgerRepository(session)
        self.participant_repo = ParticipantRepository(session)
        self.run_repo = ProcessingRunRepository(session)
        self.gap_repo = DataGapRepository(session)
    
    def aggregate_daily(
        self,
        target_date: date,
        validator_hotkey: str,
        fail_on_incomplete: bool = False
    ) -> AggregationResult:
        """
        Aggregate attributions for a single day.
        
        Args:
            target_date: The date to aggregate
            validator_hotkey: Validator to aggregate for
            fail_on_incomplete: Raise exception if data is incomplete
            
        Returns:
            AggregationResult with created ledger entries
        """
        return self._aggregate_period(
            period_type=PeriodType.DAILY,
            period_start=target_date,
            period_end=target_date,
            validator_hotkey=validator_hotkey,
            fail_on_incomplete=fail_on_incomplete
        )
    
    def aggregate_monthly(
        self,
        year: int,
        month: int,
        validator_hotkey: str,
        fail_on_incomplete: bool = False
    ) -> AggregationResult:
        """
        Aggregate attributions for a month.
        
        Args:
            year: Year (e.g., 2026)
            month: Month (1-12)
            validator_hotkey: Validator to aggregate for
            fail_on_incomplete: Raise exception if data is incomplete
            
        Returns:
            AggregationResult with created ledger entries
        """
        # Calculate month boundaries
        period_start = date(year, month, 1)
        
        if month == 12:
            period_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = date(year, month + 1, 1) - timedelta(days=1)
        
        return self._aggregate_period(
            period_type=PeriodType.MONTHLY,
            period_start=period_start,
            period_end=period_end,
            validator_hotkey=validator_hotkey,
            fail_on_incomplete=fail_on_incomplete
        )
    
    def _aggregate_period(
        self,
        period_type: PeriodType,
        period_start: date,
        period_end: date,
        validator_hotkey: str,
        fail_on_incomplete: bool
    ) -> AggregationResult:
        """
        Core aggregation logic for any period type.
        """
        # Create processing run
        run = self.run_repo.create_run(
            run_type=RunType.AGGREGATION,
            validator_hotkey=validator_hotkey,
            period=(period_start, period_end)
        )
        
        logger.info(
            "Starting aggregation",
            run_id=run.run_id,
            period_type=period_type.value,
            period_start=str(period_start),
            period_end=str(period_end),
            validator_hotkey=validator_hotkey
        )
        
        warnings = []
        entries_created = 0
        total_tao_owed = Decimal(0)
        completeness_summary = {
            "complete_entries": 0,
            "incomplete_entries": 0,
            "incomplete_blocks": [],
            "missing_conversions": False
        }
        
        try:
            # Get active participants for this period
            participants = self.participant_repo.get_active(period_start)
            
            if not participants:
                warnings.append("No active rakeback participants found")
                run.mark_completed(RunStatus.SUCCESS)
                self.session.flush()
                
                return AggregationResult(
                    run_id=run.run_id,
                    period_type=period_type,
                    period_start=period_start,
                    period_end=period_end,
                    entries_created=0,
                    total_tao_owed=Decimal(0),
                    completeness_summary=completeness_summary,
                    warnings=warnings
                )
            
            # Get block range for period
            start_datetime = datetime.combine(period_start, datetime.min.time())
            end_datetime = datetime.combine(period_end + timedelta(days=1), datetime.min.time())
            
            snapshots = self.snapshot_repo.get_by_date_range(
                start_datetime, end_datetime, validator_hotkey
            )
            
            if not snapshots:
                warnings.append("No snapshots found for period")
                if fail_on_incomplete:
                    raise IncompleteDataError("No snapshots for period")
            
            block_range = (
                min(s.block_number for s in snapshots) if snapshots else 0,
                max(s.block_number for s in snapshots) if snapshots else 0
            )
            
            # Check for gaps in the period
            if block_range[0] > 0:
                gaps = self.gap_repo.has_gaps_in_range(
                    block_range[0], block_range[1], validator_hotkey=validator_hotkey
                )
                if gaps:
                    warnings.append("Data gaps detected in period")
                    completeness_summary["has_gaps"] = True
            
            # Get attributions by delegator
            attributions_by_delegator = self.attribution_repo.get_attributed_by_delegator(
                block_range[0], block_range[1], validator_hotkey
            ) if block_range[0] > 0 else {}
            
            # Get TAO allocations for the period
            total_tao_converted = self._get_period_tao_converted(
                block_range[0], block_range[1], validator_hotkey
            )
            
            # Process each participant
            for participant in participants:
                entry = self._create_ledger_entry(
                    participant=participant,
                    period_type=period_type,
                    period_start=period_start,
                    period_end=period_end,
                    validator_hotkey=validator_hotkey,
                    block_range=block_range,
                    attributions_by_delegator=attributions_by_delegator,
                    total_tao_converted=total_tao_converted,
                    run_id=run.run_id
                )
                
                if entry:
                    self.ledger_repo.add(entry)
                    entries_created += 1
                    total_tao_owed += entry.tao_owed
                    
                    if entry.completeness_flag == CompletenessFlag.COMPLETE:
                        completeness_summary["complete_entries"] += 1
                    else:
                        completeness_summary["incomplete_entries"] += 1
            
            run.records_created = entries_created
            run.completeness_summary = completeness_summary
            run.mark_completed(RunStatus.SUCCESS if not warnings else RunStatus.PARTIAL)
            
        except Exception as e:
            logger.exception("Aggregation failed")
            warnings.append(str(e))
            run.mark_failed(e)
            
            if fail_on_incomplete:
                raise
        
        self.session.flush()
        
        logger.info(
            "Completed aggregation",
            run_id=run.run_id,
            entries_created=entries_created,
            total_tao_owed=str(total_tao_owed)
        )
        
        return AggregationResult(
            run_id=run.run_id,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            entries_created=entries_created,
            total_tao_owed=total_tao_owed,
            completeness_summary=completeness_summary,
            warnings=warnings
        )
    
    def _create_ledger_entry(
        self,
        participant: RakebackParticipant,
        period_type: PeriodType,
        period_start: date,
        period_end: date,
        validator_hotkey: str,
        block_range: tuple[int, int],
        attributions_by_delegator: dict[str, Decimal],
        total_tao_converted: Decimal,
        run_id: str
    ) -> Optional[RakebackLedgerEntry]:
        """
        Create a ledger entry for a participant.
        """
        # Match participant's delegators to attributions
        matched_addresses = self.rules_engine.match_addresses(
            participant,
            list(attributions_by_delegator.keys())
        )
        
        if not matched_addresses:
            logger.debug(
                "No matching addresses for participant",
                participant_id=participant.id
            )
            return None
        
        # Sum attributed dTAO for matched addresses
        gross_dtao = sum(
            attributions_by_delegator.get(addr, Decimal(0))
            for addr in matched_addresses
        )
        
        if gross_dtao == 0:
            return None
        
        # Calculate TAO portion
        # For now, use a simple pro-rata of total converted TAO
        # based on this participant's share of total dTAO
        total_dtao = sum(attributions_by_delegator.values())
        
        if total_dtao > 0 and total_tao_converted > 0:
            dtao_share = gross_dtao / total_dtao
            gross_tao = (total_tao_converted * dtao_share).quantize(Decimal('1'))
        else:
            gross_tao = Decimal(0)
        
        # Apply rakeback percentage
        tao_owed = (gross_tao * participant.rakeback_percentage).quantize(Decimal('1'))
        
        # Determine completeness
        completeness_flag = CompletenessFlag.COMPLETE
        completeness_details = {}
        
        # Check if we have full conversion data
        if gross_dtao > 0 and gross_tao == 0:
            completeness_flag = CompletenessFlag.INCOMPLETE
            completeness_details["reason"] = "No TAO conversion data available"
        
        # Create entry
        entry = RakebackLedgerEntry(
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            participant_id=participant.id,
            participant_type=participant.type,
            validator_hotkey=validator_hotkey,
            gross_dtao_attributed=gross_dtao,
            gross_tao_converted=gross_tao,
            rakeback_percentage=participant.rakeback_percentage,
            tao_owed=tao_owed,
            payment_status=PaymentStatus.UNPAID,
            completeness_flag=completeness_flag,
            completeness_details=completeness_details if completeness_details else None,
            run_id=run_id,
            block_count=block_range[1] - block_range[0] + 1 if block_range[0] > 0 else 0,
            attribution_count=len(matched_addresses)
        )
        
        return entry
    
    def _get_period_tao_converted(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str
    ) -> Decimal:
        """
        Get total TAO converted in a block range.
        """
        if start_block == 0:
            return Decimal(0)
        
        _, tao_converted = self.conversion_repo.get_total_converted(
            start_block, end_block, validator_hotkey
        )
        return tao_converted
    
    def recalculate_period(
        self,
        period_type: PeriodType,
        period_start: date,
        validator_hotkey: str
    ) -> AggregationResult:
        """
        Recalculate ledger entries for a period.
        
        Deletes existing entries and recreates them.
        """
        logger.info(
            "Recalculating period",
            period_type=period_type.value,
            period_start=str(period_start),
            validator_hotkey=validator_hotkey
        )
        
        # Get existing entries
        if period_type == PeriodType.DAILY:
            period_end = period_start
        else:
            if period_start.month == 12:
                period_end = date(period_start.year + 1, 1, 1) - timedelta(days=1)
            else:
                period_end = date(period_start.year, period_start.month + 1, 1) - timedelta(days=1)
        
        existing = self.ledger_repo.get_by_period(
            period_type, period_start, period_end, validator_hotkey
        )
        
        # Delete existing entries
        for entry in existing:
            self.ledger_repo.delete(entry)
        
        self.session.flush()
        
        # Re-aggregate
        if period_type == PeriodType.DAILY:
            return self.aggregate_daily(period_start, validator_hotkey)
        else:
            return self.aggregate_monthly(
                period_start.year, period_start.month, validator_hotkey
            )
