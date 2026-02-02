import sys
import os
import shutil

# Add project root to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ingestion", "src"))

from dagster import Definitions, load_assets_from_modules, ScheduleDefinition, define_asset_job, AssetSelection, schedule
from dagster_dbt import DbtCliResource
from orchestration.assets import sapo_assets, dbt, serving

# Load all assets
# Load all assets
# [Auto-Setup] Ensure dbt directories exist before loading assets
# try:
#     from scripts.ensure_dbt_directories import ensure_directories
#     ensure_directories()
# except ImportError:
#     print("[WARN] Could not import ensure_directories script. Skipping auto-check.")
# except Exception as e:
#     print(f"[WARN] Auto-check failed: {e}")

all_assets = load_assets_from_modules([sapo_assets, dbt, serving])

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

# 1. Realtime Job (Webhook)
# Triggered every minute.
sapo_realtime_sync_job = define_asset_job(
    name="sapo_realtime_sync_job",
    selection=AssetSelection.assets(sapo_assets.sapo_webhook_consumer_asset) | all_dbt_assets | AssetSelection.assets(serving.sapo_serving_db),
    # tags={"concurrency_group": "dbt_rw"}, # Removed: Using Asset-level locking
)

# 2. Incremental Job (History Log)
# Triggered every 10 minutes.
sapo_incremental_sync_job = define_asset_job(
    name="sapo_incremental_sync_job",
    selection=AssetSelection.assets(sapo_assets.sapo_history_log_asset) | all_dbt_assets | AssetSelection.assets(serving.sapo_serving_db),
    tags={"dagster/max_retries": "0"}, # Removed: concurrency_group
)

# 2.5 Targets Job (Manual)
# 2.5 Targets Job (Manual)
sapo_targets_sync_job = define_asset_job(
    name="sapo_targets_sync_job",
    selection=AssetSelection.assets(sapo_assets.sapo_targets_asset) | AssetSelection.keys("stg_targets", "fact_targets") | AssetSelection.assets(serving.sapo_serving_db),
    # tags={"concurrency_group": "dbt_rw"},
)

# 3. Nightly Reconciliation Job (Batch)
# Triggered at 04:00 AM.
sapo_nightly_reconciliation_job = define_asset_job(
    name="sapo_nightly_reconciliation_job",
    selection=(
        AssetSelection.assets(sapo_assets.sapo_orders_batch_asset) |
        AssetSelection.assets(sapo_assets.sapo_customers_batch_asset) |
        AssetSelection.assets(sapo_assets.sapo_accounts_batch_asset) |
        AssetSelection.assets(sapo_assets.sapo_targets_asset) |
        all_dbt_assets |
        AssetSelection.assets(serving.sapo_serving_db)
    ),
    # tags={"concurrency_group": "dbt_rw"},
)

# ------------------------------------------------------------------------------
# SCHEDULES
# ------------------------------------------------------------------------------

@schedule(
    job=sapo_realtime_sync_job,
    cron_schedule="* * * * *",
    execution_timezone="Asia/Ho_Chi_Minh"
)
def realtime_schedule(context):
    """
    Schedule that skips execution if a previous run of the job is still active.
    """
    from dagster import RunRequest, SkipReason, RunsFilter, DagsterRunStatus

    # Check for active runs (not terminated)
    active_runs = context.instance.get_runs(
        filters=RunsFilter(
            job_name="sapo_realtime_sync_job",
            statuses=[
                DagsterRunStatus.STARTING,
                DagsterRunStatus.STARTED,
                DagsterRunStatus.QUEUED,
                DagsterRunStatus.NOT_STARTED
            ]
        ),
        limit=1
    )

    if len(active_runs) > 0:
        return SkipReason(
            f"Skipping run because a previous run (Run ID: {active_runs[0].run_id}) is still active."
        )

    return RunRequest(run_key=None)

@schedule(
    job=sapo_incremental_sync_job,
    cron_schedule="*/10 * * * *",
    execution_timezone="Asia/Ho_Chi_Minh"
)
def incremental_schedule(context):
    """
    Schedule that skips execution if a previous run of the job is still active.
    """
    from dagster import RunRequest, SkipReason, RunsFilter, DagsterRunStatus

    active_runs = context.instance.get_runs(
        filters=RunsFilter(
            job_name="sapo_incremental_sync_job",
            statuses=[
                DagsterRunStatus.STARTING,
                DagsterRunStatus.STARTED,
                DagsterRunStatus.QUEUED,
                DagsterRunStatus.NOT_STARTED
            ]
        ),
        limit=1
    )

    if len(active_runs) > 0:
        return SkipReason(
            f"Skipping run because a previous run (Run ID: {active_runs[0].run_id}) is still active."
        )

    return RunRequest(run_key=None)

@schedule(
    job=sapo_nightly_reconciliation_job,
    cron_schedule="0 4 * * *",
    execution_timezone="Asia/Ho_Chi_Minh"
)
def nightly_schedule(context):
    """
    Schedule that skips execution if a previous run of the job is still active.
    """
    from dagster import RunRequest, SkipReason, RunsFilter, DagsterRunStatus

    active_runs = context.instance.get_runs(
        filters=RunsFilter(
            job_name="sapo_nightly_reconciliation_job",
            statuses=[
                DagsterRunStatus.STARTING,
                DagsterRunStatus.STARTED,
                DagsterRunStatus.QUEUED,
                DagsterRunStatus.NOT_STARTED
            ]
        ),
        limit=1
    )

    if len(active_runs) > 0:
        return SkipReason(
            f"Skipping run because a previous run (Run ID: {active_runs[0].run_id}) is still active."
        )

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
    schedules=[
        realtime_schedule,
        incremental_schedule,
        nightly_schedule
    ],
    resources={
        "dbt": DbtCliResource(
            project_dir=dbt.dbt_project.project_dir,
            dbt_executable=dbt_exe
        ),
    },
)
