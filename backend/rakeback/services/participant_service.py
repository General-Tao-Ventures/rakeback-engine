"""Partner/participant CRUD service with rule entity sync."""

from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from db.enums import (
    AggregationMode,
    ParticipantType,
    PartnerType,
)
from db.models import (
    EligibilityRules,
    RakebackParticipants,
    RuleChangeLog,
)
from rakeback.services._helpers import dump_json, load_json, new_id, now_iso


def _rule_id() -> str:
    return "rule_" + str(uuid4())[:12]


def _participant_id_from_name(name: str) -> str:
    base = name.lower().replace(" ", "-").replace("_", "-")
    return f"partner-{base}"


def eligibility_rules_to_matching_rules(rules: list[EligibilityRules]) -> dict:
    """Convert EligibilityRule rows → matching_rules dict for the rules engine."""
    engine_rules: list[dict] = []
    for r in rules:
        config = load_json(r.config) if isinstance(r.config, str) else (r.config or {})
        rt = r.rule_type
        if rt == "wallet":
            addresses = config.get("addresses") or (
                [config["wallet"]] if config.get("wallet") else []
            )
            if addresses:
                engine_rules.append({"type": "EXACT_ADDRESS", "addresses": addresses})
        elif rt == "memo":
            engine_rules.append(
                {
                    "type": "RT21_AUTO_DELEGATION",
                    "memo_string": config.get("memo_string", config.get("memoString", "")),
                    "match_type": config.get("match_type", config.get("matchType", "contains")),
                    "extrinsic_types": config.get(
                        "extrinsic_types",
                        config.get("extrinsicTypes", ["stake", "unstake"]),
                    ),
                }
            )
        elif rt == "subnet-filter":
            subnet_ids = config.get("subnet_ids") or config.get("subnetIds") or []
            delegation_types = (
                config.get("delegation_types")
                or config.get("delegationTypes")
                or ["subnet_dtao"]
            )
            if subnet_ids:
                engine_rules.append({"type": "SUBNET", "subnet_ids": subnet_ids})
            elif delegation_types:
                engine_rules.append(
                    {
                        "type": "DELEGATION_TYPE",
                        "delegation_types": delegation_types,
                        "subnet_ids": subnet_ids or None,
                    }
                )
    return {"rules": engine_rules}


def _build_eligibility_rule(
    participant_id: str,
    rule_type: str,
    config: dict,
    applies_from_block: Optional[int] = None,
    created_by: str = "system",
) -> EligibilityRules:
    return EligibilityRules(
        id=_rule_id(),
        participant_id=participant_id,
        rule_type=rule_type,
        config=dump_json(config),
        applies_from_block=applies_from_block,
        created_at=now_iso(),
        created_by=created_by,
    )


