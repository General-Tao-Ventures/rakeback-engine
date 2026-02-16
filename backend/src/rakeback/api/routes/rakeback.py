"""Rakeback calculation endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["rakeback"])


@router.get("/rakeback")
def list_rakeback():
    return []
