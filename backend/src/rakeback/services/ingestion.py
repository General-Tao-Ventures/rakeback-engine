"""Ingestion service for fetching and storing chain data."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, Sequence
import csv

import structlog
from sqlalchemy.orm import Session

from rakeback.models import (
    BlockSnapshot,
    BlockYield,
    ConversionEvent,
    DataSource,
    CompletenessFlag,
    GapType,
    RunType,
    RunStatus,
)
from rakeback.repositories import (
    BlockSnapshotRepository,
    BlockYieldRepository,
    ConversionEventRepository,
    ProcessingRunRepository,
    DataGapRepository,
)
from rakeback.services.chain_client import (
    ChainClient,
    ChainClientError,
    BlockNotFoundError,
)

logger = structlog.get_logger(__name__)


class IngestionError(Exception):
    """Base exception for ingestion errors."""
    pass


class ValidationError(IngestionError):
    """Data validation failed."""
    pass


class CSVImportError(IngestionError):
    """CSV import failed."""
    pass


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""
    run_id: str
    blocks_processed: int
    blocks_created: int
    blocks_skipped: int
    gaps_detected: list[tuple[int, int]]  # (start, end) tuples
    completeness_summary: dict[str, int]
    errors: list[str]


class IngestionService:
    """
    Service for ingesting chain data into the database.
    
    Handles:
    - Block snapshot ingestion
    - Block yield ingestion
    - Conversion event ingestion
    - CSV override imports
    - Gap detection and recording
    """
    
    def __init__(
        self,
        session: Session,
        chain_client: Optional[ChainClient] = None
    ):
        """Initialize the ingestion service."""
        self.session = session
        self.chain_client = chain_client or ChainClient()
        
        # Repositories
        self.snapshot_repo = BlockSnapshotRepository(session)
        self.yield_repo = BlockYieldRepository(session)
        self.conversion_repo = ConversionEventRepository(session)
        self.run_repo = ProcessingRunRepository(session)
        self.gap_repo = DataGapRepository(session)
    
    def ingest_block_range(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str,
        skip_existing: bool = True,
        fail_on_error: bool = False
    ) -> IngestionResult:
        """
        Ingest snapshots and yields for a block range.
        
        Args:
            start_block: First block to ingest (inclusive)
            end_block: Last block to ingest (inclusive)
            validator_hotkey: Validator to fetch data for
            skip_existing: Skip blocks that already have data
            fail_on_error: Raise exception on first error vs continue
            
        Returns:
            IngestionResult with statistics and any errors
        """
        # Create processing run
        run = self.run_repo.create_run(
            run_type=RunType.INGESTION,
            validator_hotkey=validator_hotkey,
            block_range=(start_block, end_block)
        )
        
        logger.info(
            "Starting block range ingestion",
            run_id=run.run_id,
            start_block=start_block,
            end_block=end_block,
            validator_hotkey=validator_hotkey
        )
        
        # Connect to chain if not already
        if not self.chain_client.is_connected():
            self.chain_client.connect()
        
        blocks_processed = 0
        blocks_created = 0
        blocks_skipped = 0
        gaps = []
        errors = []
        completeness = {
            CompletenessFlag.COMPLETE.value: 0,
            CompletenessFlag.PARTIAL.value: 0,
            CompletenessFlag.MISSING.value: 0,
        }
        
        current_gap_start = None
        
        for block_num in range(start_block, end_block + 1):
            try:
                # Check if already exists
                if skip_existing:
                    if self.snapshot_repo.exists_for_block(block_num, validator_hotkey):
                        blocks_skipped += 1
                        continue
                
                # Fetch data from chain
                result = self._ingest_single_block(block_num, validator_hotkey)
                
                blocks_processed += 1
                
                if result:
                    blocks_created += 1
                    completeness[result.value] = completeness.get(result.value, 0) + 1
                    
                    # Close any open gap
                    if current_gap_start is not None:
                        gaps.append((current_gap_start, block_num - 1))
                        self._record_gap(
                            current_gap_start,
                            block_num - 1,
                            validator_hotkey,
                            "Block data unavailable",
                            run.run_id
                        )
                        current_gap_start = None
                else:
                    # Mark as gap
                    if current_gap_start is None:
                        current_gap_start = block_num
                    completeness[CompletenessFlag.MISSING.value] += 1
                
            except BlockNotFoundError as e:
                logger.warning("Block not found", block_number=block_num, error=str(e))
                if current_gap_start is None:
                    current_gap_start = block_num
                errors.append(f"Block {block_num}: not found")
                
                if fail_on_error:
                    raise IngestionError(f"Block {block_num} not found") from e
                    
            except ChainClientError as e:
                logger.error("Chain client error", block_number=block_num, error=str(e))
                errors.append(f"Block {block_num}: {str(e)}")
                
                if fail_on_error:
                    raise IngestionError(f"Chain error at block {block_num}") from e
                    
            except Exception as e:
                logger.exception("Unexpected error during ingestion", block_number=block_num)
                errors.append(f"Block {block_num}: {str(e)}")
                
                if fail_on_error:
                    raise
        
        # Close any remaining gap
        if current_gap_start is not None:
            gaps.append((current_gap_start, end_block))
            self._record_gap(
                current_gap_start,
                end_block,
                validator_hotkey,
                "Block data unavailable",
                run.run_id
            )
        
        # Update run status
        run.records_processed = blocks_processed
        run.records_created = blocks_created
        run.records_skipped = blocks_skipped
        run.completeness_summary = completeness
        
        if errors:
            run.mark_completed(RunStatus.PARTIAL if blocks_created > 0 else RunStatus.FAILED)
            run.error_details = {"errors": errors[:100]}  # Limit error storage
        else:
            run.mark_completed(RunStatus.SUCCESS)
        
        self.session.flush()
        
        logger.info(
            "Completed block range ingestion",
            run_id=run.run_id,
            blocks_processed=blocks_processed,
            blocks_created=blocks_created,
            blocks_skipped=blocks_skipped,
            gaps=len(gaps),
            errors=len(errors)
        )
        
        return IngestionResult(
            run_id=run.run_id,
            blocks_processed=blocks_processed,
            blocks_created=blocks_created,
            blocks_skipped=blocks_skipped,
            gaps_detected=gaps,
            completeness_summary=completeness,
            errors=errors
        )
    
    def _ingest_single_block(
        self,
        block_number: int,
        validator_hotkey: str
    ) -> Optional[CompletenessFlag]:
        """
        Ingest data for a single block.
        
        Returns the completeness flag if successful, None if no data.
        """
        # Fetch validator state
        state = self.chain_client.get_validator_state(block_number, validator_hotkey)
        
        if not state or not state.delegations:
            logger.debug("No validator state for block", block_number=block_number)
            return None
        
        # Create snapshot
        delegations = [
            {
                "delegator_address": d.delegator_address,
                "delegation_type": d.delegation_type,
                "subnet_id": d.subnet_id,
                "balance_dtao": d.balance_dtao,
                "balance_tao": d.balance_tao,
            }
            for d in state.delegations
        ]
        
        self.snapshot_repo.create_snapshot(
            block_number=block_number,
            validator_hotkey=validator_hotkey,
            block_hash=state.block_hash,
            timestamp=state.timestamp,
            delegations=delegations,
            data_source=DataSource.CHAIN,
            completeness_flag=CompletenessFlag.COMPLETE
        )
        
        # Fetch and store yield
        yield_data = self.chain_client.get_block_yield(block_number, validator_hotkey)
        
        if yield_data:
            sources = [
                {"subnet_id": subnet_id, "dtao_amount": amount}
                for subnet_id, amount in yield_data.yield_by_subnet.items()
            ]
            
            self.yield_repo.create_yield(
                block_number=block_number,
                validator_hotkey=validator_hotkey,
                total_dtao_earned=yield_data.total_dtao_earned,
                yield_sources=sources if sources else None,
                data_source=DataSource.CHAIN,
                completeness_flag=CompletenessFlag.COMPLETE
            )
        
        return CompletenessFlag.COMPLETE
    
    def _record_gap(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str,
        reason: str,
        run_id: str
    ) -> None:
        """Record a data gap."""
        # Check for existing overlapping gaps
        existing = self.gap_repo.get_by_block_range(start_block, end_block, GapType.SNAPSHOT)
        
        # Only create if no overlapping open gap exists
        for gap in existing:
            if gap.validator_hotkey == validator_hotkey:
                if gap.block_start <= start_block and gap.block_end >= end_block:
                    return  # Already covered
        
        self.gap_repo.create_gap(
            gap_type=GapType.SNAPSHOT,
            block_start=start_block,
            block_end=end_block,
            reason=reason,
            validator_hotkey=validator_hotkey,
            detected_by_run_id=run_id
        )
    
    def ingest_conversions(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: Optional[str] = None
    ) -> IngestionResult:
        """
        Ingest conversion events for a block range.
        """
        run = self.run_repo.create_run(
            run_type=RunType.INGESTION,
            validator_hotkey=validator_hotkey,
            block_range=(start_block, end_block)
        )
        
        logger.info(
            "Starting conversion ingestion",
            run_id=run.run_id,
            start_block=start_block,
            end_block=end_block
        )
        
        if not self.chain_client.is_connected():
            self.chain_client.connect()
        
        events_created = 0
        events_skipped = 0
        errors = []
        
        try:
            conversions = self.chain_client.get_conversion_events(
                start_block, end_block, validator_hotkey
            )
            
            for conv in conversions:
                # Skip if already exists
                if self.conversion_repo.exists_for_tx(conv.transaction_hash):
                    events_skipped += 1
                    continue
                
                event = ConversionEvent(
                    block_number=conv.block_number,
                    transaction_hash=conv.transaction_hash,
                    validator_hotkey=conv.validator_hotkey,
                    dtao_amount=conv.dtao_amount,
                    tao_amount=conv.tao_amount,
                    conversion_rate=conv.conversion_rate,
                    subnet_id=conv.subnet_id,
                    data_source=DataSource.CHAIN
                )
                self.conversion_repo.add(event)
                events_created += 1
            
            run.records_created = events_created
            run.records_skipped = events_skipped
            run.mark_completed(RunStatus.SUCCESS)
            
        except Exception as e:
            logger.exception("Error ingesting conversions")
            errors.append(str(e))
            run.mark_failed(e)
        
        self.session.flush()
        
        return IngestionResult(
            run_id=run.run_id,
            blocks_processed=end_block - start_block + 1,
            blocks_created=events_created,
            blocks_skipped=events_skipped,
            gaps_detected=[],
            completeness_summary={},
            errors=errors
        )
    
    def import_snapshot_csv(
        self,
        csv_path: Path,
        validator_hotkey: str
    ) -> IngestionResult:
        """
        Import block snapshots from CSV override file.
        
        Expected CSV columns:
        - block_number
        - block_hash
        - timestamp (ISO format)
        - delegator_address
        - delegation_type
        - subnet_id (optional)
        - balance_dtao
        - balance_tao (optional)
        """
        run = self.run_repo.create_run(
            run_type=RunType.INGESTION,
            validator_hotkey=validator_hotkey,
            config_snapshot={"csv_path": str(csv_path), "type": "snapshot_override"}
        )
        
        logger.info("Importing snapshot CSV", run_id=run.run_id, csv_path=str(csv_path))
        
        blocks_created = 0
        errors = []
        
        try:
            # Group rows by block
            blocks_data = {}
            
            with open(csv_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        block_num = int(row['block_number'])
                        
                        if block_num not in blocks_data:
                            blocks_data[block_num] = {
                                'block_hash': row['block_hash'],
                                'timestamp': datetime.fromisoformat(row['timestamp']),
                                'delegations': []
                            }
                        
                        delegation = {
                            'delegator_address': row['delegator_address'],
                            'delegation_type': row['delegation_type'],
                            'subnet_id': int(row['subnet_id']) if row.get('subnet_id') else None,
                            'balance_dtao': Decimal(row['balance_dtao']),
                            'balance_tao': Decimal(row['balance_tao']) if row.get('balance_tao') else None,
                        }
                        blocks_data[block_num]['delegations'].append(delegation)
                        
                    except (KeyError, ValueError) as e:
                        errors.append(f"Row {row_num}: {str(e)}")
            
            # Create snapshots
            for block_num, data in sorted(blocks_data.items()):
                # Delete existing if present
                self.snapshot_repo.delete_range(block_num, block_num, validator_hotkey)
                
                self.snapshot_repo.create_snapshot(
                    block_number=block_num,
                    validator_hotkey=validator_hotkey,
                    block_hash=data['block_hash'],
                    timestamp=data['timestamp'],
                    delegations=data['delegations'],
                    data_source=DataSource.CSV_OVERRIDE,
                    completeness_flag=CompletenessFlag.COMPLETE
                )
                blocks_created += 1
            
            run.records_created = blocks_created
            run.mark_completed(RunStatus.SUCCESS if not errors else RunStatus.PARTIAL)
            
            if errors:
                run.error_details = {"parse_errors": errors[:100]}
            
        except Exception as e:
            logger.exception("Error importing CSV")
            errors.append(str(e))
            run.mark_failed(e)
        
        self.session.flush()
        
        return IngestionResult(
            run_id=run.run_id,
            blocks_processed=len(blocks_data) if 'blocks_data' in dir() else 0,
            blocks_created=blocks_created,
            blocks_skipped=0,
            gaps_detected=[],
            completeness_summary={CompletenessFlag.COMPLETE.value: blocks_created},
            errors=errors
        )
    
    def import_yield_csv(
        self,
        csv_path: Path,
        validator_hotkey: str
    ) -> IngestionResult:
        """
        Import block yields from CSV override file.
        
        Expected CSV columns:
        - block_number
        - total_dtao_earned
        - subnet_id (optional, for breakdown)
        - subnet_dtao (optional, for breakdown)
        """
        run = self.run_repo.create_run(
            run_type=RunType.INGESTION,
            validator_hotkey=validator_hotkey,
            config_snapshot={"csv_path": str(csv_path), "type": "yield_override"}
        )
        
        logger.info("Importing yield CSV", run_id=run.run_id, csv_path=str(csv_path))
        
        yields_created = 0
        errors = []
        
        try:
            # Group rows by block
            blocks_data = {}
            
            with open(csv_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        block_num = int(row['block_number'])
                        
                        if block_num not in blocks_data:
                            blocks_data[block_num] = {
                                'total_dtao_earned': Decimal(row['total_dtao_earned']),
                                'sources': []
                            }
                        
                        # Optional subnet breakdown
                        if row.get('subnet_id') and row.get('subnet_dtao'):
                            blocks_data[block_num]['sources'].append({
                                'subnet_id': int(row['subnet_id']),
                                'dtao_amount': Decimal(row['subnet_dtao'])
                            })
                        
                    except (KeyError, ValueError) as e:
                        errors.append(f"Row {row_num}: {str(e)}")
            
            # Create yields
            for block_num, data in sorted(blocks_data.items()):
                # Delete existing if present
                self.yield_repo.delete_range(block_num, block_num, validator_hotkey)
                
                self.yield_repo.create_yield(
                    block_number=block_num,
                    validator_hotkey=validator_hotkey,
                    total_dtao_earned=data['total_dtao_earned'],
                    yield_sources=data['sources'] if data['sources'] else None,
                    data_source=DataSource.CSV_OVERRIDE,
                    completeness_flag=CompletenessFlag.COMPLETE
                )
                yields_created += 1
            
            run.records_created = yields_created
            run.mark_completed(RunStatus.SUCCESS if not errors else RunStatus.PARTIAL)
            
        except Exception as e:
            logger.exception("Error importing yield CSV")
            errors.append(str(e))
            run.mark_failed(e)
        
        self.session.flush()
        
        return IngestionResult(
            run_id=run.run_id,
            blocks_processed=len(blocks_data) if 'blocks_data' in dir() else 0,
            blocks_created=yields_created,
            blocks_skipped=0,
            gaps_detected=[],
            completeness_summary={CompletenessFlag.COMPLETE.value: yields_created},
            errors=errors
        )
