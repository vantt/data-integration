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
    define_asset_job,
    AssetSelection,
    schedule,
    DefaultScheduleStatus,
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
from orchestration.assets import dbt, serving, rill, reconciliation, kpi_closure
from orchestration.connectors import load_enabled, load_enabled_jobs
from orchestration import packs as pack_registry
from orchestration.job_support import (
    ACTIVE_STATUSES as _ACTIVE_STATUSES,
    SYNC_TAGS,
    has_active_run as _has_active_run,
)
from orchestration.ops.system_backup import maintain_backup_platform_job
from orchestration.ops.morning_digest import health_report_digest_job
from orchestration.ops.purge_runs import maintain_cleanup_job
from orchestration.sensors.failure_alerting import health_alert_failure_sensor
from orchestration.sensors.stuck_run_alerter import health_alert_stuckrun_sensor
from orchestration.sensors.concurrency_pool_janitor import health_concurrency_pool_janitor
from orchestration.sensors.health_db_watchdog_sensor import health_db_watchdog_sensor
from orchestration import reports as report_site

# Load all assets — directory setup runs once at container startup
# (docker-compose.yml command: `python scripts/ensure_dbt_directories.py && ...`).
# Don't call it from here: definitions.py is re-imported on every gRPC code
# server spawn (e.g. each `dagster job launch`), which would add noise.
kernel_assets = load_assets_from_modules([dbt, serving, rill, reconciliation, kpi_closure])

# Connectors and packs enabled in orchestration/config/modules.yaml contribute their own
# assets, jobs, schedules and sensors.
connectors = load_enabled()
connector_jobs = load_enabled_jobs()
packs = pack_registry.load_enabled()
pack_jobs = pack_registry.load_enabled_jobs()
all_assets = [
    *kernel_assets,
    *(a for c in connectors for a in c.ASSETS),
    *(a for p in packs for a in p.ASSETS),
]

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

# Cross-source jobs: they select ingest assets from every enabled connector and the nightly
# assets of every enabled pack (crm: CRM write-back exports + cache refresh; sales_playbook:
# approach-script autogen).
# 3. Nightly Reconciliation Job (Batch — incremental from last cursor)
_nightly_batch_selection = (
    AssetSelection.assets(*(a for c in connectors for a in c.NIGHTLY_ASSETS)) |
    AssetSelection.assets(*(a for p in packs for a in p.NIGHTLY_ASSETS)) |
    all_dbt_assets |
    AssetSelection.assets(serving.build_serving_db) |
    AssetSelection.assets(serving.build_standalone_export) |
    AssetSelection.assets(rill.build_rill_publish)
)

pipeline_batch_nightly_job = define_asset_job(
    name="pipeline_batch_nightly_job",
    selection=_nightly_batch_selection,
    tags={**SYNC_TAGS, "inventory_window": "day"},
)

# 3b. Full Refresh Job — manual trigger only, resets all batch cursors
# Launch from Dagster UI when data gaps are suspected.
# Report site (Evidence): build request after the nightly run, build monitoring, summary messages
# (orchestration/reports/README.md).
_report_site = report_site.definitions(pipeline_batch_nightly_job)

