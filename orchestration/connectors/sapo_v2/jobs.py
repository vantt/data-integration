from dagster import AssetSelection, RunRequest, SkipReason, define_asset_job, schedule

from orchestration.assets import dbt, rill, serving
from orchestration.job_support import NIGHTLY_ONLY_ASSETS, SYNC_TAGS, after_serving_selection, has_active_run, long_dbt_rw_holder

from .assets import (
    ingest_sapo_v2_history_log_asset,
    ingest_sapo_v2_inventory_transactions_asset,
    ingest_sapo_v2_webhook_consumer_asset,
)

all_dbt_assets = AssetSelection.assets(dbt.sapo_dbt_assets)

# 1. Realtime Job (Webhook)
pipeline_sapo_v2_realtime_job = define_asset_job(
    name="pipeline_sapo_v2_realtime_job",
    selection=(
        AssetSelection.assets(ingest_sapo_v2_webhook_consumer_asset) | all_dbt_assets | AssetSelection.assets(serving.build_serving_db) | AssetSelection.assets(rill.build_rill_publish) | after_serving_selection()
    ) - NIGHTLY_ONLY_ASSETS,
    tags=SYNC_TAGS,
)

# 2. Incremental Job (History Log)
pipeline_sapo_v2_incremental_job = define_asset_job(
    name="pipeline_sapo_v2_incremental_job",
    selection=(
        AssetSelection.assets(ingest_sapo_v2_history_log_asset) | all_dbt_assets | AssetSelection.assets(serving.build_serving_db) | AssetSelection.assets(rill.build_rill_publish) | after_serving_selection()
    ) - NIGHTLY_ONLY_ASSETS,
    tags={**SYNC_TAGS, "dagster/max_retries": "0"},
)

# 3c. Generic Sapo hourly job — runs inventory-transactions-v2 ingestion through
# the real-time inventory chain: ingest → src_ → std_ → fact_inventory_movements
# (current on-hand + COGS refresh each hour). The daily on-hand snapshot
# (fact_inventory_onhand_daily, ~1.9M rows, DAILY grain) is intentionally left to
# the nightly job. Self-refresh serving views auto-pick the latest mart parquet,
# so no serving asset is needed here. Add future hourly assets to this selection.
pipeline_sapo_v2_hourly_job = define_asset_job(
    name="pipeline_sapo_v2_hourly_job",
    # dbt models tagged 'hourly' in schema.yml are exposed as Dagster tag "dagster-dbt/hourly".
    # This avoids hard-coded AssetKey strings that break silently on model rename.
    selection=(
        AssetSelection.assets(ingest_sapo_v2_inventory_transactions_asset)
        | AssetSelection.tag("dagster-dbt/hourly", "")
    ),
    tags=SYNC_TAGS,
)


@schedule(
    job=pipeline_sapo_v2_realtime_job,
    cron_schedule="*/3 * * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def pipeline_sapo_v2_realtime_schedule(context):
    active = has_active_run(context, "pipeline_sapo_v2_realtime_job")
    if active:
        return SkipReason(f"realtime: previous run still active ({active[:8]})")
    # Yield to long-running batch jobs: a new run can't start (dbt_rw=1 occupied)
    # and would sit NOT_STARTED for 60-90+ min before being auto-canceled.
    # Skip this tick; the next tick in 3 min will retry.
    holder = long_dbt_rw_holder(context)
    if holder:
        return SkipReason(f"realtime: yielding to {holder} (dbt_rw occupied)")
    # Yield to maintain_cleanup: VACUUM on index.db holds an exclusive SQLite lock, causing
    # log event writes to fail for concurrent jobs → stuck sensor kills them as "inactive".
    # Skip instead; next tick in 3 min retries after cleanup completes (~15-20 min window).
    if has_active_run(context, "maintain_cleanup_job"):
        return SkipReason("realtime: yielding to maintain_cleanup (SQLite index.db lock)")
    return RunRequest(run_key=None)


@schedule(
    job=pipeline_sapo_v2_incremental_job,
    # Skip 3 AM hour entirely — nightly batch runs then and holds the
    # dbt_rw slot for ~30-60 minutes. Excluding this hour prevents incremental
    # ticks from piling up while nightly is running.
    #
    # If nightly overruns past 4 AM, long_dbt_rw_holder() skips the tick
    # instead of creating a NOT_STARTED run that would sit for 60-90+ min
    # and trigger QUEUE_STUCK_THRESHOLD auto-cancel.
    cron_schedule="*/10 0-2,4-23 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def pipeline_sapo_v2_incremental_schedule(context):
    active = has_active_run(context, "pipeline_sapo_v2_incremental_job")
    if active:
        return SkipReason(f"incremental: previous run still active ({active[:8]})")
    holder = long_dbt_rw_holder(context)
    if holder:
        return SkipReason(f"incremental: yielding to {holder} (dbt_rw occupied)")
    if has_active_run(context, "maintain_cleanup_job"):
        return SkipReason("incremental: yielding to maintain_cleanup (SQLite index.db lock)")
    return RunRequest(run_key=None)


@schedule(
    job=pipeline_sapo_v2_hourly_job,
    # Run at :25 each hour, skip 3 AM (nightly batch holds dbt_rw ~30-60 min).
    # Minute :25 avoids collision with realtime (*/3) and incremental (*/10).
    # If nightly overruns past 4 AM, long_dbt_rw_holder() skips the tick.
    cron_schedule="25 0-2,4-23 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def pipeline_sapo_v2_hourly_schedule(context):
    active = has_active_run(context, "pipeline_sapo_v2_hourly_job")
    if active:
        return SkipReason(f"hourly: previous run still active ({active[:8]})")
    holder = long_dbt_rw_holder(context)
    if holder:
        return SkipReason(f"hourly: yielding to {holder} (dbt_rw occupied)")
    if has_active_run(context, "maintain_cleanup_job"):
        return SkipReason("hourly: yielding to maintain_cleanup (SQLite index.db lock)")
    return RunRequest(run_key=None)


JOBS = [pipeline_sapo_v2_realtime_job, pipeline_sapo_v2_incremental_job, pipeline_sapo_v2_hourly_job]
SCHEDULES = [pipeline_sapo_v2_realtime_schedule, pipeline_sapo_v2_incremental_schedule, pipeline_sapo_v2_hourly_schedule]
SENSORS = []
