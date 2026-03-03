"""Rules engine for matching delegators to rakeback participants."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import Select, and_, select
from sqlalchemy.orm import Session

from db.enums import DelegationType, RuleType
from db.models import RakebackParticipants
from rakeback.services._helpers import JsonDict, load_json
from rakeback.services._types import ParticipantSnapshot, RulesSnapshot
from rakeback.services.errors import InvalidRuleError, RulesEngineError  # noqa: F401 — re-exported


def _str_list(data: dict[str, object], key: str) -> list[str]:
    raw: object = data.get(key)
    return [str(v) for v in raw] if isinstance(raw, list) else []


def _int_list(data: dict[str, object], key: str) -> list[int]:
    raw: object = data.get(key)
    return [int(v) for v in raw] if isinstance(raw, list) else []


@dataclass(slots=True)
class Rule:
    type: RuleType
    addresses: list[str] = field(default_factory=list)
    delegation_types: list[str] = field(default_factory=list)
    subnet_ids: list[int] = field(default_factory=list)
    memo_string: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Rule | None":
        rule_type: object = data.get("type")
        if not isinstance(rule_type, str):
            return None
        try:
            parsed_type: RuleType = RuleType(rule_type)
        except ValueError:
            return None
        memo: object = data.get("memo_string")
        return cls(
            type=parsed_type,
            addresses=_str_list(data, "addresses"),
            delegation_types=_str_list(data, "delegation_types"),
            subnet_ids=_int_list(data, "subnet_ids"),
            memo_string=str(memo) if isinstance(memo, str) else None,
        )

    def matches(
        self,
        delegator_address: str,
        delegation_type_value: str,
        subnet_id: int | None,
    ) -> bool:
        match self.type:
            case RuleType.EXACT_ADDRESS:
                return delegator_address in self.addresses
            case RuleType.DELEGATION_TYPE:
                if delegation_type_value not in self.delegation_types:
                    return False
                return not self.subnet_ids or subnet_id in self.subnet_ids
            case RuleType.SUBNET:
                return subnet_id in self.subnet_ids
            case RuleType.RT21_AUTO_DELEGATION:
                return False
            case RuleType.ALL:
                return True

    def matches_address(self, address: str) -> bool:
        match self.type:
            case RuleType.EXACT_ADDRESS:
                return address in self.addresses
            case RuleType.ALL:
                return True
            case _:
                return False

    def validate(self, valid_dtypes: set[str]) -> list[str]:
        match self.type:
            case RuleType.EXACT_ADDRESS:
                if not self.addresses:
                    return [f"{self.type} has no addresses"]
                return ["Invalid address format" for addr in self.addresses if len(addr) < 10]
            case RuleType.DELEGATION_TYPE:
                return [
                    f"Invalid delegation type '{t}'"
                    for t in self.delegation_types
                    if t not in valid_dtypes
                ]
            case RuleType.SUBNET:
                if not self.subnet_ids:
                    return [f"{self.type} has no subnet_ids"]
                return []
            case RuleType.RT21_AUTO_DELEGATION:
                if self.memo_string is None:
                    return [f"{self.type} has no memo_string"]
                return []
            case RuleType.ALL:
                return []


class RulesEngine:
    """Matches delegators to rakeback participants using configurable rules."""

    def __init__(self, session: Session) -> None:
        self.session: Session = session

    def match_delegator(
        self,
        delegator_address: str,
        delegation_type: DelegationType,
        subnet_id: int | None,
        as_of_date: date | None = None,
    ) -> RakebackParticipants | None:
        check_date: str = (as_of_date or date.today()).isoformat()
        participants: Sequence[RakebackParticipants] = self._get_active_participants(check_date)
        for p in participants:
            rules: list[Rule] = self._rules_list(p)
            if any(r.matches(delegator_address, delegation_type.value, subnet_id) for r in rules):
                return p
        return None

    def match_addresses(
        self,
        participant: RakebackParticipants,
        addresses: Sequence[str],
    ) -> list[str]:
        rules: list[Rule] = self._rules_list(participant)
        return [a for a in addresses if any(r.matches_address(a) for r in rules)]

    def validate_rules(self, participant: RakebackParticipants) -> list[str]:
        rules: list[Rule] = self._rules_list(participant)
        if not rules:
            return ["No matching rules defined"]
        valid_dtypes: set[str] = {dt.value for dt in DelegationType}
        errors: list[str] = []
        for i, rule in enumerate(rules):
            for err in rule.validate(valid_dtypes):
                errors.append(f"Rule {i}: {err}")
        return errors

    def get_rules_snapshot(self, as_of: date) -> RulesSnapshot:
        check_date: str = as_of.isoformat()
        participants: Sequence[RakebackParticipants] = self._get_active_participants(check_date)
        return RulesSnapshot(
            as_of=as_of.isoformat(),
            participants=[
                ParticipantSnapshot(
                    id=p.id,
                    name=p.name,
                    type=p.type,
                    rakeback_percentage=str(p.rakeback_percentage),
                    matching_rules=load_json(p.matching_rules) or {},
                    aggregation_mode=p.aggregation_mode,
                )
                for p in participants
            ],
        )

    def _get_active_participants(
        self,
        date_str: str,
    ) -> Sequence[RakebackParticipants]:
        stmt: Select[tuple[RakebackParticipants]] = (
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
    def _rules_list(participant: RakebackParticipants) -> list[Rule]:
        raw: str | None = participant.matching_rules
        mr: JsonDict | None = load_json(raw) if isinstance(raw, str) else None
        if not isinstance(mr, dict):
            return []
        raw_rules: object = mr.get("rules")
        if not isinstance(raw_rules, list):
            return []
        parsed: list[Rule | None] = [Rule.from_dict(r) for r in raw_rules if isinstance(r, dict)]
        return [r for r in parsed if r is not None]
