"""Ensure ingestion_health.db is accessible on container startup.

SQLite with WAL mode does not leave stale locks after process kills,
so no complex recovery is needed. This script just verifies the DB
is accessible and checkpoints the WAL if present.
"""
import os
import sys


def recover() -> None:
    db_path = _resolve_path()
    if not db_path:
        print("-> [health-db] INGESTION_HEALTH_DB / DBT_DATA_LAKE_PATH not set — skip.")
        return

    import sqlite3

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
        conn.close()
        print(f"-> [health-db] SQLite DB healthy: {db_path}")
    except Exception as exc:
        # Non-fatal: DB will be created fresh on first write
        print(f"-> [health-db] DB check failed (will recreate on first write): {exc}")


def _resolve_path() -> str | None:
    explicit = os.environ.get("INGESTION_HEALTH_DB")
    if explicit:
        return explicit
    data_lake = os.environ.get("DBT_DATA_LAKE_PATH")
    if data_lake:
        from pathlib import Path
        return str(Path(data_lake) / "monitoring" / "ingestion_health.db")
    return None


if __name__ == "__main__":
    recover()
