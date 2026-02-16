"""Repository for EligibilityRule."""

from typing import Sequence

from sqlalchemy import select

from rakeback.models import EligibilityRule
from rakeback.repositories.base import BaseRepository


class EligibilityRuleRepository(BaseRepository[EligibilityRule]):
    """Repository for EligibilityRule operations."""

    model = EligibilityRule

    def get_by_participant(self, participant_id: str) -> Sequence[EligibilityRule]:
        """Get all rules for a participant."""
        stmt = (
            select(EligibilityRule)
            .where(EligibilityRule.participant_id == participant_id)
            .order_by(EligibilityRule.created_at)
        )
        return self.session.scalars(stmt).all()
