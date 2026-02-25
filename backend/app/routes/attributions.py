"""Attribution endpoints — thin routes, logic in services."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_api_key, get_db
from app.schemas.attributions import (
    AttributionResponse,
    AttributionStatsResponse,
    BlockDetailResponse,
    IngestionResultResponse,
)
from rakeback.services.attribution import AttributionEngine
from rakeback.services.chain_client import ChainClient
from rakeback.services.ingestion import IngestionService

router = APIRouter(prefix="/api", tags=["attributions"])


@router.get("/attributions", response_model=list[AttributionResponse])
def list_attributions(
    start: int = Query(0),
    end: int = Query(0),
    validator_hotkey: str | None = Query(None),
    subnet_id: int | None = Query(None),
    db: Session = Depends(get_db),
) -> list[AttributionResponse]:
    engine = AttributionEngine(db)
    return engine.list_attributions(start, end, validator_hotkey, subnet_id)


@router.get("/attributions/stats", response_model=AttributionStatsResponse)
def attribution_stats(
    start: int = Query(0),
    end: int = Query(0),
    validator_hotkey: str | None = Query(None),
    db: Session = Depends(get_db),
) -> AttributionStatsResponse:
    engine = AttributionEngine(db)
    return engine.get_stats(start, end, validator_hotkey)


@router.get(
    "/attributions/block/{block_number}",
    response_model=BlockDetailResponse,
)
def block_detail(
    block_number: int,
    validator_hotkey: str | None = Query(None),
    db: Session = Depends(get_db),
) -> BlockDetailResponse:
    engine = AttributionEngine(db)
    result = engine.get_block_detail(block_number, validator_hotkey)
    if not result:
        raise HTTPException(404, detail=f"No attributions for block {block_number}")
    return result


@router.post("/attributions/ingest", response_model=IngestionResultResponse)
def trigger_ingestion(
    start_block: int = Query(...),
    end_block: int = Query(...),
    validator_hotkey: str = Query(...),
    db: Session = Depends(get_db),
    _key: str = Depends(get_api_key),
) -> IngestionResultResponse:
    chain_client = ChainClient()
    chain_client.connect()
    ingestion = IngestionService(db, chain_client)
    ing_result = ingestion.ingest_block_range(start_block, end_block, validator_hotkey)

    engine = AttributionEngine(db)
    attr_result = engine.run_attribution(start_block, end_block, validator_hotkey)

    return IngestionResultResponse(
        run_id=attr_result.run_id,
        blocks_processed=ing_result.blocks_processed,
        blocks_created=ing_result.blocks_created,
        blocks_skipped=ing_result.blocks_skipped,
        attributions_created=attr_result.attributions_created,
        errors=ing_result.errors + attr_result.errors,
    )
