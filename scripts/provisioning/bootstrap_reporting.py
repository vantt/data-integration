"""Bootstrap reporting layers (Metabase + Rill) if not yet provisioned.

Designed to run once at data_platform container startup, before Dagster.
Idempotent — safe to re-run; skips layers that are already provisioned.

Requires rolling parquet snapshots to exist (i.e., at least one pipeline
run must have completed dbt export). If rolling dir is empty, both layers
are skipped with a warning — the first Dagster pipeline run will provision
them via the normal asset chain.
"""
from __future__ import annotations

import glob
import os

DATA_LAKE_ROOT = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
DBT_EXPORT_PATH = os.environ.get(
    "DBT_EXPORT_PATH",
    os.path.join(DATA_LAKE_ROOT, "export", "marts"),
)
ROLLING_DIR = os.path.join(DBT_EXPORT_PATH, "rolling")

# Metabase: olap.duckdb must have at least one view
SERVING_DB_PATH = os.path.join(DATA_LAKE_ROOT, "serving", "olap.duckdb")

# Rill: export/rill/current/ must have parquet files
RILL_EXPORT_ROOT = os.environ.get(
    "RILL_EXPORT_ROOT",
    os.path.join(DATA_LAKE_ROOT, "export", "rill", "current"),
)


def _has_rolling_data() -> bool:
    """Check if any rolling parquet snapshots exist."""
    if not os.path.isdir(ROLLING_DIR):
        return False
    for subdir in os.listdir(ROLLING_DIR):
        path = os.path.join(ROLLING_DIR, subdir)
        if os.path.isdir(path) and glob.glob(os.path.join(path, "*.parquet")):
            return True
    return False


def _metabase_needs_bootstrap() -> bool:
    """True if olap.duckdb is missing or has no views."""
    if not os.path.exists(SERVING_DB_PATH):
        return True
    try:
        import duckdb
        con = duckdb.connect(SERVING_DB_PATH, read_only=True)
        try:
            views = con.sql("SELECT count(*) FROM information_schema.tables WHERE table_type='VIEW'").fetchone()
            return views is None or views[0] == 0
        finally:
            con.close()
    except Exception:
        return True


def _rill_needs_publish() -> bool:
    """True if Rill export dir is missing or empty."""
    if not os.path.isdir(RILL_EXPORT_ROOT):
        return True
    return not any(f.endswith(".parquet") for f in os.listdir(RILL_EXPORT_ROOT))


def bootstrap() -> None:
    print("[bootstrap_reporting] Checking reporting layers...")

    if not _has_rolling_data():
        print("[bootstrap_reporting] No rolling parquet data yet — skipping. First pipeline run will provision.")
        return

    # --- Metabase ---
    if _metabase_needs_bootstrap():
        print("[bootstrap_reporting] Metabase: olap.duckdb needs bootstrap — running...")
        from scripts.provisioning.bootstrap_serving_views import bootstrap as bs_metabase
        bs_metabase()
        print("[bootstrap_reporting] Metabase: done.")
    else:
        print("[bootstrap_reporting] Metabase: already provisioned.")

    # --- Rill ---
    if _rill_needs_publish():
        print("[bootstrap_reporting] Rill: export dir empty — publishing...")
        from scripts.provisioning.publish_rill_assets import publish as pub_rill
        pub_rill()
        print("[bootstrap_reporting] Rill: done.")
    else:
        print("[bootstrap_reporting] Rill: already provisioned.")

    print("[bootstrap_reporting] All reporting layers checked.")


if __name__ == "__main__":
    bootstrap()
