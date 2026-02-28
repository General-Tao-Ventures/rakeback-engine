"""Tests for rakeback.services.rules_engine."""

from datetime import date

from sqlalchemy.orm import Session

from db.enums import DelegationType
from db.models import RakebackParticipants
from rakeback.services._helpers import dump_json, now_iso
from rakeback.services.rules_engine import RulesEngine


def _make_participant(
    session: Session,
    pid: str,
    rules: list[dict[str, object]],
    **kwargs: object,
) -> RakebackParticipants:
    ts: str = now_iso()
    p: RakebackParticipants = RakebackParticipants(
        id=pid,
        name=kwargs.get("name", pid),
        type=kwargs.get("type", "PARTNER"),
        matching_rules=dump_json({"rules": rules}),
        rakeback_percentage=kwargs.get("rakeback_percentage", 0.5),
        effective_from=kwargs.get("effective_from", "2020-01-01"),
        effective_to=kwargs.get("effective_to"),
        payout_address="5FHne...",
        priority=kwargs.get("priority", 1),
        created_at=ts,
        updated_at=ts,
    )
    session.add(p)
    session.flush()
    return p


class TestMatchDelegator:
    def test_exact_address_match(self, session: Session) -> None:
        _make_participant(
            session,
            "p1",
            [{"type": "EXACT_ADDRESS", "addresses": ["5Abc123456"]}],
        )
        engine: RulesEngine = RulesEngine(session)

        result: RakebackParticipants | None = engine.match_delegator(
            "5Abc123456", DelegationType.ROOT_TAO, None, date(2025, 6, 1)
        )
        assert result is not None
        assert result.id == "p1"

    def test_no_match(self, session: Session) -> None:
        _make_participant(
            session,
            "p1",
            [{"type": "EXACT_ADDRESS", "addresses": ["5Abc123456"]}],
        )
        engine: RulesEngine = RulesEngine(session)

        result: RakebackParticipants | None = engine.match_delegator(
            "5Xyz999999", DelegationType.ROOT_TAO, None, date(2025, 6, 1)
        )
        assert result is None

    def test_all_rule_matches_everything(self, session: Session) -> None:
        _make_participant(session, "catch-all", [{"type": "ALL"}])
        engine: RulesEngine = RulesEngine(session)

        result: RakebackParticipants | None = engine.match_delegator(
            "5AnyAddress", DelegationType.SUBNET_DTAO, 1, date(2025, 6, 1)
        )
        assert result is not None

    def test_delegation_type_rule(self, session: Session) -> None:
        _make_participant(
            session,
            "subnet-only",
            [{"type": "DELEGATION_TYPE", "delegation_types": ["SUBNET_DTAO"]}],
        )
        engine: RulesEngine = RulesEngine(session)

        matched: RakebackParticipants | None = engine.match_delegator(
            "5Abc", DelegationType.SUBNET_DTAO, 1, date(2025, 6, 1)
        )
        assert matched is not None

        not_matched: RakebackParticipants | None = engine.match_delegator(
            "5Abc", DelegationType.ROOT_TAO, None, date(2025, 6, 1)
        )
        assert not_matched is None

    def test_subnet_rule(self, session: Session) -> None:
        _make_participant(
            session,
            "sn1-only",
            [{"type": "SUBNET", "subnet_ids": [1, 2]}],
        )
        engine: RulesEngine = RulesEngine(session)

        assert engine.match_delegator("5A", DelegationType.SUBNET_DTAO, 1) is not None
        assert engine.match_delegator("5A", DelegationType.SUBNET_DTAO, 99) is None

    def test_priority_ordering(self, session: Session) -> None:
        _make_participant(
            session,
            "low-priority",
            [{"type": "ALL"}],
            priority=10,
        )
        _make_participant(
            session,
            "high-priority",
            [{"type": "ALL"}],
            priority=1,
        )
        engine: RulesEngine = RulesEngine(session)

        result: RakebackParticipants | None = engine.match_delegator(
            "5A",
            DelegationType.ROOT_TAO,
            None,
        )
        assert result is not None
        assert result.id == "high-priority"

    def test_expired_participant_not_matched(self, session: Session) -> None:
        _make_participant(
            session,
            "old",
            [{"type": "ALL"}],
            effective_from="2020-01-01",
            effective_to="2020-12-31",
        )
        engine: RulesEngine = RulesEngine(session)

        result: RakebackParticipants | None = engine.match_delegator(
            "5A",
            DelegationType.ROOT_TAO,
            None,
            date(2025, 1, 1),
        )
        assert result is None


class TestMatchAddresses:
    def test_filters_addresses(self, session: Session) -> None:
        p: RakebackParticipants = _make_participant(
            session,
            "p1",
            [{"type": "EXACT_ADDRESS", "addresses": ["addr1", "addr3"]}],
        )
        engine: RulesEngine = RulesEngine(session)

        matched: list[str] = engine.match_addresses(p, ["addr1", "addr2", "addr3", "addr4"])
        assert matched == ["addr1", "addr3"]

    def test_all_rule_returns_everything(self, session: Session) -> None:
        p: RakebackParticipants = _make_participant(session, "p1", [{"type": "ALL"}])
        engine: RulesEngine = RulesEngine(session)

        matched: list[str] = engine.match_addresses(p, ["a", "b", "c"])
        assert matched == ["a", "b", "c"]


class TestValidateRules:
    def test_valid_exact_address(self, session: Session) -> None:
        p: RakebackParticipants = _make_participant(
            session,
            "p1",
            [{"type": "EXACT_ADDRESS", "addresses": ["5FHneW46xGXgs5mUiveU4sbTyGBzmstUPZHb"]}],
        )
        engine: RulesEngine = RulesEngine(session)
        assert engine.validate_rules(p) == []

    def test_empty_rules(self, session: Session) -> None:
        p: RakebackParticipants = _make_participant(session, "p1", [])
        engine: RulesEngine = RulesEngine(session)
        errors: list[str] = engine.validate_rules(p)
        assert len(errors) == 1
        assert "No matching rules" in errors[0]

    def test_unknown_rule_type(self, session: Session) -> None:
        p: RakebackParticipants = _make_participant(session, "p1", [{"type": "BOGUS"}])
        engine: RulesEngine = RulesEngine(session)
        errors: list[str] = engine.validate_rules(p)
        assert any("No matching rules" in e for e in errors)
