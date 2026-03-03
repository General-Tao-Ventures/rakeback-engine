"""Export endpoints — thin routes, logic in services."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_api_key, get_db
from app.schemas.exports import ExportListResponse
from rakeback.services._types import ExportDataDict, ExportListDict
from rakeback.services.export import ExportService

router: APIRouter = APIRouter(prefix="/api", tags=["exports"])


@router.get("/exports", response_model=ExportListResponse)
def list_exports(db: Session = Depends(get_db)) -> ExportListDict:
    svc: ExportService = ExportService(db)
    return svc.list_exports()


@router.get("/exports/download")
def download_export(
    format: str = Query("csv"),
    period_start: str | None = Query(None),
    period_end: str | None = Query(None),
    partner_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _key: str = Depends(get_api_key),
) -> ExportDataDict:
    svc: ExportService = ExportService(db)
    return svc.generate_export(format, period_start, period_end, partner_id)
