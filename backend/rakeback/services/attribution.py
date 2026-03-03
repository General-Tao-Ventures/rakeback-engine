"""Attribution engine for block-by-block yield distribution."""

from collections.abc import Sequence
from decimal import ROUND_DOWN, Decimal

import structlog
from sqlalchemy import ColumnElement, Select, and_, func, select
from sqlalchemy.orm import Session, joinedload

from db.enums import CompletenessFlag, GapType, ResolutionStatus, RunStatus, RunType
from db.models import (
    BlockAttributions,
    BlockSnapshots,
    BlockYields,
    DataGaps,
    ProcessingRuns,
)
from rakeback.services._helpers import dump_json, new_id, now_iso
from rakeback.services._types import (
    AttributionDict,
    AttributionStatsDict,
    BlockDetailDict,
    DetailedAttributionStatsDict,
    ValidationIssue,
    ValidationResultDict,
)
from rakeback.services.errors import (
    AttributionError,  # noqa: F401 — re-exported for backward compat
    AttributionIncompleteDataError,
    AttributionValidationError,
)
from rakeback.services.schemas.results import AttributionResult as AttributionResult

# Backward-compatible re-exports
IncompleteDataError = AttributionIncompleteDataError
ValidationError = AttributionValidationError

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


PROPORTION_PRECISION: Decimal = Decimal("1E-15")


