"""Database connection and session management."""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from rakeback.config import get_settings
from rakeback.models import Base

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None

REQUIRED_TABLES = ("rakeback_participants", "eligibility_rules", "rule_change_log")


def get_resolved_sqlite_path() -> Path | None:
    """Return absolute path to SQLite file if using SQLite, else None."""
    db = get_settings().database
    if db._use_postgres():
        return None
    return db._resolved_sqlite_path()


def get_engine() -> Engine:
    """Get or create the database engine. Single shared instance."""
    global _engine

    if _engine is None:
        settings = get_settings()
        url = settings.database.url
        opts = {"echo": settings.debug}

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
    """Database session with commit/rollback."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _ensure_models_registered() -> None:
    """Import all models so they are registered with Base.metadata."""
    import rakeback.models  # noqa: F401


def verify_required_tables(engine: Engine | None = None) -> list[str]:
    """Return list of required tables that are missing."""
    if engine is None:
        engine = get_engine()
    insp = inspect(engine)
    existing = set(insp.get_table_names())
    return [t for t in REQUIRED_TABLES if t not in existing]


def _verify_tables_exist(engine: Engine) -> list[str]:
    return verify_required_tables(engine)


def init_database() -> None:
    """
    Create all tables at startup. Idempotent. Uses same engine as API.
    """
    _ensure_models_registered()
    engine = get_engine()
    insp = inspect(engine)
    before = set(insp.get_table_names())
    missing_before = [t for t in REQUIRED_TABLES if t not in before]

    Base.metadata.create_all(engine)
    after = set(inspect(engine).get_table_names())
    created = [t for t in missing_before if t in after]
    still_missing = [t for t in REQUIRED_TABLES if t not in after]

    if created:
        logger.info("Schema init: created tables %s", created)
    elif not still_missing:
        logger.info("Schema init: all tables present")
    if still_missing:
        logger.warning("Schema init: tables still missing %s", still_missing)
        Base.metadata.create_all(engine)
        after2 = set(inspect(engine).get_table_names())
        still_missing = [t for t in REQUIRED_TABLES if t not in after2]
        if still_missing:
            db_path = get_resolved_sqlite_path()
            hint = f" (file: {db_path})" if db_path else ""
            raise RuntimeError(
                f"Schema init failed: missing tables {still_missing}{hint}. "
                "Delete sqlite file and restart, or run: rakeback init-db"
            )


def reset_engine() -> None:
    """For testing: clear cached engine."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
