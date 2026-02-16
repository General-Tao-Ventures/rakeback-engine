"""Repository for RuleChangeLog."""

from typing import Sequence

from sqlalchemy import select

from rakeback.models import RuleChangeLog
from rakeback.repositories.base import BaseRepository


class RuleChangeLogRepository(BaseRepository[RuleChangeLog]):
    """Repository for RuleChangeLog audit entries."""

    model = RuleChangeLog

    def get_all_recent(self, limit: int = 100) -> Sequence[RuleChangeLog]:
        """Get most recent log entries."""
        stmt = (
            select(RuleChangeLog)
            .order_by(RuleChangeLog.timestamp.desc())
            .limit(limit)
        )
        return self.session.scalars(stmt).all()
