"""MISA AMIS connector: sales-ledger and account-ledger downloads and file-drop ingestion."""
from datetime import timedelta

from dagster import AssetKey

from .assets import (
    misa_account_ledger_download_asset,
    misa_account_ledger_file_drop_asset,
    misa_sales_download_asset,
    misa_sales_file_drop_asset,
)

ASSETS = [
    misa_sales_download_asset,
    misa_account_ledger_download_asset,
    misa_sales_file_drop_asset,
    misa_account_ledger_file_drop_asset,
]

# Connector-specific asset checks beyond the SLA checks (none)
ASSET_CHECKS: list = []

# SLA key (ingestion_sla.yaml) -> asset definition the checks attach to
CHECK_ASSET_DEFS = {
    "misa_amis/misa_sales_file_drop_asset": misa_sales_file_drop_asset,
}

# Ingest assets pipeline_batch_nightly_job / pipeline_batch_fullrefresh_job run
NIGHTLY_ASSETS = [
    misa_sales_file_drop_asset,
    misa_account_ledger_file_drop_asset,
]

# Morning digest rows: (short_name, sla key, recon sla key | None)
DIGEST_ASSETS = [
    ("misa",      "misa_amis/misa_sales_file_drop_asset",           "recon/misa_daily"),
    ("misa_acct", "misa_amis/misa_account_ledger_file_drop_asset",  None),
]
# short_name -> (label, asset_type, unit)
DIGEST_DISPLAY: dict[str, tuple[str, str, str]] = {
    "misa":      ("MISA — file bán hàng",            "file_drop", "dòng"),
    "misa_acct": ("MISA — sổ chi tiết tài khoản",    "file_drop", "dòng"),
}

# Absolute max runtime per job; stuck_run_alerter terminates runs older than this
JOB_MAX_RUNTIME: dict[str, timedelta] = {
    "ingest_filedrop_misa_job": timedelta(minutes=45),
    "ingest_filedrop_misa_account_ledger_job": timedelta(minutes=45),
}

# dbt source_name -> {table name: asset key}; "*" matches any other table of the source.
# Two source tables under misa_raw, each mapped to its own file-drop asset; any future
# misa_raw table defaults to the sales asset.
DBT_SOURCE_KEYS = {
    "misa_raw": {
        "account_ledger": AssetKey(["misa_amis", "misa_account_ledger_file_drop_asset"]),
        "*": AssetKey(["misa_amis", "misa_sales_file_drop_asset"]),
    },
}
