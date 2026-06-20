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
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

DATA_LAKE_ROOT = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")

# ingest_method is a hive partition (read from the path), so it is NOT a file
# column — this matches the real DLT output layout hug_raw/{name}/ingest_method=*/.
_SENTINEL_ID = "_safety_placeholder"


def _placeholder_path(table: str) -> Path:
    return Path(DATA_LAKE_ROOT) / (
        f"hug_raw/{table}/ingest_method=placeholder/"
        f"hug_{table}_safety_placeholder.parquet"
    )


def _sentinel_frame(entity_type: str) -> pd.DataFrame:
    # Columns the src_hug_* models read (besides path-derived ingest_method).
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
        path = _placeholder_path(table)
        if path.exists():
            print(f"   [=] Already present: {path}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        _sentinel_frame(entity_type).to_parquet(path, index=False)
        print(f"   [+] Created: {path}")


if __name__ == "__main__":
    ensure_placeholders()
