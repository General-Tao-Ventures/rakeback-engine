"""Enumeration types for the Rakeback Attribution Engine.

Values MUST match the CHECK constraints in migrations/001_initial_schema.sql.
"""

from enum import StrEnum


class CompletenessFlag(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    INCOMPLETE = "INCOMPLETE"


class DataSource(StrEnum):
    CHAIN = "CHAIN"
    CSV_OVERRIDE = "CSV_OVERRIDE"
    BACKFILL = "BACKFILL"


class DelegationType(StrEnum):
    ROOT_TAO = "ROOT_TAO"
    SUBNET_DTAO = "SUBNET_DTAO"
    CHILD_HOTKEY = "CHILD_HOTKEY"


class AllocationMethod(StrEnum):
    FIFO = "FIFO"
    PRORATA = "PRORATA"
    EXPLICIT = "EXPLICIT"


class PaymentStatus(StrEnum):
    UNPAID = "UNPAID"
    PAID = "PAID"
    DISPUTED = "DISPUTED"


class PeriodType(StrEnum):
    DAILY = "DAILY"
    MONTHLY = "MONTHLY"


class ParticipantType(StrEnum):
    PARTNER = "PARTNER"
    DELEGATOR_GROUP = "DELEGATOR_GROUP"
    SUBNET = "SUBNET"


class PartnerType(StrEnum):
    NAMED = "NAMED"
    TAG_BASED = "TAG_BASED"
    HYBRID = "HYBRID"


class AggregationMode(StrEnum):
    LUMP_SUM = "LUMP_SUM"
    PER_WALLET = "PER_WALLET"


class GapType(StrEnum):
    SNAPSHOT = "SNAPSHOT"
    YIELD = "YIELD"
    CONVERSION = "CONVERSION"


class ResolutionStatus(StrEnum):
    OPEN = "OPEN"
    BACKFILLED = "BACKFILLED"
    UNRECOVERABLE = "UNRECOVERABLE"


class RunType(StrEnum):
    INGESTION = "INGESTION"
    ATTRIBUTION = "ATTRIBUTION"
    AGGREGATION = "AGGREGATION"
    EXPORT = "EXPORT"
    RERUN = "RERUN"


class RuleType(StrEnum):
    EXACT_ADDRESS = "EXACT_ADDRESS"
    DELEGATION_TYPE = "DELEGATION_TYPE"
    SUBNET = "SUBNET"
    RT21_AUTO_DELEGATION = "RT21_AUTO_DELEGATION"
    ALL = "ALL"


class RunStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
