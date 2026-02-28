"""Partner/participant CRUD service with rule entity sync."""

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import Select, and_, select
from sqlalchemy.orm import Session

from app.schemas.partners import PartnerCreate, PartnerUpdate, RuleCreate
from db.enums import (
    AggregationMode,
    ApiRuleType,
    ParticipantType,
    PartnerType,
    RuleType,
)
from db.models import (
    EligibilityRules,
    RakebackParticipants,
    RuleChangeLog,
)
from rakeback.services._helpers import JsonDict, dump_json, load_json, new_id, now_iso
from rakeback.services._types import (
    ChangeLogEntry,
    MatchingRuleDict,
    MatchingRulesDict,
    PartnerUI,
    RuleUI,
)


def _rule_id() -> str:
    return "rule_" + str(uuid4())[:12]


def _participant_id_from_name(name: str) -> str:
    base: str = name.lower().replace(" ", "-").replace("_", "-")
    return f"partner-{base}"


def _load_config(raw: str | dict[str, Any] | None) -> JsonDict:
    """Load a rule config field, always returning a dict."""
    if isinstance(raw, str):
        return load_json(raw) or {}
    if isinstance(raw, dict):
        return raw
    return {}


def _cfg(config: JsonDict, snake: str, camel: str, default: Any = None) -> Any:
    """Read a config value, accepting both snake_case and camelCase keys."""
    return config.get(snake) or config.get(camel) or default


def _wallet_rule(config: JsonDict) -> MatchingRuleDict | None:
    addresses: list[str] | None = config.get("addresses") or (
        [config["wallet"]] if config.get("wallet") else None
    )
    if not addresses:
        return None
    return MatchingRuleDict(type=RuleType.EXACT_ADDRESS, addresses=addresses)


def _memo_rule(config: JsonDict) -> MatchingRuleDict:
    return MatchingRuleDict(
        type=RuleType.RT21_AUTO_DELEGATION,
        memo_string=_cfg(config, "memo_string", "memoString", ""),
        match_type=_cfg(config, "match_type", "matchType", "contains"),
        extrinsic_types=_cfg(config, "extrinsic_types", "extrinsicTypes", ["stake", "unstake"]),
    )


def _subnet_filter_rule(config: JsonDict) -> MatchingRuleDict | None:
    subnet_ids: list[int] = _cfg(config, "subnet_ids", "subnetIds", [])
    delegation_types: list[str] = _cfg(
        config, "delegation_types", "delegationTypes", ["subnet_dtao"]
    )
    if subnet_ids:
        return MatchingRuleDict(type=RuleType.SUBNET, subnet_ids=subnet_ids)
    if delegation_types:
        return MatchingRuleDict(
            type=RuleType.DELEGATION_TYPE,
            delegation_types=delegation_types,
        )
    return None


_RULE_BUILDERS = {
    ApiRuleType.WALLET: _wallet_rule,
    ApiRuleType.MEMO: _memo_rule,
    ApiRuleType.SUBNET_FILTER: _subnet_filter_rule,
}


def _new_wallet_rule(address: str, label: str = "") -> RuleCreate:
    """Build a RuleCreate for a wallet address."""
    return RuleCreate(
        type=ApiRuleType.WALLET,
        config={"wallet": address, "addresses": [address], "label": label},
    )


def _new_memo_rule(memo_string: str, match_type: str = "contains") -> RuleCreate:
    """Build a RuleCreate for a memo tag."""
    return RuleCreate(
        type=ApiRuleType.MEMO,
        config={"memo_string": memo_string, "match_type": match_type},
    )


_PARTNER_TYPE_DISPLAY: dict[str, str] = {
    PartnerType.NAMED: "Named",
    PartnerType.TAG_BASED: "Tag-based",
    PartnerType.HYBRID: "Hybrid",
}


def eligibility_rules_to_matching_rules(
    rules: list[EligibilityRules],
) -> MatchingRulesDict:
    """Convert EligibilityRule rows -> matching_rules dict for the rules engine."""
    engine_rules: list[MatchingRuleDict] = []
    for r in rules:
        config: JsonDict = _load_config(r.config)
        try:
            api_type = ApiRuleType(r.rule_type)
        except ValueError:
            continue
        builder = _RULE_BUILDERS.get(api_type)
        if builder is None:
            continue
        rule: MatchingRuleDict | None = builder(config)
        if rule is not None:
            engine_rules.append(rule)
    return MatchingRulesDict(rules=engine_rules)


