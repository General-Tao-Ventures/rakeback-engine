"""Tests for rakeback.services.export."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from db.enums import CompletenessFlag, PaymentStatus, PeriodType
from db.models import RakebackLedgerEntries
from rakeback.services._helpers import new_id, now_iso
from rakeback.services._types import ExportDataDict, ExportListDict, SummaryReportDict
from rakeback.services.export import ExportService


def _seed_ledger_entry(session: Session, **overrides: object) -> RakebackLedgerEntries:
    ts: str = now_iso()
    defaults: dict[str, object] = {
        "id": new_id(),
        "period_type": PeriodType.DAILY.value,
        "period_start": "2026-01-15",
        "period_end": "2026-01-15",
        "participant_id": "partner-test",
        "participant_type": "PARTNER",
        "validator_hotkey": "5FHne...",
        "gross_dtao_attributed": 100.0,
        "gross_tao_converted": 10.0,
        "rakeback_percentage": 0.5,
        "tao_owed": 5.0,
        "payment_status": PaymentStatus.UNPAID.value,
        "completeness_flag": CompletenessFlag.COMPLETE.value,
        "run_id": "run-1",
        "created_at": ts,
        "updated_at": ts,
    }
    defaults.update(overrides)
    entry: RakebackLedgerEntries = RakebackLedgerEntries(**defaults)
    session.add(entry)
    session.flush()
    return entry


class TestListExports:
    def test_empty(self, session: Session) -> None:
        svc: ExportService = ExportService(session)
        result: ExportListDict = svc.list_exports()
        assert result["exports"] == []


class TestGenerateExport:
    def test_json_format(self, session: Session) -> None:
        _seed_ledger_entry(session)
        svc: ExportService = ExportService(session)
        result: ExportDataDict = svc.generate_export("json")
        assert result["format"] == "json"
        assert result["record_count"] == 1
        assert len(result["data"]) == 1

    def test_csv_format(self, session: Session) -> None:
        _seed_ledger_entry(session)
        svc: ExportService = ExportService(session)
        result: ExportDataDict = svc.generate_export("csv")
        assert result["format"] == "csv"
        assert result["record_count"] == 1
        assert "participant_id" in result["content"]

    def test_filter_by_partner(self, session: Session) -> None:
        _seed_ledger_entry(session, participant_id="partner-a")
        _seed_ledger_entry(session, participant_id="partner-b")
        svc: ExportService = ExportService(session)
        result: ExportDataDict = svc.generate_export("json", partner_id="partner-a")
        assert result["record_count"] == 1


class TestMarkEntriesPaid:
    def test_marks_unpaid(self, session: Session) -> None:
        e: RakebackLedgerEntries = _seed_ledger_entry(session)
        svc: ExportService = ExportService(session)
        count: int = svc.mark_entries_paid([e.id], "0xabc123")
        assert count == 1

        session.expire(e)
        assert e.payment_status == PaymentStatus.PAID.value
        assert e.payment_tx_hash == "0xabc123"

    def test_skips_already_paid(self, session: Session) -> None:
        e: RakebackLedgerEntries = _seed_ledger_entry(
            session,
            payment_status=PaymentStatus.PAID.value,
        )
        svc: ExportService = ExportService(session)
        count: int = svc.mark_entries_paid([e.id], "0xnew")
        assert count == 0


class TestSummaryReport:
    def test_with_entries(self, session: Session) -> None:
        _seed_ledger_entry(session, tao_owed=10.0, participant_id="partner-a")
        _seed_ledger_entry(
            session,
            tao_owed=5.0,
            participant_id="partner-b",
            payment_status=PaymentStatus.PAID.value,
        )
        svc: ExportService = ExportService(session)
        report: SummaryReportDict = svc.generate_summary_report(
            PeriodType.DAILY,
            date(2026, 1, 1),
            date(2026, 1, 31),
        )
        assert report["totals"]["entries"] == 2
        assert Decimal(report["totals"]["total_tao_owed"]) == Decimal("15")
