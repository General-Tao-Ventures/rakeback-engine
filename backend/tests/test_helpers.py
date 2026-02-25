"""Tests for rakeback.services._helpers."""

import json

from rakeback.services._helpers import dump_json, load_json, new_id, now_iso, today_iso


def test_new_id_uniqueness() -> None:
    ids: set[str] = {new_id() for _ in range(100)}
    assert len(ids) == 100


def test_now_iso_format() -> None:
    ts: str = now_iso()
    assert "T" in ts
    assert ts.endswith("+00:00")


def test_today_iso_format() -> None:
    d: str = today_iso()
    assert len(d) == 10  # YYYY-MM-DD


def test_dump_load_json_roundtrip() -> None:
    data: dict[str, object] = {"key": "value", "nested": [1, 2, 3]}
    raw: str = dump_json(data)
    assert isinstance(raw, str)
    assert load_json(raw) == data


def test_load_json_none() -> None:
    assert load_json(None) is None
    assert load_json("") is None


def test_dump_json_handles_non_serializable() -> None:
    from datetime import date

    raw: str = dump_json({"d": date(2026, 1, 1)})
    parsed: dict[str, object] = json.loads(raw)
    assert parsed["d"] == "2026-01-01"
