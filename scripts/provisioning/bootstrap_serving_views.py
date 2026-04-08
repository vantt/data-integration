"""One-shot bootstrap of serving DuckDB views (requires exclusive DB lock).

Run manually when:
  - Initial deployment (olap.duckdb has no views yet)
  - Schema drift detected (refresh_rolling.py logged [!] SCHEMA_DRIFT)
  - Empty folders appeared and their views need dropping

IMPORTANT: Metabase must NOT be connected to olap.duckdb while this runs,
because Metabase's JDBC pool holds the file lock. Typical flow:

    docker compose stop metabase
    docker compose exec data_platform python scripts/provisioning/bootstrap_serving_views.py
    docker compose start metabase

After Metabase is configured with duckdb.read_only=true, it holds only a
shared lock and this script can be run without stopping Metabase (but may
briefly block reads during CREATE OR REPLACE).

See plans/260408-1611-fix-serving-db-hang-metabase-lock/plan.md Phase 2.
"""
from __future__ import annotations

import os
import re

import duckdb

# --- Paths ---
DATA_LAKE_ROOT = os.environ.get("DBT_DATA_LAKE_PATH", "/app/data_lake")
DBT_EXPORT_PATH = os.environ.get("DBT_EXPORT_PATH", os.path.join(DATA_LAKE_ROOT, "export", "marts"))
SERVING_DIR = os.path.join(DATA_LAKE_ROOT, "serving")
ROLLING_DIR = os.path.join(DBT_EXPORT_PATH, "rolling")
SERVING_DB_PATH = os.path.join(SERVING_DIR, "olap.duckdb")

# PORTABLE_ROOT is used inside SQL view definitions. MUST match the path
# DuckDB (inside the container) uses to read parquet files at query time.
PORTABLE_ROOT = DATA_LAKE_ROOT

_TABLE_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _list_subdirs(path: str) -> list[str]:
    return sorted(
        d for d in os.listdir(path)
        if os.path.isdir(os.path.join(path, d))
    )


def _make_smart_view_sql(table_name: str) -> str:
    """Build a self-refreshing view SQL.

    The view scans all parquet files in the folder, computes max(filename),
    and returns only rows from that latest file. No refresh needed when new
    files arrive — the view auto-picks the latest on each query.
    """
    portable_glob = f"{PORTABLE_ROOT}/export/marts/rolling/{table_name}/*.parquet"
    return f"""
        CREATE OR REPLACE VIEW {table_name} AS
        WITH source_files AS (
            SELECT * FROM read_parquet('{portable_glob}', filename=true, hive_partitioning=0)
        ),
        latest AS (
            SELECT max(filename) as max_fn FROM source_files
        )
        SELECT * EXCLUDE (filename)
        FROM source_files
        WHERE filename = (SELECT max_fn FROM latest)
    """


def bootstrap() -> None:
    print(f"Bootstrapping serving views in: {SERVING_DB_PATH}")

    os.makedirs(SERVING_DIR, exist_ok=True)

    if not os.path.exists(ROLLING_DIR):
        raise FileNotFoundError(f"Rolling dir does not exist: {ROLLING_DIR}")

    subdirs = _list_subdirs(ROLLING_DIR)
    if not subdirs:
        print("No table directories found. Nothing to bootstrap.")
        return

    # Require exclusive lock — if Metabase is connected, this will fail fast
    # with a clear error rather than hang.
    try:
        con = duckdb.connect(SERVING_DB_PATH)
    except Exception as e:
        raise RuntimeError(
            f"Could not acquire DuckDB lock on {SERVING_DB_PATH}: {e}\n"
            f"Is Metabase still connected? Stop it first or configure "
            f"duckdb.read_only=true in Metabase's JDBC params."
        ) from e

    try:
        con.sql("SET TimeZone = 'Asia/Ho_Chi_Minh'")

        created = 0
        dropped = 0
        skipped = 0

        for table_name in subdirs:
            if not _TABLE_NAME_RE.match(table_name):
                print(f"  [!] WARNING: skipping invalid table name: {table_name}")
                skipped += 1
                continue

            table_dir = os.path.join(ROLLING_DIR, table_name)
            has_data = any(
                f.endswith(".parquet")
                for f in os.listdir(table_dir)
                if os.path.isfile(os.path.join(table_dir, f))
            )

            if not has_data:
                # Empty folder — drop any stale view so Metabase doesn't show
                # a broken reference to missing files.
                try:
                    con.sql(f"DROP VIEW IF EXISTS {table_name}")
                    print(f"  {table_name}: DROPPED (empty folder)")
                    dropped += 1
                except Exception as e:
                    print(f"  [!] Failed to drop view {table_name}: {e}")
                continue

            try:
                con.sql(_make_smart_view_sql(table_name))
                print(f"  {table_name}: CREATED/REPLACED")
                created += 1
            except Exception as e:
                print(f"  [!] Failed to create view {table_name}: {e}")

        print(
            f"Bootstrap done: created={created} dropped={dropped} skipped={skipped}"
        )
    finally:
        con.close()


if __name__ == "__main__":
    bootstrap()
