import sys
import os
import shutil

# Add project root to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ingestion", "src"))

from datetime import datetime, timezone, timedelta

from dagster import (
    Definitions,
    load_assets_from_modules,
    ScheduleDefinition,
    define_asset_job,
    AssetSelection,
    AssetKey,
    schedule,
    RunRequest,
    SkipReason,
    RunsFilter,
    DagsterRunStatus,
    in_process_executor,
    run_status_sensor,
    RunStatusSensorContext,
)
from orchestration.asset_checks import ALL_CHECKS
from orchestration.asset_checks.reconciliation_checks import RECON_CHECKS
from orchestration.asset_checks.kpi_closure_checks import KPI_CHECKS
from dagster_dbt import DbtCliResource
from orchestration.assets import sapo_assets, sheets_assets, shopee_assets, misa_amis_assets, dbt, serving, rill, reconciliation, kpi_closure
from orchestration.ops.system_backup import maintain_backup_platform_job
from orchestration.ops.morning_digest import health_report_digest_job
from orchestration.ops.purge_runs import maintain_purge_runs_job
from orchestration.sensors.failure_alerting import health_alert_failure_sensor
from orchestration.sensors.sheets_modified_sensor import ingest_sheets_modified_sensor
from orchestration.sensors.stuck_run_alerter import health_alert_stuckrun_sensor
from orchestration.sensors.file_drop_sensors import ingest_filedrop_shopee_sensor, ingest_filedrop_misa_sensor, ingest_filedrop_misa_account_ledger_sensor
from orchestration.sensors.concurrency_pool_janitor import health_concurrency_pool_janitor
from orchestration.sensors.health_db_watchdog_sensor import health_db_watchdog_sensor

# Load all assets — directory setup runs once at container startup
# (docker-compose.yml command: `python scripts/ensure_dbt_directories.py && ...`).
# Don't call it from here: definitions.py is re-imported on every gRPC code
# server spawn (e.g. each `dagster job launch`), which would add noise.
all_assets = load_assets_from_modules([sapo_assets, sheets_assets, shopee_assets, misa_amis_assets, dbt, serving, rill, reconciliation, kpi_closure])

# ------------------------------------------------------------------------------
# ASSET SELECTIONS
# ------------------------------------------------------------------------------

# Select DBT models by tag
# Select DBT models by tag
dbt_otp_selection = AssetSelection.assets(dbt.sapo_dbt_assets)
# Note: Since dbt assets are loaded as a single "sapo_dbt_assets" group by default 
# unless we break them down, we'll rely on the job execution to run specific models via args 
# if we want granulairty. However, `dbt_assets` usually exposes all models as individual assets 
# if the manifest is parsed. 
#
# For now, we will select `sapo_dbt_assets` and rely on dbt to figure out dependencies 
# or use `build --select tag:otp` if we were using raw CLI. 
# But Dagster's `dbt_assets` allows standard asset selection.
#
# Let's assume `sapo_dbt_assets` expands to many assets.
# We want to select based on tags or simple downstream dependencies.

# Helper: All generic dbt assets
all_dbt_assets = AssetSelection.assets(dbt.sapo_dbt_assets)

# ------------------------------------------------------------------------------
# JOBS
# ------------------------------------------------------------------------------

# All sync jobs share the 'dbt_rw' concurrency group (limit 1 in dagster.yaml) —
# this is the single-source-of-truth mutex for DuckDB writers. QueuedRunCoordinator
# enforces it at the instance level, replacing the old manual SkipReason logic.
SYNC_TAGS = {"concurrency_group": "dbt_rw"}

# 1. Realtime Job (Webhook)
ingest_sapo_realtime_job = define_asset_job(
    name="ingest_sapo_realtime_job",
    selection=AssetSelection.assets(sapo_assets.sapo_webhook_consumer_asset) | all_dbt_assets | AssetSelection.assets(serving.sapo_serving_db) | AssetSelection.assets(rill.sapo_rill_publish),
    tags=SYNC_TAGS,
)

