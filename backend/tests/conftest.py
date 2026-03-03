"""Shared fixtures — in-memory SQLite DB with all tables."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base


@pytest.fixture()
def engine() -> Generator[Engine, None, None]:
    eng: Engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine: Engine) -> Generator[Session, None, None]:
    factory: sessionmaker[Session] = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    sess: Session = factory()
    yield sess
    sess.rollback()
    sess.close()
