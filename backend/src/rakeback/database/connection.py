"""Database connection and session management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from rakeback.config import get_settings
from rakeback.models import Base


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Get or create the database engine."""
    global _engine
    
    if _engine is None:
        settings = get_settings()
        
        # Build engine options
        engine_options = {
            "echo": settings.debug,
        }
        
        # PostgreSQL-specific options
        if not settings.database.sqlite_path:
            engine_options.update({
                "pool_size": settings.database.pool_size,
                "pool_timeout": settings.database.pool_timeout,
                "pool_recycle": settings.database.pool_recycle,
                "pool_pre_ping": True,
            })
        
        _engine = create_engine(settings.database.url, **engine_options)
        
        # SQLite-specific settings
        if settings.database.sqlite_path:
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()
    
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Get or create the session factory."""
    global _session_factory
    
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    
    return _session_factory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session with automatic commit/rollback."""
    factory = get_session_factory()
    session = factory()
    
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database() -> None:
    """Initialize the database schema."""
    engine = get_engine()
    Base.metadata.create_all(engine)


def reset_engine() -> None:
    """Reset the engine (for testing)."""
    global _engine, _session_factory
    
    if _engine is not None:
        _engine.dispose()
    
    _engine = None
    _session_factory = None
