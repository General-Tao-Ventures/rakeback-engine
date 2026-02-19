"""Conversion endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from rakeback.database import get_session
from rakeback.repositories import (
    ConversionEventRepository,
    TaoAllocationRepository,
    TaoPriceRepository,
)
from rakeback.services.ingestion import IngestionService
from rakeback.services.chain_client import ChainClient

router = APIRouter(prefix="/api", tags=["conversions"])


# ── Response models ──────────────────────────────────────────────────


class ConversionResponse(BaseModel):
    id: str
    blockNumber: int
    transactionHash: str
    validatorHotkey: str
    dtaoAmount: str
    taoAmount: str
    conversionRate: str
    subnetId: int | None
    fullyAllocated: bool
    taoPrice: float | None


class AllocationDetailResponse(BaseModel):
    id: str
    conversionEventId: str
    blockAttributionId: str
    taoAllocated: str
    allocationMethod: str
    completenessFlag: str


class ConversionDetailResponse(BaseModel):
    conversion: ConversionResponse
    allocations: list[AllocationDetailResponse]


class ConversionIngestionResponse(BaseModel):
    runId: str
    blocksProcessed: int
    eventsCreated: int
    eventsSkipped: int
    errors: list[str]


# ── Helpers ──────────────────────────────────────────────────────────


def _conversion_to_response(event, tao_price: float | None = None) -> dict:
    return {
        "id": event.id,
        "blockNumber": event.block_number,
        "transactionHash": event.transaction_hash,
        "validatorHotkey": event.validator_hotkey,
        "dtaoAmount": str(event.dtao_amount),
        "taoAmount": str(event.tao_amount),
        "conversionRate": str(event.conversion_rate),
        "subnetId": event.subnet_id,
        "fullyAllocated": event.fully_allocated,
        "taoPrice": tao_price,
    }


# ── Routes ───────────────────────────────────────────────────────────


@router.get("/conversions", response_model=list[ConversionResponse])
def list_conversions(
    start_block: Optional[int] = Query(None, description="Start block number"),
    end_block: Optional[int] = Query(None, description="End block number"),
):
    """List conversion events, optionally filtered by block range."""
    with get_session() as session:
        repo = ConversionEventRepository(session)
        price_repo = TaoPriceRepository(session)

        if start_block is not None and end_block is not None:
            events = repo.get_range(start_block, end_block)
        else:
            events = repo.get_all()

        results = []
        for event in events:
            # Try to find TAO price at the conversion's block
            price_record = price_repo.get_closest_to_block(event.block_number)
            tao_price = float(price_record.price_usd) if price_record else None
            results.append(_conversion_to_response(event, tao_price))

        return results


@router.get("/conversions/{conversion_id}", response_model=ConversionDetailResponse)
def conversion_detail(conversion_id: str):
    """Get a conversion event with its allocation details."""
    with get_session() as session:
        conv_repo = ConversionEventRepository(session)
        alloc_repo = TaoAllocationRepository(session)
        price_repo = TaoPriceRepository(session)

        event = conv_repo.get_by_id(conversion_id)
        if not event:
            raise HTTPException(404, detail=f"Conversion event {conversion_id} not found")

        allocations = alloc_repo.get_by_conversion(conversion_id)

        price_record = price_repo.get_closest_to_block(event.block_number)
        tao_price = float(price_record.price_usd) if price_record else None

        return {
            "conversion": _conversion_to_response(event, tao_price),
            "allocations": [
                {
                    "id": a.id,
                    "conversionEventId": a.conversion_event_id,
                    "blockAttributionId": a.block_attribution_id,
                    "taoAllocated": str(a.tao_allocated),
                    "allocationMethod": a.allocation_method.value if a.allocation_method else "",
                    "completenessFlag": a.completeness_flag.value if a.completeness_flag else "",
                }
                for a in allocations
            ],
        }


@router.post("/conversions/ingest", response_model=ConversionIngestionResponse)
def trigger_conversion_ingestion(
    start_block: int = Query(..., description="First block to scan"),
    end_block: int = Query(..., description="Last block to scan"),
    validator_hotkey: Optional[str] = Query(None, description="Optional validator filter"),
):
    """Trigger conversion event ingestion for a block range."""
    with get_session() as session:
        chain_client = ChainClient()
        chain_client.connect()

        ingestion = IngestionService(session, chain_client)
        result = ingestion.ingest_conversions(start_block, end_block, validator_hotkey)

        session.commit()

        return {
            "runId": result.run_id,
            "blocksProcessed": result.blocks_processed,
            "eventsCreated": result.blocks_created,
            "eventsSkipped": result.blocks_skipped,
            "errors": result.errors,
        }
