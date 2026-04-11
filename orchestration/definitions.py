import sys
import os
import shutil

# Add project root to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ingestion", "src"))

from dagster import (
    Definitions,
    load_assets_from_modules,
    ScheduleDefinition,
    define_asset_job,
    AssetSelection,
    schedule,
    RunRequest,
    SkipReason,
    RunsFilter,
    DagsterRunStatus,
)
from dagster_dbt import DbtCliResource
from orchestration.assets import sapo_assets, sheets_assets, shopee_assets, misa_amis_assets, dbt, serving, rill
from orchestration.sensors.failure_alerting import lark_failure_sensor
from orchestration.sensors.sheets_modified_sensor import sheets_modified_sensor
from orchestration.sensors.stuck_run_alerter import stuck_run_sensor
from orchestration.sensors.file_drop_sensors import shopee_file_drop_sensor, misa_file_drop_sensor

# Load all assets
# [Auto-Setup] Ensure dbt directories exist before loading assets
# try:
#     from scripts.ensure_dbt_directories import ensure_directories
#     ensure_directories()
# except ImportError:
#     print("[WARN] Could not import ensure_directories script. Skipping auto-check.")
# except Exception as e:
#     print(f"[WARN] Auto-check failed: {e}")

all_assets = load_assets_from_modules([sapo_assets, sheets_assets, shopee_assets, misa_amis_assets, dbt, serving, rill])

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
sapo_realtime_sync_job = define_asset_job(
    name="sapo_realtime_sync_job",
    selection=AssetSelection.assets(sapo_assets.sapo_webhook_consumer_asset) | all_dbt_assets | AssetSelection.assets(serving.sapo_serving_db) | AssetSelection.assets(rill.sapo_rill_publish),
    tags=SYNC_TAGS,
)

# 2. Incremental Job (History Log)
sapo_incremental_sync_job = define_asset_job(
    name="sapo_incremental_sync_job",
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
)
sheets_sync_job = define_asset_job(
    name="sheets_sync_job",
    selection=(
        _sheets_sources
        | _sheets_sources.downstream()
        | AssetSelection.assets(serving.sapo_serving_db)
        | AssetSelection.assets(rill.sapo_rill_publish)
    ),
    tags=SYNC_TAGS,
)

# 2.6 Shopee file-drop sync job
# Ingests Shopee income Excel → dbt (downstream of shopee sources) → serving_db.
_shopee_source = AssetSelection.assets(shopee_assets.shopee_income_file_drop_asset)
shopee_file_drop_sync_job = define_asset_job(
    name="shopee_file_drop_sync_job",
    selection=(
        _shopee_source
        | _shopee_source.downstream()
        | AssetSelection.assets(serving.sapo_serving_db)
    ),
    tags=SYNC_TAGS,
)

# 2.7 MISA file-drop sync job
_misa_source = AssetSelection.assets(misa_amis_assets.misa_sales_file_drop_asset)
misa_file_drop_sync_job = define_asset_job(
    name="misa_file_drop_sync_job",
    selection=(
        _misa_source
        | _misa_source.downstream()
        | AssetSelection.assets(serving.sapo_serving_db)
    ),
    tags=SYNC_TAGS,
)

# 3. Nightly Reconciliation Job (Batch)
sapo_nightly_reconciliation_job = define_asset_job(
    name="sapo_nightly_reconciliation_job",
    selection=(
        AssetSelection.assets(sapo_assets.sapo_orders_batch_asset) |
        AssetSelection.assets(sapo_assets.sapo_customers_batch_asset) |
        AssetSelection.assets(sapo_assets.sapo_accounts_batch_asset) |
        AssetSelection.assets(sheets_assets.sheets_targets_asset) |
        AssetSelection.assets(sheets_assets.sheets_marketing_spend_asset) |
        AssetSelection.assets(shopee_assets.shopee_income_file_drop_asset) |
        AssetSelection.assets(misa_amis_assets.misa_sales_file_drop_asset) |
        all_dbt_assets |
        AssetSelection.assets(serving.sapo_serving_db) |
        AssetSelection.assets(rill.sapo_rill_publish)
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


@schedule(
    job=sapo_realtime_sync_job,
    cron_schedule="*/3 * * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def realtime_schedule(context):
    active = _has_active_run(context, "sapo_realtime_sync_job")
    if active:
        return SkipReason(f"realtime: previous run still active ({active[:8]})")
    return RunRequest(run_key=None)


@schedule(
    job=sapo_incremental_sync_job,
    # Skip 4 AM hour entirely — nightly reconciliation runs then and holds the
    # dbt_rw slot for ~30-60 minutes. Excluding this hour prevents incremental
    # ticks from piling up while nightly is running.
    #
    # Edge case: if nightly is ever delayed past 5 AM, incremental resumes at
    # :00 of the next hour and may enqueue while nightly is still active.
    # This is safe — coordinator tag `dbt_rw=1` serializes the dequeue, and
    # incremental's own self-overlap check prevents double-enqueue.
    cron_schedule="*/10 0-3,5-23 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def incremental_schedule(context):
    active = _has_active_run(context, "sapo_incremental_sync_job")
    if active:
        return SkipReason(f"incremental: previous run still active ({active[:8]})")
    return RunRequest(run_key=None)


@schedule(
    job=sapo_nightly_reconciliation_job,
    cron_schedule="0 4 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def nightly_schedule(context):
    active = _has_active_run(context, "sapo_nightly_reconciliation_job")
    if active:
        return SkipReason(f"nightly: previous run still active ({active[:8]})")
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
    # targeting a job (e.g. sheets_modified_sensor → sheets_sync_job)
    # require the job to be present in the repository.
    jobs=[
        sapo_realtime_sync_job,
        sapo_incremental_sync_job,
        sheets_sync_job,
        shopee_file_drop_sync_job,
        misa_file_drop_sync_job,
        sapo_nightly_reconciliation_job,
    ],
    schedules=[
        realtime_schedule,
        incremental_schedule,
        nightly_schedule,
    ],
    sensors=[
        lark_failure_sensor,
        stuck_run_sensor,
        sheets_modified_sensor,
        shopee_file_drop_sensor,
        misa_file_drop_sensor,
    ],
    resources={
        "dbt": DbtCliResource(
            project_dir=dbt.dbt_project.project_dir,
            dbt_executable=dbt_exe
        ),
    },
)
