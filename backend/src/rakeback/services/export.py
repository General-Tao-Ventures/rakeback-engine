"""Export service for generating CSV and audit reports."""

import csv
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, Sequence

import structlog
from sqlalchemy.orm import Session

from rakeback.config import get_settings
from rakeback.models import (
    RakebackLedgerEntry,
    CompletenessFlag,
    PaymentStatus,
    PeriodType,
    RunType,
    RunStatus,
)
from rakeback.repositories import (
    RakebackLedgerRepository,
    BlockAttributionRepository,
    TaoAllocationRepository,
    ProcessingRunRepository,
)

logger = structlog.get_logger(__name__)


class ExportError(Exception):
    """Base exception for export errors."""
    pass


@dataclass
class ExportResult:
    """Result of an export operation."""
    run_id: str
    output_path: Path
    row_count: int
    complete_entries: int
    incomplete_entries: int
    total_tao: Decimal
    warnings: list[str]


class ExportService:
    """
    Service for exporting rakeback data to various formats.
    
    Generates:
    - Ledger CSV exports for finance
    - Audit trail exports for verification
    - Summary reports
    """
    
    def __init__(self, session: Session):
        """Initialize the export service."""
        self.session = session
        self.settings = get_settings()
        
        # Repositories
        self.ledger_repo = RakebackLedgerRepository(session)
        self.attribution_repo = BlockAttributionRepository(session)
        self.allocation_repo = TaoAllocationRepository(session)
        self.run_repo = ProcessingRunRepository(session)
    
    def export_ledger_csv(
        self,
        period_type: PeriodType,
        period_start: date,
        period_end: date,
        output_path: Optional[Path] = None,
        participant_ids: Optional[Sequence[str]] = None,
        include_incomplete: bool = True
    ) -> ExportResult:
        """
        Export ledger entries to CSV.
        
        Args:
            period_type: Daily or monthly
            period_start: Start of period
            period_end: End of period
            output_path: Output file path (auto-generated if None)
            participant_ids: Filter to specific participants
            include_incomplete: Include entries with incomplete data
            
        Returns:
            ExportResult with file path and statistics
        """
        # Create processing run
        run = self.run_repo.create_run(
            run_type=RunType.EXPORT,
            period=(period_start, period_end)
        )
        
        logger.info(
            "Starting ledger export",
            run_id=run.run_id,
            period_type=period_type.value,
            period_start=str(period_start),
            period_end=str(period_end)
        )
        
        # Generate output path if not provided
        if output_path is None:
            filename = f"rakeback_{period_type.value}_{period_start.isoformat()}_{period_end.isoformat()}.csv"
            output_path = self.settings.export_dir / filename
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get entries
        entries = self.ledger_repo.get_by_period(
            period_type, period_start, period_end
        )
        
        # Filter by participant if specified
        if participant_ids:
            entries = [e for e in entries if e.participant_id in participant_ids]
        
        # Filter by completeness if specified
        if not include_incomplete:
            entries = [e for e in entries if e.completeness_flag == CompletenessFlag.COMPLETE]
        
        warnings = []
        complete_count = 0
        incomplete_count = 0
        total_tao = Decimal(0)
        
        # Write CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header with metadata
            writer.writerow([f"# Rakeback Ledger Export - {period_type.value.title()}"])
            writer.writerow([f"# Generated: {datetime.utcnow().isoformat()}Z"])
            writer.writerow([f"# Period: {period_start} to {period_end}"])
            writer.writerow([f"# Run ID: {run.run_id}"])
            writer.writerow([])
            
            # Check for incomplete data
            incomplete_entries = [e for e in entries if e.completeness_flag != CompletenessFlag.COMPLETE]
            if incomplete_entries:
                writer.writerow(["# WARNING: This export contains incomplete data"])
                writer.writerow([f"# Incomplete entries: {len(incomplete_entries)}"])
                warnings.append(f"{len(incomplete_entries)} entries have incomplete data")
                writer.writerow([])
            
            # Column headers
            writer.writerow([
                "participant_id",
                "participant_name",
                "participant_type",
                "validator_hotkey",
                "period_start",
                "period_end",
                "gross_dtao_attributed",
                "gross_tao_converted",
                "rakeback_percentage",
                "tao_owed",
                "payment_status",
                "payment_tx_hash",
                "completeness_flag",
                "block_count",
                "attribution_count",
                "entry_id"
            ])
            
            # Write data rows
            for entry in entries:
                writer.writerow([
                    entry.participant_id,
                    "",  # participant_name - would need join
                    entry.participant_type.value,
                    entry.validator_hotkey,
                    entry.period_start.isoformat(),
                    entry.period_end.isoformat(),
                    str(entry.gross_dtao_attributed),
                    str(entry.gross_tao_converted),
                    str(entry.rakeback_percentage),
                    str(entry.tao_owed),
                    entry.payment_status.value,
                    entry.payment_tx_hash or "",
                    entry.completeness_flag.value,
                    entry.block_count,
                    entry.attribution_count,
                    entry.id
                ])
                
                total_tao += entry.tao_owed
                if entry.completeness_flag == CompletenessFlag.COMPLETE:
                    complete_count += 1
                else:
                    incomplete_count += 1
        
        # Update run
        run.records_processed = len(entries)
        run.mark_completed(RunStatus.SUCCESS)
        self.session.flush()
        
        logger.info(
            "Completed ledger export",
            run_id=run.run_id,
            output_path=str(output_path),
            row_count=len(entries),
            total_tao=str(total_tao)
        )
        
        return ExportResult(
            run_id=run.run_id,
            output_path=output_path,
            row_count=len(entries),
            complete_entries=complete_count,
            incomplete_entries=incomplete_count,
            total_tao=total_tao,
            warnings=warnings
        )
    
    def export_audit_trail(
        self,
        ledger_entry_id: str,
        output_path: Optional[Path] = None
    ) -> ExportResult:
        """
        Export detailed audit trail for a ledger entry.
        
        Shows the full lineage from blocks to final TAO owed.
        """
        entry = self.ledger_repo.get_by_id(ledger_entry_id)
        if not entry:
            raise ExportError(f"Ledger entry {ledger_entry_id} not found")
        
        logger.info(
            "Exporting audit trail",
            ledger_entry_id=ledger_entry_id,
            participant_id=entry.participant_id
        )
        
        # Generate output path
        if output_path is None:
            filename = f"audit_trail_{entry.participant_id}_{entry.period_start.isoformat()}_{entry.id[:8]}.csv"
            output_path = self.settings.export_dir / filename
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        warnings = []
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Metadata header
            writer.writerow(["# Audit Trail Export"])
            writer.writerow([f"# Ledger Entry ID: {entry.id}"])
            writer.writerow([f"# Participant: {entry.participant_id}"])
            writer.writerow([f"# Period: {entry.period_start} to {entry.period_end}"])
            writer.writerow([f"# Generated: {datetime.utcnow().isoformat()}Z"])
            writer.writerow([])
            
            # Summary section
            writer.writerow(["# Summary"])
            writer.writerow(["Field", "Value"])
            writer.writerow(["Gross dTAO Attributed", str(entry.gross_dtao_attributed)])
            writer.writerow(["Gross TAO Converted", str(entry.gross_tao_converted)])
            writer.writerow(["Rakeback Percentage", f"{entry.rakeback_percentage:.2%}"])
            writer.writerow(["TAO Owed", str(entry.tao_owed)])
            writer.writerow(["Payment Status", entry.payment_status.value])
            writer.writerow(["Completeness", entry.completeness_flag.value])
            writer.writerow(["Block Count", entry.block_count])
            writer.writerow(["Attribution Count", entry.attribution_count])
            writer.writerow([])
            
            # Completeness details
            if entry.completeness_details:
                writer.writerow(["# Completeness Details"])
                for key, value in entry.completeness_details.items():
                    writer.writerow([key, str(value)])
                writer.writerow([])
            
            # Note: Full attribution breakdown would require more complex queries
            writer.writerow(["# Note: Detailed attribution breakdown available via API"])
        
        return ExportResult(
            run_id="",
            output_path=output_path,
            row_count=1,
            complete_entries=1 if entry.completeness_flag == CompletenessFlag.COMPLETE else 0,
            incomplete_entries=0 if entry.completeness_flag == CompletenessFlag.COMPLETE else 1,
            total_tao=entry.tao_owed,
            warnings=warnings
        )
    
    def mark_entries_paid(
        self,
        entry_ids: Sequence[str],
        payment_tx_hash: str,
        payment_timestamp: Optional[datetime] = None
    ) -> int:
        """
        Mark ledger entries as paid.
        
        Returns count of entries updated.
        """
        if payment_timestamp is None:
            payment_timestamp = datetime.utcnow()
        
        count = self.ledger_repo.mark_paid(
            entry_ids, payment_tx_hash, payment_timestamp.date()
        )
        
        logger.info(
            "Marked entries as paid",
            count=count,
            payment_tx_hash=payment_tx_hash
        )
        
        return count
    
    def generate_summary_report(
        self,
        period_type: PeriodType,
        period_start: date,
        period_end: date
    ) -> dict:
        """
        Generate a summary report for a period.
        
        Returns dict with aggregate statistics.
        """
        entries = self.ledger_repo.get_by_period(period_type, period_start, period_end)
        
        total_dtao = sum(e.gross_dtao_attributed for e in entries)
        total_tao_converted = sum(e.gross_tao_converted for e in entries)
        total_tao_owed = sum(e.tao_owed for e in entries)
        
        by_status = {}
        for e in entries:
            status = e.payment_status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        by_completeness = {}
        for e in entries:
            flag = e.completeness_flag.value
            by_completeness[flag] = by_completeness.get(flag, 0) + 1
        
        by_participant = {}
        for e in entries:
            pid = e.participant_id
            if pid not in by_participant:
                by_participant[pid] = {"dtao": Decimal(0), "tao_owed": Decimal(0)}
            by_participant[pid]["dtao"] += e.gross_dtao_attributed
            by_participant[pid]["tao_owed"] += e.tao_owed
        
        return {
            "period": {
                "type": period_type.value,
                "start": period_start.isoformat(),
                "end": period_end.isoformat()
            },
            "totals": {
                "entries": len(entries),
                "gross_dtao_attributed": str(total_dtao),
                "gross_tao_converted": str(total_tao_converted),
                "total_tao_owed": str(total_tao_owed)
            },
            "by_payment_status": by_status,
            "by_completeness": by_completeness,
            "by_participant": {
                k: {"dtao": str(v["dtao"]), "tao_owed": str(v["tao_owed"])}
                for k, v in by_participant.items()
            }
        }
