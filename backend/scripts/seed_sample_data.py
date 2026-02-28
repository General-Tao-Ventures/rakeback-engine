"""Seed sample data for local Docker testing.

Idempotent: skips seeding if partners already exist.
Run: python scripts/seed_sample_data.py
"""

import json
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# Ensure backend root is on sys.path so 'config' and 'db' resolve
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from sqlalchemy.orm import Session  # noqa: E402

from db.connection import get_session  # noqa: E402
from db.models import (  # noqa: E402
    BlockAttributions,
    BlockSnapshots,
    BlockYields,
    ConversionEvents,
    DataGaps,
    DelegationEntries,
    EligibilityRules,
    ProcessingRuns,
    RakebackLedgerEntries,
    RakebackParticipants,
    TaoPrices,
    YieldSources,
)


def _uid() -> str:
    return str(uuid4())


def _ts(days_ago: int = 0) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()


VHK = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUPZHb"
BASE_BLOCK = 4_500_000
DELEGATORS = [
    "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
    "5FLSigC9HGRKVhB9FiEo4Y3koPsNmBmLJbpXg2mp1hXcS59Y",
    "5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum3PTXFy",
    "5HGjWAeFDfFCWPsjFQdVV2Msvz2XtMktvgocEZcCj68kUMaw",
]


