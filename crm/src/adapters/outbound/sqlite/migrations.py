"""
migrations.py — SQLite migration runner for crm.db.

Mirrors golang-migrate behaviour from crm/src/internal/adapters/outbound/sqlite/migrate.go:
- Reads *.up.sql files from crm/migrations/ in numeric order (0001, 0002, ...)
- Tracks applied migrations in a schema_migrations table (idempotent / safe to re-run)
- Runs each migration statement-by-statement so that idempotent DDL patterns work:
  - "duplicate column name" on ALTER TABLE ADD COLUMN → silently skipped (column already exists)
  - BEGIN...END trigger bodies kept as a single statement (not split on the inner semicolon)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


# crm/migrations/ relative to this file:
# migrations.py → sqlite/[0] → outbound/[1] → adapters/[2] → src/[3] → crm/[4]
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


def _split_statements(sql: str) -> list[str]:
    """Split SQL file into individual statements on semicolons.

    Respects BEGIN...END trigger bodies — the semicolons inside them are NOT
    treated as statement boundaries. Everything else splits on ';'.
    """
    stmts: list[str] = []
    buf: list[str] = []
    depth = 0  # nesting depth inside BEGIN...END

    for line in sql.splitlines():
        stripped = line.strip()
        stripped_upper = stripped.upper()

        # Skip full-line comments for depth analysis, but still buffer them
        if not stripped_upper.startswith("--"):
            # Track trigger BEGIN...END depth
            # Match lines that ARE exactly "BEGIN" (trigger body opener)
            if stripped_upper == "BEGIN":
                depth += 1
            # Match lines that ARE exactly "END" or "END;" (trigger body closer)
            elif stripped_upper.rstrip(";") == "END" and depth > 0:
                depth -= 1

        buf.append(line)

        # Split on ';' only when not inside a BEGIN...END block. Ignore a ';'
        # that sits inside a trailing '-- comment' — it is not a statement
        # terminator (e.g. "col TEXT  -- set on undo; prevents double-undo"),
        # otherwise the statement is cut mid-definition → "incomplete input".
        code_part = line.split("--", 1)[0]
        if ";" in code_part and depth == 0:
            stmt = "\n".join(buf).strip()
            if stmt:
                stmts.append(stmt)
            buf = []

    # Flush any trailing content (e.g. file without trailing newline)
    remainder = "\n".join(buf).strip()
    if remainder:
        stmts.append(remainder)

    return stmts


def run_migrations(conn: sqlite3.Connection) -> None:
    """Apply all pending UP migrations to the given connection.

    Safe to call on every startup — already-applied migrations are skipped.
    Raises RuntimeError on SQL failure (wraps the original sqlite3.Error).

    Atomicity:
    - Each migration file runs inside a single SAVEPOINT so that all its statements
      either all commit or all roll back.  A mid-file crash can no longer leave a
      half-applied schema (e.g. DROP TABLE committed but RENAME not yet executed).
    - The outer SAVEPOINT is released (committed) only after the version row is
      inserted into schema_migrations, so the tracking table is always consistent
      with the applied schema.

    Idempotency:
    - "duplicate column name" on ALTER TABLE ADD COLUMN is silently ignored via an
      inner SAVEPOINT: the failing statement is rolled back to the inner savepoint
      while the outer file-level savepoint remains open, allowing subsequent
      statements in the same file to proceed.
    - All other OperationalError variants propagate and roll back the entire file.
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
        sp_outer = f"mig_{version.replace('.', '_').replace('-', '_')}"
        try:
            conn.execute(f"SAVEPOINT {sp_outer}")

            for stmt in _split_statements(sql):
                stmt = stmt.strip()
                if not stmt:
                    continue

                # Inner savepoint: lets us roll back a single statement (the
                # duplicate-column-name case) without aborting the outer savepoint.
                conn.execute(f"SAVEPOINT {sp_outer}_stmt")
                try:
                    conn.execute(stmt)
                    conn.execute(f"RELEASE {sp_outer}_stmt")
                except sqlite3.OperationalError as stmt_exc:
                    conn.execute(f"ROLLBACK TO {sp_outer}_stmt")
                    conn.execute(f"RELEASE {sp_outer}_stmt")
                    if "duplicate column name" in str(stmt_exc).lower():
                        # ALTER TABLE ADD COLUMN — column already exists; skip idempotently.
                        continue
                    raise

            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)", (version,)
            )
            conn.execute(f"RELEASE {sp_outer}")
        except sqlite3.Error as exc:
            try:
                conn.execute(f"ROLLBACK TO {sp_outer}")
                conn.execute(f"RELEASE {sp_outer}")
            except sqlite3.Error:
                pass
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
