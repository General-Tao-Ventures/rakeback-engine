"""Attribution engine for block-by-block yield distribution."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Optional, Sequence

import structlog
from sqlalchemy.orm import Session

from rakeback.models import (
    BlockAttribution,
    CompletenessFlag,
    DataGap,
    DelegationType,
    GapType,
    ResolutionStatus,
    RunType,
    RunStatus,
)
from rakeback.repositories import (
    BlockSnapshotRepository,
    BlockYieldRepository,
    BlockAttributionRepository,
    ProcessingRunRepository,
    DataGapRepository,
)

logger = structlog.get_logger(__name__)


class AttributionError(Exception):
    """Base exception for attribution errors."""
    pass


class IncompleteDataError(AttributionError):
    """Required data is missing or incomplete."""
    pass


class ValidationError(AttributionError):
    """Data validation failed."""
    pass


@dataclass
class AttributionResult:
    """Result of an attribution run."""
    run_id: str
    blocks_processed: int
    attributions_created: int
    blocks_skipped: int
    blocks_incomplete: int
    total_dtao_attributed: Decimal
    completeness_summary: dict[str, int]
    errors: list[str]


class AttributionEngine:
    """
    Engine for computing block-by-block yield attribution.
    
    This is the core computation engine that:
    1. Takes block snapshots and yields as input
    2. Computes each delegator's share of the yield
    3. Creates attribution records linking delegators to their earned dTAO
    
    Key principles:
    - Deterministic: Same inputs always produce same outputs
    - Traceable: Every attribution links back to source data
    - Explicit: Incomplete data is flagged, never hidden
    """
    
    # Precision for proportion calculations
    # Using 1E-15 to allow for inevitable rounding in division (e.g., 1/3 * 3 ≠ 1)
    PROPORTION_PRECISION = Decimal('1E-15')
    
    def __init__(self, session: Session):
        """Initialize the attribution engine."""
        self.session = session
        
        # Repositories
        self.snapshot_repo = BlockSnapshotRepository(session)
        self.yield_repo = BlockYieldRepository(session)
        self.attribution_repo = BlockAttributionRepository(session)
        self.run_repo = ProcessingRunRepository(session)
        self.gap_repo = DataGapRepository(session)
    
    def run_attribution(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str,
        skip_existing: bool = True,
        fail_on_incomplete: bool = False,
        dry_run: bool = False
    ) -> AttributionResult:
        """
        Run attribution for a block range.
        
        Args:
            start_block: First block to process (inclusive)
            end_block: Last block to process (inclusive)
            validator_hotkey: Validator to attribute yields for
            skip_existing: Skip blocks that already have attributions
            fail_on_incomplete: Raise exception if any data is missing
            dry_run: Compute but don't persist (for validation)
            
        Returns:
            AttributionResult with statistics and any errors
        """
        # Create processing run
        run = self.run_repo.create_run(
            run_type=RunType.ATTRIBUTION,
            validator_hotkey=validator_hotkey,
            block_range=(start_block, end_block)
        )
        
        logger.info(
            "Starting attribution run",
            run_id=run.run_id,
            start_block=start_block,
            end_block=end_block,
            validator_hotkey=validator_hotkey,
            dry_run=dry_run
        )
        
        blocks_processed = 0
        attributions_created = 0
        blocks_skipped = 0
        blocks_incomplete = 0
        total_dtao = Decimal(0)
        errors = []
        completeness = {
            CompletenessFlag.COMPLETE.value: 0,
            CompletenessFlag.PARTIAL.value: 0,
            CompletenessFlag.INCOMPLETE.value: 0,
        }
        
        for block_num in range(start_block, end_block + 1):
            try:
                # Check for existing attributions
                if skip_existing and self.attribution_repo.exists_for_block(
                    block_num, validator_hotkey
                ):
                    blocks_skipped += 1
                    continue
                
                # Compute attributions for this block
                result = self._attribute_block(
                    block_num,
                    validator_hotkey,
                    run.run_id,
                    dry_run
                )
                
                blocks_processed += 1
                
                if result is None:
                    blocks_incomplete += 1
                    completeness[CompletenessFlag.INCOMPLETE.value] += 1
                    
                    if fail_on_incomplete:
                        raise IncompleteDataError(
                            f"Missing data for block {block_num}"
                        )
                else:
                    count, dtao, flag = result
                    attributions_created += count
                    total_dtao += dtao
                    completeness[flag.value] = completeness.get(flag.value, 0) + 1
                    
            except AttributionError as e:
                logger.error("Attribution error", block_number=block_num, error=str(e))
                errors.append(f"Block {block_num}: {str(e)}")
                
                if fail_on_incomplete:
                    raise
                    
            except Exception as e:
                logger.exception("Unexpected error during attribution", block_number=block_num)
                errors.append(f"Block {block_num}: {str(e)}")
        
        # Consolidate any recorded gaps
        if not dry_run:
            gap_counts = self.consolidate_gaps(validator_hotkey)
            total_open_gaps = sum(gap_counts.values())
        else:
            total_open_gaps = 0
        
        # Update run status
        run.records_processed = blocks_processed
        run.records_created = attributions_created
        run.records_skipped = blocks_skipped
        run.completeness_summary = {
            **completeness,
            "incomplete_blocks": blocks_incomplete,
            "total_dtao_attributed": str(total_dtao),
            "open_gaps": total_open_gaps
        }
        
        if errors:
            run.mark_completed(
                RunStatus.PARTIAL if attributions_created > 0 else RunStatus.FAILED
            )
            run.error_details = {"errors": errors[:100]}
        else:
            run.mark_completed(RunStatus.SUCCESS)
        
        if not dry_run:
            self.session.flush()
        
        logger.info(
            "Completed attribution run",
            run_id=run.run_id,
            blocks_processed=blocks_processed,
            attributions_created=attributions_created,
            total_dtao=str(total_dtao),
            incomplete_blocks=blocks_incomplete
        )
        
        return AttributionResult(
            run_id=run.run_id,
            blocks_processed=blocks_processed,
            attributions_created=attributions_created,
            blocks_skipped=blocks_skipped,
            blocks_incomplete=blocks_incomplete,
            total_dtao_attributed=total_dtao,
            completeness_summary=run.completeness_summary,
            errors=errors
        )
    
    def _attribute_block(
        self,
        block_number: int,
        validator_hotkey: str,
        run_id: str,
        dry_run: bool,
        record_gaps: bool = True
    ) -> Optional[tuple[int, Decimal, CompletenessFlag]]:
        """
        Compute and create attributions for a single block.
        
        Args:
            block_number: Block to attribute
            validator_hotkey: Validator being attributed
            run_id: Current processing run ID
            dry_run: If True, don't persist results
            record_gaps: If True, record DataGap when data is missing
        
        Returns:
            Tuple of (attribution_count, total_dtao, completeness_flag)
            or None if data is missing
        """
        # Fetch snapshot
        snapshot = self.snapshot_repo.get_by_block_and_validator(
            block_number, validator_hotkey
        )
        
        if not snapshot:
            logger.debug("No snapshot for block", block_number=block_number)
            if record_gaps and not dry_run:
                self._record_gap(
                    GapType.SNAPSHOT,
                    block_number,
                    block_number,
                    validator_hotkey,
                    "Missing snapshot during attribution",
                    run_id
                )
            return None
        
        # Fetch yield
        block_yield = self.yield_repo.get_by_block_and_validator(
            block_number, validator_hotkey
        )
        
        if not block_yield:
            logger.debug("No yield for block", block_number=block_number)
            if record_gaps and not dry_run:
                self._record_gap(
                    GapType.YIELD,
                    block_number,
                    block_number,
                    validator_hotkey,
                    "Missing yield during attribution",
                    run_id
                )
            return None
        
        # Skip if no yield to distribute
        if block_yield.total_dtao_earned == 0:
            logger.debug("Zero yield for block", block_number=block_number)
            return (0, Decimal(0), CompletenessFlag.COMPLETE)
        
        # Skip if no delegations
        if not snapshot.delegations:
            logger.warning("No delegations in snapshot", block_number=block_number)
            return (0, Decimal(0), CompletenessFlag.PARTIAL)
        
        # Validate proportions sum to 1
        total_proportion = sum(d.proportion for d in snapshot.delegations)
        if abs(total_proportion - Decimal(1)) > self.PROPORTION_PRECISION:
            raise ValidationError(
                f"Block {block_number}: Proportions sum to {total_proportion}, expected 1.0"
            )
        
        # Determine completeness flag (inherit from sources)
        completeness = self._compute_completeness(
            snapshot.completeness_flag,
            block_yield.completeness_flag
        )
        
        # Compute attributions
        attributions = []
        total_attributed = Decimal(0)
        
        for delegation in snapshot.delegations:
            # Calculate attributed amount
            # Use high precision, round down to ensure we don't over-allocate
            attributed_dtao = (
                block_yield.total_dtao_earned * delegation.proportion
            ).quantize(Decimal('1'), rounding=ROUND_DOWN)
            
            total_attributed += attributed_dtao
            
            attribution = BlockAttribution(
                block_number=block_number,
                validator_hotkey=validator_hotkey,
                delegator_address=delegation.delegator_address,
                delegation_type=delegation.delegation_type,
                subnet_id=delegation.subnet_id,
                attributed_dtao=attributed_dtao,
                delegation_proportion=delegation.proportion,
                completeness_flag=completeness,
                run_id=run_id,
            )
            attributions.append(attribution)
        
        # Handle rounding remainder
        remainder = block_yield.total_dtao_earned - total_attributed
        if remainder > 0 and attributions:
            # Add remainder to the largest attribution (deterministic)
            largest = max(attributions, key=lambda a: a.attributed_dtao)
            largest.attributed_dtao += remainder
            total_attributed += remainder
        
        # Validate total matches yield
        if total_attributed != block_yield.total_dtao_earned:
            raise ValidationError(
                f"Block {block_number}: Attribution total {total_attributed} "
                f"doesn't match yield {block_yield.total_dtao_earned}"
            )
        
        # Persist if not dry run
        if not dry_run:
            for attribution in attributions:
                self.attribution_repo.add(attribution)
        
        return (len(attributions), total_attributed, completeness)
    
    def _compute_completeness(
        self,
        *flags: CompletenessFlag
    ) -> CompletenessFlag:
        """
        Compute combined completeness from multiple sources.
        
        Rules:
        - Any MISSING → INCOMPLETE
        - Any PARTIAL or INCOMPLETE → INCOMPLETE
        - All COMPLETE → COMPLETE
        """
        for flag in flags:
            if flag == CompletenessFlag.MISSING:
                return CompletenessFlag.INCOMPLETE
            if flag in (CompletenessFlag.PARTIAL, CompletenessFlag.INCOMPLETE):
                return CompletenessFlag.INCOMPLETE
        
        return CompletenessFlag.COMPLETE
    
    def _record_gap(
        self,
        gap_type: GapType,
        block_start: int,
        block_end: int,
        validator_hotkey: str,
        reason: str,
        run_id: str
    ) -> None:
        """
        Record a data gap if one doesn't already exist for this range.
        
        Merges with existing gaps if overlapping.
        """
        # Check if gap already exists
        existing_gaps = self.gap_repo.get_by_block_range(block_start, block_end, gap_type)
        
        for gap in existing_gaps:
            if (gap.validator_hotkey == validator_hotkey and 
                gap.resolution_status == ResolutionStatus.OPEN):
                # Gap already tracked, potentially extend it
                if block_start < gap.block_start or block_end > gap.block_end:
                    gap.block_start = min(gap.block_start, block_start)
                    gap.block_end = max(gap.block_end, block_end)
                    self.session.flush()
                return
        
        # Create new gap
        self.gap_repo.create_gap(
            gap_type=gap_type,
            block_start=block_start,
            block_end=block_end,
            reason=reason,
            validator_hotkey=validator_hotkey,
            detected_by_run_id=run_id
        )
        
        logger.info(
            "Recorded data gap",
            gap_type=gap_type.value,
            block_start=block_start,
            block_end=block_end,
            validator_hotkey=validator_hotkey
        )
    
    def rerun_attribution(
        self,
        original_run_id: str,
        invalidate_previous: bool = True
    ) -> AttributionResult:
        """
        Re-run attribution for a previous run's scope.
        
        This allows recomputing attributions when:
        - Source data has been updated
        - A bug fix requires recalculation
        - CSV overrides have been applied
        """
        # Get original run
        original_run = self.run_repo.get_by_id(original_run_id)
        if not original_run:
            raise AttributionError(f"Run {original_run_id} not found")
        
        if not original_run.block_range_start or not original_run.block_range_end:
            raise AttributionError(f"Run {original_run_id} has no block range")
        
        if not original_run.validator_hotkey:
            raise AttributionError(f"Run {original_run_id} has no validator")
        
        logger.info(
            "Re-running attribution",
            original_run_id=original_run_id,
            block_range=(original_run.block_range_start, original_run.block_range_end),
            invalidate_previous=invalidate_previous
        )
        
        # Run new attribution (skip_existing=False to recompute)
        result = self.run_attribution(
            start_block=original_run.block_range_start,
            end_block=original_run.block_range_end,
            validator_hotkey=original_run.validator_hotkey,
            skip_existing=False,  # Force recompute
            fail_on_incomplete=False
        )
        
        # Update run to reference parent
        new_run = self.run_repo.get_by_id(result.run_id)
        if new_run:
            new_run.parent_run_id = original_run_id
            self.session.flush()
        
        return result
    
    def get_attribution_stats(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str
    ) -> dict:
        """
        Get comprehensive statistics for attributions in a block range.
        
        Returns:
            Dictionary with attribution statistics
        """
        attributions = self.attribution_repo.get_range(
            start_block, end_block, validator_hotkey
        )
        
        if not attributions:
            return {
                "block_range": (start_block, end_block),
                "total_blocks": end_block - start_block + 1,
                "blocks_with_attributions": 0,
                "total_attributions": 0,
                "total_dtao_attributed": Decimal(0),
                "unique_delegators": 0,
                "completeness": {},
                "by_delegation_type": {},
            }
        
        # Aggregate statistics
        blocks_with_attr = set()
        delegators = set()
        total_dtao = Decimal(0)
        by_delegation_type: dict[str, Decimal] = {}
        completeness_counts: dict[str, int] = {}
        
        for attr in attributions:
            blocks_with_attr.add(attr.block_number)
            delegators.add(attr.delegator_address)
            total_dtao += attr.attributed_dtao
            
            # By delegation type
            dtype = attr.delegation_type.value
            by_delegation_type[dtype] = by_delegation_type.get(dtype, Decimal(0)) + attr.attributed_dtao
            
            # Completeness
            cflag = attr.completeness_flag.value
            completeness_counts[cflag] = completeness_counts.get(cflag, 0) + 1
        
        return {
            "block_range": (start_block, end_block),
            "total_blocks": end_block - start_block + 1,
            "blocks_with_attributions": len(blocks_with_attr),
            "total_attributions": len(attributions),
            "total_dtao_attributed": total_dtao,
            "unique_delegators": len(delegators),
            "completeness": completeness_counts,
            "by_delegation_type": {k: str(v) for k, v in by_delegation_type.items()},
        }
    
    def consolidate_gaps(self, validator_hotkey: Optional[str] = None) -> dict:
        """
        Merge overlapping gaps of the same type.
        
        Returns:
            Dictionary with counts per gap type
        """
        results = {}
        
        for gap_type in GapType:
            count = self.gap_repo.merge_overlapping(gap_type, validator_hotkey)
            results[gap_type.value] = count
        
        return results
    
    def validate_attributions(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str
    ) -> dict:
        """
        Validate existing attributions against source data.
        
        Checks:
        1. Attribution totals match yield totals
        2. All delegators in snapshot have attributions
        3. Proportions are consistent
        
        Returns dict with validation results.
        """
        results = {
            "blocks_checked": 0,
            "blocks_valid": 0,
            "blocks_invalid": 0,
            "issues": []
        }
        
        for block_num in range(start_block, end_block + 1):
            snapshot = self.snapshot_repo.get_by_block_and_validator(
                block_num, validator_hotkey
            )
            block_yield = self.yield_repo.get_by_block_and_validator(
                block_num, validator_hotkey
            )
            attributions = self.attribution_repo.get_by_block(
                block_num, validator_hotkey
            )
            
            results["blocks_checked"] += 1
            block_valid = True
            
            # Skip if no source data
            if not snapshot or not block_yield:
                continue
            
            # Check attribution count matches delegation count
            if len(attributions) != len(snapshot.delegations):
                block_valid = False
                results["issues"].append({
                    "block": block_num,
                    "issue": "count_mismatch",
                    "expected": len(snapshot.delegations),
                    "actual": len(attributions)
                })
            
            # Check total attributed matches yield
            total_attributed = sum(a.attributed_dtao for a in attributions)
            if total_attributed != block_yield.total_dtao_earned:
                block_valid = False
                results["issues"].append({
                    "block": block_num,
                    "issue": "total_mismatch",
                    "expected": str(block_yield.total_dtao_earned),
                    "actual": str(total_attributed)
                })
            
            # Check each delegator has an attribution
            attribution_addresses = {a.delegator_address for a in attributions}
            delegation_addresses = {d.delegator_address for d in snapshot.delegations}
            
            missing = delegation_addresses - attribution_addresses
            if missing:
                block_valid = False
                results["issues"].append({
                    "block": block_num,
                    "issue": "missing_attributions",
                    "addresses": list(missing)[:10]  # Limit size
                })
            
            if block_valid:
                results["blocks_valid"] += 1
            else:
                results["blocks_invalid"] += 1
        
        return results
