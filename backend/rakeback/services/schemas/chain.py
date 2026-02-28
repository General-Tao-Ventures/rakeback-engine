"""Chain-related data transfer objects."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class BlockData:
    block_number: int
    block_hash: str
    parent_hash: str
    timestamp: datetime
    extrinsics: list[dict[str, object]]


@dataclass
class DelegationData:
    delegator_address: str
    delegation_type: str
    subnet_id: int | None
    balance_dtao: Decimal
    balance_tao: Decimal | None


@dataclass
class ValidatorState:
    block_number: int
    block_hash: str
    timestamp: datetime
    validator_hotkey: str
    total_stake: Decimal
    delegations: list[DelegationData]


@dataclass
class BlockYieldData:
    block_number: int
    validator_hotkey: str
    total_dtao_earned: Decimal
    yield_by_subnet: dict[int, Decimal]


@dataclass
class ConversionData:
    block_number: int
    transaction_hash: str
    validator_hotkey: str
    dtao_amount: Decimal
    tao_amount: Decimal
    conversion_rate: Decimal
    subnet_id: int | None