# 2. Incremental Job (History Log)
ingest_sapo_incremental_job = define_asset_job(
    name="ingest_sapo_incremental_job",
    selection=AssetSelection.assets(sapo_assets.sapo_history_log_asset) | all_dbt_assets | AssetSelection.assets(serving.sapo_serving_db) | AssetSelection.assets(rill.sapo_rill_publish),
    tags={**SYNC_TAGS, "dagster/max_retries": "0"},
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
    AssetSelection.assets(sheets_assets.sheets_targets_asset)
    | AssetSelection.assets(sheets_assets.sheets_marketing_spend_asset)
    | AssetSelection.assets(sheets_assets.sheets_team_config_asset)
    | AssetSelection.assets(sheets_assets.sheets_us_shipment_prices_asset)
)
ingest_sheets_sync_job = define_asset_job(
    name="ingest_sheets_sync_job",
    selection=(
        _sheets_sources
        | _sheets_sources.downstream()
        | AssetSelection.assets(serving.sapo_serving_db)
        | AssetSelection.assets(rill.sapo_rill_publish)
    ),
    tags=SYNC_TAGS,
)

# 2.6 Shopee file-drop sync job
# Ingests Shopee income Excel → dbt (shopee chain only) → serving_db.
# shopee_income_file_drop_asset is a @multi_asset with 4 outputs (one per table),
# so .downstream() resolves only shopee-dependent dbt models — not the full graph.
# fact_order_returns is added explicitly: it is not downstream of shopee_source, but
# fact_order_economics (which IS downstream) depends on it — without this, the first
# file-drop run on a fresh deploy fails because the parquet does not yet exist.
_shopee_source = AssetSelection.assets(shopee_assets.shopee_income_file_drop_asset)
_fact_order_returns = AssetSelection.assets(AssetKey(["marts", "fact_order_returns"]))
ingest_filedrop_shopee_job = define_asset_job(
    name="ingest_filedrop_shopee_job",
    selection=(
        _shopee_source
        | _shopee_source.downstream()
        | _fact_order_returns
        | AssetSelection.assets(serving.sapo_serving_db)
    ),
    tags=SYNC_TAGS,
)

# 2.7 MISA sales-ledger file-drop sync job
_misa_source = AssetSelection.assets(misa_amis_assets.misa_sales_file_drop_asset)
ingest_filedrop_misa_job = define_asset_job(
    name="ingest_filedrop_misa_job",
    selection=(
        _misa_source
        | _misa_source.downstream()
        | _fact_order_returns
        | AssetSelection.assets(serving.sapo_serving_db)
    ),
    tags=SYNC_TAGS,
)

# 2.8 MISA account-ledger file-drop sync job
# Ingests Sổ chi tiết các tài khoản (overhead 6421/6422) → dbt (account-ledger chain) → serving_db.
# No _fact_order_returns dependency: account-ledger is an independent overhead pool source.
_misa_account_ledger_source = AssetSelection.assets(misa_amis_assets.misa_account_ledger_file_drop_asset)
ingest_filedrop_misa_account_ledger_job = define_asset_job(
    name="ingest_filedrop_misa_account_ledger_job",
    selection=(
        _misa_account_ledger_source
        | _misa_account_ledger_source.downstream()
        | AssetSelection.assets(serving.sapo_serving_db)
    ),
    tags=SYNC_TAGS,
)

