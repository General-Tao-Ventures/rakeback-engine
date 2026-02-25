"""Rules engine for matching delegators to rakeback participants."""

from datetime import date
from typing import Optional, Sequence

import structlog
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from db.enums import DelegationType
from db.models import RakebackParticipants
from rakeback.services._helpers import load_json

logger = structlog.get_logger(__name__)


class RulesEngineError(Exception):
    pass


class InvalidRuleError(RulesEngineError):
    pass


class RulesEngine:
    """Matches delegators to rakeback participants using configurable rules."""

    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def match_delegator(
        self,
        delegator_address: str,
        delegation_type: DelegationType,
        subnet_id: Optional[int],
        as_of_date: Optional[date] = None,
    ) -> Optional[RakebackParticipants]:
        """Return the first active participant whose rules match this delegator."""
        check_date = (as_of_date or date.today()).isoformat()
        participants = self._get_active_participants(check_date)
        for p in participants:
            if self._matches_participant(
                p, delegator_address, delegation_type.value, subnet_id
            ):
                return p
        return None

    def match_addresses(
        self,
        participant: RakebackParticipants,
        addresses: Sequence[str],
    ) -> list[str]:
        """Filter *addresses* to those matching a participant's rules."""
        return [a for a in addresses if self._matches_address_rules(participant, a)]

    def validate_rules(self, participant: RakebackParticipants) -> list[str]:
        """Return validation errors for a participant's matching_rules (empty = valid)."""
        rules = self._rules_list(participant)
        errors: list[str] = []
        if not rules:
            errors.append("No matching rules defined")
            return errors
        valid_dtypes = {dt.value for dt in DelegationType}
        for i, rule in enumerate(rules):
            rule_type = rule.get("type")
            if not rule_type:
                errors.append(f"Rule {i}: Missing 'type' field")
                continue
            if rule_type == "EXACT_ADDRESS":
                addrs = rule.get("addresses", [])
                if not addrs:
                    errors.append(f"Rule {i}: EXACT_ADDRESS has no addresses")
                for addr in addrs:
                    if not isinstance(addr, str) or len(addr) < 10:
                        errors.append(f"Rule {i}: Invalid address format")
            elif rule_type == "DELEGATION_TYPE":
                for t in rule.get("delegation_types", []):
                    if t not in valid_dtypes:
                        errors.append(f"Rule {i}: Invalid delegation type '{t}'")
            elif rule_type == "SUBNET":
                if not rule.get("subnet_ids"):
                    errors.append(f"Rule {i}: SUBNET has no subnet_ids")
            elif rule_type == "RT21_AUTO_DELEGATION":
                if not rule.get("memo_string"):
                    errors.append(f"Rule {i}: RT21_AUTO_DELEGATION has no memo_string")
            elif rule_type != "ALL":
                errors.append(f"Rule {i}: Unknown rule type '{rule_type}'")
        return errors

    def get_rules_snapshot(self, as_of: date) -> dict:
        """Snapshot of all active rules as of a date (for audit trail)."""
        check_date = as_of.isoformat()
        participants = self._get_active_participants(check_date)
        return {
            "as_of": as_of.isoformat(),
            "participants": [
                {
                    "id": p.id,
                    "name": p.name,
                    "type": p.type,
                    "rakeback_percentage": str(p.rakeback_percentage),
                    "matching_rules": load_json(p.matching_rules) or {},
                    "aggregation_mode": p.aggregation_mode,
                }
                for p in participants
            ],
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_active_participants(self, date_str: str) -> Sequence[RakebackParticipants]:
        stmt = (
            select(RakebackParticipants)
            .where(
                and_(
                    RakebackParticipants.effective_from <= date_str,
                    (
                        (RakebackParticipants.effective_to.is_(None))
                        | (RakebackParticipants.effective_to >= date_str)
                    ),
                )
            )
            .order_by(RakebackParticipants.priority, RakebackParticipants.id)
        )
        return self.session.scalars(stmt).all()

    @staticmethod
    def _rules_list(participant: RakebackParticipants) -> list[dict]:
        raw = participant.matching_rules
        mr = load_json(raw) if isinstance(raw, str) else raw
        if isinstance(mr, dict):
            return mr.get("rules", [])
        return []

    def _matches_participant(
        self,
        participant: RakebackParticipants,
        delegator_address: str,
        delegation_type_value: str,
        subnet_id: Optional[int],
    ) -> bool:
        rules = self._rules_list(participant)
        return any(
            self._evaluate_rule(r, delegator_address, delegation_type_value, subnet_id)
            for r in rules
        )

    def _matches_address_rules(
        self,
        participant: RakebackParticipants,
        address: str,
    ) -> bool:
        for rule in self._rules_list(participant):
            rt = rule.get("type")
            if rt == "EXACT_ADDRESS" and address in rule.get("addresses", []):
                return True
            if rt == "ALL":
                return True
        return False

    @staticmethod
    def _evaluate_rule(
        rule: dict,
        delegator_address: str,
        delegation_type_value: str,
        subnet_id: Optional[int],
    ) -> bool:
        rt = rule.get("type")
        if rt == "EXACT_ADDRESS":
            return delegator_address in rule.get("addresses", [])
        if rt == "DELEGATION_TYPE":
            if delegation_type_value not in rule.get("delegation_types", []):
                return False
            sf = rule.get("subnet_ids")
            if sf and subnet_id not in sf:
                return False
            return True
        if rt == "SUBNET":
            return subnet_id in rule.get("subnet_ids", [])
        if rt == "RT21_AUTO_DELEGATION":
            return False
        if rt == "ALL":
            return True
        logger.warning("Unknown rule type", rule_type=rt)
        return False
