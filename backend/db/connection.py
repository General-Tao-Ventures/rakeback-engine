"""Database engine, session management, and FastAPI dependency."""

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Get or create the shared database engine."""
    global _engine

    if _engine is None:
        settings = get_settings()
        url = settings.database.url
        opts: dict = {"echo": settings.debug}

        if settings.database._use_postgres():
            opts.update(
                pool_size=settings.database.pool_size,
                pool_timeout=settings.database.pool_timeout,
                pool_recycle=settings.database.pool_recycle,
                pool_pre_ping=True,
            )

        _engine = create_engine(url, **opts)

        if not settings.database._use_postgres():

            @event.listens_for(_engine, "connect")
            def _set_sqlite_pragma(dbapi_conn, connection_record):
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.execute("PRAGMA journal_mode=WAL")
                cur.execute("PRAGMA busy_timeout=30000")
                cur.execute("PRAGMA synchronous=NORMAL")
                cur.close()

    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Get or create the session factory."""
    global _session_factory

    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context-managed session with commit/rollback."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """For testing: clear cached engine and session factory."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