# 3. Nightly Reconciliation Job (Batch — incremental from last cursor)
_nightly_batch_selection = (
    AssetSelection.assets(sapo_assets.sapo_orders_batch_asset) |
    AssetSelection.assets(sapo_assets.sapo_customers_batch_asset) |
    AssetSelection.assets(sapo_assets.sapo_accounts_batch_asset) |
    AssetSelection.assets(sapo_assets.sapo_products_batch_asset) |
    AssetSelection.assets(sapo_assets.sapo_inventory_transactions_v2_asset) |
    AssetSelection.assets(sheets_assets.sheets_targets_asset) |
    AssetSelection.assets(sheets_assets.sheets_marketing_spend_asset) |
    AssetSelection.assets(sheets_assets.sheets_team_config_asset) |
    AssetSelection.assets(sheets_assets.sheets_us_shipment_prices_asset) |
    AssetSelection.assets(shopee_assets.shopee_income_file_drop_asset) |
    AssetSelection.assets(misa_amis_assets.misa_sales_file_drop_asset) |
    AssetSelection.assets(misa_amis_assets.misa_account_ledger_file_drop_asset) |
    all_dbt_assets |
    AssetSelection.assets(serving.sapo_serving_db) |
    AssetSelection.assets(serving.sapo_standalone_export) |
    AssetSelection.assets(rill.sapo_rill_publish)
)

transform_batch_nightly_job = define_asset_job(
    name="transform_batch_nightly_job",
    selection=_nightly_batch_selection,
    tags={**SYNC_TAGS, "inventory_window": "day"},
)

# 3b. Full Refresh Job — manual trigger only, resets all batch cursors
# Launch from Dagster UI when data gaps are suspected.
transform_batch_fullrefresh_job = define_asset_job(
    name="transform_batch_fullrefresh_job",
    selection=_nightly_batch_selection,
    tags={**SYNC_TAGS, "full_refresh": "true", "inventory_window": "day"},
)

# 3c. Generic Sapo hourly job — runs inventory-transactions-v2 ingestion through
# the real-time inventory chain: ingest → src_ → std_ → fact_inventory_movements
# (current on-hand + COGS refresh each hour). The daily on-hand snapshot
# (fact_inventory_onhand_daily, ~1.9M rows, DAILY grain) is intentionally left to
# the nightly job. Self-refresh serving views auto-pick the latest mart parquet,
# so no serving asset is needed here. Add future hourly assets to this selection.
ingest_sapo_hourly_job = define_asset_job(
    name="ingest_sapo_hourly_job",
    selection=(
        AssetSelection.assets(sapo_assets.sapo_inventory_transactions_v2_asset)
        | AssetSelection.keys(
            AssetKey(["staging", "src_sapo_inventory_transactions_v2"]),
            AssetKey(["staging", "std_inventory_movements"]),
            AssetKey(["marts", "fact_inventory_movements"]),
            AssetKey(["marts", "fact_inventory_balance"]),
        )
    ),
    tags=SYNC_TAGS,
)

# ------------------------------------------------------------------------------
# SCHEDULES
# ------------------------------------------------------------------------------

# Schedule design notes:
# - QueuedRunCoordinator + tag_concurrency_limits (dagster.yaml: dbt_rw=1) handles
#   CROSS-JOB mutual exclusion at the instance level — no manual priority chain.
# - But coordinator does NOT prevent queue buildup: every tick creates a new
#   RunRequest, and if dequeue is blocked the queue grows unbounded.
# - SELF-overlap skip: each schedule checks if a run for ITS OWN job is already
#   active (queued/started). If yes, skip this tick — the existing run will
#   eventually run and pick up the latest data.
# - This is the minimal logic needed: cross-job = coordinator, self-overlap = schedule.

# Active states: anything that hasn't terminated. NOT_STARTED is included
# to catch runs that were created but haven't been picked up yet.
_ACTIVE_STATUSES = [
    DagsterRunStatus.QUEUED,
    DagsterRunStatus.NOT_STARTED,
    DagsterRunStatus.STARTING,
    DagsterRunStatus.STARTED,
]


def _has_active_run(context, job_name: str) -> str | None:
    """Return run_id of an active run for this job, or None if none active."""
    runs = context.instance.get_runs(
        filters=RunsFilter(job_name=job_name, statuses=_ACTIVE_STATUSES),
        limit=1,
    )
    return runs[0].run_id if runs else None


