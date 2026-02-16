"""EligibilityRule model - separate rule entity for audit and CRUD."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rakeback.models.base import Base, utc_now


def _rule_uid() -> str:
    import uuid
    return "rule_" + str(uuid.uuid4())[:12]


class EligibilityRule(Base):
    """
    Single eligibility rule for a partner.
    
    Replaces inline matching_rules JSON with separate entities for:
    - Per-rule audit trail
    - Add/edit rules without touching partner record
    - Rule-level effective dates
    """
    
    __tablename__ = "eligibility_rules"
    
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_rule_uid)
    
    participant_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("rakeback_participants.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Rule type: wallet (EXACT_ADDRESS), memo (RT21_AUTO_DELEGATION / memo match), subnet-filter
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    
    # Rule configuration (JSON)
    # For wallet: {"addresses": ["5C..."], "label": "..."}
    # For memo: {"memo_string": "talisman", "match_type": "contains", "extrinsic_types": ["stake","unstake"]}
    # For subnet: {"subnet_ids": [21], "delegation_types": ["subnet_dtao"]}
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # When this rule takes effect (block height or null = immediate)
    applies_from_block: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )
    created_by: Mapped[str] = mapped_column(String(256), nullable=False, default="system")
    
    participant: Mapped["RakebackParticipant"] = relationship("RakebackParticipant", back_populates="eligibility_rules")
    
    __table_args__ = (
        Index("ix_eligibility_rules_participant", "participant_id"),
    )