pipeline_batch_fullrefresh_job = define_asset_job(
    name="pipeline_batch_fullrefresh_job",
    selection=_nightly_batch_selection,
    tags={**SYNC_TAGS, "full_refresh": "true", "inventory_window": "day"},
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

# Active states, has_active_run and long_dbt_rw_holder live in orchestration/job_support.py
# (shared with the connector packages).

# Jobs that use duckdb_lock (write to DuckDB). Health checks should yield to these.
# Built dynamically from all jobs defined in this module that carry SYNC_TAGS
# (concurrency_group == "dbt_rw") — eliminates the drift risk of a manual list.
_ALL_SYNC_JOBS = [
    *(j for c in connector_jobs for j in c.JOBS),
    *(j for p in pack_jobs for j in p.JOBS),
    pipeline_batch_nightly_job,
    pipeline_batch_fullrefresh_job,
]
_INGESTION_JOBS = [
    j.name for j in _ALL_SYNC_JOBS
    if j.tags.get("concurrency_group") == "dbt_rw"
]


def _has_active_ingestion(context) -> str | None:
    """Return job_name of any active ingestion job, or None if all idle.

    Issues one get_runs() query per job (N≈10 SQLite reads per call). Called
    during the post-purge backup-sensor window (every 60 s while ingestion
    active) — acceptable load. A future optimisation would batch into a single
    get_run_records(filters=RunsFilter(job_names=[...], statuses=...)) call if
    the Dagster API adds multi-job filter support.
    """
    for job_name in _INGESTION_JOBS:
        runs = context.instance.get_runs(
            filters=RunsFilter(job_name=job_name, statuses=_ACTIVE_STATUSES),
            limit=1,
        )
        if runs:
            return job_name
    return None


@schedule(
    job=pipeline_batch_nightly_job,
    cron_schedule="0 3 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def pipeline_batch_nightly_schedule(context):
    active = _has_active_run(context, "pipeline_batch_nightly_job")
    if active:
        return SkipReason(f"nightly: previous run still active ({active[:8]})")
    return RunRequest(run_key=None)


_ICT = timezone(timedelta(hours=7))  # Asia/Ho_Chi_Minh, no pytz dependency

# Fast path: fires immediately after purge succeeds (normally ~02:35).
# run_key=date deduplicates with the fallback schedule below — only one
# backup runs per calendar day, whichever triggers first.
#
# Re-evaluation note: @run_status_sensor with minimum_interval_seconds=60 is
# re-evaluated on every polling tick (not just once per matched event). If the
# sensor returns SkipReason (ingestion still active) on the first tick, Dagster
# re-evaluates it on the next tick 60 s later — it does NOT consume the event
# on the first SkipReason. This means the skip-then-retry logic works correctly
# as long as ingestion finishes within a reasonable window. If ingestion is
# still active at 06:00, the fallback schedule is the guaranteed backup path.
@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS,
    monitored_jobs=[maintain_cleanup_job],
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


# Fallback: fires at 06:05 if sensor didn't trigger backup (purge failed).
# Offset by 5 min from health_report_digest_schedule (06:00) to separate
# concurrent run submission and reduce SQLite pressure at the same second.
# Also retries if sensor triggered but backup FAILED — run_key=None so Dagster
# does NOT deduplicate against a previously failed run with same date key.
# Dedup is handled manually: skip if a SUCCESS already exists today.
@schedule(
    job=maintain_backup_platform_job,
    cron_schedule="5 6 * * *",
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


# 01:00 daily — purge old Dagster runs and stale dbt build-cache dirs to reclaim disk space.
# Window choice: ingestion is quietest in the small hours (realtime tick
# every 3 min still fires, but no nightly/recon/health overlap), which
# minimises SQLite "database is locked" contention against event_logs
# during mass deletes. Completes well before nightly batch (03:00) and
# backup (06:00). Earlier 05:30 slot collided with the post-nightly
# realtime drain and caused warnings during cleanup.
# Keeps PURGE_KEEP_DAYS (default: 1) days of history.
# Not in dbt_rw concurrency group: operates on Dagster's internal storage and
# transformation/target/ only — never touches DuckDB.
@schedule(
    job=maintain_cleanup_job,
    cron_schedule="0 1 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
    default_status=DefaultScheduleStatus.RUNNING,  # auto-enable (schedules in defs are off by default — L49)
)
def maintain_cleanup_schedule(context):
    active = _has_active_run(context, "maintain_cleanup_job")
    if active:
        return SkipReason(f"maintain_cleanup: previous run still active ({active[:8]})")
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
    asset_checks=[*ALL_CHECKS, *RECON_CHECKS, *KPI_CHECKS, *(chk for c in connectors for chk in c.ASSET_CHECKS)],
    jobs=[
        # ingest_* (per connector)
        *(j for c in connector_jobs for j in c.JOBS),
        # pipeline_batch_*
        pipeline_batch_nightly_job,
        pipeline_batch_fullrefresh_job,
        # health_*
        health_recon_daily_job,
        health_kpi_closure_job,
        health_checks_asset_job,
        health_report_digest_job,
        # maintain_*
        maintain_backup_platform_job,
        maintain_cleanup_job,
        # per pack (crm: crm_backup_job)
        *(j for p in pack_jobs for j in p.JOBS),
        # report_* (report site build request, summary message)
        *_report_site["jobs"],
    ],
    schedules=[
        # ingest_* (per connector; add assets to a connector's jobs, not new schedules here)
        *(sch for c in connector_jobs for sch in c.SCHEDULES),
        # transform_*
        pipeline_batch_nightly_schedule,
        # health_*
        health_recon_daily_schedule,
        health_kpi_closure_schedule,
        health_checks_asset_schedule,
        health_report_digest_schedule,
        # maintain_*
        maintain_cleanup_schedule,
        maintain_backup_fallback_schedule,
        # per pack (crm: crm_backup_schedule)
        *(sch for p in pack_jobs for sch in p.SCHEDULES),
    ],
    sensors=[
        # ingest_* (per connector)
        *(sen for c in connector_jobs for sen in c.SENSORS),
        # health_*
        health_alert_failure_sensor,
        health_alert_stuckrun_sensor,
        health_concurrency_pool_janitor,
        health_db_watchdog_sensor,
        # maintain_*
        trigger_backup_after_purge,
        # per pack
        *(sen for p in pack_jobs for sen in p.SENSORS),
        # report_site_* (build after nightly, build status + summary)
        *_report_site["sensors"],
    ],
    resources={
        "dbt": DbtCliResource(
            project_dir=dbt.dbt_project.project_dir,
            dbt_executable=dbt_exe
        ),
    },
)
