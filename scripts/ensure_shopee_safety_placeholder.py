"""Ensure the Shopee `order_adjustments` source glob never matches zero parquet.

DuckDB `read_parquet(glob)` raises "No files found" when the glob matches nothing,
which cascades: src_ fails → int_ fails → fees fails → fact_order_economics fails.

This happens in fresh environments and when the first ingested file contains no
adjustment detail rows. A sentinel parquet with `order_code = '_safety_placeholder'`
keeps the glob non-empty; src_ filters the sentinel out so it never reaches int_.

Idempotent — creates the file only if missing. Safe to run on every container start.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd


DATA_LAKE_ROOT = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
PLACEHOLDER_PATH = Path(DATA_LAKE_ROOT) / (
    "shopee_raw/order_adjustments/ingest_method=file_drop/year=1970/month=1/"
    "shopee_income_safety_placeholder.parquet"
)


def ensure_placeholder() -> None:
    print("-> [Auto-Setup] checking Shopee order_adjustments safety placeholder...")
    if PLACEHOLDER_PATH.exists():
        print(f"   [=] Already present: {PLACEHOLDER_PATH}")
        return

    PLACEHOLDER_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Schema must match real adjustment parquets (9 cols; year/month are hive path).
    df = pd.DataFrame({
        "adjustment_completed_at": [date(1970, 1, 1)],
        "adjustment_type":         ["_safety_placeholder"],
        "adjustment_reason":       pd.array([pd.NA], dtype="string"),
        "adjustment_amount":       pd.array([0], dtype="Int64"),
        "order_code":              ["_safety_placeholder"],
        "payout_released_at":      [date(1970, 1, 1)],
        "ingest_method":           ["file_drop"],
        "source_file":             ["_safety_placeholder"],
        "ingested_at": pd.to_datetime(
            ["1970-01-01 00:00:00+00:00"], utc=True
        ).astype("datetime64[us, UTC]"),
    })
    df.to_parquet(PLACEHOLDER_PATH, index=False)
    print(f"   [+] Created: {PLACEHOLDER_PATH}")


if __name__ == "__main__":
    ensure_placeholder()
