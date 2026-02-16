"""RuleChangeLog model - audit trail for partner/rule changes."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from rakeback.models.base import Base, generate_uuid, utc_now


class RuleChangeLog(Base):
    """
    Immutable audit log for partner and rule configuration changes.
    """
    
    __tablename__ = "rule_change_log"
    
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )
    
    user: Mapped[str] = mapped_column(String(256), nullable=False, default="system")
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    partner_id: Mapped[str] = mapped_column(String(64), nullable=False)
    partner_name: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[str] = mapped_column(String(1024), nullable=False)
    
    # Block height from which the change applies
    applies_from_block: Mapped[int] = mapped_column(Integer, nullable=False)
