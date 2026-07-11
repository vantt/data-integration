"""Runtime serving refresh — GC rolling parquet files, detect schema drift.

This script runs on every pipeline execution. It deliberately does NOT open
the DuckDB file, so it cannot collide with Metabase's JDBC lock. All view
lifecycle management is delegated to bootstrap_serving_views.py (run manually
when schema drifts).

Retention policy: ROLLING_KEEP_VERSIONS (default 3) controls how many parquet
snapshots per table are kept. Default of 3 provides rollback safety + audit
trail (views always read max(filename) = latest). Set 1 for minimal storage.

Schema drift has TWO independent checks:
  - Table-level: a table folder appeared/disappeared since last run.
  - Column-level (added 2026-07-11, plans/260709-1638-crm-outreach-effort-report
    plan.md open Q#9): a column's TYPE changed between the previously-recorded
    schema and the latest parquet file. This matters because
    bootstrap_serving_views.py reads the rolling glob with union_by_name=true —
    correct for a plain ADDED column (the common case), but an incompatible
    TYPE change on an existing column now gets silently coerced/widened by
    DuckDB instead of erroring loudly, for as long as an old-schema file
    survives in the kept window (up to ROLLING_KEEP_VERSIONS). This check
    reads parquet schema via an in-memory DuckDB connection only (never opens
    the locked serving DB file), so it carries none of that lock risk.

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

import duckdb

# --- Paths ---
DATA_LAKE_ROOT = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
DBT_EXPORT_PATH = os.environ.get("DBT_EXPORT_PATH", os.path.join(DATA_LAKE_ROOT, "export", "marts"))
SERVING_DIR = os.path.join(DATA_LAKE_ROOT, "serving")
ROLLING_DIR = os.path.join(DBT_EXPORT_PATH, "rolling")

# Marker file tracking last-known table folders, used to detect schema drift.
# Lives alongside olap.duckdb but is a plain JSON file — no DB lock needed.
KNOWN_TABLES_MARKER = os.path.join(SERVING_DIR, ".known_tables.json")

# Number of rolling parquet versions to keep per table (>=1).
# Default 3: rollback safety net + audit trail. Set 1 for minimal storage.
ROLLING_KEEP_VERSIONS = max(1, int(os.environ.get("ROLLING_KEEP_VERSIONS", "3")))

# Allowlist: valid SQL identifier (dbt output is safe, guard against malicious dirs)
_TABLE_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def get_latest_file(folder_path: str) -> str | None:
    """Return basename of lexically latest parquet file, or None if empty."""
    files = glob.glob(os.path.join(folder_path, "*.parquet"))
    if not files:
        return None
    files.sort()
    return os.path.basename(files[-1])


def garbage_collect(folder_path: str, keep_n: int) -> tuple[int, int]:
    """Keep last keep_n parquet files (lexical max = newest), delete the rest."""
    files = sorted(glob.glob(os.path.join(folder_path, "*.parquet")))
    if len(files) <= keep_n:
        return 0, 0
    to_delete = files[:-keep_n]
    deleted = 0
    skipped = 0
    for f in to_delete:
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


def get_latest_schema(folder_path: str, latest_filename: str) -> dict[str, str] | None:
    """Return {column_name: duckdb_type} for the latest parquet file, or None
    if it can't be read (logged, never raises — a schema-read failure must not
    abort GC for every other table)."""
    path = os.path.join(folder_path, latest_filename)
    try:
        con = duckdb.connect()  # in-memory only — never touches the serving DB file
        rows = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()
        return {row[0]: row[1] for row in rows}
    except Exception as e:
        print(f"  [!] WARNING: could not read schema for {os.path.basename(folder_path)}: {e}")
        return None


def load_known_tables() -> tuple[set[str], dict[str, dict[str, str]]]:
    """Load previously-seen table folder names + per-table column schemas.

    Returns (tables, schemas). schemas is {} for markers written before the
    column-level drift check existed — first run after upgrading just
    establishes the baseline, no false-positive drift on the upgrade itself.
    """
    if not os.path.exists(KNOWN_TABLES_MARKER):
        return set(), {}
    try:
        with open(KNOWN_TABLES_MARKER, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("tables", [])), data.get("schemas", {})
    except (OSError, ValueError, TypeError):
        return set(), {}


def save_known_tables(tables: set[str], schemas: dict[str, dict[str, str]]) -> None:
    """Persist current table folder list + column schemas for next run's drift check."""
    os.makedirs(SERVING_DIR, exist_ok=True)
    tmp = KNOWN_TABLES_MARKER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"tables": sorted(tables), "schemas": schemas}, f)
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

    known_tables, known_schemas = load_known_tables()

    current_tables: set[str] = set()
    current_schemas: dict[str, dict[str, str]] = {}
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

        deleted, skipped = garbage_collect(table_dir, ROLLING_KEEP_VERSIONS)
        total_deleted += deleted
        total_skipped += skipped
        # Condensed per-table summary — no per-file spam to keep stdout small
        print(f"  {table_name}: latest={latest} keep={ROLLING_KEEP_VERSIONS} gc(deleted={deleted}, skipped={skipped})")

        # Column-level schema drift — compare latest file's types against last-known.
        # A plain added column is fine (bootstrap's union_by_name handles it); an
        # incompatible TYPE change on an EXISTING column is the residual risk that
        # introduced (plan.md open Q#9) — flag it loudly instead of letting
        # union_by_name silently coerce/widen it across the rolling window.
        schema = get_latest_schema(table_dir, latest)
        if schema is not None:
            current_schemas[table_name] = schema
            prior_schema = known_schemas.get(table_name)
            if prior_schema:
                for col, new_type in schema.items():
                    old_type = prior_schema.get(col)
                    if old_type is not None and old_type != new_type:
                        print(
                            f"  [!] SCHEMA_DRIFT: {table_name} column '{col}' type "
                            f"changed {old_type} -> {new_type}. union_by_name in "
                            f"bootstrap_serving_views.py will coerce this silently "
                            f"across the rolling window — verify the Metabase-facing "
                            f"view/cards for this column before trusting it."
                        )

    # Table-level schema drift detection — compare current vs last-known set
    if known_tables:
        new_tables = current_tables - known_tables
        for t in sorted(new_tables):
            # SCHEMA_DRIFT marker — asset will raise on this, triggering failure_sensor
            print(
                f"  [!] SCHEMA_DRIFT: new table '{t}' detected. "
                f"Run bootstrap_serving_views.py when Metabase can be stopped briefly."
            )
        # Note: disappeared tables (known - current) are benign — bootstrap drops stale views

    save_known_tables(current_tables, current_schemas)

    print(
        f"Refresh done: tables={len(current_tables)} "
        f"keep={ROLLING_KEEP_VERSIONS} deleted={total_deleted} skipped={total_skipped}"
    )


if __name__ == "__main__":
    refresh_rolling()
