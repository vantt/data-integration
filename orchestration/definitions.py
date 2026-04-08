import sys
import os
import shutil

# Add project root to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ingestion", "src"))

from dagster import Definitions, load_assets_from_modules, ScheduleDefinition, define_asset_job, AssetSelection, schedule, RunRequest
from dagster_dbt import DbtCliResource
from orchestration.assets import sapo_assets, sheets_assets, dbt, serving

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

all_assets = load_assets_from_modules([sapo_assets, sheets_assets, dbt, serving])

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
    selection=AssetSelection.assets(sapo_assets.sapo_webhook_consumer_asset) | all_dbt_assets | AssetSelection.assets(serving.sapo_serving_db),
    tags=SYNC_TAGS,
)

# 2. Incremental Job (History Log)
sapo_incremental_sync_job = define_asset_job(
    name="sapo_incremental_sync_job",
    selection=AssetSelection.assets(sapo_assets.sapo_history_log_asset) | all_dbt_assets | AssetSelection.assets(serving.sapo_serving_db),
    tags={**SYNC_TAGS, "dagster/max_retries": "0"},
)

# 2.5 Sheets Job (Manual)
# Ingests Google Sheets Data (Targets, Marketing Spend).
# Raw Sync Only - NO DBT (dbt runs in Nightly or Manual triggers of dbt job)
sheets_sync_job = define_asset_job(
    name="sheets_sync_job",
    selection=AssetSelection.assets(sheets_assets.sheets_targets_asset) | AssetSelection.assets(sheets_assets.sheets_marketing_spend_asset),
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
        all_dbt_assets |
        AssetSelection.assets(serving.sapo_serving_db)
    ),
    tags=SYNC_TAGS,
)

# ------------------------------------------------------------------------------
# SCHEDULES
# ------------------------------------------------------------------------------

# Schedules are now minimal: QueuedRunCoordinator + tag_concurrency_limits
# (dagster.yaml: concurrency_group=dbt_rw limit 1) handle mutual exclusion at
# the instance level. When a slot is busy, new runs queue instead of racing.
# No SkipReason logic needed — the coordinator is the single source of truth.

@schedule(
    job=sapo_realtime_sync_job,
    cron_schedule="*/3 * * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def realtime_schedule(_context):
    return RunRequest(run_key=None)


@schedule(
    job=sapo_incremental_sync_job,
    # Skip 4 AM hour entirely — nightly reconciliation runs then and holds the
    # dbt_rw slot for ~30-60 minutes. Excluding this hour prevents incremental
    # ticks from piling up in the queue while nightly is running.
    cron_schedule="*/10 0-3,5-23 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def incremental_schedule(_context):
    return RunRequest(run_key=None)


@schedule(
    job=sapo_nightly_reconciliation_job,
    cron_schedule="0 4 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def nightly_schedule(_context):
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
