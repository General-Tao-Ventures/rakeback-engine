"""Rules engine for matching delegators to rakeback participants."""

from datetime import date
from typing import Optional, Sequence

import structlog
from sqlalchemy.orm import Session

from rakeback.models import RakebackParticipant, DelegationType
from rakeback.repositories import ParticipantRepository

logger = structlog.get_logger(__name__)


class RulesEngineError(Exception):
    """Base exception for rules engine errors."""
    pass


class InvalidRuleError(RulesEngineError):
    """A matching rule is invalid."""
    pass


class RulesEngine:
    """
    Engine for matching delegators to rakeback participants.
    
    Supports multiple rule types:
    - EXACT_ADDRESS: Match specific wallet addresses
    - DELEGATION_TYPE: Match by delegation type (root_tao, subnet_dtao, etc.)
    - SUBNET: Match by subnet ID
    - RT21_AUTO_DELEGATION: Special rule for Talisman RT21 detection
    
    Rules are evaluated in order and combined with OR logic.
    """
    
    def __init__(self, session: Session):
        """Initialize the rules engine."""
        self.session = session
        self.participant_repo = ParticipantRepository(session)
    
    def match_delegator(
        self,
        delegator_address: str,
        delegation_type: DelegationType,
        subnet_id: Optional[int],
        as_of_date: Optional[date] = None
    ) -> Optional[RakebackParticipant]:
        """
        Find the rakeback participant that matches a delegator.
        
        Returns the first matching participant or None.
        """
        check_date = as_of_date or date.today()
        participants = self.participant_repo.get_active(check_date)
        
        for participant in participants:
            if self._matches_participant(
                participant, delegator_address, delegation_type, subnet_id
            ):
                return participant
        
        return None
    
    def match_addresses(
        self,
        participant: RakebackParticipant,
        addresses: Sequence[str]
    ) -> list[str]:
        """
        Filter addresses to those matching a participant's rules.
        
        Returns list of matching addresses.
        """
        matching = []
        
        for address in addresses:
            # For simple address matching, we check the rules
            # More complex matching would require delegation type info
            if self._matches_address_rules(participant, address):
                matching.append(address)
        
        return matching
    
    def _matches_participant(
        self,
        participant: RakebackParticipant,
        delegator_address: str,
        delegation_type: DelegationType,
        subnet_id: Optional[int]
    ) -> bool:
        """
        Check if a delegation matches a participant's rules.
        """
        rules = participant.matching_rules.get("rules", [])
        
        if not rules:
            return False
        
        # OR logic: any rule match is sufficient
        for rule in rules:
            if self._evaluate_rule(
                rule, delegator_address, delegation_type, subnet_id
            ):
                return True
        
        return False
    
    def _matches_address_rules(
        self,
        participant: RakebackParticipant,
        address: str
    ) -> bool:
        """
        Check if an address matches any address-based rules.
        """
        rules = participant.matching_rules.get("rules", [])
        
        for rule in rules:
            rule_type = rule.get("type")
            
            if rule_type == "EXACT_ADDRESS":
                if address in rule.get("addresses", []):
                    return True
            
            # For other rule types, we'd need delegation info
            # Return True for wildcard/all matching
            elif rule_type == "ALL":
                return True
        
        return False
    
    def _evaluate_rule(
        self,
        rule: dict,
        delegator_address: str,
        delegation_type: DelegationType,
        subnet_id: Optional[int]
    ) -> bool:
        """
        Evaluate a single matching rule.
        """
        rule_type = rule.get("type")
        
        if rule_type == "EXACT_ADDRESS":
            return delegator_address in rule.get("addresses", [])
        
        elif rule_type == "DELEGATION_TYPE":
            allowed_types = rule.get("delegation_types", [])
            if delegation_type.value not in allowed_types:
                return False
            
            # Check subnet filter if present
            subnet_filter = rule.get("subnet_ids")
            if subnet_filter and subnet_id not in subnet_filter:
                return False
            
            return True
        
        elif rule_type == "SUBNET":
            subnet_filter = rule.get("subnet_ids", [])
            return subnet_id in subnet_filter
        
        elif rule_type == "RT21_AUTO_DELEGATION":
            # Special handling for Talisman RT21 delegations
            # This would require additional context about how the delegation was created
            # For now, return False - actual implementation would parse extrinsics
            return False
        
        elif rule_type == "ALL":
            # Matches everything
            return True
        
        else:
            logger.warning("Unknown rule type", rule_type=rule_type)
            return False
    
    def validate_rules(self, participant: RakebackParticipant) -> list[str]:
        """
        Validate a participant's matching rules.
        
        Returns list of validation errors (empty if valid).
        """
        errors = []
        rules = participant.matching_rules.get("rules", [])
        
        if not rules:
            errors.append("No matching rules defined")
            return errors
        
        for i, rule in enumerate(rules):
            rule_type = rule.get("type")
            
            if not rule_type:
                errors.append(f"Rule {i}: Missing 'type' field")
                continue
            
            if rule_type == "EXACT_ADDRESS":
                addresses = rule.get("addresses", [])
                if not addresses:
                    errors.append(f"Rule {i}: EXACT_ADDRESS has no addresses")
                for addr in addresses:
                    if not isinstance(addr, str) or len(addr) < 10:
                        errors.append(f"Rule {i}: Invalid address format")
            
            elif rule_type == "DELEGATION_TYPE":
                types = rule.get("delegation_types", [])
                if not types:
                    errors.append(f"Rule {i}: DELEGATION_TYPE has no types")
                valid_types = [dt.value for dt in DelegationType]
                for t in types:
                    if t not in valid_types:
                        errors.append(f"Rule {i}: Invalid delegation type '{t}'")
            
            elif rule_type == "SUBNET":
                subnets = rule.get("subnet_ids", [])
                if not subnets:
                    errors.append(f"Rule {i}: SUBNET has no subnet_ids")
            
            elif rule_type == "RT21_AUTO_DELEGATION":
                if not rule.get("memo_string"):
                    errors.append(f"Rule {i}: RT21_AUTO_DELEGATION has no memo_string")
            
            elif rule_type != "ALL":
                errors.append(f"Rule {i}: Unknown rule type '{rule_type}'")
        
        return errors
    
    def add_participant(
        self,
        id: str,
        name: str,
        participant_type: str,
        matching_rules: dict,
        rakeback_percentage: float,
        payout_address: str,
        effective_from: date,
        aggregation_mode: str = "lump_sum"
    ) -> RakebackParticipant:
        """
        Add a new rakeback participant.
        """
        from decimal import Decimal
        from rakeback.models import ParticipantType, AggregationMode
        
        participant = RakebackParticipant(
            id=id,
            name=name,
            type=ParticipantType(participant_type),
            matching_rules=matching_rules,
            rakeback_percentage=Decimal(str(rakeback_percentage)),
            payout_address=payout_address,
            effective_from=effective_from,
            aggregation_mode=AggregationMode(aggregation_mode)
        )
        
        # Validate rules
        errors = self.validate_rules(participant)
        if errors:
            raise InvalidRuleError(f"Invalid rules: {errors}")
        
        self.participant_repo.add(participant)
        return participant
    
    def get_rules_snapshot(self, as_of: date) -> dict:
        """
        Get a snapshot of all active rules as of a date.
        
        Useful for audit trail and reproducibility.
        """
        participants = self.participant_repo.get_active(as_of)
        
        return {
            "as_of": as_of.isoformat(),
            "participants": [
                {
                    "id": p.id,
                    "name": p.name,
                    "type": p.type.value,
                    "rakeback_percentage": str(p.rakeback_percentage),
                    "matching_rules": p.matching_rules,
                    "aggregation_mode": p.aggregation_mode.value
                }
                for p in participants
            ]
        }