# Long-running dbt_rw jobs (60-90+ min). Submitting realtime/incremental while
# these are STARTED causes NOT_STARTED accumulation: the submitted run can't be
# dequeued (dbt_rw=1 occupied), blocks subsequent ticks via _has_active_run,
# and eventually hits the 90-min QUEUE_STUCK_THRESHOLD and gets auto-canceled.
# Better to skip the tick and retry next tick (3-10 min later).
_LONG_DPT_RW_JOBS = ["transform_batch_nightly_job", "transform_batch_fullrefresh_job"]

# Statuses that mean a job is ACTUALLY running (holds the dbt_rw slot).
# Exclude NOT_STARTED — a NOT_STARTED batch job hasn't acquired the slot yet
# and may fail to start; we shouldn't pre-emptively block on it.
_RUNNING_STATUSES = [
    DagsterRunStatus.QUEUED,
    DagsterRunStatus.STARTING,
    DagsterRunStatus.STARTED,
]


def _long_dbt_rw_holder(context) -> str | None:
    """Return job_name if a long-running dbt_rw job is currently active (holds slot)."""
    for job_name in _LONG_DPT_RW_JOBS:
        runs = context.instance.get_runs(
            filters=RunsFilter(job_name=job_name, statuses=_RUNNING_STATUSES),
            limit=1,
        )
        if runs:
            return job_name
    return None


# Jobs that use duckdb_lock (write to DuckDB). Health checks should yield to these.
# IMPORTANT: Update this list when adding new ingestion/transform jobs!
_INGESTION_JOBS = [
    "ingest_sapo_realtime_job",
    "ingest_sapo_incremental_job",
    "ingest_sapo_hourly_job",
    "ingest_sheets_sync_job",
    "ingest_filedrop_shopee_job",
    "ingest_filedrop_misa_job",
    "ingest_filedrop_misa_account_ledger_job",
    "transform_batch_nightly_job",
    "transform_batch_fullrefresh_job",
]


def _has_active_ingestion(context) -> str | None:
    """Return job_name of any active ingestion job, or None if all idle."""
    for job_name in _INGESTION_JOBS:
        runs = context.instance.get_runs(
            filters=RunsFilter(job_name=job_name, statuses=_ACTIVE_STATUSES),
            limit=1,
        )
        if runs:
            return job_name
    return None


