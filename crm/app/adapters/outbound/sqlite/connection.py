"""
connection.py — CRMDatabase: opens crm.db (WAL, read-write) and ATTACHes cache.db (read-only).

Mirrors Go adapter behaviour in crm/app/internal/adapters/outbound/sqlite/db.go:
- WAL + busy_timeout=5000 + foreign_keys=ON + synchronous=NORMAL
- Single connection (no pool) — SQLite WAL works best with a single writer
- cache.db ensured (created empty if missing), then ATTACHed read-only as "cache"
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional


class CRMDatabase:
    """Wrapper around a single sqlite3.Connection to crm.db with cache.db ATTACHed."""

    def __init__(self, data_dir: str) -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        crm_path = self._data_dir / "crm.db"
        cache_path = self._data_dir / "cache.db"

        # Single-quote guard: ATTACH uses a SQL string literal
        cache_uri = cache_path.as_posix()
        if "'" in cache_uri:
            raise ValueError(f"sqlite: cache.db path must not contain single quotes: {cache_uri}")

        # Open with uri=True so ATTACH can also use URI filenames (e.g. ?mode=ro).
        crm_uri = f"file:{crm_path.as_posix()}"
        self._conn: sqlite3.Connection = sqlite3.connect(
            crm_uri,
            uri=True,
            check_same_thread=False,  # caller controls threading; single writer enforced by design
        )
        self._conn.row_factory = sqlite3.Row
        self._apply_pragmas()
        self._ensure_cache_db(cache_path)
        self._attach_cache(cache_path)

    # ── Internal setup ────────────────────────────────────────────────────────

    def _apply_pragmas(self) -> None:
        """Apply WAL + performance pragmas matching the Go DSN flags."""
        pragmas = [
            "PRAGMA journal_mode=WAL",
            "PRAGMA busy_timeout=5000",
            "PRAGMA foreign_keys=ON",
            "PRAGMA synchronous=NORMAL",
        ]
        for stmt in pragmas:
            self._conn.execute(stmt)

    def _ensure_cache_db(self, cache_path: Path) -> None:
        """Create an empty cache.db with WAL pragmas if it does not yet exist."""
        if cache_path.exists():
            return
        tmp = sqlite3.connect(str(cache_path))
        try:
            tmp.execute("PRAGMA journal_mode=WAL")
            tmp.execute("PRAGMA synchronous=NORMAL")
        finally:
            tmp.close()

    def _attach_cache(self, cache_path: Path) -> None:
        """ATTACH cache.db as read-only schema alias 'cache'."""
        # Use POSIX path in the URI so SQLite parses it correctly on all platforms.
        cache_uri = f"file:{cache_path.as_posix()}?mode=ro"
        self._conn.execute(f"ATTACH DATABASE '{cache_uri}' AS cache")

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def conn(self) -> sqlite3.Connection:
        """Return the underlying sqlite3.Connection."""
        return self._conn

    def ping(self) -> None:
        """Raise sqlite3.Error if the connection is not alive."""
        self._conn.execute("SELECT 1")

    def cache_attached(self) -> bool:
        """Return True if the cache schema is attached and readable."""
        try:
            self._conn.execute("SELECT COUNT(*) FROM cache.sqlite_master").fetchone()
            return True
        except sqlite3.Error:
            return False

    def apply_migrations(self) -> None:
        """Locate and run all *.up.sql migrations from crm/migrations/."""
        from crm.app.adapters.outbound.sqlite.migrations import run_migrations  # noqa: PLC0415
        run_migrations(self._conn)

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "CRMDatabase":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()
