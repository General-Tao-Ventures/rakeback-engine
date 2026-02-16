"""Repository layer for data access."""

from rakeback.repositories.base import BaseRepository
from rakeback.repositories.block_snapshot import BlockSnapshotRepository
from rakeback.repositories.block_yield import BlockYieldRepository
from rakeback.repositories.block_attribution import BlockAttributionRepository
from rakeback.repositories.conversion import ConversionEventRepository, TaoAllocationRepository
from rakeback.repositories.ledger import RakebackLedgerRepository
from rakeback.repositories.participant import ParticipantRepository
from rakeback.repositories.eligibility_rule import EligibilityRuleRepository
from rakeback.repositories.rule_change_log import RuleChangeLogRepository
from rakeback.repositories.processing import ProcessingRunRepository, DataGapRepository

__all__ = [
    "BaseRepository",
    "BlockSnapshotRepository",
    "BlockYieldRepository",
    "BlockAttributionRepository",
    "ConversionEventRepository",
    "TaoAllocationRepository",
    "RakebackLedgerRepository",
    "ParticipantRepository",
    "EligibilityRuleRepository",
    "RuleChangeLogRepository",
    "ProcessingRunRepository",
    "DataGapRepository",
]