@schedule(
    job=ingest_sapo_realtime_job,
    cron_schedule="*/3 * * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def ingest_sapo_realtime_schedule(context):
    active = _has_active_run(context, "ingest_sapo_realtime_job")
    if active:
        return SkipReason(f"realtime: previous run still active ({active[:8]})")
    # Yield to long-running batch jobs: a new run can't start (dbt_rw=1 occupied)
    # and would sit NOT_STARTED for 60-90+ min before being auto-canceled.
    # Skip this tick; the next tick in 3 min will retry.
    holder = _long_dbt_rw_holder(context)
    if holder:
        return SkipReason(f"realtime: yielding to {holder} (dbt_rw occupied)")
    # Yield to purge_runs: VACUUM on index.db holds an exclusive SQLite lock, causing
    # log event writes to fail for concurrent jobs → stuck sensor kills them as "inactive".
    # Skip instead; next tick in 3 min retries after purge completes (~15-20 min window).
    if _has_active_run(context, "maintain_purge_runs_job"):
        return SkipReason("realtime: yielding to purge_runs (SQLite index.db lock)")
    return RunRequest(run_key=None)


@schedule(
    job=ingest_sapo_incremental_job,
    # Skip 3 AM hour entirely — nightly batch runs then and holds the
    # dbt_rw slot for ~30-60 minutes. Excluding this hour prevents incremental
    # ticks from piling up while nightly is running.
    #
    # If nightly overruns past 4 AM, _long_dbt_rw_holder() skips the tick
    # instead of creating a NOT_STARTED run that would sit for 60-90+ min
    # and trigger QUEUE_STUCK_THRESHOLD auto-cancel.
    cron_schedule="*/10 0-2,4-23 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def ingest_sapo_incremental_schedule(context):
    active = _has_active_run(context, "ingest_sapo_incremental_job")
    if active:
        return SkipReason(f"incremental: previous run still active ({active[:8]})")
    holder = _long_dbt_rw_holder(context)
    if holder:
        return SkipReason(f"incremental: yielding to {holder} (dbt_rw occupied)")
    if _has_active_run(context, "maintain_purge_runs_job"):
        return SkipReason("incremental: yielding to purge_runs (SQLite index.db lock)")
    return RunRequest(run_key=None)


@schedule(
    job=ingest_sapo_hourly_job,
    # Run at :25 each hour, skip 3 AM (nightly batch holds dbt_rw ~30-60 min).
    # Minute :25 avoids collision with realtime (*/3) and incremental (*/10).
    # If nightly overruns past 4 AM, _long_dbt_rw_holder() skips the tick.
    cron_schedule="25 0-2,4-23 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def ingest_sapo_hourly_schedule(context):
    active = _has_active_run(context, "ingest_sapo_hourly_job")
    if active:
        return SkipReason(f"hourly: previous run still active ({active[:8]})")
    holder = _long_dbt_rw_holder(context)
    if holder:
        return SkipReason(f"hourly: yielding to {holder} (dbt_rw occupied)")
    if _has_active_run(context, "maintain_purge_runs_job"):
        return SkipReason("hourly: yielding to purge_runs (SQLite index.db lock)")
    return RunRequest(run_key=None)


@schedule(
    job=transform_batch_nightly_job,
    cron_schedule="0 3 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def transform_batch_nightly_schedule(context):
    active = _has_active_run(context, "transform_batch_nightly_job")
    if active:
        return SkipReason(f"nightly: previous run still active ({active[:8]})")
    return RunRequest(run_key=None)


_ICT = timezone(timedelta(hours=7))  # Asia/Ho_Chi_Minh, no pytz dependency

# Fast path: fires immediately after purge succeeds (normally ~02:35).
# run_key=date deduplicates with the fallback schedule below — only one
# backup runs per calendar day, whichever triggers first.
@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS,
    monitored_jobs=[maintain_purge_runs_job],
    request_job=maintain_backup_platform_job,
    minimum_interval_seconds=60,
)
def trigger_backup_after_purge(context: RunStatusSensorContext):
    date_key = datetime.now(tz=_ICT).strftime("%Y-%m-%d")
    # Wait for active ingestion to finish before snapshotting DuckDB files —
    # cp of a live DuckDB WAL risks torn state; also avoids I/O contention.
    # Sensor retries every 60 s, so the delay is at most one ingestion cycle.
    active = _has_active_ingestion(context)
    if active:
        return SkipReason(f"backup: waiting for {active} to finish")
    return RunRequest(run_key=date_key)


# Fallback: fires at 06:00 if sensor didn't trigger backup (purge failed).
# Also retries if sensor triggered but backup FAILED — run_key=None so Dagster
# does NOT deduplicate against a previously failed run with same date key.
# Dedup is handled manually: skip if a SUCCESS already exists today.
@schedule(
    job=maintain_backup_platform_job,
    cron_schedule="0 6 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def maintain_backup_fallback_schedule(context):
    if _has_active_run(context, "maintain_backup_platform_job"):
        return SkipReason("backup: already running")
    today = datetime.now(tz=_ICT).date()
    records = context.instance.get_run_records(
        filters=RunsFilter(
            job_name="maintain_backup_platform_job",
            statuses=[DagsterRunStatus.SUCCESS],
        ),
        limit=5,
    )
    for rec in records:
        if rec.create_timestamp.astimezone(_ICT).date() == today:
            return SkipReason("backup: already succeeded today")
    return RunRequest(run_key=None)


# Recon job — daily source↔destination reconciliation.
# NOT in dbt_rw concurrency group: recon is read-only on raw DB and health DB,
# so it must never compete with nightly ingestion writes.
health_recon_daily_job = define_asset_job(
    name="health_recon_daily_job",
    selection=AssetSelection.groups("reconciliation"),
    executor_def=in_process_executor,
)

# KPI closure job — daily revenue invariant check (Phase 5).
# NOT in dbt_rw concurrency group: reads from Sapo API + serving DB (read-only).
# Gated behind KPI_CLOSURE_ENABLED=1 env flag.
health_kpi_closure_job = define_asset_job(
    name="health_kpi_closure_job",
    selection=AssetSelection.groups("kpi_closure"),
    executor_def=in_process_executor,
)


@schedule(
    job=health_recon_daily_job,
    cron_schedule="30 4 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def health_recon_daily_schedule(context):
    active = _has_active_run(context, "health_recon_daily_job")
    if active:
        return SkipReason(f"recon: previous run still active ({active[:8]})")
    return RunRequest(run_key=None)


# KPI closure — 04:45 ICT daily, after recon (04:30) and nightly batch (03:00).
# Gated behind KPI_CLOSURE_ENABLED=1 — when disabled, asset runs but writes status='disabled'.
@schedule(
    job=health_kpi_closure_job,
    cron_schedule="45 4 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def health_kpi_closure_schedule(context):
    active = _has_active_run(context, "health_kpi_closure_job")
    if active:
        return SkipReason(f"kpi_closure: previous run still active ({active[:8]})")
    return RunRequest(run_key=None)


# Health asset checks job — runs INGESTION checks only (freshness, row_trend, cursor, recon).
# Read-only against ingestion_health.duckdb; not in dbt_rw concurrency group.
#
# IMPORTANT: We explicitly EXCLUDE dbt tests from this job. Rationale:
# - `all_asset_checks()` includes dbt tests (exposed via dagster-dbt)
# - dbt tests require running `sapo_dbt_assets` step which needs `duckdb_lock`
# - This caused 55+ minute blocking when health checks and ingestion ran simultaneously
# - dbt tests already run during each ingestion job — no need to duplicate here
#
# Uses in_process_executor: checks are lightweight DuckDB reads — spawning
# heavyweight subprocesses (each re-importing dlt/dbt/duckdb) caused OOM
# ChildProcessCrashException in the default multiprocess executor.
health_checks_asset_job = define_asset_job(
    name="health_checks_asset_job",
    selection=(
        AssetSelection.all_asset_checks()
        - AssetSelection.checks_for_assets(dbt.sapo_dbt_assets)
    ),
    executor_def=in_process_executor,
)


@schedule(
    job=health_checks_asset_job,
    # Run at :05 instead of :00 to avoid collision with realtime (*/3) and incremental (*/10).
    # Both those schedules fire at :00, so health_checks would frequently skip due to yield logic.
    cron_schedule="5 */2 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def health_checks_asset_schedule(context):
    # Self-overlap check
    active = _has_active_run(context, "health_checks_asset_job")
    if active:
        return SkipReason(f"health_checks: previous run still active ({active[:8]})")

    # Yield to ingestion: skip if any ingestion job is running.
    # Health checks are fast (~12s) but we don't want to add noise during data sync.
    # At :05 minute mark, realtime (:00, :03, :06) would have completed its ~45s run,
    # so this skip is less likely to trigger than at :00.
    active_ingest = _has_active_ingestion(context)
    if active_ingest:
        return SkipReason(f"health_checks: yielding to active ingestion ({active_ingest})")

    return RunRequest(run_key=None)


# Morning digest — 06:00 ICT daily, read-only against health DB, not in dbt_rw group.
# Window is yesterday's ICT calendar day (0h-24h), so the digest describes the
# full previous day by the time stakeholders read it at 6 AM.
@schedule(
    job=health_report_digest_job,
    cron_schedule="0 6 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def health_report_digest_schedule(context):
    active = _has_active_run(context, "health_report_digest_job")
    if active:
        return SkipReason(f"morning_digest: previous run still active ({active[:8]})")
    return RunRequest(run_key=None)


# 02:30 daily — purge old Dagster runs to reclaim disk space.
# Window choice: ingestion is quietest in the small hours (realtime tick
# every 3 min still fires, but no nightly/recon/health overlap), which
# minimises SQLite "database is locked" contention against event_logs
# during mass deletes. Completes well before nightly batch (03:00) and
# backup (06:00). Earlier 05:30 slot collided with the post-nightly
# realtime drain and caused warnings during purge.
# Keeps PURGE_KEEP_DAYS (default: 1) days of history.
# Not in dbt_rw concurrency group: operates on Dagster's internal storage only.
@schedule(
    job=maintain_purge_runs_job,
    cron_schedule="0 1 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def maintain_purge_runs_schedule(context):
    active = _has_active_run(context, "maintain_purge_runs_job")
    if active:
        return SkipReason(f"purge_runs: previous run still active ({active[:8]})")
    return RunRequest(run_key=None)


# ------------------------------------------------------------------------------
# RESOURCES & DEFINITIONS
# ------------------------------------------------------------------------------

# Resolve DBT Executable
# Use shutil.which to find dbt on path, fallback to venv path if not found
dbt_exe = shutil.which("dbt")
if not dbt_exe:
    dbt_exe = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ingestion", "venv", "Scripts", "dbt.exe")

defs = Definitions(
    assets=all_assets,
    # Jobs must be listed explicitly so sensors can reference them by name.
    # Schedules already pull in their target job implicitly, but sensors
    # targeting a job (e.g. ingest_sheets_modified_sensor → ingest_sheets_sync_job)
    # require the job to be present in the repository.
    asset_checks=[*ALL_CHECKS, *RECON_CHECKS, *KPI_CHECKS],
    jobs=[
        # ingest_*
        ingest_sapo_realtime_job,
        ingest_sapo_incremental_job,
        ingest_sapo_hourly_job,
        ingest_sheets_sync_job,
        ingest_filedrop_shopee_job,
        ingest_filedrop_misa_job,
        ingest_filedrop_misa_account_ledger_job,
        # transform_*
        transform_batch_nightly_job,
        transform_batch_fullrefresh_job,
        # health_*
        health_recon_daily_job,
        health_kpi_closure_job,
        health_checks_asset_job,
        health_report_digest_job,
        # maintain_*
        maintain_backup_platform_job,
        maintain_purge_runs_job,
    ],
    schedules=[
        # ingest_*
        ingest_sapo_realtime_schedule,
        ingest_sapo_incremental_schedule,
        ingest_sapo_hourly_schedule,
        # transform_*
        transform_batch_nightly_schedule,
        # health_*
        health_recon_daily_schedule,
        health_kpi_closure_schedule,
        health_checks_asset_schedule,
        health_report_digest_schedule,
        # maintain_*
        maintain_purge_runs_schedule,
        maintain_backup_fallback_schedule,
    ],
    sensors=[
        # ingest_*
        ingest_sheets_modified_sensor,
        ingest_filedrop_shopee_sensor,
        ingest_filedrop_misa_sensor,
        ingest_filedrop_misa_account_ledger_sensor,
        # health_*
        health_alert_failure_sensor,
        health_alert_stuckrun_sensor,
        health_concurrency_pool_janitor,
        health_db_watchdog_sensor,
        # maintain_*
        trigger_backup_after_purge,
    ],
    resources={
        "dbt": DbtCliResource(
            project_dir=dbt.dbt_project.project_dir,
            dbt_executable=dbt_exe
        ),
    },
)
