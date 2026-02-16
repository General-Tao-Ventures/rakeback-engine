"""Export endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["exports"])


@router.get("/exports")
def list_exports():
    return []
