"""Partner management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_api_key, get_db
from app.schemas.partners import PartnerCreate, PartnerUpdate, RuleCreate
from rakeback.services.participant_service import ParticipantService

router = APIRouter(prefix="/api", tags=["partners"])


@router.get("/partners")
def list_partners(db: Session = Depends(get_db)):
    svc = ParticipantService(db)
    return svc.list_partners(active_only=False)


@router.get("/partners/rule-change-log/list")
def list_rule_change_log(limit: int = 100, db: Session = Depends(get_db)):
    svc = ParticipantService(db)
    return svc.get_rule_change_log(limit=limit)


@router.get("/partners/{partner_id}")
def get_partner(partner_id: str, db: Session = Depends(get_db)):
    svc = ParticipantService(db)
    p = svc.get_partner(partner_id)
    if not p:
        raise HTTPException(status_code=404, detail="Partner not found")
    return p


@router.post("/partners")
def create_partner(
    body: PartnerCreate,
    db: Session = Depends(get_db),
    _key: str = Depends(get_api_key),
):
    svc = ParticipantService(db)
    return svc.create_partner_from_request(body.model_dump())


@router.put("/partners/{partner_id}")
def update_partner(
    partner_id: str,
    body: PartnerUpdate,
    db: Session = Depends(get_db),
    _key: str = Depends(get_api_key),
):
    svc = ParticipantService(db)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    p = svc.update_partner(partner_id, updates)
    if not p:
        raise HTTPException(status_code=404, detail="Partner not found")
    return p


@router.post("/partners/{partner_id}/rules")
def add_partner_rule(
    partner_id: str,
    body: RuleCreate,
    db: Session = Depends(get_db),
    _key: str = Depends(get_api_key),
):
    svc = ParticipantService(db)
    rule = svc.add_rule(partner_id, body.model_dump())
    if not rule:
        raise HTTPException(status_code=404, detail="Partner not found or invalid rule")
    return rule