class ParticipantService:
    """Service for partner CRUD with rule and audit support."""

    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------------
    # Query helpers (replace repo calls)
    # ------------------------------------------------------------------

    def _get_participant(self, pid: str) -> Optional[RakebackParticipants]:
        return self.session.get(RakebackParticipants, pid)

    def _get_active(self, as_of_date: date) -> list[RakebackParticipants]:
        d = as_of_date.isoformat()
        stmt = (
            select(RakebackParticipants)
            .where(
                and_(
                    RakebackParticipants.effective_from <= d,
                    (
                        (RakebackParticipants.effective_to.is_(None))
                        | (RakebackParticipants.effective_to >= d)
                    ),
                )
            )
            .order_by(RakebackParticipants.priority, RakebackParticipants.id)
        )
        return list(self.session.scalars(stmt).all())

    def _get_all_participants(self) -> list[RakebackParticipants]:
        stmt = select(RakebackParticipants).order_by(RakebackParticipants.id)
        return list(self.session.scalars(stmt).all())

    def _get_rules(self, participant_id: str) -> list[EligibilityRules]:
        stmt = (
            select(EligibilityRules)
            .where(EligibilityRules.participant_id == participant_id)
            .order_by(EligibilityRules.created_at)
        )
        return list(self.session.scalars(stmt).all())

    def _participant_exists(self, pid: str) -> bool:
        return self._get_participant(pid) is not None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_partners(self, active_only: bool = True) -> list[dict]:
        participants = (
            self._get_active(date.today()) if active_only else self._get_all_participants()
        )
        return [self._participant_to_ui(p) for p in participants]

    def get_partner(self, pid: str) -> Optional[dict]:
        p = self._get_participant(pid)
        if not p:
            return None
        rules = self._get_rules(pid)
        return self._participant_to_ui(p, rules)

    def create_partner_from_request(self, data: dict) -> dict:
        """Create a partner from a PartnerCreate.model_dump() dict."""
        name = data["name"]
        partner_type = data.get("type", "named")
        rakeback_rate = data.get("rakeback_rate", 0)
        priority = data.get("priority", 1)
        payout_address = data.get("payout_address", "")
        apply_from_date = data.get("apply_from_date")
        apply_from_block = data.get("apply_from_block")

        # Build rules from flat request fields
        rules: list[dict] = []
        if data.get("wallet_address"):
            rules.append(
                {
                    "type": "wallet",
                    "config": {
                        "wallet": data["wallet_address"],
                        "addresses": [data["wallet_address"]],
                        "label": data.get("wallet_label", ""),
                    },
                }
            )
        if data.get("memo_keyword"):
            rules.append(
                {
                    "type": "memo",
                    "config": {
                        "memo_string": data["memo_keyword"],
                        "match_type": data.get("match_type", "contains"),
                    },
                }
            )
        if data.get("hybrid_wallet"):
            rules.append(
                {
                    "type": "wallet",
                    "config": {
                        "wallet": data["hybrid_wallet"],
                        "addresses": [data["hybrid_wallet"]],
                        "label": data.get("hybrid_wallet_label", ""),
                    },
                }
            )
        if data.get("hybrid_memo"):
            rules.append(
                {
                    "type": "memo",
                    "config": {
                        "memo_string": data["hybrid_memo"],
                        "match_type": data.get("hybrid_match_type", "contains"),
                    },
                }
            )

        effective_from = date.fromisoformat(apply_from_date) if apply_from_date else date.today()
        return self.create_partner(
            name=name,
            partner_type=partner_type,
            rakeback_rate=rakeback_rate,
            priority=priority,
            payout_address=payout_address,
            rules=rules,
            effective_from=effective_from,
            applies_from_block=apply_from_block,
        )

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
        pid = _participant_id_from_name(name)
        if self._participant_exists(pid):
            from datetime import datetime

            pid = f"{pid}-{int(datetime.utcnow().timestamp())}"

        pt = PartnerType(partner_type.replace("-", "_").upper())
        effective = effective_from or date.today()
        block = applies_from_block or 0
        ts = now_iso()

        participant = RakebackParticipants(
            id=pid,
            name=name,
            type=ParticipantType.PARTNER.value,
            partner_type=pt.value,
            priority=priority,
            matching_rules=dump_json({"rules": []}),
            rakeback_percentage=float(Decimal(str(rakeback_rate / 100))),
            effective_from=effective.isoformat(),
            effective_to=None,
            payout_address=payout_address or "0x0",
            aggregation_mode=AggregationMode.LUMP_SUM.value,
            created_at=ts,
            updated_at=ts,
        )
        self.session.add(participant)

        rule_entities: list[EligibilityRules] = []
        for r in rules or []:
            entity = self._create_rule_from_ui(participant.id, r, block, created_by)
            if entity:
                self.session.add(entity)
                rule_entities.append(entity)

        participant.matching_rules = dump_json(
            eligibility_rules_to_matching_rules(rule_entities)
        )
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

    def update_partner(
        self,
        pid: str,
        updates: dict,
        created_by: str = "system",
    ) -> Optional[dict]:
        p = self._get_participant(pid)
        if not p:
            return None
        if "name" in updates:
            p.name = updates["name"]
        if "rakeback_rate" in updates:
            p.rakeback_percentage = float(Decimal(str(updates["rakeback_rate"] / 100)))
        if "priority" in updates:
            p.priority = updates["priority"]
        if "payout_address" in updates:
            p.payout_address = updates["payout_address"]
        if "partner_type" in updates:
            pt = updates["partner_type"].replace("-", "_").upper()
            p.partner_type = PartnerType(pt).value
        p.updated_at = now_iso()
        self.session.flush()
        return self.get_partner(pid)

    def add_rule(
        self,
        participant_id: str,
        rule: dict,
        created_by: str = "system",
    ) -> Optional[dict]:
        p = self._get_participant(participant_id)
        if not p:
            return None
        entity = self._create_rule_from_ui(participant_id, rule, 0, created_by)
        if not entity:
            return None
        self.session.add(entity)
        all_rules = self._get_rules(participant_id)
        all_rules.append(entity)
        p.matching_rules = dump_json(eligibility_rules_to_matching_rules(all_rules))
        p.updated_at = now_iso()
        self.session.flush()
        return self._rule_to_ui(entity)

    def get_rule_change_log(self, limit: int = 100) -> list[dict]:
        stmt = (
            select(RuleChangeLog)
            .order_by(RuleChangeLog.timestamp.desc())
            .limit(limit)
        )
        entries = self.session.scalars(stmt).all()
        return [
            {
                "timestamp": (e.timestamp or "")[:19].replace("T", " "),
                "user": e.user,
                "action": e.action,
                "partner": e.partner_name,
                "details": e.details,
                "appliesFromBlock": e.applies_from_block,
            }
            for e in entries
        ]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _participant_to_ui(
        self,
        p: RakebackParticipants,
        rules: Optional[list[EligibilityRules]] = None,
    ) -> dict:
        if rules is None:
            rules = self._get_rules(p.id)

        pt_val = p.partner_type or PartnerType.NAMED.value
        partner_type_ui = {"NAMED": "Named", "TAG_BASED": "Tag-based", "HYBRID": "Hybrid"}.get(
            pt_val, "Named"
        )

        wallet = None
        memo_tag = None
        for r in rules:
            cfg = load_json(r.config) if isinstance(r.config, str) else (r.config or {})
            if r.rule_type == "wallet":
                wallet = cfg.get("wallet") or (cfg.get("addresses") or [None])[0]
                if wallet:
                    break
            elif r.rule_type == "memo":
                memo_tag = cfg.get("memo_string") or cfg.get("memoString")
                if memo_tag:
                    break

        eff_to = p.effective_to
        status = "active" if (eff_to is None or eff_to >= date.today().isoformat()) else "inactive"

        return {
            "id": p.id,
            "name": p.name,
            "type": partner_type_ui,
            "rakebackRate": float(p.rakeback_percentage) * 100,
            "priority": p.priority,
            "status": status,
            "createdBy": "system",
            "createdDate": (p.created_at or "")[:10],
            "walletAddress": wallet,
            "memoTag": memo_tag,
            "applyFromDate": p.effective_from,
            "payoutAddress": p.payout_address,
            "rules": [self._rule_to_ui(r) for r in rules],
        }

    @staticmethod
    def _rule_to_ui(r: EligibilityRules) -> dict:
        cfg = load_json(r.config) if isinstance(r.config, str) else (r.config or {})
        return {
            "id": r.id,
            "partnerId": r.participant_id,
            "type": r.rule_type,
            "config": cfg,
            "appliesFromBlock": r.applies_from_block or 0,
            "createdAt": r.created_at or "",
            "createdBy": r.created_by,
        }

    def _create_rule_from_ui(
        self,
        participant_id: str,
        rule: dict,
        default_block: int,
        created_by: str,
    ) -> Optional[EligibilityRules]:
        rule_type = rule.get("type", "wallet")
        config = rule.get("config", {})
        block = rule.get("appliesFromBlock") or rule.get("applies_from_block") or default_block

        if rule_type == "wallet":
            wallet = config.get("wallet") or rule.get("walletAddress")
            if not wallet:
                return None
            return _build_eligibility_rule(
                participant_id=participant_id,
                rule_type="wallet",
                config={"wallet": wallet, "addresses": [wallet], "label": config.get("label", "")},
                applies_from_block=block or None,
                created_by=created_by,
            )
        if rule_type == "memo":
            memo = (
                config.get("memo_string")
                or config.get("memoString")
                or rule.get("memoKeyword")
            )
            if not memo:
                return None
            return _build_eligibility_rule(
                participant_id=participant_id,
                rule_type="memo",
                config={
                    "memo_string": memo,
                    "match_type": config.get("match_type", config.get("matchType", "contains")),
                    "extrinsic_types": config.get(
                        "extrinsic_types",
                        config.get("extrinsicTypes", ["stake", "unstake", "redelegate"]),
                    ),
                },
                applies_from_block=block or None,
                created_by=created_by,
            )
        if rule_type == "subnet-filter":
            return _build_eligibility_rule(
                participant_id=participant_id,
                rule_type="subnet-filter",
                config={
                    "subnet_ids": config.get("subnet_ids", config.get("subnetIds", [])),
                    "delegation_types": config.get(
                        "delegation_types", config.get("delegationTypes", ["subnet_dtao"])
                    ),
                },
                applies_from_block=block or None,
                created_by=created_by,
            )
        return None

    def _log_change(
        self,
        action: str,
        partner_id: str,
        partner_name: str,
        details: str,
        applies_from_block: int,
        user: str = "system",
    ) -> None:
        entry = RuleChangeLog(
            id=new_id(),
            timestamp=now_iso(),
            user=user,
            action=action,
            partner_id=partner_id,
            partner_name=partner_name,
            details=details,
            applies_from_block=applies_from_block,
        )
        self.session.add(entry)
        self.session.flush()
