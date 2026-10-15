from dagster import AssetSelection, DefaultScheduleStatus, ScheduleDefinition, define_asset_job

from .crm_sync import crm_backup, crm_restore_verify

# Daily CRM backup + restore-verify drill — independent of the warehouse (no dbt_rw lock).
# crm_backup triggers /admin/backup (verified SQLite snapshot → crm_backups volume); then
# crm_restore_verify (deps=[crm_backup]) POSTs the crm_drill_runner sidecar to boot an
# ephemeral CRM from that backup and prove it's restorable. Both fail loudly so
# health_alert_failure_sensor alerts on a failed backup OR a non-restorable one — a backup
# isn't trusted until proven recoverable.
crm_backup_job = define_asset_job(
    name="crm_backup_job",
    selection=AssetSelection.assets(crm_backup, crm_restore_verify),
)
crm_backup_schedule = ScheduleDefinition(
    name="crm_backup_schedule",
    job=crm_backup_job,
    cron_schedule="0 2 * * *",  # 02:00 ICT daily (outside the 03:00-06:00 maintenance window)
    # Without it Dagster reads the cron in UTC and the job ran at 09:00 ICT.
    execution_timezone="Asia/Ho_Chi_Minh",
    default_status=DefaultScheduleStatus.RUNNING,  # auto-enable (schedules in defs are off by default — L49)
)

JOBS = [crm_backup_job]
SCHEDULES = [crm_backup_schedule]
SENSORS = []
