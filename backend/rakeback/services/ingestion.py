"""Ingestion service for fetching and storing chain data."""

import csv
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

import structlog
from sqlalchemy import ColumnElement, Select, and_, delete, func, select
from sqlalchemy.orm import Session, joinedload

from db.enums import (
    CompletenessFlag,
    DataSource,
    DelegationType,
    GapType,
    ResolutionStatus,
    RunStatus,
    RunType,
)
from db.models import (
    BlockSnapshots,
    BlockYields,
    ConversionEvents,
    DataGaps,
    DelegationEntries,
    ProcessingRuns,
    YieldSources,
)
from rakeback.services._helpers import dump_json, new_id, now_iso
from rakeback.services._types import AllocationDict, ConversionDetailDict, ConversionDict
from rakeback.services.chain_client import ChainClient
from rakeback.services.errors import (
    BlockNotFoundError,
    ChainClientError,
    CSVImportError,  # noqa: F401 — re-exported for backward compat
    IngestionError,
)
from rakeback.services.schemas.results import IngestionResult as IngestionResult

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class IngestionService:
    """Ingests chain data (snapshots, yields, conversions) into the database."""

    def __init__(self, session: Session, chain_client: ChainClient | None = None) -> None:
        self.session: Session = session
        self.chain_client: ChainClient = chain_client or ChainClient()

    def _create_run(
        self,
        run_type: RunType,
        validator_hotkey: str | None = None,
        block_range: tuple[int, int] | None = None,
        config_snapshot: dict[str, str] | None = None,
    ) -> ProcessingRuns:
        run: ProcessingRuns = ProcessingRuns(
            run_id=new_id(),
            run_type=run_type.value,
            started_at=now_iso(),
            status=RunStatus.RUNNING.value,
            validator_hotkey=validator_hotkey,
            config_snapshot=dump_json(config_snapshot) if config_snapshot else None,
        )
        if block_range:
            run.block_range_start = block_range[0]
            run.block_range_end = block_range[1]
        self.session.add(run)
        self.session.flush()
        return run

    def _snapshot_exists(self, block_number: int, vhk: str) -> bool:
        stmt = (
            select(func.count())
            .select_from(BlockSnapshots)
            .where(
                and_(
                    BlockSnapshots.block_number == block_number,
                    BlockSnapshots.validator_hotkey == vhk,
                )
            )
        )
        return (self.session.scalar(stmt) or 0) > 0

    def _conversion_exists_for_tx(self, tx_hash: str) -> bool:
        stmt = (
            select(func.count())
            .select_from(ConversionEvents)
            .where(ConversionEvents.transaction_hash == tx_hash)
        )
        return (self.session.scalar(stmt) or 0) > 0

    def _create_snapshot(
        self,
        block_number: int,
        vhk: str,
        block_hash: str,
        timestamp: str,
        delegations: list[dict[str, object]],
        data_source: DataSource,
        completeness_flag: CompletenessFlag,
    ) -> BlockSnapshots:
        total_stake: Decimal = sum(
            (Decimal(str(d.get("balance_dtao", 0))) for d in delegations),
            Decimal(0),
        )
        snap: BlockSnapshots = BlockSnapshots(
            block_number=block_number,
            validator_hotkey=vhk,
            block_hash=block_hash,
            timestamp=timestamp,
            ingestion_timestamp=now_iso(),
            data_source=data_source.value,
            completeness_flag=completeness_flag.value,
            total_stake=total_stake,
        )
        for d in delegations:
            balance: Decimal = Decimal(str(d.get("balance_dtao", 0)))
            proportion: Decimal = balance / total_stake if total_stake > 0 else Decimal(0)
            entry: DelegationEntries = DelegationEntries(
                id=new_id(),
                block_number=block_number,
                validator_hotkey=vhk,
                delegator_address=d["delegator_address"],
                delegation_type=DelegationType(str(d["delegation_type"]).upper()).value,
                subnet_id=d.get("subnet_id"),
                balance_dtao=balance,
                balance_tao=Decimal(str(d["balance_tao"])) if d.get("balance_tao") else None,
                proportion=proportion,
            )
            snap.delegations.append(entry)
        self.session.add(snap)
        self.session.flush()
        return snap

    def _create_yield(
        self,
        block_number: int,
        vhk: str,
        total_dtao_earned: Decimal,
        yield_sources: list[dict[str, object]] | None,
        data_source: DataSource,
        completeness_flag: CompletenessFlag,
    ) -> BlockYields:
        by: BlockYields = BlockYields(
            block_number=block_number,
            validator_hotkey=vhk,
            total_dtao_earned=total_dtao_earned,
            data_source=data_source.value,
            completeness_flag=completeness_flag.value,
            ingestion_timestamp=now_iso(),
        )
        if yield_sources:
            for src in yield_sources:
                ys: YieldSources = YieldSources(
                    id=new_id(),
                    block_number=block_number,
                    validator_hotkey=vhk,
                    subnet_id=src["subnet_id"],
                    dtao_amount=Decimal(str(src["dtao_amount"])),
                )
                by.yield_sources.append(ys)
        self.session.add(by)
        self.session.flush()
        return by

    def _delete_snapshot_range(self, start: int, end: int, vhk: str) -> int:
        stmt = delete(BlockSnapshots).where(
            and_(
                BlockSnapshots.block_number >= start,
                BlockSnapshots.block_number <= end,
                BlockSnapshots.validator_hotkey == vhk,
            )
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return int(result.rowcount)  # type: ignore[attr-defined]

    def _delete_yield_range(self, start: int, end: int, vhk: str) -> int:
        stmt = delete(BlockYields).where(
            and_(
                BlockYields.block_number >= start,
                BlockYields.block_number <= end,
                BlockYields.validator_hotkey == vhk,
            )
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return int(result.rowcount)  # type: ignore[attr-defined]

    def _record_gap(self, start: int, end: int, vhk: str, reason: str, run_id: str) -> None:
        existing: Sequence[DataGaps] = self.session.scalars(
            select(DataGaps).where(
                and_(
                    DataGaps.block_start <= end,
                    DataGaps.block_end >= start,
                    DataGaps.gap_type == GapType.SNAPSHOT.value,
                )
            )
        ).all()
        for g in existing:
            if g.validator_hotkey == vhk and g.block_start <= start and g.block_end >= end:
                return
        gap: DataGaps = DataGaps(
            id=new_id(),
            gap_type=GapType.SNAPSHOT.value,
            block_start=start,
            block_end=end,
            reason=reason,
            validator_hotkey=vhk,
            resolution_status=ResolutionStatus.OPEN.value,
            created_at=now_iso(),
            detected_by_run_id=run_id,
        )
        self.session.add(gap)
        self.session.flush()

    def ingest_block_range(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str,
        skip_existing: bool = True,
        fail_on_error: bool = False,
    ) -> IngestionResult:
        run: ProcessingRuns = self._create_run(
            RunType.INGESTION,
            validator_hotkey,
            (start_block, end_block),
        )

        if not self.chain_client.is_connected():
            self.chain_client.connect()

        blocks_processed: int = 0
        blocks_created: int = 0
        blocks_skipped: int = 0
        gaps: list[tuple[int, int]] = []
        errors: list[str] = []
        completeness: dict[str, int] = {
            CompletenessFlag.COMPLETE.value: 0,
            CompletenessFlag.PARTIAL.value: 0,
            CompletenessFlag.MISSING.value: 0,
        }
        current_gap_start: int | None = None

        for block_num in range(start_block, end_block + 1):
            try:
                if skip_existing and self._snapshot_exists(block_num, validator_hotkey):
                    blocks_skipped += 1
                    continue

                result: CompletenessFlag | None = self._ingest_single_block(
                    block_num,
                    validator_hotkey,
                )
                blocks_processed += 1

                if result:
                    blocks_created += 1
                    completeness[result.value] = completeness.get(result.value, 0) + 1
                    if current_gap_start is not None:
                        gaps.append((current_gap_start, block_num - 1))
                        self._record_gap(
                            current_gap_start,
                            block_num - 1,
                            validator_hotkey,
                            "Block data unavailable",
                            run.run_id,
                        )
                        current_gap_start = None
                else:
                    if current_gap_start is None:
                        current_gap_start = block_num
                    completeness[CompletenessFlag.MISSING.value] += 1

            except BlockNotFoundError as e:
                if current_gap_start is None:
                    current_gap_start = block_num
                errors.append(f"Block {block_num}: not found")
                if fail_on_error:
                    raise IngestionError(f"Block {block_num} not found") from e
            except ChainClientError as e:
                errors.append(f"Block {block_num}: {e}")
                if fail_on_error:
                    raise IngestionError(f"Chain error at block {block_num}") from e
            except Exception as e:
                logger.exception("Unexpected error during ingestion", block_number=block_num)
                errors.append(f"Block {block_num}: {e}")
                if fail_on_error:
                    raise

        if current_gap_start is not None:
            gaps.append((current_gap_start, end_block))
            self._record_gap(
                current_gap_start,
                end_block,
                validator_hotkey,
                "Block data unavailable",
                run.run_id,
            )

        run.records_processed = blocks_processed
        run.records_created = blocks_created
        run.records_skipped = blocks_skipped
        run.completeness_summary = dump_json(completeness)
        if errors:
            run.status = RunStatus.PARTIAL.value if blocks_created > 0 else RunStatus.FAILED.value
            run.error_details = dump_json({"errors": errors[:100]})
        else:
            run.status = RunStatus.SUCCESS.value
        run.completed_at = now_iso()
        self.session.flush()

        return IngestionResult(
            run_id=run.run_id,
            blocks_processed=blocks_processed,
            blocks_created=blocks_created,
            blocks_skipped=blocks_skipped,
            gaps_detected=gaps,
            completeness_summary=completeness,
            errors=errors,
        )

    def _ingest_single_block(self, block_number: int, vhk: str) -> CompletenessFlag | None:
        state = self.chain_client.get_validator_state(block_number, vhk)
        if not state or not state.delegations:
            return None

        delegations: list[dict[str, object]] = [
            {
                "delegator_address": d.delegator_address,
                "delegation_type": d.delegation_type,
                "subnet_id": d.subnet_id,
                "balance_dtao": d.balance_dtao,
                "balance_tao": d.balance_tao,
            }
            for d in state.delegations
        ]

        self._create_snapshot(
            block_number=block_number,
            vhk=vhk,
            block_hash=state.block_hash,
            timestamp=state.timestamp.isoformat(),
            delegations=delegations,
            data_source=DataSource.CHAIN,
            completeness_flag=CompletenessFlag.COMPLETE,
        )

        yield_data = self.chain_client.get_block_yield(block_number, vhk)
        if yield_data:
            sources: list[dict[str, object]] = [
                {"subnet_id": sid, "dtao_amount": amt}
                for sid, amt in yield_data.yield_by_subnet.items()
            ]
            self._create_yield(
                block_number=block_number,
                vhk=vhk,
                total_dtao_earned=yield_data.total_dtao_earned,
                yield_sources=sources or None,
                data_source=DataSource.CHAIN,
                completeness_flag=CompletenessFlag.COMPLETE,
            )

        return CompletenessFlag.COMPLETE

    def ingest_conversions(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str | None = None,
    ) -> IngestionResult:
        run: ProcessingRuns = self._create_run(
            RunType.INGESTION,
            validator_hotkey,
            (start_block, end_block),
        )

        if not self.chain_client.is_connected():
            self.chain_client.connect()

        events_created: int = 0
        events_skipped: int = 0
        errors: list[str] = []

        try:
            conversions = self.chain_client.get_conversion_events(
                start_block, end_block, validator_hotkey
            )
            for conv in conversions:
                if self._conversion_exists_for_tx(conv.transaction_hash):
                    events_skipped += 1
                    continue
                event: ConversionEvents = ConversionEvents(
                    id=new_id(),
                    block_number=conv.block_number,
                    transaction_hash=conv.transaction_hash,
                    validator_hotkey=conv.validator_hotkey,
                    dtao_amount=Decimal(str(conv.dtao_amount)),
                    tao_amount=Decimal(str(conv.tao_amount)),
                    conversion_rate=Decimal(str(conv.conversion_rate)),
                    subnet_id=conv.subnet_id,
                    data_source=DataSource.CHAIN.value,
                    ingestion_timestamp=now_iso(),
                    fully_allocated=0,
                )
                self.session.add(event)
                events_created += 1

            run.records_created = events_created
            run.records_skipped = events_skipped
            run.status = RunStatus.SUCCESS.value
            run.completed_at = now_iso()
        except Exception as e:
            logger.exception("Error ingesting conversions")
            errors.append(str(e))
            run.status = RunStatus.FAILED.value
            run.error_details = dump_json({"error": str(e)})
            run.completed_at = now_iso()

        self.session.flush()

        return IngestionResult(
            run_id=run.run_id,
            blocks_processed=end_block - start_block + 1,
            blocks_created=events_created,
            blocks_skipped=events_skipped,
            gaps_detected=[],
            completeness_summary={},
            errors=errors,
        )

    def import_snapshot_csv(self, csv_path: Path, validator_hotkey: str) -> IngestionResult:
        run: ProcessingRuns = self._create_run(
            RunType.INGESTION,
            validator_hotkey,
            config_snapshot={"csv_path": str(csv_path), "type": "snapshot_override"},
        )
        blocks_created: int = 0
        errors: list[str] = []
        blocks_data: dict[int, dict[str, object]] = {}

        try:
            with open(csv_path, newline="") as f:
                reader: csv.DictReader[str] = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=2):
                    try:
                        bn: int = int(row["block_number"])
                        if bn not in blocks_data:
                            blocks_data[bn] = {
                                "block_hash": row["block_hash"],
                                "timestamp": row["timestamp"],
                                "delegations": [],
                            }
                        deleg_list: object = blocks_data[bn]["delegations"]
                        if isinstance(deleg_list, list):
                            deleg_list.append(
                                {
                                    "delegator_address": row["delegator_address"],
                                    "delegation_type": row["delegation_type"],
                                    "subnet_id": (
                                        int(row["subnet_id"]) if row.get("subnet_id") else None
                                    ),
                                    "balance_dtao": Decimal(row["balance_dtao"]),
                                    "balance_tao": (
                                        Decimal(row["balance_tao"])
                                        if row.get("balance_tao")
                                        else None
                                    ),
                                }
                            )
                    except (KeyError, ValueError) as e:
                        errors.append(f"Row {row_num}: {e}")

            for bn, data in sorted(blocks_data.items()):
                self._delete_snapshot_range(bn, bn, validator_hotkey)
                delegs: object = data["delegations"]
                self._create_snapshot(
                    block_number=bn,
                    vhk=validator_hotkey,
                    block_hash=str(data["block_hash"]),
                    timestamp=str(data["timestamp"]),
                    delegations=delegs if isinstance(delegs, list) else [],
                    data_source=DataSource.CSV_OVERRIDE,
                    completeness_flag=CompletenessFlag.COMPLETE,
                )
                blocks_created += 1

            run.records_created = blocks_created
            run.status = RunStatus.SUCCESS.value if not errors else RunStatus.PARTIAL.value
            if errors:
                run.error_details = dump_json({"parse_errors": errors[:100]})
        except Exception as e:
            logger.exception("Error importing CSV")
            errors.append(str(e))
            run.status = RunStatus.FAILED.value
            run.error_details = dump_json({"error": str(e)})

        run.completed_at = now_iso()
        self.session.flush()

        return IngestionResult(
            run_id=run.run_id,
            blocks_processed=len(blocks_data),
            blocks_created=blocks_created,
            blocks_skipped=0,
            gaps_detected=[],
            completeness_summary={CompletenessFlag.COMPLETE.value: blocks_created},
            errors=errors,
        )

    def import_yield_csv(self, csv_path: Path, validator_hotkey: str) -> IngestionResult:
        run: ProcessingRuns = self._create_run(
            RunType.INGESTION,
            validator_hotkey,
            config_snapshot={"csv_path": str(csv_path), "type": "yield_override"},
        )
        yields_created: int = 0
        errors: list[str] = []
        blocks_data: dict[int, dict[str, object]] = {}

        try:
            with open(csv_path, newline="") as f:
                reader: csv.DictReader[str] = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=2):
                    try:
                        bn: int = int(row["block_number"])
                        if bn not in blocks_data:
                            blocks_data[bn] = {
                                "total_dtao_earned": Decimal(row["total_dtao_earned"]),
                                "sources": [],
                            }
                        if row.get("subnet_id") and row.get("subnet_dtao"):
                            src_list: object = blocks_data[bn]["sources"]
                            if isinstance(src_list, list):
                                src_list.append(
                                    {
                                        "subnet_id": int(row["subnet_id"]),
                                        "dtao_amount": Decimal(row["subnet_dtao"]),
                                    }
                                )
                    except (KeyError, ValueError) as e:
                        errors.append(f"Row {row_num}: {e}")

            for bn, data in sorted(blocks_data.items()):
                self._delete_yield_range(bn, bn, validator_hotkey)
                sources: object = data["sources"]
                self._create_yield(
                    block_number=bn,
                    vhk=validator_hotkey,
                    total_dtao_earned=Decimal(str(data["total_dtao_earned"])),
                    yield_sources=sources if isinstance(sources, list) else None,
                    data_source=DataSource.CSV_OVERRIDE,
                    completeness_flag=CompletenessFlag.COMPLETE,
                )
                yields_created += 1

            run.records_created = yields_created
            run.status = RunStatus.SUCCESS.value if not errors else RunStatus.PARTIAL.value
        except Exception as e:
            logger.exception("Error importing yield CSV")
            errors.append(str(e))
            run.status = RunStatus.FAILED.value
            run.error_details = dump_json({"error": str(e)})

        run.completed_at = now_iso()
        self.session.flush()

        return IngestionResult(
            run_id=run.run_id,
            blocks_processed=len(blocks_data),
            blocks_created=yields_created,
            blocks_skipped=0,
            gaps_detected=[],
            completeness_summary={CompletenessFlag.COMPLETE.value: yields_created},
            errors=errors,
        )

    def list_conversions(
        self, start_block: int | None = None, end_block: int | None = None
    ) -> list[ConversionDict]:
        conditions: list[ColumnElement[bool]] = []
        if start_block is not None:
            conditions.append(ConversionEvents.block_number >= start_block)
        if end_block is not None:
            conditions.append(ConversionEvents.block_number <= end_block)
        stmt: Select[tuple[ConversionEvents]] = select(ConversionEvents).order_by(
            ConversionEvents.block_number,
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        rows: Sequence[ConversionEvents] = self.session.scalars(stmt).all()
        return [
            ConversionDict(
                id=r.id,
                block_number=r.block_number,
                transaction_hash=r.transaction_hash,
                validator_hotkey=r.validator_hotkey,
                dtao_amount=str(r.dtao_amount),
                tao_amount=str(r.tao_amount),
                conversion_rate=str(r.conversion_rate),
                subnet_id=r.subnet_id,
                fully_allocated=bool(r.fully_allocated),
                tao_price=None,
            )
            for r in rows
        ]

    def get_conversion_detail(self, conversion_id: str) -> ConversionDetailDict | None:
        stmt: Select[tuple[ConversionEvents]] = (
            select(ConversionEvents)
            .where(ConversionEvents.id == conversion_id)
            .options(joinedload(ConversionEvents.allocations))
        )
        event: ConversionEvents | None = self.session.scalar(stmt)
        if not event:
            return None
        return ConversionDetailDict(
            conversion=ConversionDict(
                id=event.id,
                block_number=event.block_number,
                transaction_hash=event.transaction_hash,
                validator_hotkey=event.validator_hotkey,
                dtao_amount=str(event.dtao_amount),
                tao_amount=str(event.tao_amount),
                conversion_rate=str(event.conversion_rate),
                subnet_id=event.subnet_id,
                fully_allocated=bool(event.fully_allocated),
                tao_price=None,
            ),
            allocations=[
                AllocationDict(
                    id=a.id,
                    conversion_event_id=a.conversion_event_id,
                    block_attribution_id=a.block_attribution_id,
                    tao_allocated=str(a.tao_allocated),
                    allocation_method=a.allocation_method,
                    completeness_flag=a.completeness_flag,
                )
                for a in (event.allocations or [])
            ],
        )
