"""One-shot bootstrap of serving DuckDB views.

Run manually when:
  - Initial deployment (olap.duckdb has no views yet)
  - Schema drift detected (refresh_rolling.py logged [!] SCHEMA_DRIFT)
  - Empty folders appeared and their views need dropping

METABASE LOCK (re-verified 2026-06-10 — STOP METABASE FIRST):

Metabase MUST be stopped before running this script. Even with duckdb
`read_only=true` in its JDBC URL, Metabase's open read connection holds a
DuckDB lock that BLOCKS this writer ("Conflicting lock is held in PID 0").
Sequence:

    docker compose stop metabase
    docker compose exec -T data_platform python scripts/provisioning/bootstrap_serving_views.py
    docker compose start metabase

(History: a 2026-04-08 note claimed read_only readers coexist with the writer
so no stop was needed. That no longer holds with the current DuckDB version —
the read connection now takes a shared lock that conflicts with the exclusive
write lock; observed empirically 2026-06-10. See lessons-learned.md L18 and
plans/260408-1611-fix-serving-db-hang-metabase-lock/plan.md Phase 2.)
"""
from __future__ import annotations

import os
import re

import duckdb

# --- Paths ---
DATA_LAKE_ROOT = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
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


def _build_rolling_view_sql(table_name: str) -> str:
    """Build SQL for a Rolling Self-Refresh View.

    Mechanism:
      - "Rolling":      multiple parquet versions coexist in rolling/<table>/,
                        older files are GC'd after each pipeline run
      - "Self-Refresh": view scans the folder glob and picks max(filename)
                        at query time — no manual CREATE OR REPLACE needed
                        when new parquet files arrive
      - Zero-downtime:  Metabase queries continue to work during GC because
                        the view always resolves to the latest surviving file
    """
    portable_glob = f"{PORTABLE_ROOT}/export/marts/rolling/{table_name}/*.parquet"
    return f"""
        CREATE OR REPLACE VIEW {table_name} AS
        WITH source_files AS (
            SELECT * FROM read_parquet(
                '{portable_glob}', filename=true, hive_partitioning=0, union_by_name=true
            )
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

    # Open RW. Metabase (read_only=true) does not lock the file, so this
    # should always succeed unless another writer (dbt build) is active.
    try:
        con = duckdb.connect(SERVING_DB_PATH)
    except Exception as e:
        raise RuntimeError(
            f"Could not open {SERVING_DB_PATH}: {e}\n"
            f"If Metabase is configured with duckdb.read_only=true, it should "
            f"not block this. Check for another writer process holding the file."
        ) from e

    try:
        con.sql("SET TimeZone = 'Asia/Ho_Chi_Minh'")

        # Schema alias for dbt-metabase lineage: dbt manifest uses main_marts
        # schema (target=main + dbt schema=marts → main_marts), but Metabase
        # sees flat main.{table}. This alias schema lets dbt-metabase match
        # main_marts.fact_orders (manifest) → main_marts.fact_orders (Metabase).
        # Existing main.{table} views are untouched — no Metabase SQL breaks.
        con.execute("CREATE SCHEMA IF NOT EXISTS main_marts")

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
                    con.execute(f"DROP VIEW IF EXISTS main_marts.{table_name}")
                    print(f"  {table_name}: DROPPED (empty folder)")
                    dropped += 1
                except Exception as e:
                    print(f"  [!] Failed to drop view {table_name}: {e}")
                continue

            try:
                con.sql(_build_rolling_view_sql(table_name))
                print(f"  {table_name}: CREATED/REPLACED")
                con.execute(f"CREATE OR REPLACE VIEW main_marts.{table_name} AS SELECT * FROM main.{table_name}")
                print(f"  + main_marts alias: {table_name}")
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
