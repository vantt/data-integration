"""Runtime serving refresh — GC rolling parquet files, detect schema drift.

This script runs on every pipeline execution. It deliberately does NOT open
the DuckDB file, so it cannot collide with Metabase's JDBC lock. All view
lifecycle management is delegated to bootstrap_serving_views.py (run manually
when schema drifts).

Output conventions:
  - Summary counters per table (1 line each)
  - [!] SCHEMA_DRIFT: <table>  — raised as hard error by the Dagster asset
  - [!] Failed / [!] WARNING / [!] ERROR  — picked up by asset as warnings

See plans/260408-1611-fix-serving-db-hang-metabase-lock/plan.md Phase 2.
"""
from __future__ import annotations

import glob
import json
import os
import re
import time

# --- Paths ---
DATA_LAKE_ROOT = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
DBT_EXPORT_PATH = os.environ.get("DBT_EXPORT_PATH", os.path.join(DATA_LAKE_ROOT, "export", "marts"))
SERVING_DIR = os.path.join(DATA_LAKE_ROOT, "serving")
ROLLING_DIR = os.path.join(DBT_EXPORT_PATH, "rolling")

# Marker file tracking last-known table folders, used to detect schema drift.
# Lives alongside olap.duckdb but is a plain JSON file — no DB lock needed.
KNOWN_TABLES_MARKER = os.path.join(SERVING_DIR, ".known_tables.json")

# Allowlist: valid SQL identifier (dbt output is safe, guard against malicious dirs)
_TABLE_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def get_latest_file(folder_path: str) -> str | None:
    """Return basename of lexically latest parquet file, or None if empty."""
    files = glob.glob(os.path.join(folder_path, "*.parquet"))
    if not files:
        return None
    files.sort()
    return os.path.basename(files[-1])


def garbage_collect(folder_path: str, latest_file: str) -> tuple[int, int]:
    """Delete all parquet files except latest_file. Returns (deleted, skipped)."""
    files = glob.glob(os.path.join(folder_path, "*.parquet"))
    deleted = 0
    skipped = 0
    for f in files:
        if os.path.basename(f) == latest_file:
            continue
        try:
            os.remove(f)
            deleted += 1
        except PermissionError:
            # Windows: file handle held by reader
            skipped += 1
        except OSError:
            # Linux: advisory lock or in-flight read — retry once briefly
            time.sleep(0.5)
            try:
                os.remove(f)
                deleted += 1
            except Exception:
                skipped += 1
        except Exception as e:
            print(f"  [!] ERROR deleting {os.path.basename(f)}: {e}")
            skipped += 1
    return deleted, skipped


def load_known_tables() -> set[str]:
    """Load previously-seen table folder names from marker file."""
    if not os.path.exists(KNOWN_TABLES_MARKER):
        return set()
    try:
        with open(KNOWN_TABLES_MARKER, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("tables", []))
    except (OSError, ValueError, TypeError):
        return set()


def save_known_tables(tables: set[str]) -> None:
    """Persist current table folder list for next run's drift check."""
    os.makedirs(SERVING_DIR, exist_ok=True)
    tmp = KNOWN_TABLES_MARKER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"tables": sorted(tables)}, f)
    os.replace(tmp, KNOWN_TABLES_MARKER)


def refresh_rolling() -> None:
    print(f"Refreshing rolling dir: {ROLLING_DIR}")

    if not os.path.exists(ROLLING_DIR):
        print(f"  [!] WARNING: rolling dir not found. Pipeline may not have run yet.")
        return

    subdirs = sorted(
        d for d in os.listdir(ROLLING_DIR)
        if os.path.isdir(os.path.join(ROLLING_DIR, d))
    )
    if not subdirs:
        print("  [!] WARNING: no table directories found in rolling/")
        return

    current_tables: set[str] = set()
    total_deleted = 0
    total_skipped = 0

    for table_name in subdirs:
        if not _TABLE_NAME_RE.match(table_name):
            print(f"  [!] WARNING: skipping invalid table name: {table_name}")
            continue
        current_tables.add(table_name)

        table_dir = os.path.join(ROLLING_DIR, table_name)
        latest = get_latest_file(table_dir)
        if not latest:
            # Empty folder is normal (dbt model produced no rows this run).
            # bootstrap_serving_views.py handles view lifecycle separately.
            print(f"  {table_name}: empty folder")
            continue

        deleted, skipped = garbage_collect(table_dir, latest)
        total_deleted += deleted
        total_skipped += skipped
        # Condensed per-table summary — no per-file spam to keep stdout small
        print(f"  {table_name}: latest={latest} gc(deleted={deleted}, skipped={skipped})")

    # Schema drift detection — compare current vs last-known set
    known = load_known_tables()
    if known:
        new_tables = current_tables - known
        for t in sorted(new_tables):
            # SCHEMA_DRIFT marker — asset will raise on this, triggering failure_sensor
            print(
                f"  [!] SCHEMA_DRIFT: new table '{t}' detected. "
                f"Run bootstrap_serving_views.py when Metabase can be stopped briefly."
            )
        # Note: disappeared tables (known - current) are benign — bootstrap drops stale views

    save_known_tables(current_tables)

    print(
        f"Refresh done: tables={len(current_tables)} "
        f"deleted={total_deleted} skipped={total_skipped}"
    )


if __name__ == "__main__":
    refresh_rolling()
