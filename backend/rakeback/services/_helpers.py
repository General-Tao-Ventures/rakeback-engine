"""Shared utilities for the service layer."""

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import uuid4

# JSON column type — every JSON TEXT column in this DB stores a dict.
JsonDict = dict[str, object]
Serializable = Mapping[str, object] | list[Mapping[str, object]]


def new_id() -> str:
    return str(uuid4())


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


def load_json(raw: str | None) -> JsonDict | None:
    """Deserialize a JSON TEXT column. Always a dict or None in this codebase."""
    if not raw:
        return None
    result: object = json.loads(raw)
    if isinstance(result, dict):
        return dict(result)
    return None


def dump_json(obj: Serializable) -> str:
    return json.dumps(obj, default=str)
