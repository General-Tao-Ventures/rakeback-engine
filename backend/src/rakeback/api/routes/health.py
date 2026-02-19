"""Health endpoints. _get_db_info() used by app; always returns 200, never raises."""

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)


def _redact_password(dsn: str) -> str:
    """Redact password from postgres DSN (user:password@host -> user:***@host)."""
    if not dsn:
        return dsn
    return re.sub(r":([^:@]+)@", r":***@", dsn)


def _get_db_info() -> dict[str, Any]:
    """
    Gather DB info. Never raises; returns error details in the response if something fails.
    """
    try:
        from rakeback.config import get_settings
        from rakeback.database import get_engine, get_resolved_sqlite_path

        settings = get_settings()
        db = settings.database

        if db._use_postgres():
            backend_type = "postgres"
            database_url_or_path = db._redacted_postgres_dsn() or _redact_password(db.url)
        else:
            backend_type = "sqlite"
            path = get_resolved_sqlite_path()
            database_url_or_path = path.as_posix() if path else ""

        engine = get_engine()
        existing = set()
        missing: list[str] = []
        try:
            from sqlalchemy import inspect
            insp = inspect(engine)
            existing = set(insp.get_table_names())
        except Exception as e:
            logger.warning("Could not inspect DB: %s", e)
            existing = set()

        from rakeback.database.connection import REQUIRED_TABLES
        tables_present = [t for t in REQUIRED_TABLES if t in existing]
        tables_missing = [t for t in REQUIRED_TABLES if t not in existing]
        schema_initialized = len(tables_missing) == 0

        return {
            "backend_type": backend_type,
            "database_url_or_path": database_url_or_path,
            "tables_present": sorted(tables_present),
            "tables_missing": sorted(tables_missing),
            "schema_initialized": schema_initialized,
            "pid": os.getpid(),
        }
    except Exception as e:
        logger.exception("Health DB check failed: %s", e)
        return {
            "backend_type": "unknown",
            "database_url_or_path": None,
            "tables_present": [],
            "tables_missing": ["rakeback_participants", "eligibility_rules", "rule_change_log"],
            "schema_initialized": False,
            "error": str(e),
            "pid": os.getpid(),
        }
