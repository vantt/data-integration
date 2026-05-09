"""Build a self-contained standalone export DuckDB from olap.duckdb views.

Materializes every VIEW in `serving/olap.duckdb` (schema `main`) into BASE
TABLEs inside a new `sapo_export_<timestamp>.duckdb`.  The resulting file is
fully self-contained — no parquet paths are needed to query it.

Output dir: serving/standalone/
  - sapo_export_<YYYYMMDDHHMMSS>.duckdb   (timestamped snapshot)
  - sapo_export_latest.duckdb             (atomic alias, always points to newest)
GC: keeps last 3 timestamped files; deletes older ones with retry (Windows/Linux safe).

Usage:
    docker compose exec data_platform python scripts/provisioning/build_standalone_export.py

Lock safety:
    olap.duckdb is opened READ_ONLY → safe to run alongside Metabase.
    Output is written to a fresh .tmp file then atomically renamed → no
    partial state visible to readers.
"""
from __future__ import annotations

import os
import re
import shutil
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import duckdb

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_LAKE_ROOT = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
SERVING_DIR = os.path.join(DATA_LAKE_ROOT, "serving")
OLAP_DB = os.path.join(SERVING_DIR, "olap.duckdb")
OUT_DIR = os.path.join(SERVING_DIR, "standalone")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Allowlist: valid SQL identifier (mirrors bootstrap_serving_views.py:42)
_TABLE_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Keep last N timestamped snapshots (oldest are GC'd)
GC_KEEP = 3

# File prefix / suffix
_EXPORT_PREFIX = "sapo_export_"
_EXPORT_SUFFIX = ".duckdb"
_LATEST_FILENAME = f"{_EXPORT_PREFIX}latest{_EXPORT_SUFFIX}"


# ---------------------------------------------------------------------------
# GC helper
# ---------------------------------------------------------------------------

def _gc_old_exports(out_dir: str, keep: int = GC_KEEP) -> None:
    """Delete oldest timestamped export files, keeping the last `keep` files.

    Excludes the `_latest` alias.  Uses PermissionError/OSError retry pattern
    mirroring refresh_rolling.py:46-71 for Windows/Linux compat.
    """
    # Only match timestamped files (14-digit timestamp), not `_latest`
    candidates = [
        f for f in os.listdir(out_dir)
        if f.startswith(_EXPORT_PREFIX)
        and f.endswith(_EXPORT_SUFFIX)
        and f != _LATEST_FILENAME
        # timestamp portion: sapo_export_<14 digits>.duckdb
        and re.match(r"^sapo_export_\d{14}\.duckdb$", f)
    ]
    candidates.sort()  # lexical sort = chronological order (YYYYMMDDHHMMSS)

    to_delete = candidates[:-keep] if len(candidates) > keep else []
    for fname in to_delete:
        fpath = os.path.join(out_dir, fname)
        try:
            os.remove(fpath)
            print(f"  GC: deleted {fname}")
        except PermissionError:
            # Windows: file handle held by reader — skip silently this run
            print(f"  [!] WARNING: GC skipped {fname} (PermissionError)")
        except OSError:
            # Linux: advisory lock or in-flight read — retry once briefly
            time.sleep(0.5)
            try:
                os.remove(fpath)
                print(f"  GC: deleted {fname} (retry)")
            except Exception as e:
                print(f"  [!] WARNING: GC failed to delete {fname}: {e}")
        except Exception as e:
            print(f"  [!] ERROR: GC unexpected error deleting {fname}: {e}")


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def _sweep_stale_tmp(out_dir: str) -> None:
    """Delete any leftover .tmp files from prior crashed builds.

    Only sweeps OUR naming pattern (sapo_export_*.duckdb.tmp); leaves other
    files untouched. Idempotent — safe to call at every build start.
    """
    for fname in os.listdir(out_dir):
        if fname.startswith(_EXPORT_PREFIX) and fname.endswith(".tmp"):
            try:
                os.remove(os.path.join(out_dir, fname))
                print(f"  Swept stale tmp: {fname}")
            except Exception as e:
                print(f"  [!] WARNING: could not sweep {fname}: {e}")


def build_standalone_export() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    _sweep_stale_tmp(OUT_DIR)

    if not os.path.exists(OLAP_DB):
        raise FileNotFoundError(
            f"olap.duckdb not found at {OLAP_DB}. "
            "Ensure sapo_serving_db asset has run successfully first."
        )

    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    ts = datetime.now(tz).strftime("%Y%m%d%H%M%S")

    out_final = os.path.join(OUT_DIR, f"{_EXPORT_PREFIX}{ts}{_EXPORT_SUFFIX}")
    out_tmp = out_final + ".tmp"

    print(f"Building standalone export: {out_final}")
    print(f"  Source: {OLAP_DB}")

    # --- Open output (tmp) and attach source as read-only ---
    con = duckdb.connect(out_tmp)
    try:
        con.sql("SET TimeZone = 'Asia/Ho_Chi_Minh'")

        # Escape single quotes in path (should never occur in practice but be safe)
        olap_path_escaped = OLAP_DB.replace("'", "''")
        con.sql(f"ATTACH '{olap_path_escaped}' AS src (READ_ONLY)")

        # Enumerate views from source catalog.
        # DuckDB's information_schema is unified across attached DBs — filter by
        # table_catalog. The `src.information_schema.X` form does NOT work
        # (DuckDB parses 'information_schema' as a schema inside `src`, which
        # doesn't exist as a relation; verified via CatalogException 2026-05-08).
        rows = con.sql(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_catalog = 'src' AND table_schema = 'main' AND table_type = 'VIEW' "
            "ORDER BY table_name"
        ).fetchall()

        view_names: list[str] = []
        skipped = 0
        for (view_name,) in rows:
            if not _TABLE_NAME_RE.match(view_name):
                print(f"  [!] WARNING: skipping view with invalid name: {view_name!r}")
                skipped += 1
                continue
            view_names.append(view_name)

        if not view_names:
            print("  [!] WARNING: no views found in olap.duckdb — output will be empty")

        # Materialize each view as a base table
        row_counts: dict[str, int] = {}
        for view_name in view_names:
            try:
                con.sql(f"CREATE TABLE {view_name} AS SELECT * FROM src.{view_name}")
                count_result = con.sql(f"SELECT count(*) FROM {view_name}").fetchone()
                row_count = count_result[0] if count_result else 0
                row_counts[view_name] = row_count
                print(f"  {view_name}: {row_count:,} rows")
            except Exception as e:
                print(f"  [!] ERROR: failed to materialize view {view_name!r}: {e}")
                skipped += 1

        con.sql("DETACH src")
    finally:
        con.close()

    # --- Atomic promotion: tmp -> final ---
    os.replace(out_tmp, out_final)
    print(f"  Promoted tmp -> {os.path.basename(out_final)}")

    # --- Atomic refresh of _latest alias via copy + replace ---
    latest_path = os.path.join(OUT_DIR, _LATEST_FILENAME)
    latest_tmp = latest_path + ".tmp"
    shutil.copy2(out_final, latest_tmp)
    os.replace(latest_tmp, latest_path)
    print(f"  Updated {_LATEST_FILENAME}")

    # --- GC old timestamped files ---
    _gc_old_exports(OUT_DIR, keep=GC_KEEP)

    # --- Summary ---
    tables_materialized = len(row_counts)
    total_rows = sum(row_counts.values())
    print(
        f"\nStandalone build done: views={len(view_names)} "
        f"tables={tables_materialized} "
        f"total_rows={total_rows:,} "
        f"latest={_LATEST_FILENAME}"
    )


if __name__ == "__main__":
    build_standalone_export()