def seed(session: Session) -> None:
    # Check idempotency — skip if data exists
    existing = session.query(RakebackParticipants).first()
    if existing:
        print("Sample data already seeded — skipping.")
        return

    print("Seeding sample data...")

    # --- Partners ---
    partners = []
    partner_data = [
        (
            "Creative Builds",
            "PARTNER",
            "NAMED",
            Decimal("0.15"),
            "5Ew3MyB15VprZrjQVkpDGq8r2YhC55WwZ2yQ",
            1,
        ),
        (
            "Talisman",
            "PARTNER",
            "TAG_BASED",
            Decimal("0.10"),
            "5HYYeCa1Hae5YYGJ2pHskHLVrA7V5WjaSuS",
            2,
        ),
        (
            "Subnet Alpha Fund",
            "PARTNER",
            "HYBRID",
            Decimal("0.08"),
            "5CiPPseXPECbkjWCa6MnjNokrgYjMqmKndv",
            3,
        ),
    ]
    for name, ptype, partner_type, rate, payout, priority in partner_data:
        pid = _uid()
        rules = {"rules": [{"type": "ALL"}]}
        p = RakebackParticipants(
            id=pid,
            name=name,
            type=ptype,
            partner_type=partner_type,
            matching_rules=json.dumps(rules),
            rakeback_percentage=rate,
            effective_from="2026-01-01",
            payout_address=payout,
            priority=priority,
            created_at=_ts(30),
            updated_at=_ts(30),
        )
        session.add(p)
        partners.append(p)

        # Eligibility rule for each partner
        rule = EligibilityRules(
            id=_uid(),
            participant_id=pid,
            rule_type=(
                "wallet"
                if partner_type == "NAMED"
                else "memo"
                if partner_type == "TAG_BASED"
                else "subnet-filter"
            ),
            config=json.dumps({"type": "ALL"}),
            applies_from_block=BASE_BLOCK,
            created_at=_ts(30),
            created_by="admin",
        )
        session.add(rule)

    session.flush()

    # --- Block snapshots, yields, delegations, attributions ---
    run_id = _uid()
    for i in range(20):
        block = BASE_BLOCK + i
        ts = _ts(20 - i)

        # Snapshot
        snap = BlockSnapshots(
            block_number=block,
            validator_hotkey=VHK,
            block_hash="0x" + f"{block:064x}",
            timestamp=ts,
            ingestion_timestamp=ts,
            data_source="CHAIN",
            completeness_flag="COMPLETE" if i < 18 else "PARTIAL",
            total_stake=Decimal("25000.5"),
        )
        session.add(snap)
        session.flush()

        # Delegations (4 delegators with different proportions)
        proportions = [Decimal("0.40"), Decimal("0.30"), Decimal("0.20"), Decimal("0.10")]
        for addr, prop in zip(DELEGATORS, proportions, strict=True):
            d = DelegationEntries(
                id=_uid(),
                block_number=block,
                validator_hotkey=VHK,
                delegator_address=addr,
                delegation_type="ROOT_TAO",
                balance_dtao=Decimal("25000.5") * prop,
                proportion=prop,
            )
            session.add(d)

        # Yield
        dtao_earned = Decimal("12.5") + Decimal(str(i)) * Decimal("0.3")
        by = BlockYields(
            block_number=block,
            validator_hotkey=VHK,
            total_dtao_earned=dtao_earned,
            data_source="CHAIN",
            completeness_flag="COMPLETE" if i < 18 else "PARTIAL",
            ingestion_timestamp=ts,
        )
        session.add(by)

        # Yield source
        ys = YieldSources(
            id=_uid(),
            block_number=block,
            validator_hotkey=VHK,
            subnet_id=1,
            dtao_amount=dtao_earned,
        )
        session.add(ys)
        session.flush()

        # Attributions
        for addr, prop in zip(DELEGATORS, proportions, strict=True):
            attr = BlockAttributions(
                id=_uid(),
                block_number=block,
                validator_hotkey=VHK,
                delegator_address=addr,
                delegation_type="ROOT_TAO",
                attributed_dtao=dtao_earned * prop,
                delegation_proportion=prop,
                completeness_flag="COMPLETE" if i < 18 else "INCOMPLETE",
                computation_timestamp=ts,
                run_id=run_id,
            )
            session.add(attr)

    session.flush()

    # --- Conversion events ---
    for i in range(5):
        block = BASE_BLOCK + i * 4
        dtao = Decimal("50.0") + Decimal(str(i * 10))
        tao = dtao * Decimal("0.85")
        conv = ConversionEvents(
            id=_uid(),
            block_number=block,
            transaction_hash="0x" + _uid().replace("-", "") + f"{i:032x}",
            validator_hotkey=VHK,
            dtao_amount=dtao,
            tao_amount=tao,
            conversion_rate=Decimal("0.85"),
            subnet_id=1,
            data_source="CHAIN",
            ingestion_timestamp=_ts(20 - i * 4),
            fully_allocated=1 if i < 3 else 0,
        )
        session.add(conv)

    session.flush()

    # --- Rakeback ledger entries ---
    for idx, partner in enumerate(partners):
        gross_dtao = Decimal("120.5") + Decimal(str(idx * 30))
        gross_tao = gross_dtao * Decimal("0.85")
        tao_owed = gross_tao * partner.rakeback_percentage

        entry = RakebackLedgerEntries(
            id=_uid(),
            period_type="DAILY",
            period_start="2026-02-01",
            period_end="2026-02-01",
            participant_id=partner.id,
            participant_type="PARTNER",
            validator_hotkey=VHK,
            gross_dtao_attributed=gross_dtao,
            gross_tao_converted=gross_tao,
            rakeback_percentage=partner.rakeback_percentage,
            tao_owed=tao_owed,
            payment_status="PAID" if idx == 0 else "UNPAID",
            payment_tx_hash="0xabc123def456" if idx == 0 else None,
            payment_timestamp=_ts(5) if idx == 0 else None,
            completeness_flag="COMPLETE",
            run_id=run_id,
            created_at=_ts(10),
            updated_at=_ts(10),
            block_count=20,
            attribution_count=80,
        )
        session.add(entry)

        # Second period
        entry2 = RakebackLedgerEntries(
            id=_uid(),
            period_type="DAILY",
            period_start="2026-02-02",
            period_end="2026-02-02",
            participant_id=partner.id,
            participant_type="PARTNER",
            validator_hotkey=VHK,
            gross_dtao_attributed=gross_dtao * Decimal("1.1"),
            gross_tao_converted=gross_tao * Decimal("1.1"),
            rakeback_percentage=partner.rakeback_percentage,
            tao_owed=tao_owed * Decimal("1.1"),
            payment_status="UNPAID",
            completeness_flag="COMPLETE",
            run_id=run_id,
            created_at=_ts(9),
            updated_at=_ts(9),
            block_count=20,
            attribution_count=80,
        )
        session.add(entry2)

    session.flush()

    # --- Processing runs (activity log) ---
    run_types = ["INGESTION", "ATTRIBUTION", "AGGREGATION"]
    for i, rt in enumerate(run_types):
        pr = ProcessingRuns(
            run_id=_uid(),
            run_type=rt,
            started_at=_ts(10 - i),
            completed_at=_ts(10 - i),
            status="SUCCESS",
            block_range_start=BASE_BLOCK,
            block_range_end=BASE_BLOCK + 19,
            validator_hotkey=VHK,
            records_processed=20 * (i + 1),
            records_created=20 * (i + 1),
            records_skipped=0,
        )
        session.add(pr)

    # A partial run
    pr_partial = ProcessingRuns(
        run_id=_uid(),
        run_type="INGESTION",
        started_at=_ts(2),
        completed_at=_ts(2),
        status="PARTIAL",
        block_range_start=BASE_BLOCK + 20,
        block_range_end=BASE_BLOCK + 25,
        validator_hotkey=VHK,
        records_processed=6,
        records_created=4,
        records_skipped=2,
    )
    session.add(pr_partial)
    session.flush()

    # --- Data gap (one open issue) ---
    gap = DataGaps(
        id=_uid(),
        gap_type="YIELD",
        block_start=BASE_BLOCK + 18,
        block_end=BASE_BLOCK + 19,
        validator_hotkey=VHK,
        reason="Yield data incomplete for blocks 4500018-4500019 — partial chain response",
        resolution_status="OPEN",
        created_at=_ts(1),
        detected_by_run_id=run_id,
    )
    session.add(gap)

    # --- TAO prices ---
    for i in range(7):
        tp = TaoPrices(
            id=_uid(),
            timestamp=_ts(7 - i),
            price_usd=Decimal("487.32") + Decimal(str(i * 3)),
            source="taostats",
            block_number=BASE_BLOCK + i * 3,
            created_at=_ts(7 - i),
        )
        session.add(tp)

    session.flush()
    print(f"  {len(partners)} partners")
    print("  20 block snapshots with delegations")
    print("  20 block yields with attributions")
    print("  5 conversion events")
    print(f"  {len(partners) * 2} ledger entries")
    print("  4 processing runs")
    print("  1 data gap (open)")
    print("  7 TAO prices")
    print("Done.")


if __name__ == "__main__":
    with get_session() as session:
        seed(session)
