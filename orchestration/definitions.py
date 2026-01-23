import sys
import os

# Add project root to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dagster import Definitions, load_assets_from_modules, ScheduleDefinition, define_asset_job
from orchestration.assets import sapo_assets

all_assets = load_assets_from_modules([sapo_assets])

# Job Definitions (implicit jobs from assets)
# We define explicit jobs to attach schedules to them.

sapo_orders_batch_job = define_asset_job(name="sapo_orders_batch_job", selection=["sapo_orders_batch_asset"])
sapo_customers_batch_job = define_asset_job(name="sapo_customers_batch_job", selection=["sapo_customers_batch_asset"])
sapo_history_job = define_asset_job(
    name="sapo_history_log_job", 
    selection=["sapo_history_log_asset"],
    # Prevent retries from piling up if the job takes too long or fails
    tags={"dagster/max_retries": "0"},
)
sapo_webhook_job = define_asset_job(name="sapo_webhook_consumer_job", selection=["sapo_webhook_consumer_asset"])

# Schedules
# 1. Orders Batch Sync: Daily at 2:00 AM
orders_batch_schedule = ScheduleDefinition(
    job=sapo_orders_batch_job,
    cron_schedule="0 4 * * *",
    execution_timezone="Asia/Ho_Chi_Minh"
)

# 2. Customers Batch Sync: Daily at 2:00 AM (Parallel with Orders)
customers_batch_schedule = ScheduleDefinition(
    job=sapo_customers_batch_job,
    cron_schedule="0 5 * * *",
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
    schedules=[orders_batch_schedule, customers_batch_schedule, history_schedule, webhook_schedule]
)
