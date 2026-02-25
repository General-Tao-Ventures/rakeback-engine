"""Enumeration types for the Rakeback Attribution Engine.

Values MUST match the CHECK constraints in migrations/001_initial_schema.sql.
"""

from enum import Enum


class CompletenessFlag(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    INCOMPLETE = "INCOMPLETE"


class DataSource(str, Enum):
    CHAIN = "CHAIN"
    CSV_OVERRIDE = "CSV_OVERRIDE"
    BACKFILL = "BACKFILL"


class DelegationType(str, Enum):
    ROOT_TAO = "ROOT_TAO"
    SUBNET_DTAO = "SUBNET_DTAO"
    CHILD_HOTKEY = "CHILD_HOTKEY"


class AllocationMethod(str, Enum):
    FIFO = "FIFO"
    PRORATA = "PRORATA"
    EXPLICIT = "EXPLICIT"


class PaymentStatus(str, Enum):
    UNPAID = "UNPAID"
    PAID = "PAID"
    DISPUTED = "DISPUTED"


class PeriodType(str, Enum):
    DAILY = "DAILY"
    MONTHLY = "MONTHLY"


class ParticipantType(str, Enum):
    PARTNER = "PARTNER"
    DELEGATOR_GROUP = "DELEGATOR_GROUP"
    SUBNET = "SUBNET"


class PartnerType(str, Enum):
    NAMED = "NAMED"
    TAG_BASED = "TAG_BASED"
    HYBRID = "HYBRID"


class AggregationMode(str, Enum):
    LUMP_SUM = "LUMP_SUM"
    PER_WALLET = "PER_WALLET"


class GapType(str, Enum):
    SNAPSHOT = "SNAPSHOT"
    YIELD = "YIELD"
    CONVERSION = "CONVERSION"


class ResolutionStatus(str, Enum):
    OPEN = "OPEN"
    BACKFILLED = "BACKFILLED"
    UNRECOVERABLE = "UNRECOVERABLE"


class RunType(str, Enum):
    INGESTION = "INGESTION"
    ATTRIBUTION = "ATTRIBUTION"
    AGGREGATION = "AGGREGATION"
    EXPORT = "EXPORT"
    RERUN = "RERUN"


class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
