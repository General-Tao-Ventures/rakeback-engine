"""Partner/participant CRUD service with rule entity sync."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Select, and_, select
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
from rakeback.services._helpers import JsonDict, dump_json, load_json, new_id, now_iso
from rakeback.services._types import ChangeLogEntry, PartnerUI, RuleUI


def _rule_id() -> str:
    return "rule_" + str(uuid4())[:12]


def _participant_id_from_name(name: str) -> str:
    base: str = name.lower().replace(" ", "-").replace("_", "-")
    return f"partner-{base}"


def _load_config(raw: object) -> JsonDict:
    """Load a rule config field, always returning a dict."""
    if isinstance(raw, str):
        return load_json(raw) or {}
    if isinstance(raw, dict):
        return raw
    return {}


def eligibility_rules_to_matching_rules(
    rules: list[EligibilityRules],
) -> dict[str, object]:
    """Convert EligibilityRule rows -> matching_rules dict for the rules engine."""
    engine_rules: list[dict[str, object]] = []
    for r in rules:
        config: JsonDict = _load_config(r.config)
        rt: str = r.rule_type
        if rt == "wallet":
            addresses: object = config.get("addresses") or (
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
            subnet_ids: object = config.get("subnet_ids") or config.get("subnetIds") or []
            delegation_types: object = (
                config.get("delegation_types") or config.get("delegationTypes") or ["subnet_dtao"]
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
    config: dict[str, object],
    applies_from_block: int | None = None,
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

    def __init__(self, session: Session) -> None:
        self.session: Session = session

    def _get_participant(self, pid: str) -> RakebackParticipants | None:
        return self.session.get(RakebackParticipants, pid)

    def _get_active(self, as_of_date: date) -> list[RakebackParticipants]:
        d: str = as_of_date.isoformat()
        stmt: Select[tuple[RakebackParticipants]] = (
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
        stmt: Select[tuple[RakebackParticipants]] = select(RakebackParticipants).order_by(
            RakebackParticipants.id
        )
        return list(self.session.scalars(stmt).all())

    def _get_rules(self, participant_id: str) -> list[EligibilityRules]:
        stmt: Select[tuple[EligibilityRules]] = (
            select(EligibilityRules)
            .where(EligibilityRules.participant_id == participant_id)
            .order_by(EligibilityRules.created_at)
        )
        return list(self.session.scalars(stmt).all())

    def _participant_exists(self, pid: str) -> bool:
        return self._get_participant(pid) is not None

    def list_partners(self, active_only: bool = True) -> list[PartnerUI]:
        participants: list[RakebackParticipants] = (
            self._get_active(date.today()) if active_only else self._get_all_participants()
        )
        return [self._participant_to_ui(p) for p in participants]

    def get_partner(self, pid: str) -> PartnerUI | None:
        p: RakebackParticipants | None = self._get_participant(pid)
        if not p:
            return None
        rules: list[EligibilityRules] = self._get_rules(pid)
        return self._participant_to_ui(p, rules)

    def create_partner_from_request(self, data: dict[str, object]) -> PartnerUI:
        name: str = str(data["name"])
        partner_type: str = str(data.get("type", "named"))
        rakeback_rate: float = float(str(data.get("rakeback_rate", 0) or 0))
        priority: int = int(str(data.get("priority", 1) or 1))
        payout_address: str = str(data.get("payout_address", "") or "")
        apply_from_date: object = data.get("apply_from_date")
        apply_from_block: object = data.get("apply_from_block")

        # Build rules from flat request fields
        rules: list[dict[str, object]] = []
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

        effective_from: date = (
            date.fromisoformat(str(apply_from_date)) if apply_from_date else date.today()
        )
        return self.create_partner(
            name=name,
            partner_type=partner_type,
            rakeback_rate=rakeback_rate,
            priority=priority,
            payout_address=payout_address,
            rules=rules,
            effective_from=effective_from,
            applies_from_block=int(str(apply_from_block)) if apply_from_block else None,
        )

    def create_partner(
        self,
        name: str,
        partner_type: str,
        rakeback_rate: float,
        priority: int = 1,
        payout_address: str = "",
        rules: list[dict[str, object]] | None = None,
        effective_from: date | None = None,
        applies_from_block: int | None = None,
        created_by: str = "system",
    ) -> PartnerUI:
        pid: str = _participant_id_from_name(name)
        if self._participant_exists(pid):
            from datetime import UTC, datetime

            pid = f"{pid}-{int(datetime.now(UTC).timestamp())}"

        pt: PartnerType = PartnerType(partner_type.replace("-", "_").upper())
        effective: date = effective_from or date.today()
        block: int = applies_from_block or 0
        ts: str = now_iso()

        participant: RakebackParticipants = RakebackParticipants(
            id=pid,
            name=name,
            type=ParticipantType.PARTNER.value,
            partner_type=pt.value,
            priority=priority,
            matching_rules=dump_json({"rules": []}),
            rakeback_percentage=Decimal(str(rakeback_rate / 100)),
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
            entity: EligibilityRules | None = self._create_rule_from_ui(
                participant.id, r, block, created_by
            )
            if entity:
                self.session.add(entity)
                rule_entities.append(entity)

        participant.matching_rules = dump_json(eligibility_rules_to_matching_rules(rule_entities))
        self.session.flush()

        self._log_change(
            action="Created partner",
            partner_id=pid,
            partner_name=name,
            details=f"{partner_type} partner at {rakeback_rate}% rakeback",
            applies_from_block=block,
            user=created_by,
        )
        return self.get_partner(pid) or PartnerUI()

    def update_partner(
        self,
        pid: str,
        updates: dict[str, object],
        created_by: str = "system",
    ) -> PartnerUI | None:
        p: RakebackParticipants | None = self._get_participant(pid)
        if not p:
            return None
        if "name" in updates:
            p.name = str(updates["name"])
        if "rakeback_rate" in updates:
            p.rakeback_percentage = Decimal(str(float(str(updates["rakeback_rate"])) / 100))
        if "priority" in updates:
            p.priority = int(str(updates["priority"]))
        if "payout_address" in updates:
            p.payout_address = str(updates["payout_address"])
        if "partner_type" in updates:
            pt: str = str(updates["partner_type"]).replace("-", "_").upper()
            p.partner_type = PartnerType(pt).value
        p.updated_at = now_iso()
        self.session.flush()
        return self.get_partner(pid)

    def add_rule(
        self,
        participant_id: str,
        rule: dict[str, object],
        created_by: str = "system",
    ) -> RuleUI | None:
        p: RakebackParticipants | None = self._get_participant(participant_id)
        if not p:
            return None
        entity: EligibilityRules | None = self._create_rule_from_ui(
            participant_id, rule, 0, created_by
        )
        if not entity:
            return None
        self.session.add(entity)
        all_rules: list[EligibilityRules] = self._get_rules(participant_id)
        all_rules.append(entity)
        p.matching_rules = dump_json(eligibility_rules_to_matching_rules(all_rules))
        p.updated_at = now_iso()
        self.session.flush()
        return self._rule_to_ui(entity)

    def get_rule_change_log(self, limit: int = 100) -> list[ChangeLogEntry]:
        stmt: Select[tuple[RuleChangeLog]] = (
            select(RuleChangeLog).order_by(RuleChangeLog.timestamp.desc()).limit(limit)
        )
        entries: list[RuleChangeLog] = list(self.session.scalars(stmt).all())
        return [
            ChangeLogEntry(
                timestamp=(e.timestamp or "")[:19].replace("T", " "),
                user=e.user,
                action=e.action,
                partner=e.partner_name,
                details=e.details,
                appliesFromBlock=e.applies_from_block,
            )
            for e in entries
        ]

    def _participant_to_ui(
        self,
        p: RakebackParticipants,
        rules: list[EligibilityRules] | None = None,
    ) -> PartnerUI:
        if rules is None:
            rules = self._get_rules(p.id)

        pt_val: str = p.partner_type or PartnerType.NAMED.value
        partner_type_ui: str = {"NAMED": "Named", "TAG_BASED": "Tag-based", "HYBRID": "Hybrid"}.get(
            pt_val, "Named"
        )

        wallet: object = None
        memo_tag: object = None
        for r in rules:
            cfg: JsonDict = _load_config(r.config)
            if r.rule_type == "wallet":
                addrs: object = cfg.get("addresses")
                wallet = cfg.get("wallet") or (
                    addrs[0] if isinstance(addrs, list) and addrs else None
                )
                if wallet:
                    break
            elif r.rule_type == "memo":
                memo_tag = cfg.get("memo_string") or cfg.get("memoString")
                if memo_tag:
                    break

        eff_to: str | None = p.effective_to
        status: str = (
            "active" if (eff_to is None or eff_to >= date.today().isoformat()) else "inactive"
        )

        return PartnerUI(
            id=p.id,
            name=p.name,
            type=partner_type_ui,
            rakebackRate=float(p.rakeback_percentage) * 100,
            priority=p.priority,
            status=status,
            createdBy="system",
            createdDate=(p.created_at or "")[:10],
            walletAddress=wallet,
            memoTag=memo_tag,
            applyFromDate=p.effective_from,
            payoutAddress=p.payout_address,
            rules=[self._rule_to_ui(r) for r in rules],
        )

    @staticmethod
    def _rule_to_ui(r: EligibilityRules) -> RuleUI:
        cfg: JsonDict = _load_config(r.config)
        return RuleUI(
            id=r.id,
            partnerId=r.participant_id,
            type=r.rule_type,
            config=cfg or None,
            appliesFromBlock=r.applies_from_block or 0,
            createdAt=r.created_at or "",
            createdBy=r.created_by,
        )

    def _create_rule_from_ui(
        self,
        participant_id: str,
        rule: dict[str, object],
        default_block: int,
        created_by: str,
    ) -> EligibilityRules | None:
        rule_type: str = str(rule.get("type", "wallet"))
        config_raw: object = rule.get("config", {})
        config: dict[str, object] = config_raw if isinstance(config_raw, dict) else {}
        block_val: object = (
            rule.get("appliesFromBlock") or rule.get("applies_from_block") or default_block
        )
        block: int = int(str(block_val)) if block_val else default_block

        if rule_type == "wallet":
            wallet: object = config.get("wallet") or rule.get("walletAddress")
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
            memo: object = (
                config.get("memo_string") or config.get("memoString") or rule.get("memoKeyword")
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
        entry: RuleChangeLog = RuleChangeLog(
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
