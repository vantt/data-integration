"""Recover ingestion_health.duckdb stale WAL lock on container startup.

DuckDB leaves a stale WAL when the previous process was killed (SIGKILL / OOM /
container restart). On a fresh container start, no previous process holds the
lock, so it is safe to remove the WAL and force a checkpoint.

Run this script once during container startup — before Dagster launches.
"""
import os
import sys


def recover() -> None:
    db_path = _resolve_path()
    if not db_path:
        print("-> [health-db-recover] INGESTION_HEALTH_DB / DBT_DATA_LAKE_PATH not set — skip.")
        return

    wal_path = db_path + ".wal"
    if not os.path.exists(wal_path):
        print("-> [health-db-recover] No WAL file found — nothing to recover.")
        return

    print(f"-> [health-db-recover] WAL detected at {wal_path}. Attempting recovery...")
    import duckdb

    # First attempt: DuckDB can self-recover a stale WAL if we just open it.
    try:
        conn = duckdb.connect(db_path)
        conn.execute("CHECKPOINT")
        conn.close()
        print("-> [health-db-recover] Recovery successful (DuckDB self-healed WAL).")
        return
    except duckdb.IOException as exc:
        if "PID 0" not in str(exc) and "being used by another process" not in str(exc):
            # Unexpected error — don't silently swallow it.
            print(f"-> [health-db-recover] Unexpected error: {exc}. Skipping recovery.")
            return
        print(f"-> [health-db-recover] PID 0 stale lock confirmed: {exc}")

    # Second attempt: remove WAL (data in WAL is from the killed session — already lost).
    print(f"-> [health-db-recover] Removing stale WAL: {wal_path}")
    try:
        os.remove(wal_path)
    except OSError as e:
        print(f"-> [health-db-recover] Could not remove WAL: {e}. Skipping.")
        return

    try:
        conn = duckdb.connect(db_path)
        conn.execute("CHECKPOINT")
        conn.close()
        print("-> [health-db-recover] Recovery successful after WAL removal.")
    except Exception as e:
        print(f"-> [health-db-recover] Recovery failed after WAL removal: {e}. Continuing anyway.")


def _resolve_path() -> str | None:
    explicit = os.environ.get("INGESTION_HEALTH_DB")
    if explicit:
        return explicit
    data_lake = os.environ.get("DBT_DATA_LAKE_PATH")
    if data_lake:
        from pathlib import Path
        return str(Path(data_lake) / "monitoring" / "ingestion_health.duckdb")
    return None


if __name__ == "__main__":
    recover()
