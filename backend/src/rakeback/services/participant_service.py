"""Partner/participant CRUD service with rule entity sync."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from rakeback.models import (
    EligibilityRule,
    RakebackParticipant,
    RuleChangeLog,
    ParticipantType,
    PartnerType,
    AggregationMode,
)
from rakeback.repositories import (
    EligibilityRuleRepository,
    ParticipantRepository,
    RuleChangeLogRepository,
)


def _rule_id() -> str:
    return "rule_" + str(uuid4())[:12]


def _participant_id_from_name(name: str) -> str:
    """Generate slug-like ID from partner name."""
    base = name.lower().replace(" ", "-").replace("_", "-")
    return f"partner-{base}"


def eligibility_rules_to_matching_rules(rules: list[EligibilityRule]) -> dict:
    """
    Convert EligibilityRule entities to matching_rules dict for RulesEngine.
    """
    engine_rules = []
    for r in rules:
        rule_type = r.rule_type
        config = r.config or {}
        if rule_type == "wallet":
            addresses = config.get("addresses") or (
                [config["wallet"]] if config.get("wallet") else []
            )
            if addresses:
                engine_rules.append({"type": "EXACT_ADDRESS", "addresses": addresses})
        elif rule_type == "memo":
            engine_rules.append({
                "type": "RT21_AUTO_DELEGATION",
                "memo_string": config.get("memo_string", config.get("memoString", "")),
                "match_type": config.get("match_type", config.get("matchType", "contains")),
                "extrinsic_types": config.get("extrinsic_types", config.get("extrinsicTypes", ["stake", "unstake"])),
            })
        elif rule_type == "subnet-filter":
            subnet_ids = config.get("subnet_ids") or config.get("subnetIds") or []
            delegation_types = config.get("delegation_types") or config.get("delegationTypes") or ["subnet_dtao"]
            if subnet_ids:
                engine_rules.append({
                    "type": "SUBNET",
                    "subnet_ids": subnet_ids,
                })
            elif delegation_types:
                engine_rules.append({
                    "type": "DELEGATION_TYPE",
                    "delegation_types": delegation_types,
                    "subnet_ids": subnet_ids or None,
                })
    return {"rules": engine_rules}


def build_eligibility_rule(
    participant_id: str,
    rule_type: str,
    config: dict,
    applies_from_block: Optional[int] = None,
    created_by: str = "system",
) -> EligibilityRule:
    """Create EligibilityRule entity."""
    rule_id = _rule_id()
    return EligibilityRule(
        id=rule_id,
        participant_id=participant_id,
        rule_type=rule_type,
        config=config,
        applies_from_block=applies_from_block,
        created_by=created_by,
    )


class ParticipantService:
    """Service for partner CRUD with rule and audit support."""

    def __init__(self, session: Session):
        self.session = session
        self.participant_repo = ParticipantRepository(session)
        self.rule_repo = EligibilityRuleRepository(session)
        self.log_repo = RuleChangeLogRepository(session)

    def list_partners(self, active_only: bool = True) -> list[dict]:
        """List partners in UI shape."""
        as_of = date.today() if active_only else None
        if active_only:
            participants = self.participant_repo.get_active(date.today())
        else:
            participants = self.participant_repo.get_all()
        out = []
        for p in participants:
            out.append(self._participant_to_ui(p))
        return out

    def get_partner(self, id: str) -> Optional[dict]:
        """Get single partner with rules."""
        p = self.participant_repo.get_by_id(id)
        if not p:
            return None
        rules = self.rule_repo.get_by_participant(id)
        return self._participant_to_ui(p, rules)

    def _participant_to_ui(
        self,
        p: RakebackParticipant,
        rules: Optional[list[EligibilityRule]] = None,
    ) -> dict:
        """Convert participant to UI Partner shape."""
        if rules is None:
            rules = self.rule_repo.get_by_participant(p.id)
        pt = p.partner_type or PartnerType.NAMED
        partner_type_ui = {"named": "Named", "tag_based": "Tag-based", "hybrid": "Hybrid"}.get(pt.value, "Named")

        wallet = None
        memo_tag = None
        for r in rules:
            if r.rule_type == "wallet":
                wallet = (r.config or {}).get("wallet") or ((r.config or {}).get("addresses") or [None])[0]
                if wallet:
                    break
            elif r.rule_type == "memo":
                memo_tag = (r.config or {}).get("memo_string") or (r.config or {}).get("memoString")
                if memo_tag:
                    break

        effective_to = p.effective_to
        status = "active" if (effective_to is None or effective_to >= date.today()) else "inactive"

        return {
            "id": p.id,
            "name": p.name,
            "type": partner_type_ui,
            "rakebackRate": float(p.rakeback_percentage) * 100,
            "priority": p.priority,
            "status": status,
            "createdBy": "system",
            "createdDate": p.created_at.date().isoformat() if p.created_at else "",
            "walletAddress": wallet,
            "memoTag": memo_tag,
            "applyFromDate": p.effective_from.isoformat() if p.effective_from else None,
            "payoutAddress": p.payout_address,
            "rules": [self._rule_to_ui(r) for r in rules],
        }

    def _rule_to_ui(self, r: EligibilityRule) -> dict:
        """Convert rule to UI EligibilityRule shape."""
        config = r.config or {}
        type_map = {"wallet": "wallet", "memo": "memo", "subnet-filter": "subnet-filter"}
        ui_type = type_map.get(r.rule_type, r.rule_type)
        return {
            "id": r.id,
            "partnerId": r.participant_id,
            "type": ui_type,
            "config": config,
            "appliesFromBlock": r.applies_from_block or 0,
            "createdAt": r.created_at.isoformat() if r.created_at else "",
            "createdBy": r.created_by,
        }

    def create_partner(
        self,
        name: str,
        partner_type: str,
        rakeback_rate: float,
        priority: int = 1,
        payout_address: str = "",
        rules: Optional[list[dict]] = None,
        effective_from: Optional[date] = None,
        applies_from_block: Optional[int] = None,
        created_by: str = "system",
    ) -> dict:
        """Create partner with optional rules."""
        pid = _participant_id_from_name(name)
        if self.participant_repo.exists(pid):
            pid = f"{pid}-{int(datetime.utcnow().timestamp())}"

        pt = PartnerType(partner_type.replace("-", "_").lower())
        effective = effective_from or date.today()
        block = applies_from_block or 0

        participant = RakebackParticipant(
            id=pid,
            name=name,
            type=ParticipantType.PARTNER,
            partner_type=pt,
            priority=priority,
            matching_rules={"rules": []},
            rakeback_percentage=Decimal(str(rakeback_rate / 100)),
            effective_from=effective,
            effective_to=None,
            payout_address=payout_address or "0x0",
            aggregation_mode=AggregationMode.LUMP_SUM,
        )
        self.participant_repo.add(participant)

        rule_entities: list[EligibilityRule] = []
        for r in rules or []:
            re = self._create_rule_from_ui(participant.id, r, block, created_by)
            if re:
                self.rule_repo.add(re)
                rule_entities.append(re)

        participant.matching_rules = eligibility_rules_to_matching_rules(rule_entities)
        self.session.flush()

        self._log_change(
            action="Created partner",
            partner_id=pid,
            partner_name=name,
            details=f"{partner_type} partner at {rakeback_rate}% rakeback",
            applies_from_block=block,
            user=created_by,
        )

        return self.get_partner(pid) or {}

    def _create_rule_from_ui(
        self,
        participant_id: str,
        rule: dict,
        default_block: int,
        created_by: str,
    ) -> Optional[EligibilityRule]:
        """Create EligibilityRule from UI rule payload."""
        rule_type = rule.get("type", "wallet")
        config = rule.get("config", {})
        block = rule.get("appliesFromBlock") or default_block

        if rule_type == "wallet":
            wallet = config.get("wallet") or rule.get("walletAddress")
            if not wallet:
                return None
            return build_eligibility_rule(
                participant_id=participant_id,
                rule_type="wallet",
                config={"wallet": wallet, "addresses": [wallet], "label": config.get("label", "")},
                applies_from_block=block or None,
                created_by=created_by,
            )
        elif rule_type == "memo":
            memo = config.get("memo_string") or config.get("memoString") or rule.get("memoKeyword")
            if not memo:
                return None
            return build_eligibility_rule(
                participant_id=participant_id,
                rule_type="memo",
                config={
                    "memo_string": memo,
                    "match_type": config.get("match_type", config.get("matchType", "contains")),
                    "extrinsic_types": config.get("extrinsic_types", config.get("extrinsicTypes", ["stake", "unstake", "redelegate"])),
                },
                applies_from_block=block or None,
                created_by=created_by,
            )
        elif rule_type == "subnet-filter":
            return build_eligibility_rule(
                participant_id=participant_id,
                rule_type="subnet-filter",
                config={
                    "subnet_ids": config.get("subnet_ids", config.get("subnetIds", [])),
                    "delegation_types": config.get("delegation_types", config.get("delegationTypes", ["subnet_dtao"])),
                },
                applies_from_block=block or None,
                created_by=created_by,
            )
        return None

    def update_partner(
        self,
        id: str,
        updates: dict,
        created_by: str = "system",
    ) -> Optional[dict]:
        """Update partner fields."""
        p = self.participant_repo.get_by_id(id)
        if not p:
            return None
        if "name" in updates:
            p.name = updates["name"]
        if "rakebackRate" in updates:
            p.rakeback_percentage = Decimal(str(updates["rakebackRate"] / 100))
        if "priority" in updates:
            p.priority = updates["priority"]
        if "payoutAddress" in updates:
            p.payout_address = updates["payoutAddress"]
        if "partnerType" in updates:
            pt = updates["partnerType"].replace("-", "_").lower()
            p.partner_type = PartnerType(pt)
        self.session.flush()
        return self.get_partner(id)

    def add_rule(
        self,
        participant_id: str,
        rule: dict,
        created_by: str = "system",
    ) -> Optional[dict]:
        """Add rule to partner and sync matching_rules."""
        p = self.participant_repo.get_by_id(participant_id)
        if not p:
            return None
        re = self._create_rule_from_ui(participant_id, rule, 0, created_by)
        if not re:
            return None
        self.rule_repo.add(re)
        rules = self.rule_repo.get_by_participant(participant_id)
        p.matching_rules = eligibility_rules_to_matching_rules(rules)
        self.session.flush()
        return self._rule_to_ui(re)

    def get_rule_change_log(self, limit: int = 100) -> list[dict]:
        """Get audit log entries."""
        entries = self.log_repo.get_all_recent(limit)
        return [
            {
                "timestamp": e.timestamp.isoformat().replace("T", " ")[:19] if e.timestamp else "",
                "user": e.user,
                "action": e.action,
                "partner": e.partner_name,
                "details": e.details,
                "appliesFromBlock": e.applies_from_block,
            }
            for e in entries
        ]

    def _log_change(
        self,
        action: str,
        partner_id: str,
        partner_name: str,
        details: str,
        applies_from_block: int,
        user: str = "system",
    ) -> None:
        """Append rule change log entry."""
        entry = RuleChangeLog(
            action=action,
            partner_id=partner_id,
            partner_name=partner_name,
            details=details,
            applies_from_block=applies_from_block,
            user=user,
        )
        self.log_repo.add(entry)
        self.session.flush()
