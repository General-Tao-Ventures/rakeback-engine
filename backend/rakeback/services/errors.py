"""Shared exception hierarchy for rakeback services."""

# ── Chain ─────────────────────────────────────────────────────────────────────


class ChainClientError(Exception):
    """Base exception for chain client errors."""


class RPCError(ChainClientError):
    """RPC call failed."""


class BlockNotFoundError(ChainClientError):
    """Requested block not found."""


class ChainConnectionError(ChainClientError):
    """Cannot connect to RPC endpoint."""


# ── Ingestion ─────────────────────────────────────────────────────────────────


class IngestionError(Exception):
    """Base exception for ingestion errors."""


class CSVImportError(IngestionError):
    """CSV import failed."""


# ── Attribution ───────────────────────────────────────────────────────────────


class AttributionError(Exception):
    """Base exception for attribution errors."""


class AttributionIncompleteDataError(AttributionError):
    """Required data is missing or incomplete."""


class AttributionValidationError(AttributionError):
    """Data validation failed during attribution."""


# ── Aggregation ───────────────────────────────────────────────────────────────


class AggregationError(Exception):
    """Base exception for aggregation errors."""


class AggregationIncompleteDataError(AggregationError):
    """Required data is incomplete."""


# ── Rules ─────────────────────────────────────────────────────────────────────


class RulesEngineError(Exception):
    """Base exception for rules engine errors."""


class InvalidRuleError(RulesEngineError):
    """A matching rule is invalid."""


# ── Export ────────────────────────────────────────────────────────────────────


class ExportError(Exception):
    """Base exception for export errors."""
