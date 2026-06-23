"""Ensure the Hug raw source globs never match zero parquet.

DuckDB `read_parquet(glob)` raises "No files found" when the glob matches nothing,
which reds the whole dbt run (src_hug_* → stg_hug_* → mart_hug_optin, and because
they share the project dbt build, the Sapo realtime/incremental jobs fail too).

Until the hug_webhook_consumer DLT pipeline has landed real data, both
hug_raw/scan/ and hug_raw/optin_event/ are empty. A sentinel parquet with
entity_id='_safety_placeholder' keeps each glob non-empty; the src_hug_* models
filter the sentinel out so it never reaches staging/marts.

Idempotent — creates each file only if missing. Safe on every container start.
Mirrors scripts/ensure_shopee_safety_placeholder.py.

IMPORTANT: The placeholder path must have the same Hive partition depth as the real
DLT output: ingest_method=*/year=*/month=*. DuckDB's hive_partitioning=1 auto-detects
partition keys from path depth and raises a Binder Error when files in the same glob
have different partition key sets (e.g. one file has only ingest_method= while others
have ingest_method=/year=/month=).
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

DATA_LAKE_ROOT = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")

# ingest_method, year, month are all hive partitions (read from path), NOT file columns.
# Path depth must match the real DLT output: ingest_method=*/year=*/month=*.
_SENTINEL_ID = "_safety_placeholder"


def _placeholder_path(table: str) -> Path:
    # year=1970/month=1 matches the 3-level partition depth of real webhook output:
    # ingest_method=webhook/year=YYYY/month=M/
    return Path(DATA_LAKE_ROOT) / (
        f"hug_raw/{table}/ingest_method=placeholder/year=1970/month=1/"
        f"hug_{table}_safety_placeholder.parquet"
    )


def _old_placeholder_path(table: str) -> Path:
    """Pre-fix location (single-level partition). Removed to prevent Binder Error."""
    return Path(DATA_LAKE_ROOT) / (
        f"hug_raw/{table}/ingest_method=placeholder/"
        f"hug_{table}_safety_placeholder.parquet"
    )


def _sentinel_frame(entity_type: str) -> pd.DataFrame:
    # Columns the src_hug_* models read (besides path-derived ingest_method/year/month).
    # payload is a JSON string so json_extract_string(...) yields NULLs cleanly.
    return pd.DataFrame({
        "entity_id":       [_SENTINEL_ID],
        "entity_type":     [entity_type],
        "event_timestamp": ["1970-01-01T00:00:00+00:00"],
        "_dlt_load_id":    ["0"],
        "payload":         ["{}"],
    })


def ensure_placeholders() -> None:
    print("-> [Auto-Setup] checking Hug raw safety placeholders...")
    for table, entity_type in (("scan", "scan"), ("optin_event", "optin")):
        # Remove stale single-level placeholder that causes Binder Error when real
        # data (3-level: ingest_method/year/month) coexists in the same glob.
        old_path = _old_placeholder_path(table)
        if old_path.exists():
            old_path.unlink()
            print(f"   [-] Removed stale shallow placeholder: {old_path}")

        path = _placeholder_path(table)
        if path.exists():
            print(f"   [=] Already present: {path}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        _sentinel_frame(entity_type).to_parquet(path, index=False)
        print(f"   [+] Created: {path}")


if __name__ == "__main__":
    ensure_placeholders()
