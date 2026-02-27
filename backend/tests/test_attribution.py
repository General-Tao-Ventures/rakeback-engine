"""Tests for rakeback.services.attribution."""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from db.enums import CompletenessFlag, GapType
from db.models import (
    BlockAttributions,
    BlockSnapshots,
    BlockYields,
    DataGaps,
    DelegationEntries,
)
from rakeback.services._helpers import new_id, now_iso
from rakeback.services.attribution import (
    AttributionEngine,
    AttributionResult,
    ValidationError,
)

VHK: str = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUPZHb"


def _seed_snapshot(
    session: Session,
    block: int,
    delegations: list[tuple[str, Decimal]] | None = None,
    completeness: str = "COMPLETE",
) -> None:
    """Seed a snapshot with optional delegations (address, proportion) pairs."""
    snap = BlockSnapshots(
        block_number=block,
        validator_hotkey=VHK,
        block_hash="0x" + "a" * 64,
        timestamp="2026-01-15T00:00:00",
        ingestion_timestamp=now_iso(),
        completeness_flag=completeness,
        total_stake=Decimal("1000"),
    )
    session.add(snap)
    session.flush()

    if delegations:
        for addr, proportion in delegations:
            entry = DelegationEntries(
                id=new_id(),
                block_number=block,
                validator_hotkey=VHK,
                delegator_address=addr,
                delegation_type="ROOT_TAO",
                balance_dtao=Decimal("100"),
                proportion=proportion,
            )
            session.add(entry)
        session.flush()


def _seed_yield(
    session: Session,
    block: int,
    dtao: Decimal,
    completeness: str = "COMPLETE",
) -> None:
    by = BlockYields(
        block_number=block,
        validator_hotkey=VHK,
        total_dtao_earned=dtao,
        completeness_flag=completeness,
        ingestion_timestamp=now_iso(),
    )
    session.add(by)
    session.flush()


class TestSingleDelegator:
    def test_single_delegator_gets_100_percent(self, session: Session) -> None:
        _seed_snapshot(session, 100, [("delegator-A", Decimal("1"))])
        _seed_yield(session, 100, Decimal("1000"))

        engine = AttributionEngine(session)
        result: AttributionResult = engine.run_attribution(100, 100, VHK)

        assert result.attributions_created == 1
        assert result.total_dtao_attributed == Decimal("1000")

        rows = session.query(BlockAttributions).all()
        assert len(rows) == 1
        assert rows[0].attributed_dtao == Decimal("1000")
        assert rows[0].delegator_address == "delegator-A"


class TestMultipleDelegatorsEqual:
    def test_even_split(self, session: Session) -> None:
        _seed_snapshot(
            session,
            100,
            [
                ("delegator-A", Decimal("0.5")),
                ("delegator-B", Decimal("0.5")),
            ],
        )
        _seed_yield(session, 100, Decimal("1000"))

        engine = AttributionEngine(session)
        result = engine.run_attribution(100, 100, VHK)

        assert result.attributions_created == 2
        rows = session.query(BlockAttributions).order_by(BlockAttributions.delegator_address).all()
        assert rows[0].attributed_dtao == Decimal("500")
        assert rows[1].attributed_dtao == Decimal("500")


class TestUnequalProportionsRemainder:
    def test_round_down_remainder_to_largest(self, session: Session) -> None:
        # 3 delegators with unequal proportions — remainder goes to largest
        _seed_snapshot(
            session,
            100,
            [
                ("delegator-A", Decimal("0.5")),
                ("delegator-B", Decimal("0.3")),
                ("delegator-C", Decimal("0.2")),
            ],
        )
        # Yield of 7 with proportions 0.5/0.3/0.2 causes rounding:
        # ROUND_DOWN: 3, 2, 1 = 6 → remainder 1 goes to largest (A → 4)
        _seed_yield(session, 100, Decimal("7"))

        engine = AttributionEngine(session)
        result = engine.run_attribution(100, 100, VHK)

        assert result.attributions_created == 3
        rows = session.query(BlockAttributions).all()
        total = sum(r.attributed_dtao for r in rows)
        assert total == Decimal("7")


class TestSumAlwaysEqualsTotal:
    def test_sum_equals_yield(self, session: Session) -> None:
        _seed_snapshot(
            session,
            100,
            [
                ("d1", Decimal("0.7")),
                ("d2", Decimal("0.2")),
                ("d3", Decimal("0.1")),
            ],
        )
        _seed_yield(session, 100, Decimal("999"))

        engine = AttributionEngine(session)
        result = engine.run_attribution(100, 100, VHK)

        rows = session.query(BlockAttributions).all()
        total = sum(r.attributed_dtao for r in rows)
        assert total == Decimal("999")
        assert result.total_dtao_attributed == Decimal("999")


