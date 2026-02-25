"""Simple SQL migration runner.

Reads .sql files from the migrations/ directory in lexicographic order,
tracks applied migrations in a _migrations table, and skips already-applied ones.

Usage:
    python migrations/migrate.py                # apply pending migrations
    python migrations/migrate.py --dry-run      # show what would be applied
    python migrations/migrate.py --status       # show migration status
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parent


def _get_db_path() -> str:
    """Resolve the SQLite database path from env or default."""
    from dotenv import load_dotenv

    backend_root = MIGRATIONS_DIR.parent
    for candidate in (backend_root / ".env", backend_root.parent / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)

    db_path = os.environ.get("DB_SQLITE_PATH", "data/rakeback.db")
    if not os.path.isabs(db_path):
        db_path = str(backend_root / db_path)
    return db_path


def _ensure_tracking_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _migrations ("
        "  filename TEXT PRIMARY KEY,"
        "  applied_at TEXT NOT NULL"
        ")"
    )
    conn.commit()


def _get_applied(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT filename FROM _migrations").fetchall()
    return {r[0] for r in rows}


def _get_pending(applied: set[str]) -> list[Path]:
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    return [f for f in sql_files if f.name not in applied]


def migrate(dry_run: bool = False) -> None:
    db_path = _get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    print(f"Database: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    _ensure_tracking_table(conn)
    applied = _get_applied(conn)
    pending = _get_pending(applied)

    if not pending:
        print("No pending migrations.")
        return

    for migration in pending:
        print(f"{'[DRY RUN] ' if dry_run else ''}Applying {migration.name} ...")
        if dry_run:
            continue

        sql = migration.read_text()
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO _migrations (filename, applied_at) VALUES (?, ?)",
            (migration.name, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        print(f"  Applied {migration.name}")

    conn.close()
    print("Done.")


def status() -> None:
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        print("No migrations applied yet.")
        return

    conn = sqlite3.connect(db_path)
    _ensure_tracking_table(conn)
    applied = _get_applied(conn)
    pending = _get_pending(applied)

    print(f"Database: {db_path}")
    print(f"Applied:  {len(applied)}")
    for name in sorted(applied):
        print(f"  [x] {name}")
    print(f"Pending:  {len(pending)}")
    for p in pending:
        print(f"  [ ] {p.name}")
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="SQL migration runner")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be applied")
    parser.add_argument("--status", action="store_true", help="Show migration status")
    args = parser.parse_args()

    if args.status:
        status()
    else:
        migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
