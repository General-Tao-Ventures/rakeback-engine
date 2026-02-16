"""Partner management endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["partners"])


@router.get("/partners")
def list_partners():
    return []


@router.post("/partners")
def create_partner():
    return {"status": "not_implemented"}
