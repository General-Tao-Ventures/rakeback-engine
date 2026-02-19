"""Chain RPC client for fetching blockchain data."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Any
import time

import structlog

from rakeback.config import get_settings

logger = structlog.get_logger(__name__)


class ChainClientError(Exception):
    """Base exception for chain client errors."""
    pass


class RPCError(ChainClientError):
    """RPC call failed."""
    pass


class BlockNotFoundError(ChainClientError):
    """Requested block not found."""
    pass


class ConnectionError(ChainClientError):
    """Cannot connect to RPC endpoint."""
    pass


@dataclass
class BlockData:
    """Raw block data from chain."""
    block_number: int
    block_hash: str
    parent_hash: str
    timestamp: datetime
    extrinsics: list[dict]


@dataclass
class DelegationData:
    """Delegation state for a delegator."""
    delegator_address: str
    delegation_type: str  # "root_tao", "subnet_dtao", "child_hotkey"
    subnet_id: Optional[int]
    balance_dtao: Decimal
    balance_tao: Optional[Decimal]


@dataclass
class ValidatorState:
    """Complete validator state at a block."""
    block_number: int
    block_hash: str
    timestamp: datetime
    validator_hotkey: str
    total_stake: Decimal
    delegations: list[DelegationData]


@dataclass
class BlockYieldData:
    """Yield earned by validator at a block."""
    block_number: int
    validator_hotkey: str
    total_dtao_earned: Decimal
    yield_by_subnet: dict[int, Decimal]


@dataclass
class ConversionData:
    """dTAO to TAO conversion event."""
    block_number: int
    transaction_hash: str
    validator_hotkey: str
    dtao_amount: Decimal
    tao_amount: Decimal
    conversion_rate: Decimal
    subnet_id: Optional[int]


class ChainClient:
    """
    Client for interacting with the Bittensor chain.
    
    This class abstracts the Substrate RPC interface and provides
    typed methods for fetching validator-related data.
    
    Note: The actual Substrate integration requires the substrate-interface
    library. This implementation provides the interface and stub
    implementations that can be replaced with real chain calls.
    """
    
    def __init__(
        self,
        rpc_url: Optional[str] = None,
        timeout: Optional[int] = None,
        retry_attempts: Optional[int] = None,
        retry_delay: Optional[float] = None
    ):
        """Initialize the chain client."""
        settings = get_settings()
        
        self.rpc_url = rpc_url or settings.chain.rpc_url
        self.timeout = timeout or settings.chain.rpc_timeout
        self.retry_attempts = retry_attempts or settings.chain.retry_attempts
        self.retry_delay = retry_delay or settings.chain.retry_delay
        self.finality_depth = settings.chain.finality_depth

        self._substrate = None
        self._connected = False

        # Cache of active subnet IDs per validator, populated by get_validator_state
        self._active_netuids_cache: dict[str, list[int]] = {}
    
    def connect(self) -> bool:
        """
        Establish connection to the chain.
        
        Supports both HTTP(S) and WebSocket endpoints.
        Returns True if connection successful, False otherwise.
        """
        try:
            # Import here to allow running without substrate-interface installed
            from substrateinterface import SubstrateInterface
            
            # Determine if using HTTP or WebSocket
            is_http = self.rpc_url.startswith("http://") or self.rpc_url.startswith("https://")
            
            self._substrate = SubstrateInterface(
                url=self.rpc_url,
                ss58_format=42,  # Bittensor format
                auto_discover=True,
                auto_reconnect=True,
            )
            self._connected = True
            logger.info(
                "Connected to chain", 
                rpc_url=self.rpc_url[:50] + "..." if len(self.rpc_url) > 50 else self.rpc_url,
                protocol="HTTP" if is_http else "WebSocket"
            )
            return True
            
        except ImportError:
            logger.warning(
                "substrate-interface not installed, using mock mode",
                rpc_url=self.rpc_url
            )
            self._connected = False
            return False
            
        except Exception as e:
            logger.error("Failed to connect to chain", error=str(e), rpc_url=self.rpc_url[:50])
            raise ConnectionError(f"Failed to connect to {self.rpc_url}: {e}")
    
    def disconnect(self) -> None:
        """Close the chain connection."""
        if self._substrate:
            try:
                self._substrate.close()
            except Exception:
                pass
        self._substrate = None
        self._connected = False
    
    # Maximum number of subnets on the Bittensor network
    MAX_NETUIDS = 128

    def is_connected(self) -> bool:
        """Check if connected to chain."""
        return self._connected and self._substrate is not None
    
    def _retry_call(self, func: callable, *args, **kwargs) -> Any:
        """Execute a call with retry logic."""
        last_error = None
        
        for attempt in range(self.retry_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e)
                last_error = e
                
                # Check for unrecoverable errors (state pruned, no archive access)
                if "State already discarded" in error_str or "portable_registry" in error_str:
                    logger.warning(
                        "Unrecoverable chain error - state not available",
                        error=error_str[:100]
                    )
                    raise RPCError(f"State not available (archive node required): {error_str[:100]}")
                
                logger.warning(
                    "RPC call failed, retrying",
                    attempt=attempt + 1,
                    max_attempts=self.retry_attempts,
                    error=error_str[:100]
                )
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
        
        raise RPCError(f"RPC call failed after {self.retry_attempts} attempts: {last_error}")
    
    def get_latest_block(self) -> int:
        """Get the latest finalized block number."""
        if not self._connected:
            # Mock mode - return a placeholder
            logger.debug("Mock mode: returning placeholder latest block")
            return 1000000
        
        def _fetch():
            header = self._substrate.get_block_header(finalized_only=True)
            return header['header']['number']
        
        return self._retry_call(_fetch)
    
    def get_block(self, block_number: int) -> BlockData:
        """Fetch block data by number."""
        if not self._connected:
            # Mock mode
            logger.debug("Mock mode: returning placeholder block", block_number=block_number)
            return BlockData(
                block_number=block_number,
                block_hash=f"0x{'0' * 64}",
                parent_hash=f"0x{'0' * 64}",
                timestamp=datetime.now(timezone.utc),
                extrinsics=[]
            )
        
        def _fetch():
            block_hash = self._substrate.get_block_hash(block_number)
            if not block_hash:
                raise BlockNotFoundError(f"Block {block_number} not found")
            
            block = self._substrate.get_block(block_hash)
            
            # Parse timestamp from extrinsics
            timestamp = datetime.now(timezone.utc)
            for ext in block['extrinsics']:
                if hasattr(ext, 'call') and ext.call.call_module.name == 'Timestamp':
                    ts_ms = ext.call.call_args['now']['__value__']
                    timestamp = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                    break
            
            return BlockData(
                block_number=block_number,
                block_hash=block_hash,
                parent_hash=block['header']['parentHash'],
                timestamp=timestamp,
                extrinsics=[ext.value for ext in block['extrinsics']]
            )
        
        return self._retry_call(_fetch)
    
    def get_validator_state(
        self,
        block_number: int,
        validator_hotkey: str
    ) -> Optional[ValidatorState]:
        """
        Fetch complete validator delegation state at a block.
        
        This queries the chain storage for all delegations to the validator.
        """
        if not self._connected:
            # Mock mode - return placeholder data
            logger.debug(
                "Mock mode: returning placeholder validator state",
                block_number=block_number,
                validator_hotkey=validator_hotkey
            )
            return ValidatorState(
                block_number=block_number,
                block_hash=f"0x{'0' * 64}",
                timestamp=datetime.now(timezone.utc),
                validator_hotkey=validator_hotkey,
                total_stake=Decimal("1000000000000"),
                delegations=[
                    DelegationData(
                        delegator_address="5C" + "a" * 46,
                        delegation_type="root_tao",
                        subnet_id=None,
                        balance_dtao=Decimal("500000000000"),
                        balance_tao=Decimal("500000000000")
                    ),
                    DelegationData(
                        delegator_address="5C" + "b" * 46,
                        delegation_type="subnet_dtao",
                        subnet_id=1,
                        balance_dtao=Decimal("500000000000"),
                        balance_tao=None
                    )
                ]
            )
        
        def _fetch():
            block_hash = self._substrate.get_block_hash(block_number)
            if not block_hash:
                raise BlockNotFoundError(f"Block {block_number} not found")
            
            # Get block for timestamp
            block = self._substrate.get_block(block_hash)
            timestamp = datetime.now(timezone.utc)
            
            # Parse timestamp from extrinsics if available
            for ext in block.get('extrinsics', []):
                try:
                    if hasattr(ext, 'call') and ext.call.call_module.name == 'Timestamp':
                        ts_ms = ext.call.call_args['now']['__value__']
                        timestamp = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                        break
                except Exception:
                    pass
            
            delegations = []
            total_stake = Decimal(0)
            
            # Get TotalHotkeyAlpha for each subnet to find which subnets have stake
            active_netuids = []
            for netuid in range(0, self.MAX_NETUIDS):
                try:
                    result = self._substrate.query(
                        module='SubtensorModule',
                        storage_function='TotalHotkeyAlpha',
                        params=[validator_hotkey, netuid],
                        block_hash=block_hash
                    )
                    alpha_total = result.value if result and result.value else 0
                    if alpha_total > 0:
                        active_netuids.append((netuid, alpha_total))
                except Exception:
                    pass
            
            # Cache active netuids for use by get_block_yield
            self._active_netuids_cache[validator_hotkey] = [n for n, _ in active_netuids]

            # For each active subnet, query Alpha delegations
            for netuid, subnet_total in active_netuids:
                try:
                    # Try query_map with just the hotkey to get all delegators
                    alpha_query = self._substrate.query_map(
                        module='SubtensorModule',
                        storage_function='Alpha',
                        params=[validator_hotkey],
                        block_hash=block_hash
                    )
                    
                    for item in alpha_query:
                        try:
                            # Parse the result - format varies by substrate version
                            if isinstance(item, (list, tuple)) and len(item) >= 2:
                                key_part = item[0]
                                value_part = item[1]
                                
                                # Extract alpha value from bits structure
                                if hasattr(value_part, 'value'):
                                    val = value_part.value
                                    if isinstance(val, dict) and 'bits' in val:
                                        alpha_value = Decimal(str(val['bits']))
                                    else:
                                        alpha_value = Decimal(str(val)) if val else Decimal(0)
                                else:
                                    alpha_value = Decimal(str(value_part)) if value_part else Decimal(0)
                                
                                if alpha_value > 0:
                                    # Create delegation entry
                                    # Note: key_part may contain (coldkey, netuid) tuple
                                    delegator = f"delegator_{len(delegations)}"  # Placeholder
                                    if hasattr(key_part, 'value'):
                                        if isinstance(key_part.value, (list, tuple)):
                                            delegator = str(key_part.value[0]) if key_part.value else delegator
                                        else:
                                            delegator = str(key_part.value)
                                    elif key_part is not None:
                                        delegator = str(key_part)
                                    
                                    delegations.append(DelegationData(
                                        delegator_address=delegator,
                                        delegation_type="subnet_dtao",
                                        subnet_id=netuid,
                                        balance_dtao=alpha_value,
                                        balance_tao=None
                                    ))
                                    total_stake += alpha_value
                        except Exception as e:
                            logger.debug("Error parsing Alpha entry", error=str(e))
                            continue
                    
                    # Break after first successful query since Alpha is per-hotkey
                    break
                    
                except Exception as e:
                    logger.debug("Could not query Alpha for validator", error=str(e))
            
            # If no individual delegations found, create aggregate entries per subnet
            if not delegations and active_netuids:
                for netuid, subnet_total in active_netuids:
                    delegations.append(DelegationData(
                        delegator_address=f"aggregate_subnet_{netuid}",
                        delegation_type="subnet_dtao",
                        subnet_id=netuid,
                        balance_dtao=Decimal(str(subnet_total)),
                        balance_tao=None
                    ))
                    total_stake += Decimal(str(subnet_total))
            
            # If still no delegations, return None
            if not delegations:
                return None
            
            return ValidatorState(
                block_number=block_number,
                block_hash=block_hash,
                timestamp=timestamp,
                validator_hotkey=validator_hotkey,
                total_stake=total_stake,
                delegations=delegations
            )
        
        return self._retry_call(_fetch)
    
    def get_block_yield(
        self,
        block_number: int,
        validator_hotkey: str
    ) -> Optional[BlockYieldData]:
        """
        Fetch yield earned by validator at a block.
        
        This parses block events for emission/reward events.
        """
        if not self._connected:
            # Mock mode
            logger.debug(
                "Mock mode: returning placeholder yield",
                block_number=block_number,
                validator_hotkey=validator_hotkey
            )
            return BlockYieldData(
                block_number=block_number,
                validator_hotkey=validator_hotkey,
                total_dtao_earned=Decimal("1000000"),
                yield_by_subnet={1: Decimal("600000"), 2: Decimal("400000")}
            )
        
        def _fetch():
            block_hash = self._substrate.get_block_hash(block_number)
            if not block_hash:
                raise BlockNotFoundError(f"Block {block_number} not found")

            prev_hash = self._substrate.get_block_hash(block_number - 1)
            if not prev_hash:
                return None

            # Determine which subnets to check for this validator.
            # Use cached active netuids from get_validator_state if available,
            # otherwise scan for active subnets.
            netuids_to_check = self._active_netuids_cache.get(validator_hotkey)
            if netuids_to_check is None:
                netuids_to_check = []
                for netuid in range(0, self.MAX_NETUIDS):
                    try:
                        result = self._substrate.query(
                            module='SubtensorModule',
                            storage_function='TotalHotkeyAlpha',
                            params=[validator_hotkey, netuid],
                            block_hash=block_hash
                        )
                        if result and result.value and result.value > 0:
                            netuids_to_check.append(netuid)
                    except Exception:
                        pass

            total_yield = Decimal(0)
            yield_by_subnet = {}

            # Detect emissions by comparing TotalHotkeyAlpha between this
            # block and the previous block. Bittensor distributes emissions
            # at tempo boundaries (every N blocks per subnet). A positive
            # delta in TotalHotkeyAlpha indicates emissions were received.
            for netuid in netuids_to_check:
                try:
                    curr = self._substrate.query(
                        module='SubtensorModule',
                        storage_function='TotalHotkeyAlpha',
                        params=[validator_hotkey, netuid],
                        block_hash=block_hash
                    )
                    curr_val = curr.value if curr and curr.value else 0
                    if curr_val == 0:
                        continue

                    prev = self._substrate.query(
                        module='SubtensorModule',
                        storage_function='TotalHotkeyAlpha',
                        params=[validator_hotkey, netuid],
                        block_hash=prev_hash
                    )
                    prev_val = prev.value if prev and prev.value else 0

                    delta = curr_val - prev_val
                    if delta > 0:
                        yield_amount = Decimal(str(delta))
                        total_yield += yield_amount
                        yield_by_subnet[netuid] = yield_amount
                        logger.debug(
                            "Emission detected via alpha delta",
                            block=block_number,
                            netuid=netuid,
                            delta=delta,
                        )
                except Exception as e:
                    logger.debug(
                        "Error checking alpha delta",
                        netuid=netuid,
                        error=str(e),
                    )

            if total_yield == 0:
                return None

            return BlockYieldData(
                block_number=block_number,
                validator_hotkey=validator_hotkey,
                total_dtao_earned=total_yield,
                yield_by_subnet=yield_by_subnet
            )

        return self._retry_call(_fetch)
    
    def get_conversion_events(
        self,
        start_block: int,
        end_block: int,
        validator_hotkey: Optional[str] = None
    ) -> list[ConversionData]:
        """
        Fetch dTAO to TAO conversion events in a block range.
        
        This parses extrinsics for conversion/swap operations.
        """
        if not self._connected:
            # Mock mode
            logger.debug(
                "Mock mode: returning empty conversions",
                start_block=start_block,
                end_block=end_block
            )
            return []
        
        def _fetch():
            conversions = []
            
            for block_num in range(start_block, end_block + 1):
                block_hash = self._substrate.get_block_hash(block_num)
                if not block_hash:
                    continue
                
                block = self._substrate.get_block(block_hash)
                events = self._substrate.get_events(block_hash)
                
                # Parse extrinsics for swap / conversion calls
                if block and "extrinsics" in block:
                    for ext_idx, ext in enumerate(block["extrinsics"]):
                        call = ext.get("call", {})
                        call_module = call.get("call_module", "")
                        call_function = call.get("call_function", "")

                        # Match known swap extrinsic names
                        swap_functions = {
                            "do_swap_alpha_for_tao",
                            "swap_alpha_for_tao",
                            "swap",
                            "do_swap",
                        }

                        if call_module == "SubtensorModule" and call_function in swap_functions:
                            # Extract args
                            args = {
                                p.get("name", ""): p.get("value")
                                for p in call.get("call_args", [])
                            }

                            ext_hotkey = args.get("hotkey") or args.get("validator_hotkey", "")
                            if validator_hotkey and ext_hotkey != validator_hotkey:
                                continue

                            subnet_id = args.get("netuid") or args.get("subnet_id")
                            if subnet_id is not None:
                                subnet_id = int(subnet_id)

                            dtao_amt = Decimal(str(args.get("alpha_amount", 0) or args.get("amount", 0)))
                            tao_amt = Decimal(0)
                            rate = Decimal(0)

                            # Try to find corresponding event with actual TAO received
                            for evt in events:
                                evt_module = getattr(evt, "event_module", "") or ""
                                evt_id = getattr(evt, "event_id", "") or ""
                                if evt_module == "SubtensorModule" and evt_id in (
                                    "AlphaSwapped", "SwapExecuted", "StakeRemoved"
                                ):
                                    evt_attrs = getattr(evt, "attributes", {}) or {}
                                    if isinstance(evt_attrs, dict):
                                        evt_tao = evt_attrs.get("tao_amount") or evt_attrs.get("amount_tao", 0)
                                        tao_amt = Decimal(str(evt_tao))
                                        break
                                    elif isinstance(evt_attrs, (list, tuple)) and len(evt_attrs) >= 2:
                                        tao_amt = Decimal(str(evt_attrs[1]))
                                        break

                            if dtao_amt > 0 and tao_amt > 0:
                                rate = (tao_amt / dtao_amt).quantize(Decimal("1E-18"))

                            tx_hash = ext.get("extrinsic_hash", f"0x{block_num:x}-{ext_idx}")

                            conversions.append(ConversionData(
                                block_number=block_num,
                                transaction_hash=tx_hash,
                                validator_hotkey=ext_hotkey,
                                dtao_amount=dtao_amt,
                                tao_amount=tao_amt,
                                conversion_rate=rate,
                                subnet_id=subnet_id,
                            ))

                # Also scan events directly for swap events not tied to parsed extrinsics
                for evt in events:
                    evt_module = getattr(evt, "event_module", "") or ""
                    evt_id = getattr(evt, "event_id", "") or ""
                    if evt_module == "SubtensorModule" and evt_id in (
                        "AlphaSwapped", "SwapExecuted"
                    ):
                        evt_attrs = getattr(evt, "attributes", {}) or {}
                        if not isinstance(evt_attrs, dict):
                            continue
                        evt_hotkey = evt_attrs.get("hotkey", "")
                        if validator_hotkey and evt_hotkey != validator_hotkey:
                            continue

                        # Skip if we already captured this via extrinsic parsing
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

                        tx_hash = evt_attrs.get("extrinsic_hash", f"0xevt-{block_num:x}")

                        conversions.append(ConversionData(
                            block_number=block_num,
                            transaction_hash=tx_hash,
                            validator_hotkey=evt_hotkey,
                            dtao_amount=dtao_amt,
                            tao_amount=tao_amt,
                            conversion_rate=rate,
                            subnet_id=subnet_id,
                        ))

            return conversions
        
        return self._retry_call(_fetch)
    
    def verify_block_hash(self, block_number: int, expected_hash: str) -> bool:
        """
        Verify a block hash matches the chain.
        
        Used for reorg detection.
        """
        if not self._connected:
            return True  # Mock mode assumes valid
        
        try:
            actual_hash = self._substrate.get_block_hash(block_number)
            return actual_hash == expected_hash
        except Exception:
            return False
