"""Attribution endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["attributions"])


@router.get("/attributions")
def list_attributions():
    return []
