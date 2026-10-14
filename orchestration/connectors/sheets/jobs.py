from dagster import AssetSelection, RunRequest, SkipReason, define_asset_job, schedule

from orchestration.assets import rill, serving
from orchestration.packs.crm import crm_sync
from orchestration.job_support import SYNC_TAGS, has_active_run
from orchestration.sensors.sheets_modified_sensor import ingest_sheets_modified_sensor

from .assets import (
    budget_sheet_sync_asset,
    budget_suggestion_writeback_asset,
    sheets_marketing_spend_asset,
    sheets_overhead_classification_asset,
    sheets_targets_asset,
    sheets_team_config_asset,
    sheets_us_shipment_prices_asset,
)

# 2.5 Sheets Job (Manual or sensor-triggered on sheet edit)
# Ingests Google Sheets (Targets, Marketing Spend) AND cascades downstream:
# dbt models that depend on the raw sheet tables + serving_db refresh.
#
# Why downstream is included: sheets are rarely edited (manual input by analysts)
# and users expect the dashboard to reflect the change without waiting for
# the 04:00 nightly. `AssetSelection.downstream()` limits the cascade to
# marts that actually depend on these sources (fact_targets, fact_marketing_spend,
# and anything derived) — NOT the whole dbt graph.
_sheets_sources = (
    AssetSelection.assets(sheets_targets_asset)
    | AssetSelection.assets(sheets_marketing_spend_asset)
    | AssetSelection.assets(sheets_team_config_asset)
    | AssetSelection.assets(sheets_us_shipment_prices_asset)
    | AssetSelection.assets(sheets_overhead_classification_asset)
)
ingest_sheets_sync_job = define_asset_job(
    name="ingest_sheets_sync_job",
    selection=(
        _sheets_sources
        | _sheets_sources.downstream()
        | AssetSelection.assets(serving.build_serving_db)
        | AssetSelection.assets(rill.build_rill_publish)
        | AssetSelection.assets(crm_sync.crm_cache_refresh)
    ),
    tags=SYNC_TAGS,
)

# Daily budget sheet sync — writes dbt seeds directly (not the gsheet_raw data lake),
# scheduled 30 min before the nightly dbt build so seeds are fresh when `dbt build` runs.
budget_sheet_sync_job = define_asset_job(
    name="budget_sheet_sync_job",
    selection=AssetSelection.assets(
        budget_sheet_sync_asset,
    ),
)

# Monthly budget suggestion write-back — computes + writes "Gợi Ý" cells for next
# month only, never "Budget". Requires GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH (shared GCP
# service account, Editor access on this sheet) — fails loud at RUNTIME, not at code-load,
# if unset. See plans/260707-1201-google-sheets-service-account/phase-01-service-account-setup.md.
budget_suggestion_writeback_job = define_asset_job(
    name="budget_suggestion_writeback_job",
    selection=AssetSelection.assets(
        budget_suggestion_writeback_asset,
    ),
)


# 02:30 ICT daily — 30 min before the nightly dbt build (03:00 ICT) so fresh budget
# seeds are in place before `dbt build` runs.
@schedule(
    job=budget_sheet_sync_job,
    cron_schedule="30 2 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def budget_sheet_sync_schedule(context):
    active = has_active_run(context, "budget_sheet_sync_job")
    if active:
        return SkipReason(f"budget_sheet_sync: previous run still active ({active[:8]})")
    return RunRequest(run_key=None)


# 1st of month, 08:00 ICT — after ingest_monthly_job (07:00 ICT) lands fresh MISA account-ledger
# actuals, so recurring/reserve suggestions reflect the latest month's real numbers. Will raise
# loud (RuntimeError, caught by health_alert_failure_sensor) every tick until a human completes
# the GCP service-account setup described in gsheet_budget_sync.py — expected until then.
@schedule(
    job=budget_suggestion_writeback_job,
    cron_schedule="0 8 1 * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def budget_suggestion_writeback_schedule(context):
    active = has_active_run(context, "budget_suggestion_writeback_job")
    if active:
        return SkipReason(f"budget_suggestion_writeback: previous run still active ({active[:8]})")
    return RunRequest(run_key=None)


JOBS = [ingest_sheets_sync_job, budget_sheet_sync_job, budget_suggestion_writeback_job]
SCHEDULES = [budget_sheet_sync_schedule, budget_suggestion_writeback_schedule]
# Stays in orchestration/sensors/: its default sheet URLs are tenant values.
SENSORS = [ingest_sheets_modified_sensor]
