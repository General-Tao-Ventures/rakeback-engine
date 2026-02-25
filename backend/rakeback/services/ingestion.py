"""Ingestion service for fetching and storing chain data."""

import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import structlog
from sqlalchemy import select, and_, func, delete
from sqlalchemy.orm import Session, joinedload

from db.enums import CompletenessFlag, DataSource, DelegationType, GapType, ResolutionStatus, RunStatus, RunType
from db.models import (
    BlockSnapshots,
    BlockYields,
    ConversionEvents,
    DataGaps,
    DelegationEntries,
    ProcessingRuns,
    TaoAllocations,
    YieldSources,
)
from rakeback.services._helpers import dump_json, new_id, now_iso
from rakeback.services.chain_client import ChainClient, ChainClientError, BlockNotFoundError

logger = structlog.get_logger(__name__)


class IngestionError(Exception):
    pass


class CSVImportError(IngestionError):
    pass


@dataclass
class IngestionResult:
    run_id: str
    blocks_processed: int
    blocks_created: int
    blocks_skipped: int
    gaps_detected: list[tuple[int, int]]
    completeness_summary: dict[str, int]
    errors: list[str]


class IngestionService:
    """Ingests chain data (snapshots, yields, conversions) into the database."""

    def __init__(self, session: Session, chain_client: Optional[ChainClient] = None):
        self.session = session
        self.chain_client = chain_client or ChainClient()

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def _create_run(
        self,
        run_type: RunType,
        validator_hotkey: Optional[str] = None,
        block_range: Optional[tuple[int, int]] = None,
        config_snapshot: Optional[dict] = None,
    ) -> ProcessingRuns:
        run = ProcessingRuns(
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
        delegations: list[dict],
        data_source: DataSource,
        completeness_flag: CompletenessFlag,
    ) -> BlockSnapshots:
        total_stake = sum(Decimal(str(d.get("balance_dtao", 0))) for d in delegations)
        snap = BlockSnapshots(
            block_number=block_number,
            validator_hotkey=vhk,
            block_hash=block_hash,
            timestamp=timestamp,
            ingestion_timestamp=now_iso(),
            data_source=data_source.value,
            completeness_flag=completeness_flag.value,
            total_stake=float(total_stake),
        )
        for d in delegations:
            balance = Decimal(str(d.get("balance_dtao", 0)))
            proportion = balance / total_stake if total_stake > 0 else Decimal(0)
            entry = DelegationEntries(
                id=new_id(),
                block_number=block_number,
                validator_hotkey=vhk,
                delegator_address=d["delegator_address"],
                delegation_type=DelegationType(d["delegation_type"].upper()).value,
                subnet_id=d.get("subnet_id"),
                balance_dtao=float(balance),
                balance_tao=float(d["balance_tao"]) if d.get("balance_tao") else None,
                proportion=float(proportion),
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
        yield_sources: Optional[list[dict]],
        data_source: DataSource,
        completeness_flag: CompletenessFlag,
    ) -> BlockYields:
        by = BlockYields(
            block_number=block_number,
            validator_hotkey=vhk,
            total_dtao_earned=float(total_dtao_earned),
            data_source=data_source.value,
            completeness_flag=completeness_flag.value,
            ingestion_timestamp=now_iso(),
        )
        if yield_sources:
            for src in yield_sources:
                ys = YieldSources(
                    id=new_id(),
                    block_number=block_number,
                    validator_hotkey=vhk,
                    subnet_id=src["subnet_id"],
                    dtao_amount=float(Decimal(str(src["dtao_amount"]))),
                )
                by.yield_sources.append(ys)
        self.session.add(by)
        self.session.flush()
        return by

    def _delete_snapshot_range(self, start: int, end: int, vhk: str) -> int:
        stmt = (
            delete(BlockSnapshots)
            .where(
                and_(
                    BlockSnapshots.block_number >= start,
                    BlockSnapshots.block_number <= end,
                    BlockSnapshots.validator_hotkey == vhk,
                )
            )
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount

    def _delete_yield_range(self, start: int, end: int, vhk: str) -> int:
        stmt = (
            delete(BlockYields)
            .where(
                and_(
                    BlockYields.block_number >= start,
                    BlockYields.block_number <= end,
                    BlockYields.validator_hotkey == vhk,
                )
            )
        )
        result = self.session.execute(stmt)
        self.session.flush()
        return result.rowcount

    def _record_gap(
        self, start: int, end: int, vhk: str, reason: str, run_id: str
    ) -> None:
        existing = self.session.scalars(
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
        gap = DataGaps(
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

    # ------------------------------------------------------------------
    # Block ingestion
    # ------------------------------------------------------------------

    def ingest_block_range(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: str,
        skip_existing: bool = True,
        fail_on_error: bool = False,
    ) -> IngestionResult:
        run = self._create_run(RunType.INGESTION, validator_hotkey, (start_block, end_block))

        if not self.chain_client.is_connected():
            self.chain_client.connect()

        blocks_processed = 0
        blocks_created = 0
        blocks_skipped = 0
        gaps: list[tuple[int, int]] = []
        errors: list[str] = []
        completeness: dict[str, int] = {
            CompletenessFlag.COMPLETE.value: 0,
            CompletenessFlag.PARTIAL.value: 0,
            CompletenessFlag.MISSING.value: 0,
        }
        current_gap_start: Optional[int] = None

        for block_num in range(start_block, end_block + 1):
            try:
                if skip_existing and self._snapshot_exists(block_num, validator_hotkey):
                    blocks_skipped += 1
                    continue

                result = self._ingest_single_block(block_num, validator_hotkey)
                blocks_processed += 1

                if result:
                    blocks_created += 1
                    completeness[result.value] = completeness.get(result.value, 0) + 1
                    if current_gap_start is not None:
                        gaps.append((current_gap_start, block_num - 1))
                        self._record_gap(
                            current_gap_start, block_num - 1, validator_hotkey,
                            "Block data unavailable", run.run_id,
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
                current_gap_start, end_block, validator_hotkey,
                "Block data unavailable", run.run_id,
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

    def _ingest_single_block(
        self, block_number: int, vhk: str
    ) -> Optional[CompletenessFlag]:
        state = self.chain_client.get_validator_state(block_number, vhk)
        if not state or not state.delegations:
            return None

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
            sources = [
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

    # ------------------------------------------------------------------
    # Conversion ingestion
    # ------------------------------------------------------------------

    def ingest_conversions(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: Optional[str] = None,
    ) -> IngestionResult:
        run = self._create_run(RunType.INGESTION, validator_hotkey, (start_block, end_block))

        if not self.chain_client.is_connected():
            self.chain_client.connect()

        events_created = 0
        events_skipped = 0
        errors: list[str] = []

        try:
            conversions = self.chain_client.get_conversion_events(
                start_block, end_block, validator_hotkey
            )
            for conv in conversions:
                if self._conversion_exists_for_tx(conv.transaction_hash):
                    events_skipped += 1
                    continue
                event = ConversionEvents(
                    id=new_id(),
                    block_number=conv.block_number,
                    transaction_hash=conv.transaction_hash,
                    validator_hotkey=conv.validator_hotkey,
                    dtao_amount=float(conv.dtao_amount),
                    tao_amount=float(conv.tao_amount),
                    conversion_rate=float(conv.conversion_rate),
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

    # ------------------------------------------------------------------
    # CSV imports
    # ------------------------------------------------------------------

    def import_snapshot_csv(self, csv_path: Path, validator_hotkey: str) -> IngestionResult:
        run = self._create_run(
            RunType.INGESTION, validator_hotkey,
            config_snapshot={"csv_path": str(csv_path), "type": "snapshot_override"},
        )
        blocks_created = 0
        errors: list[str] = []
        blocks_data: dict = {}

        try:
            with open(csv_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=2):
                    try:
                        bn = int(row["block_number"])
                        if bn not in blocks_data:
                            blocks_data[bn] = {
                                "block_hash": row["block_hash"],
                                "timestamp": row["timestamp"],
                                "delegations": [],
                            }
                        blocks_data[bn]["delegations"].append(
                            {
                                "delegator_address": row["delegator_address"],
                                "delegation_type": row["delegation_type"],
                                "subnet_id": int(row["subnet_id"]) if row.get("subnet_id") else None,
                                "balance_dtao": Decimal(row["balance_dtao"]),
                                "balance_tao": Decimal(row["balance_tao"]) if row.get("balance_tao") else None,
                            }
                        )
                    except (KeyError, ValueError) as e:
                        errors.append(f"Row {row_num}: {e}")

            for bn, data in sorted(blocks_data.items()):
                self._delete_snapshot_range(bn, bn, validator_hotkey)
                self._create_snapshot(
                    block_number=bn,
                    vhk=validator_hotkey,
                    block_hash=data["block_hash"],
                    timestamp=data["timestamp"],
                    delegations=data["delegations"],
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
        run = self._create_run(
            RunType.INGESTION, validator_hotkey,
            config_snapshot={"csv_path": str(csv_path), "type": "yield_override"},
        )
        yields_created = 0
        errors: list[str] = []
        blocks_data: dict = {}

        try:
            with open(csv_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=2):
                    try:
                        bn = int(row["block_number"])
                        if bn not in blocks_data:
                            blocks_data[bn] = {
                                "total_dtao_earned": Decimal(row["total_dtao_earned"]),
                                "sources": [],
                            }
                        if row.get("subnet_id") and row.get("subnet_dtao"):
                            blocks_data[bn]["sources"].append(
                                {"subnet_id": int(row["subnet_id"]), "dtao_amount": Decimal(row["subnet_dtao"])}
                            )
                    except (KeyError, ValueError) as e:
                        errors.append(f"Row {row_num}: {e}")

            for bn, data in sorted(blocks_data.items()):
                self._delete_yield_range(bn, bn, validator_hotkey)
                self._create_yield(
                    block_number=bn,
                    vhk=validator_hotkey,
                    total_dtao_earned=data["total_dtao_earned"],
                    yield_sources=data["sources"] or None,
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

    # ------------------------------------------------------------------
    # Route-facing methods
    # ------------------------------------------------------------------

    def list_conversions(
        self, start_block: Optional[int] = None, end_block: Optional[int] = None
    ) -> list[dict]:
        conditions = []
        if start_block is not None:
            conditions.append(ConversionEvents.block_number >= start_block)
        if end_block is not None:
            conditions.append(ConversionEvents.block_number <= end_block)
        stmt = select(ConversionEvents).order_by(ConversionEvents.block_number)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        rows = self.session.scalars(stmt).all()
        return [
            {
                "id": r.id,
                "block_number": r.block_number,
                "transaction_hash": r.transaction_hash,
                "validator_hotkey": r.validator_hotkey,
                "dtao_amount": str(r.dtao_amount),
                "tao_amount": str(r.tao_amount),
                "conversion_rate": str(r.conversion_rate),
                "subnet_id": r.subnet_id,
                "fully_allocated": bool(r.fully_allocated),
                "tao_price": None,
            }
            for r in rows
        ]

    def get_conversion_detail(self, conversion_id: str) -> Optional[dict]:
        stmt = (
            select(ConversionEvents)
            .where(ConversionEvents.id == conversion_id)
            .options(joinedload(ConversionEvents.allocations))
        )
        event = self.session.scalar(stmt)
        if not event:
            return None
        return {
            "conversion": {
                "id": event.id,
                "block_number": event.block_number,
                "transaction_hash": event.transaction_hash,
                "validator_hotkey": event.validator_hotkey,
                "dtao_amount": str(event.dtao_amount),
                "tao_amount": str(event.tao_amount),
                "conversion_rate": str(event.conversion_rate),
                "subnet_id": event.subnet_id,
                "fully_allocated": bool(event.fully_allocated),
                "tao_price": None,
            },
            "allocations": [
                {
                    "id": a.id,
                    "conversion_event_id": a.conversion_event_id,
                    "block_attribution_id": a.block_attribution_id,
                    "tao_allocated": str(a.tao_allocated),
                    "allocation_method": a.allocation_method,
                    "completeness_flag": a.completeness_flag,
                }
                for a in (event.allocations or [])
            ],
        }
