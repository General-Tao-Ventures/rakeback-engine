"""Partner management endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from rakeback.services.participant_service import ParticipantService

router = APIRouter(prefix="/api", tags=["partners"])


class PartnerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: str = Field(..., description="named | tag-based | hybrid")
    rakebackRate: float = Field(..., ge=0, le=100)
    priority: int = Field(1, ge=1)
    payoutAddress: str = Field("", max_length=64)
    walletAddress: Optional[str] = None
    walletLabel: Optional[str] = None
    memoKeyword: Optional[str] = None
    matchType: Optional[str] = "contains"
    applyFromDate: Optional[str] = None
    applyFromBlock: Optional[int] = None
    # Hybrid can have both
    hybridWallet: Optional[str] = None
    hybridWalletLabel: Optional[str] = None
    hybridMemo: Optional[str] = None
    hybridMatchType: Optional[str] = "contains"


class RuleCreate(BaseModel):
    type: str = Field(..., description="wallet | memo | subnet-filter")
    config: dict = Field(default_factory=dict)
    appliesFromBlock: Optional[int] = None


class PartnerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    rakebackRate: Optional[float] = Field(None, ge=0, le=100)
    priority: Optional[int] = Field(None, ge=1)
    payoutAddress: Optional[str] = Field(None, max_length=64)
    partnerType: Optional[str] = None


@router.get("/partners")
def list_partners():
    """List all partners."""
    from rakeback.database import get_session
    with get_session() as session:
        svc = ParticipantService(session)
        return svc.list_partners(active_only=False)


@router.get("/partners/rule-change-log/list")
def list_rule_change_log(limit: int = 100):
    """Get rule change audit log."""
    from rakeback.database import get_session
    with get_session() as session:
        svc = ParticipantService(session)
        return svc.get_rule_change_log(limit=limit)


@router.get("/partners/{partner_id}")
def get_partner(partner_id: str):
    """Get a single partner with rules."""
    from rakeback.database import get_session
    with get_session() as session:
        svc = ParticipantService(session)
        p = svc.get_partner(partner_id)
        if not p:
            raise HTTPException(status_code=404, detail="Partner not found")
        return p


@router.post("/partners")
def create_partner(body: PartnerCreate):
    """Create a new partner with rules."""
    from rakeback.database import get_session
    with get_session() as session:
        svc = ParticipantService(session)
        rules = []
        pt = body.type.lower().replace(" ", "-")
        if pt in ("named", "tag-based", "hybrid"):
            if pt == "named" and body.walletAddress:
                rules.append({
                    "type": "wallet",
                    "config": {"wallet": body.walletAddress, "label": body.walletLabel or ""},
                    "appliesFromBlock": body.applyFromBlock,
                })
            elif pt == "tag-based" and body.memoKeyword:
                rules.append({
                    "type": "memo",
                    "config": {
                        "memo_string": body.memoKeyword,
                        "match_type": body.matchType or "contains",
                        "extrinsic_types": ["stake", "unstake", "redelegate"],
                    },
                    "appliesFromBlock": body.applyFromBlock,
                })
            elif pt == "hybrid":
                if body.hybridWallet:
                    rules.append({
                        "type": "wallet",
                        "config": {"wallet": body.hybridWallet, "label": body.hybridWalletLabel or ""},
                        "appliesFromBlock": body.applyFromBlock,
                    })
                if body.hybridMemo:
                    rules.append({
                        "type": "memo",
                        "config": {
                            "memo_string": body.hybridMemo,
                            "match_type": body.hybridMatchType or "contains",
                            "extrinsic_types": ["stake", "unstake", "redelegate"],
                        },
                        "appliesFromBlock": body.applyFromBlock,
                    })
        return svc.create_partner(
            name=body.name,
            partner_type=pt,
            rakeback_rate=body.rakebackRate,
            priority=body.priority,
            payout_address=body.payoutAddress or "0x0",
            rules=rules if rules else None,
            applies_from_block=body.applyFromBlock,
        )


@router.put("/partners/{partner_id}")
def update_partner(partner_id: str, body: PartnerUpdate):
    """Update partner fields."""
    from rakeback.database import get_session
    with get_session() as session:
        svc = ParticipantService(session)
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        p = svc.update_partner(partner_id, updates)
        if not p:
            raise HTTPException(status_code=404, detail="Partner not found")
        return p


@router.post("/partners/{partner_id}/rules")
def add_partner_rule(partner_id: str, body: RuleCreate):
    """Add a rule to a partner."""
    from rakeback.database import get_session
    with get_session() as session:
        svc = ParticipantService(session)
        rule = svc.add_rule(partner_id, {"type": body.type, "config": body.config, "appliesFromBlock": body.appliesFromBlock})
        if not rule:
            raise HTTPException(status_code=404, detail="Partner not found or invalid rule")
        return rule
