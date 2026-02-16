"""Repository for RakebackParticipant."""

from datetime import date
from typing import Optional, Sequence

from sqlalchemy import select, and_

from rakeback.models import RakebackParticipant, ParticipantType
from rakeback.repositories.base import BaseRepository


class ParticipantRepository(BaseRepository[RakebackParticipant]):
    """Repository for RakebackParticipant operations."""
    
    model = RakebackParticipant
    
    def get_by_id(self, id: str) -> Optional[RakebackParticipant]:
        """Get participant by ID."""
        return self.session.get(RakebackParticipant, id)
    
    def get_active(self, as_of: date) -> Sequence[RakebackParticipant]:
        """Get all participants active as of a date."""
        stmt = (
            select(RakebackParticipant)
            .where(
                and_(
                    RakebackParticipant.effective_from <= as_of,
                    (
                        (RakebackParticipant.effective_to == None) |
                        (RakebackParticipant.effective_to >= as_of)
                    )
                )
            )
            .order_by(RakebackParticipant.id)
        )
        return self.session.scalars(stmt).all()
    
    def get_by_type(
        self,
        participant_type: ParticipantType,
        active_only: bool = True,
        as_of: Optional[date] = None
    ) -> Sequence[RakebackParticipant]:
        """Get participants by type."""
        conditions = [RakebackParticipant.type == participant_type]
        
        if active_only:
            check_date = as_of or date.today()
            conditions.extend([
                RakebackParticipant.effective_from <= check_date,
                (
                    (RakebackParticipant.effective_to == None) |
                    (RakebackParticipant.effective_to >= check_date)
                )
            ])
        
        stmt = (
            select(RakebackParticipant)
            .where(and_(*conditions))
            .order_by(RakebackParticipant.id)
        )
        return self.session.scalars(stmt).all()
    
    def deactivate(self, id: str, effective_date: date) -> bool:
        """Deactivate a participant as of a date."""
        participant = self.get_by_id(id)
        if not participant:
            return False
        
        participant.effective_to = effective_date
        self.session.flush()
        return True
    
    def update_percentage(self, id: str, new_percentage: float) -> bool:
        """Update rakeback percentage for a participant."""
        from decimal import Decimal
        
        participant = self.get_by_id(id)
        if not participant:
            return False
        
        participant.rakeback_percentage = Decimal(str(new_percentage))
        self.session.flush()
        return True
    
    def search_by_address(self, address: str) -> Sequence[RakebackParticipant]:
        """
        Search for participants whose matching rules include an address.
        
        Note: This is a basic search. Complex rule matching should be
        done in the rules engine service.
        """
        # Get all participants and filter in Python
        # (JSON querying varies by database)
        all_participants = self.get_all()
        matching = []
        
        for p in all_participants:
            rules = p.matching_rules.get("rules", [])
            for rule in rules:
                if rule.get("type") == "EXACT_ADDRESS":
                    if address in rule.get("addresses", []):
                        matching.append(p)
                        break
        
        return matching
