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

    import duckdb

    wal_path = db_path + ".wal"
    has_wal = os.path.exists(wal_path)

    if has_wal:
        print(f"-> [health-db-recover] WAL detected at {wal_path}. Attempting recovery...")
    else:
        print(f"-> [health-db-recover] No WAL file — attempting open to check for stale lock...")

    # First attempt: DuckDB can self-recover a stale WAL if we just open it.
    # Also handles no-WAL stale lock (lock stored inside DB file, not WAL).
    try:
        conn = duckdb.connect(db_path)
        conn.execute("CHECKPOINT")
        conn.close()
        print("-> [health-db-recover] Recovery successful (DuckDB opened cleanly).")
        return
    except duckdb.IOException as exc:
        exc_str = str(exc)
        if "PID 0" not in exc_str and "being used by another process" not in exc_str:
            print(f"-> [health-db-recover] Unexpected error: {exc}. Skipping recovery.")
            return
        print(f"-> [health-db-recover] PID 0 stale lock confirmed: {exc}")

    # Second attempt: remove WAL if present (data in WAL is from the killed session — already lost).
    if has_wal:
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
            return
        except Exception as e:
            print(f"-> [health-db-recover] Recovery failed after WAL removal: {e}. Continuing anyway.")
            return

    # No WAL but still locked: copy DB file to break filesystem-level stale lock.
    # This happens on named Docker volumes after SIGKILL when the lock is embedded in the file.
    print("-> [health-db-recover] No WAL but stale lock persists — copying DB to reset filesystem lock...")
    backup_path = db_path + ".recovering"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        os.replace(backup_path, db_path)
    except OSError as e:
        print(f"-> [health-db-recover] Could not copy DB file: {e}. Continuing anyway.")
        return

    try:
        conn = duckdb.connect(db_path)
        conn.execute("CHECKPOINT")
        conn.close()
        print("-> [health-db-recover] Recovery successful after file copy (stale lock cleared).")
    except Exception as e:
        print(f"-> [health-db-recover] Recovery failed after file copy: {e}. Continuing anyway.")


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
