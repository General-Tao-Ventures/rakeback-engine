"""Tests for all API routes via FastAPI TestClient."""

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.routes import attributions, conversions, exports, partners, rakeback
from db.connection import get_db
from db.enums import CompletenessFlag, PaymentStatus, PeriodType
from db.models import (
    Base,
    BlockAttributions,
    ConversionEvents,
    RakebackLedgerEntries,
)
from rakeback.services._helpers import new_id, now_iso
from rakeback.services._types import PartnerUI
from rakeback.services.participant_service import ParticipantService


def _create_test_app() -> FastAPI:
    """Minimal app without lifespan (no migrations)."""
    test_app: FastAPI = FastAPI()

    @test_app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    test_app.include_router(partners.router)
    test_app.include_router(attributions.router)
    test_app.include_router(conversions.router)
    test_app.include_router(rakeback.router)
    test_app.include_router(exports.router)
    return test_app


_test_app: FastAPI = _create_test_app()


@pytest.fixture()
def _route_engine() -> Generator[Engine, None, None]:
    """In-memory SQLite engine with check_same_thread=False for TestClient."""
    eng: Engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def _route_session(_route_engine: Engine) -> Generator[Session, None, None]:
    factory: sessionmaker[Session] = sessionmaker(
        bind=_route_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    sess: Session = factory()
    yield sess
    sess.rollback()
    sess.close()


@pytest.fixture()
def client(_route_session: Session) -> Generator[TestClient, None, None]:
    """TestClient with DB dependency overridden to use test session."""

    def _override_db() -> Generator[Session, None, None]:
        yield _route_session

    _test_app.dependency_overrides[get_db] = _override_db
    with TestClient(_test_app, raise_server_exceptions=True) as c:
        yield c
    _test_app.dependency_overrides.clear()


@pytest.fixture()
def session(_route_session: Session) -> Session:
    """Alias so seed helpers can use the same session as the client."""
    return _route_session


# ---------- seed helpers ----------


def _seed_partner(session: Session, name: str = "Test Partner", rate: float = 50.0) -> PartnerUI:
    svc: ParticipantService = ParticipantService(session)
    return svc.create_partner(
        name=name,
        partner_type="named",
        rakeback_rate=rate,
        payout_address="5FHneW46xGXgs5mUiveU4sbTyGBzmstUPZHb",
    )


def _seed_ledger_entry(session: Session, **overrides: object) -> RakebackLedgerEntries:
    ts: str = now_iso()
    defaults: dict[str, object] = {
        "id": new_id(),
        "period_type": PeriodType.DAILY.value,
        "period_start": "2026-01-15",
        "period_end": "2026-01-15",
        "participant_id": "partner-test",
        "participant_type": "PARTNER",
        "validator_hotkey": "5FHne...",
        "gross_dtao_attributed": 100.0,
        "gross_tao_converted": 10.0,
        "rakeback_percentage": 0.5,
        "tao_owed": 5.0,
        "payment_status": PaymentStatus.UNPAID.value,
        "completeness_flag": CompletenessFlag.COMPLETE.value,
        "run_id": "run-1",
        "created_at": ts,
        "updated_at": ts,
    }
    defaults.update(overrides)
    entry: RakebackLedgerEntries = RakebackLedgerEntries(**defaults)
    session.add(entry)
    session.flush()
    return entry


def _seed_attribution(session: Session, **overrides: object) -> BlockAttributions:
    defaults: dict[str, object] = {
        "id": new_id(),
        "block_number": 1000,
        "validator_hotkey": "5FHne...",
        "delegator_address": "5Abc...",
        "delegation_type": "subnet_dtao",
        "subnet_id": 1,
        "attributed_dtao": 100.0,
        "delegation_proportion": 0.5,
        "completeness_flag": CompletenessFlag.COMPLETE.value,
        "computation_timestamp": now_iso(),
        "tao_allocated": 10.0,
        "fully_allocated": True,
        "run_id": "run-1",
    }
    defaults.update(overrides)
    attr: BlockAttributions = BlockAttributions(**defaults)
    session.add(attr)
    session.flush()
    return attr


def _seed_conversion(session: Session, **overrides: object) -> ConversionEvents:
    defaults: dict[str, object] = {
        "id": new_id(),
        "block_number": 1000,
        "transaction_hash": "0x" + new_id()[:8],
        "validator_hotkey": "5FHne...",
        "dtao_amount": 100.0,
        "tao_amount": 10.0,
        "conversion_rate": 0.1,
        "subnet_id": 1,
        "fully_allocated": False,
        "ingestion_timestamp": now_iso(),
    }
    defaults.update(overrides)
    conv: ConversionEvents = ConversionEvents(**defaults)
    session.add(conv)
    session.flush()
    return conv


# ===================================================================
# Health
# ===================================================================


class TestHealth:
    def test_health(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ===================================================================
# Partners
# ===================================================================


class TestPartnerRoutes:
    def test_list_partners_empty(self, client: TestClient) -> None:
        resp = client.get("/api/partners")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_and_list_partners(self, client: TestClient, session: Session) -> None:
        _seed_partner(session, "Alpha", 30.0)
        _seed_partner(session, "Beta", 40.0)
        resp = client.get("/api/partners")
        assert resp.status_code == 200
        data: list[dict[str, object]] = resp.json()
        assert len(data) == 2
        names: set[object] = {p["name"] for p in data}
        assert names == {"Alpha", "Beta"}

    def test_get_partner(self, client: TestClient, session: Session) -> None:
        _seed_partner(session, "FindMe", 25.0)
        resp = client.get("/api/partners/partner-findme")
        assert resp.status_code == 200
        assert resp.json()["name"] == "FindMe"

    def test_get_partner_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/partners/nonexistent")
        assert resp.status_code == 404

    def test_create_partner_via_post(self, client: TestClient) -> None:
        resp = client.post(
            "/api/partners",
            json={
                "name": "New Partner",
                "type": "named",
                "rakebackRate": 20.0,
                "payoutAddress": "5FHneW46xGXgs5mUiveU4sbTyGBzmstUPZHb",
            },
            headers={"X-API-Key": ""},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Partner"

    def test_update_partner(self, client: TestClient, session: Session) -> None:
        _seed_partner(session, "UpdMe", 10.0)
        resp = client.put(
            "/api/partners/partner-updme",
            json={"name": "Updated"},
            headers={"X-API-Key": ""},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_update_partner_not_found(self, client: TestClient) -> None:
        resp = client.put(
            "/api/partners/nope",
            json={"name": "X"},
            headers={"X-API-Key": ""},
        )
        assert resp.status_code == 404

    def test_add_rule(self, client: TestClient, session: Session) -> None:
        _seed_partner(session, "RuleTarget", 15.0)
        resp = client.post(
            "/api/partners/partner-ruletarget/rules",
            json={
                "type": "wallet",
                "config": {"wallet": "5FHneW46xGXgs5mUiveU4sbTyGBzmstUPZHb"},
            },
            headers={"X-API-Key": ""},
        )
        assert resp.status_code == 200
        assert resp.json()["type"] == "wallet"

    def test_add_rule_partner_not_found(self, client: TestClient) -> None:
        resp = client.post(
            "/api/partners/nonexistent/rules",
            json={"type": "wallet", "config": {}},
            headers={"X-API-Key": ""},
        )
        assert resp.status_code == 404

    def test_rule_change_log(self, client: TestClient, session: Session) -> None:
        _seed_partner(session, "LogMe", 10.0)
        resp = client.get("/api/partners/rule-change-log/list")
        assert resp.status_code == 200
        data: list[dict[str, object]] = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1


# ===================================================================
# Rakeback ledger
# ===================================================================


class TestRakebackRoutes:
    def test_list_empty(self, client: TestClient) -> None:
        resp = client.get("/api/rakeback")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_with_entries(self, client: TestClient, session: Session) -> None:
        _seed_ledger_entry(session)
        resp = client.get("/api/rakeback")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_filter_by_partner(self, client: TestClient, session: Session) -> None:
        _seed_ledger_entry(session, participant_id="partner-a")
        _seed_ledger_entry(session, participant_id="partner-b")
        resp = client.get("/api/rakeback", params={"partner_id": "partner-a"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_summary_empty(self, client: TestClient) -> None:
        resp = client.get("/api/rakeback/summary")
        assert resp.status_code == 200
        data: dict[str, object] = resp.json()
        assert data["totalEntries"] == 0

    def test_summary_with_entries(self, client: TestClient, session: Session) -> None:
        _seed_ledger_entry(session, tao_owed=10.0, participant_id="partner-a")
        _seed_ledger_entry(
            session,
            tao_owed=5.0,
            participant_id="partner-b",
            payment_status=PaymentStatus.PAID.value,
        )
        resp = client.get("/api/rakeback/summary")
        assert resp.status_code == 200
        data: dict[str, object] = resp.json()
        assert data["totalEntries"] == 2


# ===================================================================
# Attributions
# ===================================================================


class TestAttributionRoutes:
    def test_list_empty(self, client: TestClient) -> None:
        resp = client.get("/api/attributions", params={"start": 0, "end": 9999})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_with_data(self, client: TestClient, session: Session) -> None:
        _seed_attribution(session)
        resp = client.get("/api/attributions", params={"start": 0, "end": 9999})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_stats_empty(self, client: TestClient) -> None:
        resp = client.get("/api/attributions/stats")
        assert resp.status_code == 200
        data: dict[str, object] = resp.json()
        assert data["totalAttributions"] == 0

    def test_stats_with_data(self, client: TestClient, session: Session) -> None:
        _seed_attribution(session, block_number=100)
        _seed_attribution(session, block_number=101, delegator_address="5Xyz...")
        resp = client.get(
            "/api/attributions/stats",
            params={"start": 100, "end": 101},
        )
        assert resp.status_code == 200
        data: dict[str, object] = resp.json()
        assert data["totalAttributions"] == 2

    def test_block_detail(self, client: TestClient, session: Session) -> None:
        _seed_attribution(session, block_number=500)
        resp = client.get("/api/attributions/block/500")
        assert resp.status_code == 200
        data: dict[str, object] = resp.json()
        assert data["blockNumber"] == 500
        assert len(data["attributions"]) == 1  # type: ignore[arg-type]

    def test_block_detail_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/attributions/block/9999")
        assert resp.status_code == 404


# ===================================================================
# Conversions
# ===================================================================


class TestConversionRoutes:
    def test_list_empty(self, client: TestClient) -> None:
        resp = client.get("/api/conversions")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_with_data(self, client: TestClient, session: Session) -> None:
        _seed_conversion(session)
        resp = client.get("/api/conversions")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_detail(self, client: TestClient, session: Session) -> None:
        conv: ConversionEvents = _seed_conversion(session)
        resp = client.get(f"/api/conversions/{conv.id}")
        assert resp.status_code == 200
        data: dict[str, object] = resp.json()
        assert data["conversion"]["id"] == conv.id  # type: ignore[index]

    def test_detail_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/conversions/nonexistent")
        assert resp.status_code == 404


# ===================================================================
# Exports
# ===================================================================


class TestExportRoutes:
    def test_list_empty(self, client: TestClient) -> None:
        resp = client.get("/api/exports")
        assert resp.status_code == 200
        data: dict[str, object] = resp.json()
        assert data["exports"] == []

    def test_download_json(self, client: TestClient, session: Session) -> None:
        _seed_ledger_entry(session)
        resp = client.get(
            "/api/exports/download",
            params={"format": "json"},
            headers={"X-API-Key": ""},
        )
        assert resp.status_code == 200
        data: dict[str, object] = resp.json()
        assert data["format"] == "json"
        assert data["record_count"] == 1

    def test_download_csv(self, client: TestClient, session: Session) -> None:
        _seed_ledger_entry(session)
        resp = client.get(
            "/api/exports/download",
            params={"format": "csv"},
            headers={"X-API-Key": ""},
        )
        assert resp.status_code == 200
        data: dict[str, object] = resp.json()
        assert data["format"] == "csv"
        assert "participant_id" in data["content"]  # type: ignore[operator]

    def test_download_filter_by_partner(self, client: TestClient, session: Session) -> None:
        _seed_ledger_entry(session, participant_id="partner-a")
        _seed_ledger_entry(session, participant_id="partner-b")
        resp = client.get(
            "/api/exports/download",
            params={"format": "json", "partner_id": "partner-a"},
            headers={"X-API-Key": ""},
        )
        assert resp.status_code == 200
        assert resp.json()["record_count"] == 1
