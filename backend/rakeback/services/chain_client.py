"""Chain RPC client for fetching blockchain data."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
import time

import structlog

from config import get_settings

logger = structlog.get_logger(__name__)


class ChainClientError(Exception):
    """Base exception for chain client errors."""


class RPCError(ChainClientError):
    """RPC call failed."""


class BlockNotFoundError(ChainClientError):
    """Requested block not found."""


class ConnectionError(ChainClientError):
    """Cannot connect to RPC endpoint."""


@dataclass
class BlockData:
    block_number: int
    block_hash: str
    parent_hash: str
    timestamp: datetime
    extrinsics: list[dict]


@dataclass
class DelegationData:
    delegator_address: str
    delegation_type: str
    subnet_id: Optional[int]
    balance_dtao: Decimal
    balance_tao: Optional[Decimal]


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
    subnet_id: Optional[int]


class ChainClient:
    """Client for interacting with the Bittensor chain via Substrate RPC."""

    MAX_NETUIDS = 128

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        timeout: Optional[int] = None,
        retry_attempts: Optional[int] = None,
        retry_delay: Optional[float] = None,
    ):
        settings = get_settings()
        self.rpc_url = rpc_url or settings.chain.rpc_url
        self.timeout = timeout or settings.chain.rpc_timeout
        self.retry_attempts = retry_attempts or settings.chain.retry_attempts
        self.retry_delay = retry_delay or settings.chain.retry_delay
        self.finality_depth = settings.chain.finality_depth
        self._substrate = None
        self._connected = False
        self._active_netuids_cache: dict[str, list[int]] = {}

    def connect(self) -> bool:
        """Connect to the chain. Raises ConnectionError on failure."""
        try:
            from substrateinterface import SubstrateInterface

            self._substrate = SubstrateInterface(
                url=self.rpc_url,
                ss58_format=42,
                auto_discover=True,
                auto_reconnect=True,
            )
            self._connected = True
            logger.info("Connected to chain", rpc_url=self.rpc_url[:50])
            return True
        except ImportError:
            raise ConnectionError(
                "substrate-interface not installed — pip install substrate-interface"
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.rpc_url}: {e}")

    def disconnect(self) -> None:
        if self._substrate:
            try:
                self._substrate.close()
            except Exception:
                pass
        self._substrate = None
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected and self._substrate is not None

    def _require_connection(self) -> None:
        if not self.is_connected():
            raise ConnectionError("Not connected — call connect() first")

    def _retry_call(self, func: callable, *args, **kwargs) -> Any:
        last_error = None
        for attempt in range(self.retry_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e)
                last_error = e
                if "State already discarded" in error_str or "portable_registry" in error_str:
                    raise RPCError(
                        f"State not available (archive node required): {error_str[:100]}"
                    )
                logger.warning(
                    "RPC call failed, retrying",
                    attempt=attempt + 1,
                    error=error_str[:100],
                )
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        raise RPCError(f"RPC call failed after {self.retry_attempts} attempts: {last_error}")

    def get_latest_block(self) -> int:
        self._require_connection()

        def _fetch():
            header = self._substrate.get_block_header(finalized_only=True)
            return header["header"]["number"]

        return self._retry_call(_fetch)

    def get_block(self, block_number: int) -> BlockData:
        self._require_connection()

        def _fetch():
            block_hash = self._substrate.get_block_hash(block_number)
            if not block_hash:
                raise BlockNotFoundError(f"Block {block_number} not found")
            block = self._substrate.get_block(block_hash)
            timestamp = datetime.now(timezone.utc)
            for ext in block["extrinsics"]:
                if hasattr(ext, "call") and ext.call.call_module.name == "Timestamp":
                    ts_ms = ext.call.call_args["now"]["__value__"]
                    timestamp = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                    break
            return BlockData(
                block_number=block_number,
                block_hash=block_hash,
                parent_hash=block["header"]["parentHash"],
                timestamp=timestamp,
                extrinsics=[ext.value for ext in block["extrinsics"]],
            )

        return self._retry_call(_fetch)

    def get_validator_state(
        self, block_number: int, validator_hotkey: str
    ) -> Optional[ValidatorState]:
        self._require_connection()

        def _fetch():
            block_hash = self._substrate.get_block_hash(block_number)
            if not block_hash:
                raise BlockNotFoundError(f"Block {block_number} not found")

            block = self._substrate.get_block(block_hash)
            timestamp = datetime.now(timezone.utc)
            for ext in block.get("extrinsics", []):
                try:
                    if hasattr(ext, "call") and ext.call.call_module.name == "Timestamp":
                        ts_ms = ext.call.call_args["now"]["__value__"]
                        timestamp = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                        break
                except Exception:
                    pass

            delegations = []
            total_stake = Decimal(0)

            active_netuids = []
            for netuid in range(0, self.MAX_NETUIDS):
                try:
                    result = self._substrate.query(
                        module="SubtensorModule",
                        storage_function="TotalHotkeyAlpha",
                        params=[validator_hotkey, netuid],
                        block_hash=block_hash,
                    )
                    alpha_total = result.value if result and result.value else 0
                    if alpha_total > 0:
                        active_netuids.append((netuid, alpha_total))
                except Exception:
                    pass

            self._active_netuids_cache[validator_hotkey] = [n for n, _ in active_netuids]

            for netuid, subnet_total in active_netuids:
                try:
                    alpha_query = self._substrate.query_map(
                        module="SubtensorModule",
                        storage_function="Alpha",
                        params=[validator_hotkey],
                        block_hash=block_hash,
                    )

                    for item in alpha_query:
                        try:
                            if isinstance(item, (list, tuple)) and len(item) >= 2:
                                key_part = item[0]
                                value_part = item[1]
                                if hasattr(value_part, "value"):
                                    val = value_part.value
                                    if isinstance(val, dict) and "bits" in val:
                                        alpha_value = Decimal(str(val["bits"]))
                                    else:
                                        alpha_value = Decimal(str(val)) if val else Decimal(0)
                                else:
                                    alpha_value = (
                                        Decimal(str(value_part)) if value_part else Decimal(0)
                                    )

                                if alpha_value > 0:
                                    delegator = f"delegator_{len(delegations)}"
                                    if hasattr(key_part, "value"):
                                        if isinstance(key_part.value, (list, tuple)):
                                            delegator = (
                                                str(key_part.value[0])
                                                if key_part.value
                                                else delegator
                                            )
                                        else:
                                            delegator = str(key_part.value)
                                    elif key_part is not None:
                                        delegator = str(key_part)

                                    delegations.append(
                                        DelegationData(
                                            delegator_address=delegator,
                                            delegation_type="subnet_dtao",
                                            subnet_id=netuid,
                                            balance_dtao=alpha_value,
                                            balance_tao=None,
                                        )
                                    )
                                    total_stake += alpha_value
                        except Exception as e:
                            logger.debug("Error parsing Alpha entry", error=str(e))
                            continue
                    break
                except Exception as e:
                    logger.debug("Could not query Alpha for validator", error=str(e))

            if not delegations and active_netuids:
                for netuid, subnet_total in active_netuids:
                    delegations.append(
                        DelegationData(
                            delegator_address=f"aggregate_subnet_{netuid}",
                            delegation_type="subnet_dtao",
                            subnet_id=netuid,
                            balance_dtao=Decimal(str(subnet_total)),
                            balance_tao=None,
                        )
                    )
                    total_stake += Decimal(str(subnet_total))

            if not delegations:
                return None

            return ValidatorState(
                block_number=block_number,
                block_hash=block_hash,
                timestamp=timestamp,
                validator_hotkey=validator_hotkey,
                total_stake=total_stake,
                delegations=delegations,
            )

        return self._retry_call(_fetch)

    def get_block_yield(
        self, block_number: int, validator_hotkey: str
    ) -> Optional[BlockYieldData]:
        self._require_connection()

        def _fetch():
            block_hash = self._substrate.get_block_hash(block_number)
            if not block_hash:
                raise BlockNotFoundError(f"Block {block_number} not found")

            prev_hash = self._substrate.get_block_hash(block_number - 1)
            if not prev_hash:
                return None

            netuids_to_check = self._active_netuids_cache.get(validator_hotkey)
            if netuids_to_check is None:
                netuids_to_check = []
                for netuid in range(0, self.MAX_NETUIDS):
                    try:
                        result = self._substrate.query(
                            module="SubtensorModule",
                            storage_function="TotalHotkeyAlpha",
                            params=[validator_hotkey, netuid],
                            block_hash=block_hash,
                        )
                        if result and result.value and result.value > 0:
                            netuids_to_check.append(netuid)
                    except Exception:
                        pass

            total_yield = Decimal(0)
            yield_by_subnet = {}

            for netuid in netuids_to_check:
                try:
                    curr = self._substrate.query(
                        module="SubtensorModule",
                        storage_function="TotalHotkeyAlpha",
                        params=[validator_hotkey, netuid],
                        block_hash=block_hash,
                    )
                    curr_val = curr.value if curr and curr.value else 0
                    if curr_val == 0:
                        continue

                    prev = self._substrate.query(
                        module="SubtensorModule",
                        storage_function="TotalHotkeyAlpha",
                        params=[validator_hotkey, netuid],
                        block_hash=prev_hash,
                    )
                    prev_val = prev.value if prev and prev.value else 0

                    delta = curr_val - prev_val
                    if delta > 0:
                        yield_amount = Decimal(str(delta))
                        total_yield += yield_amount
                        yield_by_subnet[netuid] = yield_amount
                except Exception as e:
                    logger.debug("Error checking alpha delta", netuid=netuid, error=str(e))

            if total_yield == 0:
                return None

            return BlockYieldData(
                block_number=block_number,
                validator_hotkey=validator_hotkey,
                total_dtao_earned=total_yield,
                yield_by_subnet=yield_by_subnet,
            )

        return self._retry_call(_fetch)

    def get_conversion_events(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: Optional[str] = None,
    ) -> list[ConversionData]:
        self._require_connection()

        def _fetch():
            conversions = []
            for block_num in range(start_block, end_block + 1):
                block_hash = self._substrate.get_block_hash(block_num)
                if not block_hash:
                    continue
                block = self._substrate.get_block(block_hash)
                events = self._substrate.get_events(block_hash)

                if block and "extrinsics" in block:
                    for ext_idx, ext in enumerate(block["extrinsics"]):
                        call = ext.get("call", {})
                        call_module = call.get("call_module", "")
                        call_function = call.get("call_function", "")
                        swap_functions = {
                            "do_swap_alpha_for_tao",
                            "swap_alpha_for_tao",
                            "swap",
                            "do_swap",
                        }
                        if (
                            call_module == "SubtensorModule"
                            and call_function in swap_functions
                        ):
                            args = {
                                p.get("name", ""): p.get("value")
                                for p in call.get("call_args", [])
                            }
                            ext_hotkey = args.get("hotkey") or args.get(
                                "validator_hotkey", ""
                            )
                            if validator_hotkey and ext_hotkey != validator_hotkey:
                                continue
                            subnet_id = args.get("netuid") or args.get("subnet_id")
                            if subnet_id is not None:
                                subnet_id = int(subnet_id)
                            dtao_amt = Decimal(
                                str(args.get("alpha_amount", 0) or args.get("amount", 0))
                            )
                            tao_amt = Decimal(0)
                            rate = Decimal(0)
                            for evt in events:
                                evt_module = getattr(evt, "event_module", "") or ""
                                evt_id = getattr(evt, "event_id", "") or ""
                                if evt_module == "SubtensorModule" and evt_id in (
                                    "AlphaSwapped",
                                    "SwapExecuted",
                                    "StakeRemoved",
                                ):
                                    evt_attrs = getattr(evt, "attributes", {}) or {}
                                    if isinstance(evt_attrs, dict):
                                        evt_tao = evt_attrs.get(
                                            "tao_amount"
                                        ) or evt_attrs.get("amount_tao", 0)
                                        tao_amt = Decimal(str(evt_tao))
                                        break
                                    elif isinstance(evt_attrs, (list, tuple)) and len(
                                        evt_attrs
                                    ) >= 2:
                                        tao_amt = Decimal(str(evt_attrs[1]))
                                        break
                            if dtao_amt > 0 and tao_amt > 0:
                                rate = (tao_amt / dtao_amt).quantize(Decimal("1E-18"))
                            tx_hash = ext.get(
                                "extrinsic_hash", f"0x{block_num:x}-{ext_idx}"
                            )
                            conversions.append(
                                ConversionData(
                                    block_number=block_num,
                                    transaction_hash=tx_hash,
                                    validator_hotkey=ext_hotkey,
                                    dtao_amount=dtao_amt,
                                    tao_amount=tao_amt,
                                    conversion_rate=rate,
                                    subnet_id=subnet_id,
                                )
                            )

                for evt in events:
                    evt_module = getattr(evt, "event_module", "") or ""
                    evt_id = getattr(evt, "event_id", "") or ""
                    if evt_module == "SubtensorModule" and evt_id in (
                        "AlphaSwapped",
                        "SwapExecuted",
                    ):
                        evt_attrs = getattr(evt, "attributes", {}) or {}
                        if not isinstance(evt_attrs, dict):
                            continue
                        evt_hotkey = evt_attrs.get("hotkey", "")
                        if validator_hotkey and evt_hotkey != validator_hotkey:
                            continue
                        already_found = any(
                            c.block_number == block_num and c.validator_hotkey == evt_hotkey
                            for c in conversions
                        )
                        if already_found:
                            continue
                        dtao_amt = Decimal(str(evt_attrs.get("alpha_amount", 0)))
                        tao_amt = Decimal(str(evt_attrs.get("tao_amount", 0)))
                        subnet_id = evt_attrs.get("netuid")
                        if subnet_id is not None:
                            subnet_id = int(subnet_id)
                        rate = Decimal(0)
                        if dtao_amt > 0 and tao_amt > 0:
                            rate = (tao_amt / dtao_amt).quantize(Decimal("1E-18"))
                        tx_hash = evt_attrs.get(
                            "extrinsic_hash", f"0xevt-{block_num:x}"
                        )
                        conversions.append(
                            ConversionData(
                                block_number=block_num,
                                transaction_hash=tx_hash,
                                validator_hotkey=evt_hotkey,
                                dtao_amount=dtao_amt,
                                tao_amount=tao_amt,
                                conversion_rate=rate,
                                subnet_id=subnet_id,
                            )
                        )
            return conversions

        return self._retry_call(_fetch)

    def verify_block_hash(self, block_number: int, expected_hash: str) -> bool:
        self._require_connection()
        try:
            actual_hash = self._substrate.get_block_hash(block_number)
            return actual_hash == expected_hash
        except Exception:
            return False