def _build_eligibility_rule(
    participant_id: str,
    rule_type: ApiRuleType,
    config: dict[str, Any],
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

    def create_partner_from_request(self, data: PartnerCreate) -> PartnerUI:
        rules: list[RuleCreate] = []
        if data.wallet_address:
            rules.append(_new_wallet_rule(data.wallet_address, data.wallet_label or ""))
        if data.memo_keyword:
            rules.append(_new_memo_rule(data.memo_keyword, data.match_type or "contains"))
        if data.hybrid_wallet:
            rules.append(_new_wallet_rule(data.hybrid_wallet, data.hybrid_wallet_label or ""))
        if data.hybrid_memo:
            rules.append(_new_memo_rule(data.hybrid_memo, data.hybrid_match_type or "contains"))

        effective_from: date = (
            date.fromisoformat(data.apply_from_date) if data.apply_from_date else date.today()
        )
        return self.create_partner(
            name=data.name,
            partner_type=data.type,
            rakeback_rate=data.rakeback_rate,
            priority=data.priority,
            payout_address=data.payout_address,
            rules=rules,
            effective_from=effective_from,
            applies_from_block=data.apply_from_block,
        )

    def create_partner(
        self,
        name: str,
        partner_type: str,
        rakeback_rate: float,
        priority: int = 1,
        payout_address: str = "",
        rules: list[RuleCreate] | None = None,
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
            entity: EligibilityRules | None = self._create_rule_entity(
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
        updates: PartnerUpdate,
        created_by: str = "system",
    ) -> PartnerUI | None:
        p: RakebackParticipants | None = self._get_participant(pid)
        if not p:
            return None
        if updates.name is not None:
            p.name = updates.name
        if updates.rakeback_rate is not None:
            p.rakeback_percentage = Decimal(str(updates.rakeback_rate / 100))
        if updates.priority is not None:
            p.priority = updates.priority
        if updates.payout_address is not None:
            p.payout_address = updates.payout_address
        if updates.partner_type is not None:
            pt: str = updates.partner_type.replace("-", "_").upper()
            p.partner_type = PartnerType(pt).value
        p.updated_at = now_iso()
        self.session.flush()
        return self.get_partner(pid)

    def add_rule(
        self,
        participant_id: str,
        rule: RuleCreate,
        created_by: str = "system",
    ) -> RuleUI | None:
        p: RakebackParticipants | None = self._get_participant(participant_id)
        if not p:
            return None
        entity: EligibilityRules | None = self._create_rule_entity(
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
        partner_type_ui: str = _PARTNER_TYPE_DISPLAY.get(pt_val, "Named")

        wallet: str | None = None
        memo_tag: str | None = None
        for r in rules:
            cfg: JsonDict = _load_config(r.config)
            if r.rule_type == ApiRuleType.WALLET:
                addrs: list[str] | None = cfg.get("addresses")
                wallet = cfg.get("wallet") or (
                    addrs[0] if isinstance(addrs, list) and addrs else None
                )
                if wallet:
                    break
            elif r.rule_type == ApiRuleType.MEMO:
                memo_tag = _cfg(cfg, "memo_string", "memoString")
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

    def _create_rule_entity(
        self,
        participant_id: str,
        rule: RuleCreate,
        default_block: int,
        created_by: str,
    ) -> EligibilityRules | None:
        rule_type: str = rule.type
        config: dict[str, Any] = rule.config
        block: int = rule.applies_from_block or default_block

        if rule_type == ApiRuleType.WALLET:
            wallet: str | None = config.get("wallet")
            if not wallet:
                return None
            return _build_eligibility_rule(
                participant_id=participant_id,
                rule_type=ApiRuleType.WALLET,
                config={
                    "wallet": wallet,
                    "addresses": [wallet],
                    "label": config.get("label", ""),
                },
                applies_from_block=block or None,
                created_by=created_by,
            )
        if rule_type == ApiRuleType.MEMO:
            memo: str | None = _cfg(config, "memo_string", "memoString")
            if not memo:
                return None
            return _build_eligibility_rule(
                participant_id=participant_id,
                rule_type=ApiRuleType.MEMO,
                config={
                    "memo_string": memo,
                    "match_type": _cfg(config, "match_type", "matchType", "contains"),
                    "extrinsic_types": _cfg(
                        config,
                        "extrinsic_types",
                        "extrinsicTypes",
                        ["stake", "unstake", "redelegate"],
                    ),
                },
                applies_from_block=block or None,
                created_by=created_by,
            )
        if rule_type == ApiRuleType.SUBNET_FILTER:
            return _build_eligibility_rule(
                participant_id=participant_id,
                rule_type=ApiRuleType.SUBNET_FILTER,
                config={
                    "subnet_ids": _cfg(config, "subnet_ids", "subnetIds", []),
                    "delegation_types": _cfg(
                        config, "delegation_types", "delegationTypes", ["subnet_dtao"]
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
