"""Conversion endpoints — thin routes, logic in services."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_api_key, get_db
from app.schemas.conversions import (
    ConversionDetailResponse,
    ConversionIngestionResponse,
    ConversionResponse,
)
from rakeback.services.chain_client import ChainClient
from rakeback.services.ingestion import IngestionService

router = APIRouter(prefix="/api", tags=["conversions"])


@router.get("/conversions", response_model=list[ConversionResponse])
def list_conversions(
    start_block: int | None = Query(None),
    end_block: int | None = Query(None),
    db: Session = Depends(get_db),
) -> list[ConversionResponse]:
    svc = IngestionService(db)
    return svc.list_conversions(start_block, end_block)


@router.get("/conversions/{conversion_id}", response_model=ConversionDetailResponse)
def conversion_detail(
    conversion_id: str,
    db: Session = Depends(get_db),
) -> ConversionDetailResponse:
    svc = IngestionService(db)
    result = svc.get_conversion_detail(conversion_id)
    if not result:
        raise HTTPException(404, detail=f"Conversion {conversion_id} not found")
    return result


@router.post("/conversions/ingest", response_model=ConversionIngestionResponse)
def trigger_conversion_ingestion(
    start_block: int = Query(...),
    end_block: int = Query(...),
    validator_hotkey: str | None = Query(None),
    db: Session = Depends(get_db),
    _key: str = Depends(get_api_key),
) -> ConversionIngestionResponse:
    chain_client = ChainClient()
    chain_client.connect()
    svc = IngestionService(db, chain_client)
    result = svc.ingest_conversions(start_block, end_block, validator_hotkey)

    return ConversionIngestionResponse(
        run_id=result.run_id,
        blocks_processed=result.blocks_processed,
        events_created=result.blocks_created,
        events_skipped=result.blocks_skipped,
        errors=result.errors,
    )
