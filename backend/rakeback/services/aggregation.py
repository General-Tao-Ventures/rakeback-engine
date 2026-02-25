"""Aggregation service for daily/monthly rakeback calculations."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from db.enums import (
    CompletenessFlag,
    GapType,
    PaymentStatus,
    PeriodType,
    ResolutionStatus,
    RunStatus,
    RunType,
)
from db.models import (
    BlockAttributions,
    BlockSnapshots,
    ConversionEvents,
    DataGaps,
    ProcessingRuns,
    RakebackLedgerEntries,
    RakebackParticipants,
)
from rakeback.services._helpers import dump_json, new_id, now_iso
from rakeback.services.rules_engine import RulesEngine

logger = structlog.get_logger(__name__)


class AggregationError(Exception):
    pass


class IncompleteDataError(AggregationError):
    pass


@dataclass
class AggregationResult:
    run_id: str
    period_type: PeriodType
    period_start: date
    period_end: date
    entries_created: int
    total_tao_owed: Decimal
    completeness_summary: dict
    warnings: list[str]


class AggregationService:
    """Aggregates attributions into rakeback ledger entries."""

    def __init__(self, session: Session, rules_engine: Optional[RulesEngine] = None):
        self.session = session
        self.rules_engine = rules_engine or RulesEngine(session)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def _create_run(
        self,
        run_type: RunType,
        validator_hotkey: Optional[str] = None,
        period: Optional[tuple[date, date]] = None,
    ) -> ProcessingRuns:
        run = ProcessingRuns(
            run_id=new_id(),
            run_type=run_type.value,
            started_at=now_iso(),
            status=RunStatus.RUNNING.value,
            validator_hotkey=validator_hotkey,
        )
        if period:
            run.period_start = period[0].isoformat()
            run.period_end = period[1].isoformat()
        self.session.add(run)
        self.session.flush()
        return run

    def _get_active_participants(self, as_of: date):
        d = as_of.isoformat()
        stmt = (
            select(RakebackParticipants)
            .where(
                and_(
                    RakebackParticipants.effective_from <= d,
                    (
                        (RakebackParticipants.effective_to.is_(None))
                        | (RakebackParticipants.effective_to >= d)
                    ),
                )
            )
            .order_by(RakebackParticipants.priority, RakebackParticipants.id)
        )
        return self.session.scalars(stmt).all()

    def _get_snapshots_by_date_range(self, start_dt: str, end_dt: str, vhk: str):
        stmt = (
            select(BlockSnapshots)
            .where(
                and_(
                    BlockSnapshots.timestamp >= start_dt,
                    BlockSnapshots.timestamp < end_dt,
                    BlockSnapshots.validator_hotkey == vhk,
                )
            )
            .order_by(BlockSnapshots.block_number)
        )
        return self.session.scalars(stmt).all()

    def _has_gaps_in_range(self, start: int, end: int, vhk: str) -> bool:
        stmt = (
            select(DataGaps)
            .where(
                and_(
                    DataGaps.block_start <= end,
                    DataGaps.block_end >= start,
                    DataGaps.resolution_status == ResolutionStatus.OPEN.value,
                    DataGaps.validator_hotkey == vhk,
                )
            )
            .limit(1)
        )
        return self.session.scalar(stmt) is not None

    def _get_attributed_by_delegator(
        self, start: int, end: int, vhk: str
    ) -> dict[str, Decimal]:
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

    def _get_total_tao_converted(self, start: int, end: int, vhk: str) -> Decimal:
        if start == 0:
            return Decimal(0)
        stmt = (
            select(func.sum(ConversionEvents.tao_amount))
            .where(
                and_(
                    ConversionEvents.block_number >= start,
                    ConversionEvents.block_number <= end,
                    ConversionEvents.validator_hotkey == vhk,
                )
            )
        )
        return Decimal(str(self.session.scalar(stmt) or 0))

    # ------------------------------------------------------------------
    # Core aggregation
    # ------------------------------------------------------------------

    def aggregate_daily(
        self, target_date: date, validator_hotkey: str, fail_on_incomplete: bool = False
    ) -> AggregationResult:
        return self._aggregate_period(
            PeriodType.DAILY, target_date, target_date, validator_hotkey, fail_on_incomplete
        )

    def aggregate_monthly(
        self, year: int, month: int, validator_hotkey: str, fail_on_incomplete: bool = False
    ) -> AggregationResult:
        period_start = date(year, month, 1)
        period_end = (
            date(year + 1, 1, 1) - timedelta(days=1)
            if month == 12
            else date(year, month + 1, 1) - timedelta(days=1)
        )
        return self._aggregate_period(
            PeriodType.MONTHLY, period_start, period_end, validator_hotkey, fail_on_incomplete
        )

    def _aggregate_period(
        self,
        period_type: PeriodType,
        period_start: date,
        period_end: date,
        validator_hotkey: str,
        fail_on_incomplete: bool,
    ) -> AggregationResult:
        run = self._create_run(RunType.AGGREGATION, validator_hotkey, (period_start, period_end))

        warnings: list[str] = []
        entries_created = 0
        total_tao_owed = Decimal(0)
        comp_summary = {
            "complete_entries": 0,
            "incomplete_entries": 0,
            "incomplete_blocks": [],
            "missing_conversions": False,
        }

        try:
            participants = self._get_active_participants(period_start)
            if not participants:
                warnings.append("No active rakeback participants found")
                run.status = RunStatus.SUCCESS.value
                run.completed_at = now_iso()
                self.session.flush()
                return AggregationResult(
                    run_id=run.run_id, period_type=period_type,
                    period_start=period_start, period_end=period_end,
                    entries_created=0, total_tao_owed=Decimal(0),
                    completeness_summary=comp_summary, warnings=warnings,
                )

            start_dt = datetime.combine(period_start, datetime.min.time()).isoformat()
            end_dt = datetime.combine(period_end + timedelta(days=1), datetime.min.time()).isoformat()

            snapshots = self._get_snapshots_by_date_range(start_dt, end_dt, validator_hotkey)
            if not snapshots:
                warnings.append("No snapshots found for period")
                if fail_on_incomplete:
                    raise IncompleteDataError("No snapshots for period")

            block_range = (
                (min(s.block_number for s in snapshots), max(s.block_number for s in snapshots))
                if snapshots
                else (0, 0)
            )

            if block_range[0] > 0 and self._has_gaps_in_range(
                block_range[0], block_range[1], validator_hotkey
            ):
                warnings.append("Data gaps detected in period")
                comp_summary["has_gaps"] = True

            attr_by_delegator = (
                self._get_attributed_by_delegator(block_range[0], block_range[1], validator_hotkey)
                if block_range[0] > 0
                else {}
            )

            total_tao_converted = self._get_total_tao_converted(
                block_range[0], block_range[1], validator_hotkey
            )

            for participant in participants:
                entry = self._create_ledger_entry(
                    participant=participant,
                    period_type=period_type,
                    period_start=period_start,
                    period_end=period_end,
                    validator_hotkey=validator_hotkey,
                    block_range=block_range,
                    attr_by_delegator=attr_by_delegator,
                    total_tao_converted=total_tao_converted,
                    run_id=run.run_id,
                )
                if entry:
                    self.session.add(entry)
                    entries_created += 1
                    total_tao_owed += Decimal(str(entry.tao_owed))
                    if entry.completeness_flag == CompletenessFlag.COMPLETE.value:
                        comp_summary["complete_entries"] += 1
                    else:
                        comp_summary["incomplete_entries"] += 1

            run.records_created = entries_created
            run.completeness_summary = dump_json(comp_summary)
            run.status = RunStatus.SUCCESS.value if not warnings else RunStatus.PARTIAL.value
        except Exception as e:
            logger.exception("Aggregation failed")
            warnings.append(str(e))
            run.status = RunStatus.FAILED.value
            run.error_details = dump_json({"error": str(e)})
            if fail_on_incomplete:
                raise

        run.completed_at = now_iso()
        self.session.flush()

        return AggregationResult(
            run_id=run.run_id,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            entries_created=entries_created,
            total_tao_owed=total_tao_owed,
            completeness_summary=comp_summary,
            warnings=warnings,
        )

    def _create_ledger_entry(
        self,
        participant: RakebackParticipants,
        period_type: PeriodType,
        period_start: date,
        period_end: date,
        validator_hotkey: str,
        block_range: tuple[int, int],
        attr_by_delegator: dict[str, Decimal],
        total_tao_converted: Decimal,
        run_id: str,
    ) -> Optional[RakebackLedgerEntries]:
        matched = self.rules_engine.match_addresses(
            participant, list(attr_by_delegator.keys())
        )
        if not matched:
            return None

        gross_dtao = sum(attr_by_delegator.get(a, Decimal(0)) for a in matched)
        if gross_dtao == 0:
            return None

        total_dtao = sum(attr_by_delegator.values())
        if total_dtao > 0 and total_tao_converted > 0:
            dtao_share = gross_dtao / total_dtao
            gross_tao = (total_tao_converted * dtao_share).quantize(Decimal("1"))
        else:
            gross_tao = Decimal(0)

        rakeback_pct = Decimal(str(participant.rakeback_percentage))
        tao_owed = (gross_tao * rakeback_pct).quantize(Decimal("1"))

        comp_flag = CompletenessFlag.COMPLETE
        comp_details: dict = {}
        if gross_dtao > 0 and gross_tao == 0:
            comp_flag = CompletenessFlag.INCOMPLETE
            comp_details["reason"] = "No TAO conversion data available"

        ts = now_iso()
        return RakebackLedgerEntries(
            id=new_id(),
            period_type=period_type.value,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            participant_id=participant.id,
            participant_type=participant.type,
            validator_hotkey=validator_hotkey,
            gross_dtao_attributed=float(gross_dtao),
            gross_tao_converted=float(gross_tao),
            rakeback_percentage=float(rakeback_pct),
            tao_owed=float(tao_owed),
            payment_status=PaymentStatus.UNPAID.value,
            completeness_flag=comp_flag.value,
            completeness_details=dump_json(comp_details) if comp_details else None,
            run_id=run_id,
            created_at=ts,
            updated_at=ts,
            block_count=block_range[1] - block_range[0] + 1 if block_range[0] > 0 else 0,
            attribution_count=len(matched),
        )

    # ------------------------------------------------------------------
    # Route-facing methods
    # ------------------------------------------------------------------

    def list_ledger_entries(
        self,
        partner_id: Optional[str] = None,
        period_type: Optional[str] = None,
    ) -> list[dict]:
        conditions = []
        if partner_id:
            conditions.append(RakebackLedgerEntries.participant_id == partner_id)
        if period_type:
            conditions.append(RakebackLedgerEntries.period_type == period_type.upper())
        stmt = select(RakebackLedgerEntries).order_by(
            RakebackLedgerEntries.period_start.desc()
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        rows = self.session.scalars(stmt).all()
        return [
            {
                "id": r.id,
                "period_type": r.period_type,
                "period_start": r.period_start,
                "period_end": r.period_end,
                "participant_id": r.participant_id,
                "participant_type": r.participant_type,
                "validator_hotkey": r.validator_hotkey,
                "gross_dtao_attributed": str(r.gross_dtao_attributed),
                "gross_tao_converted": str(r.gross_tao_converted),
                "rakeback_percentage": r.rakeback_percentage,
                "tao_owed": str(r.tao_owed),
                "payment_status": r.payment_status,
                "payment_tx_hash": r.payment_tx_hash,
                "payment_timestamp": r.payment_timestamp,
                "completeness_flag": r.completeness_flag,
                "block_count": r.block_count,
                "attribution_count": r.attribution_count,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in rows
        ]

    def get_ledger_summary(self, partner_id: Optional[str] = None) -> dict:
        conditions = []
        if partner_id:
            conditions.append(RakebackLedgerEntries.participant_id == partner_id)

        stmt = select(RakebackLedgerEntries)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        entries = self.session.scalars(stmt).all()

        total_owed = sum(Decimal(str(e.tao_owed)) for e in entries)
        total_paid = sum(
            Decimal(str(e.tao_owed))
            for e in entries
            if e.payment_status == PaymentStatus.PAID.value
        )
        total_outstanding = total_owed - total_paid
        complete = sum(
            1 for e in entries if e.completeness_flag == CompletenessFlag.COMPLETE.value
        )
        incomplete = len(entries) - complete

        return {
            "total_entries": len(entries),
            "total_tao_owed": str(total_owed),
            "total_tao_paid": str(total_paid),
            "total_tao_outstanding": str(total_outstanding),
            "complete_entries": complete,
            "incomplete_entries": incomplete,
        }
