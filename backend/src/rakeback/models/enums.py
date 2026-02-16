"""Enumeration types for the Rakeback Attribution Engine."""

from enum import Enum


class CompletenessFlag(str, Enum):
    """Indicates data completeness status."""
    
    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING = "missing"
    INCOMPLETE = "incomplete"  # Derived from missing upstream data


class DataSource(str, Enum):
    """Source of ingested data."""
    
    CHAIN = "chain"
    CSV_OVERRIDE = "csv_override"
    BACKFILL = "backfill"


class DelegationType(str, Enum):
    """Type of delegation to validator."""
    
    ROOT_TAO = "root_tao"
    SUBNET_DTAO = "subnet_dtao"
    CHILD_HOTKEY = "child_hotkey"


class AllocationMethod(str, Enum):
    """Method used to allocate converted TAO to attributions."""
    
    FIFO = "fifo"
    PRORATA = "prorata"
    EXPLICIT = "explicit"


class PaymentStatus(str, Enum):
    """Payment status for rakeback ledger entries."""
    
    UNPAID = "unpaid"
    PAID = "paid"
    DISPUTED = "disputed"


class PeriodType(str, Enum):
    """Aggregation period type."""
    
    DAILY = "daily"
    MONTHLY = "monthly"


class ParticipantType(str, Enum):
    """Type of rakeback participant."""
    
    PARTNER = "partner"
    DELEGATOR_GROUP = "delegator_group"
    SUBNET = "subnet"


class PartnerType(str, Enum):
    """Discovery mechanism for partners (aligns with UI)."""
    
    NAMED = "named"
    TAG_BASED = "tag_based"
    HYBRID = "hybrid"


class AggregationMode(str, Enum):
    """How rakeback should be aggregated for a participant."""
    
    LUMP_SUM = "lump_sum"
    PER_WALLET = "per_wallet"


class GapType(str, Enum):
    """Type of data gap detected."""
    
    SNAPSHOT = "snapshot"
    YIELD = "yield"
    CONVERSION = "conversion"


class ResolutionStatus(str, Enum):
    """Resolution status of a data gap."""
    
    OPEN = "open"
    BACKFILLED = "backfilled"
    UNRECOVERABLE = "unrecoverable"


class RunType(str, Enum):
    """Type of processing run."""
    
    INGESTION = "ingestion"
    ATTRIBUTION = "attribution"
    AGGREGATION = "aggregation"
    EXPORT = "export"
    RERUN = "rerun"


class RunStatus(str, Enum):
    """Status of a processing run."""
    
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
