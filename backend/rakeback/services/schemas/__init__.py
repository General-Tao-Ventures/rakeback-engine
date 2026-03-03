"""Shared dataclasses for rakeback services."""

from rakeback.services.schemas.chain import (
    BlockData,
    BlockYieldData,
    ConversionData,
    DelegationData,
    ValidatorState,
)
from rakeback.services.schemas.results import (
    AggregationResult,
    AttributionResult,
    ExportResult,
    IngestionResult,
)

__all__ = [
    # Chain schemas
    "BlockData",
    "BlockYieldData",
    "ConversionData",
    "DelegationData",
    "ValidatorState",
    # Result schemas
    "AggregationResult",
    "AttributionResult",
    "ExportResult",
    "IngestionResult",
]
