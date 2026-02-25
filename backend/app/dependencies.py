"""FastAPI dependencies — DB sessions and auth."""

from fastapi import Header, HTTPException

from config import get_settings
from db.connection import get_db as get_db  # noqa: F401 — re-exported for routes


def get_api_key(x_api_key: str = Header(default="")) -> str:
    """Validate API key on mutation endpoints."""
    expected: str | None = get_settings().api_key
    if not expected:
        return ""  # auth disabled when no key configured
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key
