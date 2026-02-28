"""Partner request/response schemas."""

from typing import Any

from pydantic import Field

from app.schemas.common import CamelModel


class PartnerCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: str = Field(..., description="named | tag-based | hybrid")
    rakeback_rate: float = Field(..., ge=0, le=100)
    priority: int = Field(1, ge=1)
    payout_address: str = Field("", max_length=64)
    wallet_address: str | None = None
    wallet_label: str | None = None
    memo_keyword: str | None = None
    match_type: str | None = "contains"
    apply_from_date: str | None = None
    apply_from_block: int | None = None
    hybrid_wallet: str | None = None
    hybrid_wallet_label: str | None = None
    hybrid_memo: str | None = None
    hybrid_match_type: str | None = "contains"


class PartnerUpdate(CamelModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    rakeback_rate: float | None = Field(None, ge=0, le=100)
    priority: int | None = Field(None, ge=1)
    payout_address: str | None = Field(None, max_length=64)
    partner_type: str | None = None


class RuleCreate(CamelModel):
    type: str = Field(..., description="wallet | memo | subnet-filter")
    config: dict[str, Any] = Field(default_factory=dict)
    applies_from_block: int | None = None


class RuleResponse(CamelModel):
    id: str
    participant_id: str
    rule_type: str
    config: dict[str, Any]
    applies_from_block: int | None
    created_at: str
    created_by: str


class PartnerResponse(CamelModel):
    id: str
    name: str
    partner_type: str | None
    priority: int
    type: str
    rakeback_percentage: float
    effective_from: str
    effective_to: str | None
    payout_address: str
    aggregation_mode: str
    created_at: str
    updated_at: str
    notes: str | None
    rules: list[RuleResponse] = []
