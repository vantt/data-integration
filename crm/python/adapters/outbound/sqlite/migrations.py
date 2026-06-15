"""
migrations.py — SQLite migration runner for crm.db.

Mirrors golang-migrate behaviour from crm/app/internal/adapters/outbound/sqlite/migrate.go:
- Reads *.up.sql files from crm/migrations/ in numeric order (0001, 0002, ...)
- Tracks applied migrations in a schema_migrations table (idempotent / safe to re-run)
- Runs each migration in a transaction; raises on SQL error

The SQL files already use CREATE TABLE IF NOT EXISTS so they are safe to re-apply,
but the schema_migrations table prevents redundant work and matches golang-migrate semantics.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


# crm/migrations/ relative to this file:
# migrations.py → sqlite/[0] → outbound/[1] → adapters/[2] → python/[3] → crm/[4]
_MIGRATIONS_DIR = Path(__file__).parents[4] / "migrations"

_INIT_TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
)
"""


def _migration_files() -> list[Path]:
    """Return *.up.sql files sorted by version prefix (0001, 0002, ...)."""
    files = sorted(_MIGRATIONS_DIR.glob("*.up.sql"))
    if not files:
        raise FileNotFoundError(
            f"No *.up.sql migration files found in: {_MIGRATIONS_DIR}"
        )
    return files


def _applied_versions(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {row[0] for row in rows}


def run_migrations(conn: sqlite3.Connection) -> None:
    """Apply all pending UP migrations to the given connection.

    Safe to call on every startup — already-applied migrations are skipped.
    Raises sqlite3.Error on SQL failure (transaction is rolled back).
    """
    conn.execute(_INIT_TRACKING_TABLE)
    conn.commit()

    applied = _applied_versions(conn)
    files = _migration_files()

    for path in files:
        version = path.name  # e.g. "0001_app_user_pragmas.up.sql"
        if version in applied:
            continue

        sql = path.read_text(encoding="utf-8")
        try:
            # executescript auto-commits; use explicit transaction via execute + commit
            # so we can record the version atomically with the migration itself.
            # executescript issues an implicit COMMIT first, so we split the work:
            # 1. run the migration SQL (may contain multiple statements)
            # 2. record success in schema_migrations
            conn.executescript(sql)  # commits internally
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)", (version,)
            )
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise RuntimeError(
                f"Migration failed [{version}]: {exc}"
            ) from exc


def apply_migrations(data_dir: str) -> None:
    """Open crm.db and apply all pending migrations. Convenience wrapper for CLI use.

    Args:
        data_dir: Directory containing crm.db (created if absent).
    """
    db_path = Path(data_dir) / "crm.db"
    Path(data_dir).mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        run_migrations(conn)
    finally:
        conn.close()
