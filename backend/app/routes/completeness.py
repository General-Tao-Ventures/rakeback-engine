"""Data completeness endpoints — live quality metrics from DB."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from db.enums import CompletenessFlag, ResolutionStatus
from db.models import (
    BlockSnapshots,
    BlockYields,
    ConversionEvents,
    DataGaps,
    ProcessingRuns,
    RakebackLedgerEntries,
)

router: APIRouter = APIRouter(prefix="/api/health", tags=["completeness"])


@router.get("/completeness")
def get_completeness(db: Session = Depends(get_db)) -> dict:
    # Block snapshots completeness
    snap_total = db.scalar(select(func.count()).select_from(BlockSnapshots)) or 0
    snap_complete = (
        db.scalar(
            select(func.count())
            .select_from(BlockSnapshots)
            .where(BlockSnapshots.completeness_flag == CompletenessFlag.COMPLETE.value)
        )
        or 0
    )
    snap_partial = (
        db.scalar(
            select(func.count())
            .select_from(BlockSnapshots)
            .where(BlockSnapshots.completeness_flag == CompletenessFlag.PARTIAL.value)
        )
        or 0
    )
    snap_missing = snap_total - snap_complete - snap_partial

    # Block yields completeness
    yield_total = db.scalar(select(func.count()).select_from(BlockYields)) or 0
    yield_complete = (
        db.scalar(
            select(func.count())
            .select_from(BlockYields)
            .where(BlockYields.completeness_flag == CompletenessFlag.COMPLETE.value)
        )
        or 0
    )
    yield_partial = (
        db.scalar(
            select(func.count())
            .select_from(BlockYields)
            .where(BlockYields.completeness_flag == CompletenessFlag.PARTIAL.value)
        )
        or 0
    )
    yield_missing = yield_total - yield_complete - yield_partial

    # Conversion events
    conv_total = db.scalar(select(func.count()).select_from(ConversionEvents)) or 0
    conv_allocated = (
        db.scalar(
            select(func.count())
            .select_from(ConversionEvents)
            .where(ConversionEvents.fully_allocated == 1)
        )
        or 0
    )
    conv_unallocated = conv_total - conv_allocated

    # Ledger entries
    ledger_total = db.scalar(select(func.count()).select_from(RakebackLedgerEntries)) or 0
    ledger_complete = (
        db.scalar(
            select(func.count())
            .select_from(RakebackLedgerEntries)
            .where(RakebackLedgerEntries.completeness_flag == CompletenessFlag.COMPLETE.value)
        )
        or 0
    )
    ledger_incomplete = ledger_total - ledger_complete

    # Open data gaps → issues
    open_gaps = list(
        db.scalars(
            select(DataGaps)
            .where(DataGaps.resolution_status == ResolutionStatus.OPEN.value)
            .order_by(DataGaps.created_at.desc())
            .limit(50)
        ).all()
    )
    issues = [
        {
            "id": g.id,
            "type": g.gap_type.lower().replace("_", "-"),
            "severity": "critical" if g.gap_type == "SNAPSHOT" else "warning",
            "description": g.reason,
            "affectedBlocks": f"{g.block_start}-{g.block_end}"
            if g.block_start != g.block_end
            else str(g.block_start),
            "detectedAt": g.created_at,
            "requiresReview": True,
        }
        for g in open_gaps
    ]

    # Recent processing runs → activity log
    recent_runs = list(
        db.scalars(
            select(ProcessingRuns).order_by(ProcessingRuns.started_at.desc()).limit(20)
        ).all()
    )
    activity = [
        {
            "timestamp": r.started_at,
            "event": f"{r.run_type} run {'completed' if r.completed_at else 'started'}",
            "details": (
                f"Run {r.run_id[:8]}... — "
                f"{r.records_processed or 0} processed, "
                f"{r.records_created or 0} created"
            ),
            "status": "success"
            if r.status == "SUCCESS"
            else "warning"
            if r.status == "PARTIAL"
            else "error"
            if r.status == "FAILED"
            else "info",
        }
        for r in recent_runs
    ]

    def _pct(complete: int, total: int) -> float:
        return round(complete / total * 100, 3) if total > 0 else 100.0

    return {
        "systemMetrics": {
            "blockCoverage": {
                "total": snap_total,
                "complete": snap_complete,
                "partial": snap_partial,
                "missing": snap_missing,
                "percentage": _pct(snap_complete, snap_total),
            },
            "yieldData": {
                "total": yield_total,
                "complete": yield_complete,
                "partial": yield_partial,
                "missing": yield_missing,
                "percentage": _pct(yield_complete, yield_total),
            },
            "conversionEvents": {
                "total": conv_total,
                "allocated": conv_allocated,
                "unallocated": conv_unallocated,
                "percentage": _pct(conv_allocated, conv_total),
            },
            "ledgerEntries": {
                "total": ledger_total,
                "complete": ledger_complete,
                "incomplete": ledger_incomplete,
                "percentage": _pct(ledger_complete, ledger_total),
            },
        },
        "issues": issues,
        "recentActivity": activity,
    }
