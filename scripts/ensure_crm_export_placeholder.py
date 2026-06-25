"""Ensure CRM export parquet sources are never empty on first deploy.

DuckDB read_parquet() raises "No files found" / "File not found" when the
source path doesn't exist, which reds every dbt model that references
stg_crm__* staging views (including mart_customer_action_queue).

Creates minimal empty parquets so dbt models compile and return 0 rows
rather than failing. The CRM writeback Dagster assets overwrite these
with real data on first nightly run.

Idempotent — skips files that already exist (real data or prior placeholder).
Safe on every container start.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

DATA_LAKE_ROOT = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
CRM_EXPORT = Path(DATA_LAKE_ROOT) / "crm_export"


# Minimal column schemas matching the CRM export queries
_SNAPSHOT_SCHEMAS: dict[str, dict[str, list]] = {
    "crm_last_contact": {
        "party_id":             [],
        "customer_id":          [],
        "last_contacted_at":    [],
        "last_contact_result":  [],
        "last_contact_channel": [],
        "updated_at":           [],
    },
    "crm_hug_voucher": {
        "code":        [],
        "customer_id": [],
        "token":       [],
        "campaign_id": [],
        "min_order":   [],
        "issued_at":   [],
        "redeemed_at": [],
        "order_code":  [],
    },
    "crm_campaign_target": {
        "campaign_id":           [],
        "party_id":              [],
        "customer_id":           [],
        "status":                [],
        "assigned_user_id":      [],
        "last_touch_at":         [],
        "converted_order_code":  [],
        "converted_revenue_vnd": [],
        "converted_at":          [],
    },
}

# Incremental table: date-partitioned glob — needs at least one parquet in any date= dir
_INCREMENTAL_SCHEMA = {
    "activity_id":        [],
    "party_id":           [],
    "customer_id":        [],
    "activity_type":      [],
    "direction":          [],
    "channel":            [],
    "outcome":            [],
    "contact_outcome":    [],
    "callback_at":        [],
    "contact_duration_s": [],
    "task_id":            [],
    "related_order_code": [],
    "staff_user_id":      [],
    "occurred_at":        [],
    "created_at":         [],
}


def ensure_placeholders() -> None:
    print("-> [Auto-Setup] checking CRM export safety placeholders...")

    # Snapshot tables: single parquet per table
    for table, schema in _SNAPSHOT_SCHEMAS.items():
        path = CRM_EXPORT / f"{table}.parquet"
        if path.exists():
            print(f"   [=] Already present: {path}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(schema).to_parquet(path, index=False)
        print(f"   [+] Created placeholder: {path}")

    # Incremental table: needs a file matching the date=*/ glob
    inc_path = CRM_EXPORT / "crm_activity_log" / "date=19700101" / "placeholder.parquet"
    if inc_path.exists():
        print(f"   [=] Already present: {inc_path}")
    else:
        inc_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(_INCREMENTAL_SCHEMA).to_parquet(inc_path, index=False)
        print(f"   [+] Created placeholder: {inc_path}")


if __name__ == "__main__":
    ensure_placeholders()
