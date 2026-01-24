import sys
import os

# Add project root to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dagster import Definitions, load_assets_from_modules, ScheduleDefinition, define_asset_job
from dagster_dbt import DbtCliResource
from orchestration.assets import sapo_assets, dbt

all_assets = load_assets_from_modules([sapo_assets, dbt])

# Job Definitions
sapo_orders_batch_job = define_asset_job(name="sapo_orders_batch_job", selection=["sapo_orders_batch_asset"])
sapo_customers_batch_job = define_asset_job(name="sapo_customers_batch_job", selection=["sapo_customers_batch_asset"])
sapo_accounts_batch_job = define_asset_job(name="sapo_accounts_batch_job", selection=["sapo_accounts_batch_asset"])
sapo_history_job = define_asset_job(
    name="sapo_history_log_job", 
    selection=["sapo_history_log_asset"],
    tags={"dagster/max_retries": "0"},
)
sapo_webhook_job = define_asset_job(name="sapo_webhook_consumer_job", selection=["sapo_webhook_consumer_asset"])

from dagster import AssetSelection

# dbt Jobs
# 1. OTP Job: Runs Staging + Intermediate layers (Fast, Operational)
sapo_dbt_otp_job = define_asset_job(
    name="sapo_dbt_otp_job", 
    selection=AssetSelection.tag("otp")
)

# 2. OLAP Job: Runs Marts layer (Slower, Analytical)
sapo_dbt_olap_job = define_asset_job(
    name="sapo_dbt_olap_job", 
    selection=AssetSelection.tag("olap")
)

# Schedules
orders_batch_schedule = ScheduleDefinition(
    job=sapo_orders_batch_job,
    cron_schedule="0 4 * * *",
    execution_timezone="Asia/Ho_Chi_Minh"
)

customers_batch_schedule = ScheduleDefinition(
    job=sapo_customers_batch_job,
    cron_schedule="0 5 * * *",
    execution_timezone="Asia/Ho_Chi_Minh"
)

accounts_batch_schedule = ScheduleDefinition(
    job=sapo_accounts_batch_job,
    cron_schedule="0 6 * * *",
    execution_timezone="Asia/Ho_Chi_Minh"
)

history_schedule = ScheduleDefinition(
    job=sapo_history_job,
    cron_schedule="*/10 * * * *",
    execution_timezone="Asia/Ho_Chi_Minh"
)

webhook_schedule = ScheduleDefinition(
    job=sapo_webhook_job,
    cron_schedule="* * * * *",
    execution_timezone="Asia/Ho_Chi_Minh"
)

# OTP Schedule: Every 10 minutes (following History Log)
dbt_otp_schedule = ScheduleDefinition(
    job=sapo_dbt_otp_job,
    cron_schedule="*/10 * * * *",
    execution_timezone="Asia/Ho_Chi_Minh"
)

# OLAP Schedule: Hourly (sufficient for BI/Reporting)
dbt_olap_schedule = ScheduleDefinition(
    job=sapo_dbt_olap_job,
    cron_schedule="0 * * * *",
    execution_timezone="Asia/Ho_Chi_Minh"
)

defs = Definitions(
    assets=all_assets,
    schedules=[
        orders_batch_schedule, 
        customers_batch_schedule, 
        accounts_batch_schedule, 
        history_schedule, 
        webhook_schedule, 
        dbt_otp_schedule, 
        dbt_olap_schedule
    ],
    resources={
        "dbt": DbtCliResource(project_dir=dbt.dbt_project),
    },
)
