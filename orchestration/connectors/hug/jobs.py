from dagster import AssetSelection, RunRequest, SkipReason, define_asset_job, schedule

from orchestration.job_support import SYNC_TAGS, has_active_run, long_dbt_rw_holder

from .assets import ingest_hug_webhook_consumer_asset

# Hug webhook poll — separate dataset from Sapo
pipeline_hug_realtime_job = define_asset_job(
    name="pipeline_hug_realtime_job",
    selection=AssetSelection.assets(ingest_hug_webhook_consumer_asset),
    tags=SYNC_TAGS,
)


@schedule(
    job=pipeline_hug_realtime_job,
    cron_schedule="*/3 * * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def pipeline_hug_realtime_schedule(context):
    active = has_active_run(context, "pipeline_hug_realtime_job")
    if active:
        return SkipReason(f"hug_realtime: previous run still active ({active[:8]})")
    holder = long_dbt_rw_holder(context)
    if holder:
        return SkipReason(f"hug_realtime: yielding to {holder} (dbt_rw occupied)")
    if has_active_run(context, "maintain_cleanup_job"):
        return SkipReason("hug_realtime: yielding to maintain_cleanup (SQLite index.db lock)")
    return RunRequest(run_key=None)


JOBS = [pipeline_hug_realtime_job]
SCHEDULES = [pipeline_hug_realtime_schedule]
SENSORS = []
