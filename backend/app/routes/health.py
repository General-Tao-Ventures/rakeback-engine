"""Health endpoints."""

import logging
import os
import re

from sqlalchemy import inspect

from config import get_settings
from db.connection import get_engine

logger = logging.getLogger(__name__)


def _redact_password(dsn: str) -> str:
    if not dsn:
        return dsn
    return re.sub(r":([^:@]+)@", r":***@", dsn)


def get_db_info() -> dict:
    """Gather DB info. Never raises."""
    try:
        db = get_settings().database

        if db._use_postgres():
            backend_type = "postgres"
            url_or_path = db._redacted_postgres_dsn() or _redact_password(db.url)
        else:
            backend_type = "sqlite"
            url_or_path = db._resolved_sqlite_path().as_posix()

        engine = get_engine()
        existing: set[str] = set()
        try:
            existing = set(inspect(engine).get_table_names())
        except Exception as e:
            logger.warning("Could not inspect DB: %s", e)

        return {
            "backend_type": backend_type,
            "database_url_or_path": url_or_path,
            "tables_present": sorted(existing),
            "tables_missing": [],
            "schema_initialized": len(existing) > 0,
            "pid": os.getpid(),
        }
    except Exception as e:
        logger.exception("Health DB check failed: %s", e)
        return {
            "backend_type": "unknown",
            "database_url_or_path": None,
            "tables_present": [],
            "tables_missing": [],
            "schema_initialized": False,
            "error": str(e),
            "pid": os.getpid(),
        }