class AttributionEngine:
    """Computes block-by-block yield attribution."""

    def __init__(self, session: Session) -> None:
        self.session: Session = session

    def _create_run(
        self,
        run_type: RunType,
        validator_hotkey: str,
        block_range: tuple[int, int] | None = None,
    ) -> ProcessingRuns:
        run: ProcessingRuns = ProcessingRuns(
            run_id=new_id(),
            run_type=run_type.value,
            started_at=now_iso(),
            status=RunStatus.RUNNING.value,
            validator_hotkey=validator_hotkey,
        )
        if block_range:
            run.block_range_start = block_range[0]
            run.block_range_end = block_range[1]
        self.session.add(run)
        self.session.flush()
        return run

    def _attribution_exists_for_block(self, block_number: int, vhk: str) -> bool:
        stmt = (
            select(func.count())
            .select_from(BlockAttributions)
            .where(
                and_(
                    BlockAttributions.block_number == block_number,
                    BlockAttributions.validator_hotkey == vhk,
                )
            )
        )
        return (self.session.scalar(stmt) or 0) > 0

    def _get_snapshot(self, block_number: int, vhk: str) -> BlockSnapshots | None:
        stmt: Select[tuple[BlockSnapshots]] = (
            select(BlockSnapshots)
            .where(
                and_(
                    BlockSnapshots.block_number == block_number,
                    BlockSnapshots.validator_hotkey == vhk,
                )
            )
            .options(joinedload(BlockSnapshots.delegations))
        )
        return self.session.scalar(stmt)

    def _get_yield(self, block_number: int, vhk: str) -> BlockYields | None:
        stmt: Select[tuple[BlockYields]] = select(BlockYields).where(
            and_(
                BlockYields.block_number == block_number,
                BlockYields.validator_hotkey == vhk,
            )
        )
        return self.session.scalar(stmt)

    def _get_attributions_for_block(self, block_number: int, vhk: str) -> list[BlockAttributions]:
        stmt: Select[tuple[BlockAttributions]] = (
            select(BlockAttributions)
            .where(
                and_(
                    BlockAttributions.block_number == block_number,
                    BlockAttributions.validator_hotkey == vhk,
                )
            )
            .order_by(BlockAttributions.delegator_address)
        )
        return list(self.session.scalars(stmt).all())

    def _get_attributions_range(
        self, start: int, end: int, vhk: str | None = None, subnet_id: int | None = None
    ) -> list[BlockAttributions]:
        conditions: list[ColumnElement[bool]] = [
            BlockAttributions.block_number >= start,
            BlockAttributions.block_number <= end,
        ]
        if vhk:
            conditions.append(BlockAttributions.validator_hotkey == vhk)
        if subnet_id is not None:
            conditions.append(BlockAttributions.subnet_id == subnet_id)
        stmt: Select[tuple[BlockAttributions]] = (
            select(BlockAttributions)
            .where(and_(*conditions))
            .order_by(BlockAttributions.block_number, BlockAttributions.delegator_address)
        )
        return list(self.session.scalars(stmt).all())

    def _get_attributed_by_delegator(self, start: int, end: int, vhk: str) -> dict[str, Decimal]:
        stmt = (
            select(
                BlockAttributions.delegator_address,
                func.sum(BlockAttributions.attributed_dtao),
            )
            .where(
                and_(
                    BlockAttributions.block_number >= start,
                    BlockAttributions.block_number <= end,
                    BlockAttributions.validator_hotkey == vhk,
                )
            )
            .group_by(BlockAttributions.delegator_address)
        )
        return {addr: Decimal(str(amt)) for addr, amt in self.session.execute(stmt).all()}

    def _record_gap(
        self,
        gap_type: GapType,
        block_start: int,
        block_end: int,
        vhk: str,
        reason: str,
        run_id: str,
    ) -> None:
        existing: Sequence[DataGaps] = self.session.scalars(
            select(DataGaps).where(
                and_(
                    DataGaps.block_start <= block_end,
                    DataGaps.block_end >= block_start,
                    DataGaps.gap_type == gap_type.value,
                )
            )
        ).all()
        for gap in existing:
            if gap.validator_hotkey == vhk and gap.resolution_status == ResolutionStatus.OPEN.value:
                if block_start < gap.block_start or block_end > gap.block_end:
                    gap.block_start = min(gap.block_start, block_start)
                    gap.block_end = max(gap.block_end, block_end)
                    self.session.flush()
                return

        gap_record: DataGaps = DataGaps(
            id=new_id(),
            gap_type=gap_type.value,
            block_start=block_start,
            block_end=block_end,
            validator_hotkey=vhk,
            reason=reason,
            resolution_status=ResolutionStatus.OPEN.value,
            created_at=now_iso(),
            detected_by_run_id=run_id,
        )
        self.session.add(gap_record)
        self.session.flush()

    def _merge_overlapping_gaps(self, gap_type: GapType, vhk: str | None = None) -> int:
        conditions: list[ColumnElement[bool]] = [
            DataGaps.resolution_status == ResolutionStatus.OPEN.value,
            DataGaps.gap_type == gap_type.value,
        ]
        if vhk:
            conditions.append(DataGaps.validator_hotkey == vhk)
        stmt: Select[tuple[DataGaps]] = (
            select(DataGaps).where(and_(*conditions)).order_by(DataGaps.block_start)
        )
        gaps: list[DataGaps] = list(self.session.scalars(stmt).all())
        if len(gaps) <= 1:
            return len(gaps)

        merged: list[DataGaps] = []
        current: DataGaps = gaps[0]
        for gap in gaps[1:]:
            if gap.block_start <= current.block_end + 1:
                current.block_end = max(current.block_end, gap.block_end)
                current.reason = f"{current.reason}; {gap.reason}"
                self.session.delete(gap)
            else:
                merged.append(current)
                current = gap
        merged.append(current)
        self.session.flush()
        return len(merged)

    def consolidate_gaps(self, vhk: str | None = None) -> dict[str, int]:
        results: dict[str, int] = {}
        for gt in GapType:
            results[gt.value] = self._merge_overlapping_gaps(gt, vhk)
        return results

    def run_attribution(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str,
        skip_existing: bool = True,
        fail_on_incomplete: bool = False,
        dry_run: bool = False,
    ) -> AttributionResult:
        run: ProcessingRuns = self._create_run(
            RunType.ATTRIBUTION, validator_hotkey, (start_block, end_block)
        )

        blocks_processed: int = 0
        attributions_created: int = 0
        blocks_skipped: int = 0
        blocks_incomplete: int = 0
        total_dtao: Decimal = Decimal(0)
        errors: list[str] = []
        completeness: dict[str, int] = {
            CompletenessFlag.COMPLETE.value: 0,
            CompletenessFlag.PARTIAL.value: 0,
            CompletenessFlag.INCOMPLETE.value: 0,
        }

        for block_num in range(start_block, end_block + 1):
            try:
                if skip_existing and self._attribution_exists_for_block(
                    block_num, validator_hotkey
                ):
                    blocks_skipped += 1
                    continue

                result: tuple[int, Decimal, CompletenessFlag] | None = self._attribute_block(
                    block_num, validator_hotkey, run.run_id, dry_run
                )
                blocks_processed += 1

                if result is None:
                    blocks_incomplete += 1
                    completeness[CompletenessFlag.INCOMPLETE.value] += 1
                    if fail_on_incomplete:
                        raise IncompleteDataError(f"Missing data for block {block_num}")
                else:
                    count: int
                    dtao: Decimal
                    flag: CompletenessFlag
                    count, dtao, flag = result
                    attributions_created += count
                    total_dtao += dtao
                    completeness[flag.value] = completeness.get(flag.value, 0) + 1

            except AttributionError as e:
                errors.append(f"Block {block_num}: {e}")
                if fail_on_incomplete:
                    raise
            except Exception as e:
                logger.exception("Unexpected error during attribution", block_number=block_num)
                errors.append(f"Block {block_num}: {e}")

        if not dry_run:
            gap_counts: dict[str, int] = self.consolidate_gaps(validator_hotkey)
            total_open_gaps: int = sum(gap_counts.values())
        else:
            total_open_gaps = 0

        run.records_processed = blocks_processed
        run.records_created = attributions_created
        run.records_skipped = blocks_skipped
        run.completeness_summary = dump_json(
            {
                **completeness,
                "incomplete_blocks": blocks_incomplete,
                "total_dtao_attributed": str(total_dtao),
                "open_gaps": total_open_gaps,
            }
        )

        if errors:
            run.status = (
                RunStatus.PARTIAL.value if attributions_created > 0 else RunStatus.FAILED.value
            )
            run.error_details = dump_json({"errors": errors[:100]})
        else:
            run.status = RunStatus.SUCCESS.value
        run.completed_at = now_iso()

        if not dry_run:
            self.session.flush()

        return AttributionResult(
            run_id=run.run_id,
            blocks_processed=blocks_processed,
            attributions_created=attributions_created,
            blocks_skipped=blocks_skipped,
            blocks_incomplete=blocks_incomplete,
            total_dtao_attributed=total_dtao,
            completeness_summary=completeness,
            errors=errors,
        )

    def _attribute_block(
        self,
        block_number: int,
        vhk: str,
        run_id: str,
        dry_run: bool,
    ) -> tuple[int, Decimal, CompletenessFlag] | None:
        snapshot: BlockSnapshots | None = self._get_snapshot(block_number, vhk)
        if not snapshot:
            if not dry_run:
                self._record_gap(
                    GapType.SNAPSHOT,
                    block_number,
                    block_number,
                    vhk,
                    "Missing snapshot during attribution",
                    run_id,
                )
            return None

        block_yield: BlockYields | None = self._get_yield(block_number, vhk)
        if not block_yield:
            if not dry_run:
                self._record_gap(
                    GapType.YIELD,
                    block_number,
                    block_number,
                    vhk,
                    "Missing yield during attribution",
                    run_id,
                )
            return None

        yield_earned: Decimal = Decimal(str(block_yield.total_dtao_earned))
        if yield_earned == 0:
            return (0, Decimal(0), CompletenessFlag.COMPLETE)

        if not snapshot.delegations:
            return (0, Decimal(0), CompletenessFlag.PARTIAL)

        total_proportion: Decimal = sum(
            (Decimal(str(d.proportion)) for d in snapshot.delegations), Decimal(0)
        )
        if abs(total_proportion - Decimal(1)) > PROPORTION_PRECISION:
            raise ValidationError(
                f"Block {block_number}: Proportions sum to {total_proportion}, expected 1.0"
            )

        snap_flag: CompletenessFlag = CompletenessFlag(snapshot.completeness_flag)
        yield_flag: CompletenessFlag = CompletenessFlag(block_yield.completeness_flag)
        completeness: CompletenessFlag = self._compute_completeness(snap_flag, yield_flag)

        attributions: list[BlockAttributions] = []
        total_attributed: Decimal = Decimal(0)

        for d in snapshot.delegations:
            proportion: Decimal = Decimal(str(d.proportion))
            attributed_dtao: Decimal = (yield_earned * proportion).quantize(
                Decimal("1"), rounding=ROUND_DOWN
            )
            total_attributed += attributed_dtao

            attr: BlockAttributions = BlockAttributions(
                id=new_id(),
                block_number=block_number,
                validator_hotkey=vhk,
                delegator_address=d.delegator_address,
                delegation_type=d.delegation_type,
                subnet_id=d.subnet_id,
                attributed_dtao=attributed_dtao,
                delegation_proportion=proportion,
                completeness_flag=completeness.value,
                computation_timestamp=now_iso(),
                run_id=run_id,
                tao_allocated=Decimal(0),
                fully_allocated=0,
            )
            attributions.append(attr)

        remainder: Decimal = yield_earned - total_attributed
        if remainder > 0 and attributions:
            largest: BlockAttributions = max(attributions, key=lambda a: a.attributed_dtao)
            largest.attributed_dtao = Decimal(str(largest.attributed_dtao)) + remainder
            total_attributed += remainder

        if total_attributed != yield_earned:
            raise ValidationError(
                f"Block {block_number}: Attribution total {total_attributed} "
                f"doesn't match yield {yield_earned}"
            )

        if not dry_run:
            for attr in attributions:
                self.session.add(attr)

        return (len(attributions), total_attributed, completeness)

    @staticmethod
    def _compute_completeness(*flags: CompletenessFlag) -> CompletenessFlag:
        for flag in flags:
            if flag in (
                CompletenessFlag.MISSING,
                CompletenessFlag.PARTIAL,
                CompletenessFlag.INCOMPLETE,
            ):
                return CompletenessFlag.INCOMPLETE
        return CompletenessFlag.COMPLETE

    def list_attributions(
        self,
        start: int = 0,
        end: int = 0,
        validator_hotkey: str | None = None,
        subnet_id: int | None = None,
    ) -> list[AttributionDict]:
        rows: list[BlockAttributions] = self._get_attributions_range(
            start, end, validator_hotkey, subnet_id
        )
        return [
            AttributionDict(
                id=r.id,
                block_number=r.block_number,
                validator_hotkey=r.validator_hotkey,
                delegator_address=r.delegator_address,
                delegation_type=r.delegation_type,
                subnet_id=r.subnet_id,
                attributed_dtao=str(r.attributed_dtao),
                delegation_proportion=str(r.delegation_proportion),
                completeness_flag=r.completeness_flag,
                tao_allocated=str(r.tao_allocated),
                fully_allocated=bool(r.fully_allocated),
            )
            for r in rows
        ]

    def get_stats(
        self, start: int = 0, end: int = 0, validator_hotkey: str | None = None
    ) -> AttributionStatsDict:
        rows: list[BlockAttributions] = self._get_attributions_range(start, end, validator_hotkey)
        if not rows:
            return AttributionStatsDict(
                total_blocks=max(end - start + 1, 0),
                blocks_with_attributions=0,
                total_attributions=0,
                total_dtao_attributed="0",
                unique_delegators=0,
            )
        blocks: set[int] = set()
        delegators: set[str] = set()
        total_dtao: Decimal = Decimal(0)
        for r in rows:
            blocks.add(r.block_number)
            delegators.add(r.delegator_address)
            total_dtao += Decimal(str(r.attributed_dtao))
        return AttributionStatsDict(
            total_blocks=max(end - start + 1, 0),
            blocks_with_attributions=len(blocks),
            total_attributions=len(rows),
            total_dtao_attributed=str(total_dtao),
            unique_delegators=len(delegators),
        )

    def get_block_detail(
        self, block_number: int, validator_hotkey: str | None = None
    ) -> BlockDetailDict | None:
        conditions: list[ColumnElement[bool]] = [
            BlockAttributions.block_number == block_number,
        ]
        if validator_hotkey:
            conditions.append(BlockAttributions.validator_hotkey == validator_hotkey)
        stmt: Select[tuple[BlockAttributions]] = (
            select(BlockAttributions)
            .where(and_(*conditions))
            .order_by(BlockAttributions.delegator_address)
        )
        rows: Sequence[BlockAttributions] = self.session.scalars(stmt).all()
        if not rows:
            return None

        vhk: str = rows[0].validator_hotkey
        snapshot: BlockSnapshots | None = self._get_snapshot(block_number, vhk)
        total_dtao: Decimal = sum((Decimal(str(r.attributed_dtao)) for r in rows), Decimal(0))

        return BlockDetailDict(
            block_number=block_number,
            timestamp=snapshot.timestamp if snapshot else None,
            validator_hotkey=vhk,
            total_dtao=str(total_dtao),
            delegator_count=len(rows),
            completeness_flag=rows[0].completeness_flag,
            attributions=[
                AttributionDict(
                    id=r.id,
                    block_number=r.block_number,
                    validator_hotkey=r.validator_hotkey,
                    delegator_address=r.delegator_address,
                    delegation_type=r.delegation_type,
                    subnet_id=r.subnet_id,
                    attributed_dtao=str(r.attributed_dtao),
                    delegation_proportion=str(r.delegation_proportion),
                    completeness_flag=r.completeness_flag,
                    tao_allocated=str(r.tao_allocated),
                    fully_allocated=bool(r.fully_allocated),
                )
                for r in rows
            ],
        )

    def get_attribution_stats(
        self, start_block: int, end_block: int, validator_hotkey: str
    ) -> DetailedAttributionStatsDict:
        rows: list[BlockAttributions] = self._get_attributions_range(
            start_block, end_block, validator_hotkey
        )
        if not rows:
            return DetailedAttributionStatsDict(
                block_range=(start_block, end_block),
                total_blocks=end_block - start_block + 1,
                blocks_with_attributions=0,
                total_attributions=0,
                total_dtao_attributed=Decimal(0),
                unique_delegators=0,
                completeness={},
                by_delegation_type={},
            )
        blocks_with_attr: set[int] = set()
        delegators: set[str] = set()
        total_dtao: Decimal = Decimal(0)
        by_dtype: dict[str, Decimal] = {}
        by_completeness: dict[str, int] = {}
        for a in rows:
            blocks_with_attr.add(a.block_number)
            delegators.add(a.delegator_address)
            dtao: Decimal = Decimal(str(a.attributed_dtao))
            total_dtao += dtao
            by_dtype[a.delegation_type] = by_dtype.get(a.delegation_type, Decimal(0)) + dtao
            by_completeness[a.completeness_flag] = by_completeness.get(a.completeness_flag, 0) + 1
        return DetailedAttributionStatsDict(
            block_range=(start_block, end_block),
            total_blocks=end_block - start_block + 1,
            blocks_with_attributions=len(blocks_with_attr),
            total_attributions=len(rows),
            total_dtao_attributed=total_dtao,
            unique_delegators=len(delegators),
            completeness=by_completeness,
            by_delegation_type={k: str(v) for k, v in by_dtype.items()},
        )

    def validate_attributions(
        self, start_block: int, end_block: int, validator_hotkey: str
    ) -> ValidationResultDict:
        blocks_checked: int = 0
        blocks_valid: int = 0
        blocks_invalid: int = 0
        issues: list[ValidationIssue] = []
        for bn in range(start_block, end_block + 1):
            snapshot: BlockSnapshots | None = self._get_snapshot(bn, validator_hotkey)
            block_yield: BlockYields | None = self._get_yield(bn, validator_hotkey)
            attribs: list[BlockAttributions] = self._get_attributions_for_block(
                bn, validator_hotkey
            )
            blocks_checked += 1
            if not snapshot or not block_yield:
                continue
            valid: bool = True
            if len(attribs) != len(snapshot.delegations):
                valid = False
                issues.append(
                    ValidationIssue(
                        block=bn,
                        issue="count_mismatch",
                        expected=len(snapshot.delegations),
                        actual=len(attribs),
                    )
                )
            total: Decimal = sum((Decimal(str(a.attributed_dtao)) for a in attribs), Decimal(0))
            if total != Decimal(str(block_yield.total_dtao_earned)):
                valid = False
                issues.append(
                    ValidationIssue(
                        block=bn,
                        issue="total_mismatch",
                        expected=str(block_yield.total_dtao_earned),
                        actual=str(total),
                    )
                )
            if valid:
                blocks_valid += 1
            else:
                blocks_invalid += 1
        return ValidationResultDict(
            blocks_checked=blocks_checked,
            blocks_valid=blocks_valid,
            blocks_invalid=blocks_invalid,
            issues=issues,
        )
