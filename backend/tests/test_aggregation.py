"""Tests for rakeback.services.aggregation."""

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from db.enums import CompletenessFlag, PeriodType
from db.models import (
    BlockAttributions,
    BlockSnapshots,
    ConversionEvents,
    RakebackParticipants,
)
from rakeback.services._helpers import dump_json, new_id, now_iso
from rakeback.services._types import LedgerSummaryDict
from rakeback.services.aggregation import AggregationResult, AggregationService

VHK: str = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUPZHb"


def _seed_participant(
    session: Session, pid: str = "partner-test", addresses: list[str] | None = None
) -> RakebackParticipants:
    rules: list[dict[str, object]] = [{"type": "ALL"}]
    if addresses:
        rules = [{"type": "EXACT_ADDRESS", "addresses": addresses}]
    ts: str = now_iso()
    p: RakebackParticipants = RakebackParticipants(
        id=pid,
        name="Test",
        type="PARTNER",
        matching_rules=dump_json({"rules": rules}),
        rakeback_percentage=0.5,
        effective_from="2020-01-01",
        payout_address="5FHne...",
        priority=1,
        created_at=ts,
        updated_at=ts,
    )
    session.add(p)
    session.flush()
    return p


def _seed_snapshot(session: Session, block: int, ts: str = "2026-01-15T00:00:00") -> None:
    s: BlockSnapshots = BlockSnapshots(
        block_number=block,
        validator_hotkey=VHK,
        block_hash="0x" + "a" * 64,
        timestamp=ts,
        ingestion_timestamp=now_iso(),
        total_stake=Decimal("1000"),
    )
    session.add(s)
    session.flush()


def _seed_attribution(
    session: Session, block: int, delegator: str, dtao: Decimal, run_id: str = "run-1"
) -> None:
    a: BlockAttributions = BlockAttributions(
        id=new_id(),
        block_number=block,
        validator_hotkey=VHK,
        delegator_address=delegator,
        delegation_type="ROOT_TAO",
        attributed_dtao=dtao,
        delegation_proportion=Decimal("1"),
        completeness_flag=CompletenessFlag.COMPLETE.value,
        computation_timestamp=now_iso(),
        run_id=run_id,
    )
    session.add(a)
    session.flush()


def _seed_conversion(session: Session, block: int, dtao: Decimal, tao: Decimal) -> None:
    c: ConversionEvents = ConversionEvents(
        id=new_id(),
        block_number=block,
        transaction_hash="0x" + new_id()[:60],
        validator_hotkey=VHK,
        dtao_amount=dtao,
        tao_amount=tao,
        conversion_rate=(tao / dtao) if dtao else Decimal(0),
        ingestion_timestamp=now_iso(),
    )
    session.add(c)
    session.flush()


class TestAggregateDailyNoData:
    def test_no_participants(self, session: Session) -> None:
        svc: AggregationService = AggregationService(session)
        result: AggregationResult = svc.aggregate_daily(date(2026, 1, 15), VHK)
        assert result.entries_created == 0
        assert "No active rakeback participants" in result.warnings[0]

    def test_no_snapshots(self, session: Session) -> None:
        _seed_participant(session)
        svc: AggregationService = AggregationService(session)
        result: AggregationResult = svc.aggregate_daily(date(2026, 1, 15), VHK)
        assert result.entries_created == 0
        assert any("No snapshots" in w for w in result.warnings)


class TestAggregateDailyWithData:
    def test_single_delegator(self, session: Session) -> None:
        _seed_participant(session, addresses=["delegator-1"])
        _seed_snapshot(session, 1000, "2026-01-15T00:00:00")
        _seed_attribution(session, 1000, "delegator-1", Decimal("100"))
        _seed_conversion(session, 1000, Decimal("200"), Decimal("50"))

        svc: AggregationService = AggregationService(session)
        result: AggregationResult = svc.aggregate_daily(date(2026, 1, 15), VHK)

        assert result.entries_created == 1
        assert result.total_tao_owed > 0
        assert result.period_type == PeriodType.DAILY

    def test_no_match_creates_no_entries(self, session: Session) -> None:
        _seed_participant(session, addresses=["other-delegator"])
        _seed_snapshot(session, 1000, "2026-01-15T00:00:00")
        _seed_attribution(session, 1000, "delegator-1", Decimal("100"))

        svc: AggregationService = AggregationService(session)
        result: AggregationResult = svc.aggregate_daily(date(2026, 1, 15), VHK)
        assert result.entries_created == 0


class TestAggregateMonthly:
    def test_monthly_period_range(self, session: Session) -> None:
        _seed_participant(session, addresses=["d1"])
        _seed_snapshot(session, 1000, "2026-01-10T00:00:00")
        _seed_attribution(session, 1000, "d1", Decimal("100"))
        _seed_conversion(session, 1000, Decimal("100"), Decimal("10"))

        svc: AggregationService = AggregationService(session)
        result: AggregationResult = svc.aggregate_monthly(2026, 1, VHK)

        assert result.period_start == date(2026, 1, 1)
        assert result.period_end == date(2026, 1, 31)
        assert result.period_type == PeriodType.MONTHLY


class TestLedgerSummary:
    def test_empty_summary(self, session: Session) -> None:
        svc: AggregationService = AggregationService(session)
        summary: LedgerSummaryDict = svc.get_ledger_summary()
        assert summary["total_entries"] == 0
        assert summary["total_tao_owed"] == "0"
