"""Attribution request/response schemas."""

from app.schemas.common import CamelModel


class AttributionResponse(CamelModel):
    id: str
    block_number: int
    validator_hotkey: str
    delegator_address: str
    delegation_type: str
    subnet_id: int | None
    attributed_dtao: str
    delegation_proportion: str
    completeness_flag: str
    tao_allocated: str
    fully_allocated: bool


class AttributionStatsResponse(CamelModel):
    total_blocks: int
    blocks_with_attributions: int
    total_attributions: int
    total_dtao_attributed: str
    unique_delegators: int


class BlockDetailResponse(CamelModel):
    block_number: int
    timestamp: str | None
    validator_hotkey: str
    total_dtao: str
    delegator_count: int
    completeness_flag: str
    attributions: list[AttributionResponse]


class IngestionResultResponse(CamelModel):
    run_id: str
    blocks_processed: int
    blocks_created: int
    blocks_skipped: int
    attributions_created: int
    errors: list[str]
