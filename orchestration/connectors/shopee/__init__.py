"""Shopee connector: income Excel file-drop ingestion."""
from datetime import timedelta

from dagster import AssetKey

from .assets import shopee_income_file_drop_asset

ASSETS = [shopee_income_file_drop_asset]

# SLA key (ingestion_sla.yaml) -> asset definition (or key) the checks attach to.
# shopee_income_file_drop_asset is a @multi_asset and @asset_check(asset=) requires a
# single key, so order_revenue is the anchor; the check logic still queries the health DB
# through the "shopee/shopee_income_file_drop_asset" string key.
CHECK_ASSET_DEFS = {
    "shopee/shopee_income_file_drop_asset": AssetKey(["shopee", "order_revenue"]),
}

# Ingest assets pipeline_batch_nightly_job / pipeline_batch_fullrefresh_job run
NIGHTLY_ASSETS = [shopee_income_file_drop_asset]

# Morning digest rows: (short_name, sla key, recon sla key | None)
DIGEST_ASSETS = [
    ("shopee", "shopee/shopee_income_file_drop_asset", "recon/shopee_daily"),
]
# short_name -> (label, asset_type, unit)
DIGEST_DISPLAY: dict[str, tuple[str, str, str]] = {
    "shopee": ("Shopee — file thu nhập", "file_drop", "dòng"),
}

# Absolute max runtime per job; stuck_run_alerter terminates runs older than this
JOB_MAX_RUNTIME: dict[str, timedelta] = {
    "ingest_filedrop_shopee_job": timedelta(minutes=45),
}

# dbt source_name -> {table name: asset key}; "*" matches any other table of the source.
# One key per table (4 outputs of the @multi_asset) satisfies dagster-dbt's uniqueness rule.
DBT_SOURCE_KEYS = {
    "shopee_raw": {
        "order_revenue": AssetKey(["shopee", "order_revenue"]),
        "order_revenue_items": AssetKey(["shopee", "order_revenue_items"]),
        "order_service_fees": AssetKey(["shopee", "order_service_fees"]),
        "order_adjustments": AssetKey(["shopee", "order_adjustments"]),
    },
}
