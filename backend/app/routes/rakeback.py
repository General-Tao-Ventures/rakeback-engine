"""Rakeback ledger endpoints — thin routes, logic in services."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.rakeback import (
    LedgerEntryResponse,
    LedgerSummaryResponse,
)
from rakeback.services._types import LedgerEntryDict, LedgerSummaryDict
from rakeback.services.aggregation import AggregationService

router: APIRouter = APIRouter(prefix="/api", tags=["rakeback"])


@router.get("/rakeback", response_model=list[LedgerEntryResponse])
def list_rakeback(
    partner_id: str | None = Query(None),
    period_type: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[LedgerEntryDict]:
    svc: AggregationService = AggregationService(db)
    return svc.list_ledger_entries(partner_id, period_type)


@router.get("/rakeback/summary", response_model=LedgerSummaryResponse)
def rakeback_summary(
    partner_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> LedgerSummaryDict:
    svc: AggregationService = AggregationService(db)
    return svc.get_ledger_summary(partner_id)
