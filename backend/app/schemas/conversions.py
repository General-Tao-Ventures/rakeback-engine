"""Conversion request/response schemas."""

from app.schemas.common import CamelModel


class ConversionResponse(CamelModel):
    id: str
    block_number: int
    transaction_hash: str
    validator_hotkey: str
    dtao_amount: str
    tao_amount: str
    conversion_rate: str
    subnet_id: int | None
    fully_allocated: bool
    tao_price: float | None


class AllocationDetailResponse(CamelModel):
    id: str
    conversion_event_id: str
    block_attribution_id: str
    tao_allocated: str
    allocation_method: str
    completeness_flag: str


class ConversionDetailResponse(CamelModel):
    conversion: ConversionResponse
    allocations: list[AllocationDetailResponse]


class ConversionIngestionResponse(CamelModel):
    run_id: str
    blocks_processed: int
    events_created: int
    events_skipped: int
    errors: list[str]
