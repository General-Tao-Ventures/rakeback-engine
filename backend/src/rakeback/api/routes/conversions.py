"""Conversion endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["conversions"])


@router.get("/conversions")
def list_conversions():
    return []
