"""Publish a stable current-file contract for the local Rill project.

Copies the latest rolling Parquet snapshot for a curated table allowlist from:
  <DBT_EXPORT_PATH>/rolling/<table>/*.parquet
to:
  <RILL_EXPORT_ROOT>/<table>.parquet

This gives the Rill project a simple, stable input contract while dbt continues
to own the rolling snapshot lifecycle.
"""
from __future__ import annotations

import glob
import json
import os
import shutil
from datetime import datetime, timezone

DATA_LAKE_ROOT = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
DBT_EXPORT_PATH = os.environ.get(
    "DBT_EXPORT_PATH",
    os.path.join(DATA_LAKE_ROOT, "export", "marts"),
)
ROLLING_DIR = os.path.join(DBT_EXPORT_PATH, "rolling")
RILL_EXPORT_ROOT = os.environ.get(
    "RILL_EXPORT_ROOT",
    os.path.join(DATA_LAKE_ROOT, "export", "rill", "current"),
)

DEFAULT_TABLES = [
    "fact_orders",
    "fact_sales",
    "fact_marketing_spend",
    "fact_targets",
    "dim_channels",
    "dim_branch_location",
    "dim_geography",
    "dim_staff",
    "dim_products",
    "dim_order_status",
    "dim_customers",
]


def _table_allowlist() -> list[str]:
    raw = os.environ.get("RILL_PUBLISH_TABLES", "")
    if not raw.strip():
        return DEFAULT_TABLES
    return [table.strip() for table in raw.split(",") if table.strip()]


def _latest_snapshot(table_name: str) -> str | None:
    pattern = os.path.join(ROLLING_DIR, table_name, "*.parquet")
    matches = sorted(glob.glob(pattern))
    return matches[-1] if matches else None


def _atomic_copy(src: str, dst: str) -> None:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = f"{dst}.tmp"
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)


def publish() -> None:
    if not os.path.exists(ROLLING_DIR):
        raise FileNotFoundError(f"Rolling dir does not exist: {ROLLING_DIR}")

    os.makedirs(RILL_EXPORT_ROOT, exist_ok=True)

    manifest: dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rolling_dir": ROLLING_DIR,
        "export_root": RILL_EXPORT_ROOT,
        "tables": {},
    }

    published = 0
    missing = 0

    for table_name in _table_allowlist():
        latest = _latest_snapshot(table_name)
        if latest is None:
            print(f"  [!] WARNING: missing rolling snapshot for {table_name}")
            manifest["tables"][table_name] = {"status": "missing"}
            missing += 1
            continue

        destination = os.path.join(RILL_EXPORT_ROOT, f"{table_name}.parquet")
        _atomic_copy(latest, destination)
        manifest["tables"][table_name] = {
            "status": "published",
            "source": latest,
            "destination": destination,
            "source_basename": os.path.basename(latest),
        }
        print(f"  {table_name}: published {os.path.basename(latest)}")
        published += 1

    manifest_path = os.path.join(RILL_EXPORT_ROOT, "_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(
        f"Publish done: published={published} missing={missing} manifest={manifest_path}"
    )


if __name__ == "__main__":
    publish()
