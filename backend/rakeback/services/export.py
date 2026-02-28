"""Export service for generating CSV / JSON reports and managing payments."""

import csv
import io
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path

import structlog
from sqlalchemy import ColumnElement, Select, and_, select
from sqlalchemy.orm import Session

from db.enums import (
    CompletenessFlag,
    PaymentStatus,
    PeriodType,
    RunStatus,
    RunType,
)
from db.models import ProcessingRuns, RakebackLedgerEntries
from rakeback.services._helpers import new_id, now_iso
from rakeback.services._types import (
    ExportDataDict,
    ExportListDict,
    ExportRunDict,
    SummaryPeriod,
    SummaryReportDict,
    SummaryTotals,
)
from rakeback.services.errors import ExportError  # noqa: F401 — re-exported
from rakeback.services.schemas.results import ExportResult

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class ExportService:
    """Exports rakeback data to CSV / JSON and manages payment marking."""

    def __init__(self, session: Session, export_dir: str = "exports") -> None:
        self.session: Session = session
        self.export_dir: Path = Path(export_dir)

    def _create_run(self, period: tuple[date, date] | None = None) -> ProcessingRuns:
        run: ProcessingRuns = ProcessingRuns(
            run_id=new_id(),
            run_type=RunType.EXPORT.value,
            started_at=now_iso(),
            status=RunStatus.RUNNING.value,
        )
        if period:
            run.period_start = period[0].isoformat()
            run.period_end = period[1].isoformat()
        self.session.add(run)
        self.session.flush()
        return run

    def _get_entries(
        self,
        period_type: PeriodType | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
        participant_id: str | None = None,
        include_incomplete: bool = True,
    ) -> list[RakebackLedgerEntries]:
        conditions: list[ColumnElement[bool]] = []
        if period_type:
            conditions.append(RakebackLedgerEntries.period_type == period_type.value)
        if period_start:
            conditions.append(RakebackLedgerEntries.period_start >= period_start.isoformat())
        if period_end:
            conditions.append(RakebackLedgerEntries.period_end <= period_end.isoformat())
        if participant_id:
            conditions.append(RakebackLedgerEntries.participant_id == participant_id)
        if not include_incomplete:
            conditions.append(
                RakebackLedgerEntries.completeness_flag == CompletenessFlag.COMPLETE.value
            )

        stmt: Select[tuple[RakebackLedgerEntries]] = select(RakebackLedgerEntries).order_by(
            RakebackLedgerEntries.period_start.desc()
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        return list(self.session.scalars(stmt).all())

    _CSV_COLUMNS = [
        "participant_id",
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
        "entry_id",
    ]

    def export_ledger_csv(
        self,
        period_type: PeriodType,
        period_start: date,
        period_end: date,
        output_path: Path | None = None,
        participant_ids: Sequence[str] | None = None,
        include_incomplete: bool = True,
    ) -> ExportResult:
        run: ProcessingRuns = self._create_run((period_start, period_end))

        if output_path is None:
            filename: str = (
                f"rakeback_{period_type.value}_{period_start.isoformat()}"
                f"_{period_end.isoformat()}.csv"
            )
            output_path = self.export_dir / filename

        output_path.parent.mkdir(parents=True, exist_ok=True)

        entries: list[RakebackLedgerEntries] = self._get_entries(
            period_type,
            period_start,
            period_end,
            include_incomplete=include_incomplete,
        )
        if participant_ids:
            ids_set: set[str] = set(participant_ids)
            entries = [e for e in entries if e.participant_id in ids_set]

        warnings: list[str] = []
        complete_count: int = 0
        incomplete_count: int = 0
        total_tao: Decimal = Decimal(0)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            writer.writerow([f"# Rakeback Ledger Export - {period_type.value}"])
            writer.writerow([f"# Generated: {now_iso()}"])
            writer.writerow([f"# Period: {period_start} to {period_end}"])
            writer.writerow([f"# Run ID: {run.run_id}"])
            writer.writerow([])

            incomplete: list[RakebackLedgerEntries] = [
                e for e in entries if e.completeness_flag != CompletenessFlag.COMPLETE.value
            ]
            if incomplete:
                writer.writerow(["# WARNING: This export contains incomplete data"])
                writer.writerow([f"# Incomplete entries: {len(incomplete)}"])
                warnings.append(f"{len(incomplete)} entries have incomplete data")
                writer.writerow([])

            writer.writerow(self._CSV_COLUMNS)

            for entry in entries:
                writer.writerow(
                    [
                        entry.participant_id,
                        entry.participant_type,
                        entry.validator_hotkey,
                        entry.period_start,
                        entry.period_end,
                        str(entry.gross_dtao_attributed),
                        str(entry.gross_tao_converted),
                        str(entry.rakeback_percentage),
                        str(entry.tao_owed),
                        entry.payment_status,
                        entry.payment_tx_hash or "",
                        entry.completeness_flag,
                        entry.block_count,
                        entry.attribution_count,
                        entry.id,
                    ]
                )
                total_tao += Decimal(str(entry.tao_owed))
                if entry.completeness_flag == CompletenessFlag.COMPLETE.value:
                    complete_count += 1
                else:
                    incomplete_count += 1

        run.records_created = len(entries)
        run.status = RunStatus.SUCCESS.value
        run.completed_at = now_iso()
        self.session.flush()

        return ExportResult(
            run_id=run.run_id,
            output_path=output_path,
            row_count=len(entries),
            complete_entries=complete_count,
            incomplete_entries=incomplete_count,
            total_tao=total_tao,
            warnings=warnings,
        )

    def export_audit_trail(
        self,
        ledger_entry_id: str,
        output_path: Path | None = None,
    ) -> ExportResult:
        entry: RakebackLedgerEntries | None = self.session.get(
            RakebackLedgerEntries, ledger_entry_id
        )
        if not entry:
            raise ExportError(f"Ledger entry {ledger_entry_id} not found")

        if output_path is None:
            filename: str = (
                f"audit_trail_{entry.participant_id}_{entry.period_start}_{entry.id[:8]}.csv"
            )
            output_path = self.export_dir / filename

        output_path.parent.mkdir(parents=True, exist_ok=True)
        warnings: list[str] = []

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["# Audit Trail Export"])
            writer.writerow([f"# Ledger Entry ID: {entry.id}"])
            writer.writerow([f"# Participant: {entry.participant_id}"])
            writer.writerow([f"# Period: {entry.period_start} to {entry.period_end}"])
            writer.writerow([f"# Generated: {now_iso()}"])
            writer.writerow([])
            writer.writerow(["# Summary"])
            writer.writerow(["Field", "Value"])
            writer.writerow(["Gross dTAO Attributed", str(entry.gross_dtao_attributed)])
            writer.writerow(["Gross TAO Converted", str(entry.gross_tao_converted)])
            writer.writerow(["Rakeback Percentage", str(entry.rakeback_percentage)])
            writer.writerow(["TAO Owed", str(entry.tao_owed)])
            writer.writerow(["Payment Status", entry.payment_status])
            writer.writerow(["Completeness", entry.completeness_flag])
            writer.writerow(["Block Count", entry.block_count])
            writer.writerow(["Attribution Count", entry.attribution_count])

        is_complete: bool = entry.completeness_flag == CompletenessFlag.COMPLETE.value
        return ExportResult(
            run_id="",
            output_path=output_path,
            row_count=1,
            complete_entries=1 if is_complete else 0,
            incomplete_entries=0 if is_complete else 1,
            total_tao=Decimal(str(entry.tao_owed)),
            warnings=warnings,
        )

    def mark_entries_paid(
        self,
        entry_ids: Sequence[str],
        payment_tx_hash: str,
        payment_timestamp: str | None = None,
    ) -> int:
        ts: str = payment_timestamp or now_iso()
        count: int = 0
        for eid in entry_ids:
            entry: RakebackLedgerEntries | None = self.session.get(RakebackLedgerEntries, eid)
            if entry and entry.payment_status != PaymentStatus.PAID.value:
                entry.payment_status = PaymentStatus.PAID.value
                entry.payment_tx_hash = payment_tx_hash
                entry.payment_timestamp = ts
                entry.updated_at = now_iso()
                count += 1
        self.session.flush()
        return count

    def generate_summary_report(
        self,
        period_type: PeriodType,
        period_start: date,
        period_end: date,
    ) -> SummaryReportDict:
        entries: list[RakebackLedgerEntries] = self._get_entries(
            period_type, period_start, period_end
        )

        total_dtao: Decimal = sum(
            (Decimal(str(e.gross_dtao_attributed)) for e in entries), Decimal(0)
        )
        total_tao_converted: Decimal = sum(
            (Decimal(str(e.gross_tao_converted)) for e in entries), Decimal(0)
        )
        total_tao_owed: Decimal = sum((Decimal(str(e.tao_owed)) for e in entries), Decimal(0))

        by_status: dict[str, int] = {}
        for e in entries:
            by_status[e.payment_status] = by_status.get(e.payment_status, 0) + 1

        by_completeness: dict[str, int] = {}
        for e in entries:
            flag = e.completeness_flag
            by_completeness[flag] = by_completeness.get(flag, 0) + 1

        by_participant: dict[str, dict[str, Decimal]] = {}
        for e in entries:
            pid = e.participant_id
            if pid not in by_participant:
                by_participant[pid] = {"dtao": Decimal(0), "tao_owed": Decimal(0)}
            by_participant[pid]["dtao"] += Decimal(str(e.gross_dtao_attributed))
            by_participant[pid]["tao_owed"] += Decimal(str(e.tao_owed))

        return SummaryReportDict(
            period=SummaryPeriod(
                type=period_type.value,
                start=period_start.isoformat(),
                end=period_end.isoformat(),
            ),
            totals=SummaryTotals(
                entries=len(entries),
                gross_dtao_attributed=str(total_dtao),
                gross_tao_converted=str(total_tao_converted),
                total_tao_owed=str(total_tao_owed),
            ),
            by_payment_status=by_status,
            by_completeness=by_completeness,
            by_participant={
                k: {"dtao": str(v["dtao"]), "tao_owed": str(v["tao_owed"])}
                for k, v in by_participant.items()
            },
        )

    def list_exports(self) -> ExportListDict:
        stmt: Select[tuple[ProcessingRuns]] = (
            select(ProcessingRuns)
            .where(ProcessingRuns.run_type == RunType.EXPORT.value)
            .order_by(ProcessingRuns.started_at.desc())
        )
        runs: Sequence[ProcessingRuns] = self.session.scalars(stmt).all()
        return ExportListDict(
            exports=[
                ExportRunDict(
                    id=r.run_id,
                    filename=(
                        f"rakeback_{r.period_start}_{r.period_end}.csv" if r.period_start else ""
                    ),
                    format="csv",
                    period_start=r.period_start or "",
                    period_end=r.period_end or "",
                    record_count=r.records_created or 0,
                    created_at=r.started_at,
                )
                for r in runs
            ],
        )

    def generate_export(
        self,
        fmt: str = "csv",
        period_start: str | None = None,
        period_end: str | None = None,
        partner_id: str | None = None,
    ) -> ExportDataDict:
        p_start: date | None = date.fromisoformat(period_start) if period_start else None
        p_end: date | None = date.fromisoformat(period_end) if period_end else None

        entries: list[RakebackLedgerEntries] = self._get_entries(
            period_start=p_start,
            period_end=p_end,
            participant_id=partner_id,
        )

        rows: list[dict[str, object]] = [
            {
                "id": e.id,
                "participant_id": e.participant_id,
                "participant_type": e.participant_type,
                "validator_hotkey": e.validator_hotkey,
                "period_start": e.period_start,
                "period_end": e.period_end,
                "gross_dtao_attributed": str(e.gross_dtao_attributed),
                "gross_tao_converted": str(e.gross_tao_converted),
                "rakeback_percentage": e.rakeback_percentage,
                "tao_owed": str(e.tao_owed),
                "payment_status": e.payment_status,
                "completeness_flag": e.completeness_flag,
            }
            for e in entries
        ]

        if fmt == "csv":
            buf: io.StringIO = io.StringIO()
            if rows:
                writer: csv.DictWriter[str] = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            return ExportDataDict(format="csv", content=buf.getvalue(), record_count=len(rows))

        return ExportDataDict(format="json", data=rows, record_count=len(rows))
