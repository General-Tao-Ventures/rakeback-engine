"""Shared utilities for the service layer."""

import json
from datetime import UTC, datetime
from uuid import uuid4


def new_id() -> str:
    """Generate a UUID string for use as primary key."""
    return str(uuid4())


def now_iso() -> str:
    """Current UTC timestamp as ISO-8601 string."""
    return datetime.now(UTC).isoformat()


def today_iso() -> str:
    """Current UTC date as ISO-8601 string."""
    return datetime.now(UTC).date().isoformat()


def load_json(raw: str | None) -> dict | list | None:
    """Deserialize a JSON TEXT column. Returns None for NULL."""
    if not raw:
        return None
    return json.loads(raw)


def dump_json(obj) -> str:
    """Serialize a dict/list for storage in a JSON TEXT column."""
    return json.dumps(obj, default=str)
