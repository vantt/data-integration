import os

from dagster import AssetSelection, RunRequest, SkipReason, define_asset_job, schedule

from orchestration.assets import serving
from orchestration.job_support import FACT_ORDER_RETURNS, NIGHTLY_ONLY_ASSETS, SYNC_TAGS, after_serving_selection, has_active_run
from orchestration.sensors.file_drop_sensors import make_file_drop_sensor

from .assets import (
    misa_account_ledger_download_asset,
    misa_account_ledger_file_drop_asset,
    misa_sales_download_asset,
    misa_sales_file_drop_asset,
)

# Cadence-based ingest jobs — browser automation, no DuckDB writes, no SYNC_TAGS lock.
# Add new assets to the matching job; schedules below stay unchanged.
ingest_weekly_job = define_asset_job(
    name="ingest_weekly_job",
    selection=AssetSelection.assets(
        misa_sales_download_asset,
    ),
)

ingest_monthly_job = define_asset_job(
    name="ingest_monthly_job",
    selection=AssetSelection.assets(
        misa_account_ledger_download_asset,
    ),
)

# 2.7 MISA sales-ledger file-drop sync job
_misa_source = AssetSelection.assets(misa_sales_file_drop_asset)
ingest_filedrop_misa_job = define_asset_job(
    name="ingest_filedrop_misa_job",
    selection=(
        _misa_source
        | _misa_source.downstream()
        | FACT_ORDER_RETURNS
        | AssetSelection.assets(serving.build_serving_db)
        | after_serving_selection()
    ) - NIGHTLY_ONLY_ASSETS,
    tags=SYNC_TAGS,
)

# 2.8 MISA account-ledger file-drop sync job
# Ingests Sổ chi tiết các tài khoản (overhead 6421/6422) → dbt (account-ledger chain) → serving_db.
# No FACT_ORDER_RETURNS dependency: account-ledger is an independent overhead pool source.
_misa_account_ledger_source = AssetSelection.assets(misa_account_ledger_file_drop_asset)
ingest_filedrop_misa_account_ledger_job = define_asset_job(
    name="ingest_filedrop_misa_account_ledger_job",
    selection=(
        _misa_account_ledger_source
        | _misa_account_ledger_source.downstream()
        | AssetSelection.assets(serving.build_serving_db)
        | after_serving_selection()
    ) - NIGHTLY_ONLY_ASSETS,
    tags=SYNC_TAGS,
)


# Monday 07:00 ICT — runs all assets in ingest_weekly_job (currently: MISA sales ledger).
# 1st of month 07:00 ICT — runs all assets in ingest_monthly_job (currently: MISA account ledger).
# To add a new periodic ingest task: add its asset to the matching job above — no new schedule needed.
@schedule(
    job=ingest_weekly_job,
    cron_schedule="0 7 * * 1",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def ingest_weekly_schedule(context):
    active = has_active_run(context, "ingest_weekly_job")
    if active:
        return SkipReason(f"ingest_weekly: previous run still active ({active[:8]})")
    return RunRequest(run_key=None)


@schedule(
    job=ingest_monthly_job,
    cron_schedule="0 7 1 * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def ingest_monthly_schedule(context):
    active = has_active_run(context, "ingest_monthly_job")
    if active:
        return SkipReason(f"ingest_monthly: previous run still active ({active[:8]})")
    return RunRequest(run_key=None)


# Day 10, 07:00 ICT — re-pull of ingest_monthly_job (currently: MISA account ledger).
# MISA's books for a month typically don't close/finalize until day ~5-10 of the
# following month, so the day-1 pull above often misses late bookkeeping entries.
# The downloader defaults to "last month" and the ingest mechanism fully replaces
# (UPSERT-by year/month) the target month's partition on each run, so re-running
# on day 10 is safe/idempotent — no double-counting, just fresher data.
@schedule(
    job=ingest_monthly_job,
    cron_schedule="0 7 10 * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def ingest_monthly_repull_schedule(context):
    active = has_active_run(context, "ingest_monthly_job")
    if active:
        return SkipReason(f"ingest_monthly_repull: previous run still active ({active[:8]})")
    return RunRequest(run_key=None)


# Env var if set, otherwise Docker default (/app/var/input_source/).
# Local dev: set MISA_INPUT_DIR / MISA_ACCOUNT_LEDGER_INPUT_DIR in .env.local.
ingest_filedrop_misa_sensor = make_file_drop_sensor(
    name="ingest_filedrop_misa_sensor",
    job_name="ingest_filedrop_misa_job",
    input_dir=os.environ.get("MISA_INPUT_DIR", "/app/var/input_source/misa-sales-ledger"),
    asset_op_name="misa_amis__misa_sales_file_drop_asset",
    run_key_prefix="misa",
    source_label="MISA",
    drop_dir_hint="misa-sales-ledger",
)

ingest_filedrop_misa_account_ledger_sensor = make_file_drop_sensor(
    name="ingest_filedrop_misa_account_ledger_sensor",
    job_name="ingest_filedrop_misa_account_ledger_job",
    input_dir=os.environ.get("MISA_ACCOUNT_LEDGER_INPUT_DIR", "/app/var/input_source/misa-account-ledger"),
    asset_op_name="misa_amis__misa_account_ledger_file_drop_asset",
    run_key_prefix="misa-account-ledger",
    source_label="MISA account-ledger",
    drop_dir_hint="misa-account-ledger",
)

JOBS = [
    ingest_weekly_job,
    ingest_monthly_job,
    ingest_filedrop_misa_job,
    ingest_filedrop_misa_account_ledger_job,
]
SCHEDULES = [ingest_weekly_schedule, ingest_monthly_schedule, ingest_monthly_repull_schedule]
SENSORS = [ingest_filedrop_misa_sensor, ingest_filedrop_misa_account_ledger_sensor]
