"""Attribution endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from rakeback.database import get_session
from rakeback.repositories import (
    BlockAttributionRepository,
    BlockSnapshotRepository,
    BlockYieldRepository,
)
from rakeback.services.ingestion import IngestionService
from rakeback.services.attribution import AttributionEngine
from rakeback.services.chain_client import ChainClient

router = APIRouter(prefix="/api", tags=["attributions"])


# ── Response models ──────────────────────────────────────────────────


class AttributionResponse(BaseModel):
    id: str
    blockNumber: int
    validatorHotkey: str
    delegatorAddress: str
    delegationType: str
    subnetId: int | None
    attributedDtao: str
    delegationProportion: str
    completenessFlag: str
    taoAllocated: str
    fullyAllocated: bool


class AttributionStatsResponse(BaseModel):
    totalBlocks: int
    blocksWithAttributions: int
    totalAttributions: int
    totalDtaoAttributed: str
    uniqueDelegators: int


class BlockDetailResponse(BaseModel):
    blockNumber: int
    timestamp: str | None
    validatorHotkey: str
    totalDtao: str
    delegatorCount: int
    completenessFlag: str
    attributions: list[AttributionResponse]


class IngestionResultResponse(BaseModel):
    runId: str
    blocksProcessed: int
    blocksCreated: int
    blocksSkipped: int
    attributionsCreated: int
    errors: list[str]


# ── Helpers ──────────────────────────────────────────────────────────


def _attribution_to_response(attr) -> dict:
    return {
        "id": attr.id,
        "blockNumber": attr.block_number,
        "validatorHotkey": attr.validator_hotkey,
        "delegatorAddress": attr.delegator_address,
        "delegationType": attr.delegation_type.value if attr.delegation_type else "",
        "subnetId": attr.subnet_id,
        "attributedDtao": str(attr.attributed_dtao),
        "delegationProportion": str(attr.delegation_proportion),
        "completenessFlag": attr.completeness_flag.value if attr.completeness_flag else "",
        "taoAllocated": str(attr.tao_allocated),
        "fullyAllocated": attr.fully_allocated,
    }


# ── Routes ───────────────────────────────────────────────────────────


@router.get("/attributions", response_model=list[AttributionResponse])
def list_attributions(
    start: int = Query(0, description="Start block number"),
    end: int = Query(0, description="End block number"),
    validator_hotkey: Optional[str] = Query(None, description="Filter by validator hotkey"),
    subnet_id: Optional[int] = Query(None, description="Filter by subnet ID"),
):
    """List attributions for a block range."""
    if end == 0:
        end = start + 100

    with get_session() as session:
        repo = BlockAttributionRepository(session)
        rows = repo.get_range(start, end, validator_hotkey)

        results = []
        for attr in rows:
            if subnet_id is not None and attr.subnet_id != subnet_id:
                continue
            results.append(_attribution_to_response(attr))

        return results


@router.get("/attributions/stats", response_model=AttributionStatsResponse)
def attribution_stats(
    start: int = Query(0, description="Start block number"),
    end: int = Query(0, description="End block number"),
    validator_hotkey: Optional[str] = Query(None, description="Filter by validator hotkey"),
):
    """Get summary statistics for attributions in a block range."""
    if end == 0:
        end = start + 100

    with get_session() as session:
        repo = BlockAttributionRepository(session)
        rows = repo.get_range(start, end, validator_hotkey)

        blocks_set = set()
        delegators_set = set()
        total_dtao = 0

        for attr in rows:
            blocks_set.add(attr.block_number)
            delegators_set.add(attr.delegator_address)
            total_dtao += attr.attributed_dtao

        return {
            "totalBlocks": end - start + 1,
            "blocksWithAttributions": len(blocks_set),
            "totalAttributions": len(rows),
            "totalDtaoAttributed": str(total_dtao),
            "uniqueDelegators": len(delegators_set),
        }


@router.get("/attributions/block/{block_number}", response_model=BlockDetailResponse)
def block_detail(
    block_number: int,
    validator_hotkey: Optional[str] = Query(None),
):
    """Get all delegator attributions for a single block."""
    with get_session() as session:
        attr_repo = BlockAttributionRepository(session)
        snap_repo = BlockSnapshotRepository(session)
        yield_repo = BlockYieldRepository(session)

        attributions = attr_repo.get_by_block(block_number, validator_hotkey)

        if not attributions:
            raise HTTPException(404, detail=f"No attributions found for block {block_number}")

        # Determine hotkey from first attribution if not provided
        hotkey = validator_hotkey or attributions[0].validator_hotkey

        # Get block metadata
        snapshot = snap_repo.get_by_block_and_validator(block_number, hotkey)
        block_yield = yield_repo.get_by_block_and_validator(block_number, hotkey)

        total_dtao = sum(a.attributed_dtao for a in attributions)

        # Determine combined completeness
        flags = set(a.completeness_flag.value for a in attributions if a.completeness_flag)
        if "missing" in flags or "incomplete" in flags:
            combined_flag = "incomplete"
        elif "partial" in flags:
            combined_flag = "partial"
        else:
            combined_flag = "complete"

        timestamp = None
        if snapshot and snapshot.timestamp:
            timestamp = snapshot.timestamp.isoformat()

        return {
            "blockNumber": block_number,
            "timestamp": timestamp,
            "validatorHotkey": hotkey,
            "totalDtao": str(total_dtao),
            "delegatorCount": len(attributions),
            "completenessFlag": combined_flag,
            "attributions": [_attribution_to_response(a) for a in attributions],
        }


@router.post("/attributions/ingest", response_model=IngestionResultResponse)
def trigger_ingestion(
    start_block: int = Query(..., description="First block to ingest"),
    end_block: int = Query(..., description="Last block to ingest"),
    validator_hotkey: str = Query(..., description="Validator hotkey"),
):
    """Trigger block range ingestion (snapshot + yield) then attribution."""
    with get_session() as session:
        chain_client = ChainClient()
        chain_client.connect()

        # Step 1: Ingest snapshots and yields
        ingestion = IngestionService(session, chain_client)
        ing_result = ingestion.ingest_block_range(
            start_block, end_block, validator_hotkey
        )

        # Step 2: Run attribution
        engine = AttributionEngine(session)
        attr_result = engine.run_attribution(
            start_block, end_block, validator_hotkey
        )

        session.commit()

        return {
            "runId": attr_result.run_id,
            "blocksProcessed": ing_result.blocks_processed,
            "blocksCreated": ing_result.blocks_created,
            "blocksSkipped": ing_result.blocks_skipped,
            "attributionsCreated": attr_result.attributions_created,
            "errors": ing_result.errors + attr_result.errors,
        }
