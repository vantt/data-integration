"""Google Sheets connector: analyst-maintained inputs (targets, marketing spend, team config, ...)."""
from datetime import timedelta

from dagster import AssetKey

from .assets import (
    budget_sheet_sync_asset,
    budget_suggestion_writeback_asset,
    sheets_marketing_spend_asset,
    sheets_overhead_classification_asset,
    sheets_targets_asset,
    sheets_team_config_asset,
    sheets_us_shipment_prices_asset,
)

ASSETS = [
    sheets_targets_asset,
    sheets_marketing_spend_asset,
    sheets_team_config_asset,
    sheets_us_shipment_prices_asset,
    sheets_overhead_classification_asset,
    budget_sheet_sync_asset,
    budget_suggestion_writeback_asset,
]

# Connector-specific asset checks beyond the SLA checks (none)
ASSET_CHECKS: list = []

# SLA key (ingestion_sla.yaml) -> asset definition the checks attach to
CHECK_ASSET_DEFS = {
    "sheets/sheets_targets_asset": sheets_targets_asset,
    "sheets/sheets_marketing_spend_asset": sheets_marketing_spend_asset,
    "sheets/sheets_team_config_asset": sheets_team_config_asset,
}

# Ingest assets pipeline_batch_nightly_job / pipeline_batch_fullrefresh_job run
NIGHTLY_ASSETS = [
    sheets_targets_asset,
    sheets_marketing_spend_asset,
    sheets_team_config_asset,
    sheets_us_shipment_prices_asset,
    sheets_overhead_classification_asset,
]

# Morning digest rows: (short_name, sla key, recon sla key | None)
DIGEST_ASSETS = [
    ("sheet_targets",   "sheets/sheets_targets_asset",                  None),
    ("sheet_spend",     "sheets/sheets_marketing_spend_asset",          None),
    ("sheet_team",      "sheets/sheets_team_config_asset",              None),
    ("sheet_us_prices", "sheets/sheets_us_shipment_prices_asset",       None),
    ("sheet_overhead",  "sheets/sheets_overhead_classification_asset",  None),
]
# short_name -> (label, asset_type, unit)
DIGEST_DISPLAY: dict[str, tuple[str, str, str]] = {
    "sheet_targets":   ("Google Sheet — Mục tiêu",                 "file_drop", "dòng"),
    "sheet_spend":     ("Google Sheet — Chi marketing",            "file_drop", "dòng"),
    "sheet_team":      ("Google Sheet — Cấu hình nhóm",            "file_drop", "dòng"),
    "sheet_us_prices": ("Google Sheet — Giá vận chuyển US",        "file_drop", "dòng"),
    "sheet_overhead":  ("Google Sheet — Phân loại overhead",       "file_drop", "dòng"),
}

# Absolute max runtime per job; stuck_run_alerter terminates runs older than this
JOB_MAX_RUNTIME: dict[str, timedelta] = {
    "ingest_sheets_sync_job": timedelta(minutes=45),
}

# dbt source_name -> {table name: asset key}; "*" matches any other table of the source.
# teams_raw and team_members_raw both come from sheets_team_config_asset but cannot share
# its key — their dependency is omitted by design.
DBT_SOURCE_KEYS = {
    "gsheet_raw": {
        "targets_raw": AssetKey(["sheets", "sheets_targets_asset"]),
        "marketing_spend_raw": AssetKey(["sheets", "sheets_marketing_spend_asset"]),
    },
}
