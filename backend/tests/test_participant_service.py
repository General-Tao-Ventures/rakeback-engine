"""Tests for rakeback.services.participant_service."""

from sqlalchemy.orm import Session

from app.schemas.partners import PartnerCreate, PartnerUpdate, RuleCreate
from db.enums import ApiRuleType
from rakeback.services._types import PartnerUI
from rakeback.services.participant_service import ParticipantService


class TestCreatePartner:
    def test_basic_creation(self, session: Session) -> None:
        svc: ParticipantService = ParticipantService(session)
        result: PartnerUI = svc.create_partner(
            name="Test Partner",
            partner_type="named",
            rakeback_rate=50.0,
            payout_address="5FHneW46xGXgs5mUiveU4sbTyGBzmstUPZHb",
        )
        assert result["id"] == "partner-test-partner"
        assert result["name"] == "Test Partner"
        assert result["rakebackRate"] == 50.0

    def test_duplicate_name_gets_unique_id(self, session: Session) -> None:
        svc: ParticipantService = ParticipantService(session)
        r1: PartnerUI = svc.create_partner(name="Dupe", partner_type="named", rakeback_rate=10.0)
        r2: PartnerUI = svc.create_partner(name="Dupe", partner_type="named", rakeback_rate=20.0)
        assert r1["id"] != r2["id"]

    def test_with_wallet_rule(self, session: Session) -> None:
        svc: ParticipantService = ParticipantService(session)
        result: PartnerUI = svc.create_partner(
            name="Wallet Partner",
            partner_type="named",
            rakeback_rate=25.0,
            rules=[
                RuleCreate(
                    type=ApiRuleType.WALLET,
                    config={"wallet": "5FHneW46xGXgs5mUiveU4sbTyGBzmstUPZHb"},
                ),
            ],
        )
        assert len(result["rules"]) == 1
        assert result["rules"][0]["type"] == ApiRuleType.WALLET


class TestGetPartner:
    def test_not_found(self, session: Session) -> None:
        svc: ParticipantService = ParticipantService(session)
        assert svc.get_partner("nonexistent") is None

    def test_found(self, session: Session) -> None:
        svc: ParticipantService = ParticipantService(session)
        svc.create_partner(name="Find Me", partner_type="named", rakeback_rate=10.0)
        result: PartnerUI | None = svc.get_partner("partner-find-me")
        assert result is not None
        assert result["name"] == "Find Me"


class TestUpdatePartner:
    def test_update_name(self, session: Session) -> None:
        svc: ParticipantService = ParticipantService(session)
        svc.create_partner(name="Original", partner_type="named", rakeback_rate=10.0)
        result: PartnerUI | None = svc.update_partner(
            "partner-original", PartnerUpdate(name="Updated")
        )
        assert result is not None
        assert result["name"] == "Updated"

    def test_update_nonexistent(self, session: Session) -> None:
        svc: ParticipantService = ParticipantService(session)
        assert svc.update_partner("nope", PartnerUpdate(name="X")) is None


class TestListPartners:
    def test_empty(self, session: Session) -> None:
        svc: ParticipantService = ParticipantService(session)
        assert svc.list_partners(active_only=False) == []

    def test_returns_created(self, session: Session) -> None:
        svc: ParticipantService = ParticipantService(session)
        svc.create_partner(name="P1", partner_type="named", rakeback_rate=10.0)
        svc.create_partner(name="P2", partner_type="named", rakeback_rate=20.0)
        result: list[PartnerUI] = svc.list_partners(active_only=False)
        assert len(result) == 2


class TestCreatePartnerFromRequest:
    def test_wallet_partner(self, session: Session) -> None:
        svc: ParticipantService = ParticipantService(session)
        result: PartnerUI = svc.create_partner_from_request(
            PartnerCreate(
                name="Req Partner",
                type="named",
                rakeback_rate=30.0,
                wallet_address="5FHneW46xGXgs5mUiveU4sbTyGBzmstUPZHb",
                payout_address="5FHneW46xGXgs5mUiveU4sbTyGBzmstUPZHb",
            )
        )
        assert result["name"] == "Req Partner"
        assert result["rakebackRate"] == 30.0
        assert len(result["rules"]) == 1