class TestZeroYield:
    def test_zero_yield_returns_complete_no_rows(self, session: Session) -> None:
        _seed_snapshot(session, 100, [("d1", Decimal("1"))])
        _seed_yield(session, 100, Decimal("0"))

        engine = AttributionEngine(session)
        result = engine.run_attribution(100, 100, VHK)

        assert result.attributions_created == 0
        assert result.total_dtao_attributed == Decimal("0")
        assert result.completeness_summary[CompletenessFlag.COMPLETE.value] == 1
        assert session.query(BlockAttributions).count() == 0


class TestNoDelegations:
    def test_no_delegations_returns_partial(self, session: Session) -> None:
        _seed_snapshot(session, 100, delegations=None)
        _seed_yield(session, 100, Decimal("1000"))

        engine = AttributionEngine(session)
        result = engine.run_attribution(100, 100, VHK)

        assert result.attributions_created == 0
        assert result.total_dtao_attributed == Decimal("0")
        assert result.completeness_summary[CompletenessFlag.PARTIAL.value] == 1


class TestMissingSnapshot:
    def test_missing_snapshot_records_gap(self, session: Session) -> None:
        # Only yield, no snapshot
        _seed_yield(session, 100, Decimal("1000"))

        engine = AttributionEngine(session)
        result = engine.run_attribution(100, 100, VHK)

        # Block returns None → counted as incomplete
        assert result.blocks_incomplete == 1
        gaps = session.query(DataGaps).filter(DataGaps.gap_type == GapType.SNAPSHOT.value).all()
        assert len(gaps) == 1
        assert gaps[0].block_start == 100


class TestMissingYield:
    def test_missing_yield_records_gap(self, session: Session) -> None:
        _seed_snapshot(session, 100, [("d1", Decimal("1"))])
        # No yield seeded

        engine = AttributionEngine(session)
        result = engine.run_attribution(100, 100, VHK)

        assert result.blocks_incomplete == 1
        gaps = session.query(DataGaps).filter(DataGaps.gap_type == GapType.YIELD.value).all()
        assert len(gaps) == 1
        assert gaps[0].block_start == 100


class TestCompletenessPropagation:
    def test_complete_plus_complete_is_complete(self, session: Session) -> None:
        _seed_snapshot(session, 100, [("d1", Decimal("1"))], completeness="COMPLETE")
        _seed_yield(session, 100, Decimal("100"), completeness="COMPLETE")

        engine = AttributionEngine(session)
        result = engine.run_attribution(100, 100, VHK)

        assert result.completeness_summary[CompletenessFlag.COMPLETE.value] == 1

    def test_complete_plus_partial_is_incomplete(self, session: Session) -> None:
        _seed_snapshot(session, 100, [("d1", Decimal("1"))], completeness="COMPLETE")
        _seed_yield(session, 100, Decimal("100"), completeness="PARTIAL")

        engine = AttributionEngine(session)
        result = engine.run_attribution(100, 100, VHK)

        assert result.completeness_summary[CompletenessFlag.INCOMPLETE.value] == 1

    def test_partial_plus_complete_is_incomplete(self, session: Session) -> None:
        _seed_snapshot(session, 100, [("d1", Decimal("1"))], completeness="PARTIAL")
        _seed_yield(session, 100, Decimal("100"), completeness="COMPLETE")

        engine = AttributionEngine(session)
        result = engine.run_attribution(100, 100, VHK)

        assert result.completeness_summary[CompletenessFlag.INCOMPLETE.value] == 1


class TestInvalidProportions:
    def test_proportions_not_summing_to_one_raises(self, session: Session) -> None:
        _seed_snapshot(
            session,
            100,
            [
                ("d1", Decimal("0.5")),
                ("d2", Decimal("0.3")),
            ],
        )
        _seed_yield(session, 100, Decimal("1000"))

        engine = AttributionEngine(session)
        with pytest.raises(ValidationError, match="Proportions sum to"):
            engine.run_attribution(100, 100, VHK, fail_on_incomplete=True)


class TestDryRun:
    def test_dry_run_no_rows_persisted(self, session: Session) -> None:
        _seed_snapshot(session, 100, [("d1", Decimal("1"))])
        _seed_yield(session, 100, Decimal("500"))

        engine = AttributionEngine(session)
        result = engine.run_attribution(100, 100, VHK, dry_run=True)

        assert result.attributions_created == 1
        assert result.total_dtao_attributed == Decimal("500")
        # No rows actually written
        assert session.query(BlockAttributions).count() == 0
