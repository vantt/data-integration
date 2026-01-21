import sys
import os

# Add project root to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dagster import Definitions, load_assets_from_modules, ScheduleDefinition, define_asset_job
from orchestration.assets import sapo_assets

all_assets = load_assets_from_modules([sapo_assets])

# Job Definitions (implicit jobs from assets)
# We define explicit jobs to attach schedules to them.

sapo_batch_job = define_asset_job(name="sapo_batch_sync_job", selection=["sapo_batch_sync_asset"])
sapo_history_job = define_asset_job(name="sapo_history_log_job", selection=["sapo_history_log_asset"])
sapo_webhook_job = define_asset_job(name="sapo_webhook_consumer_job", selection=["sapo_webhook_consumer_asset"])

# Schedules
# 1. Batch Sync: Daily at 2:00 AM
batch_schedule = ScheduleDefinition(
    job=sapo_batch_job,
    cron_schedule="0 2 * * *",
    execution_timezone="Asia/Ho_Chi_Minh"
)

# 2. History Log: Every 10 minutes
history_schedule = ScheduleDefinition(
    job=sapo_history_job,
    cron_schedule="*/10 * * * *",
    execution_timezone="Asia/Ho_Chi_Minh"
)

# 3. Webhook: Every 1 minute
webhook_schedule = ScheduleDefinition(
    job=sapo_webhook_job,
    cron_schedule="* * * * *",
    execution_timezone="Asia/Ho_Chi_Minh"
)

defs = Definitions(
    assets=all_assets,
    schedules=[batch_schedule, history_schedule, webhook_schedule]
)
