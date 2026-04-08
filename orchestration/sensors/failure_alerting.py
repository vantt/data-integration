"""Run failure sensor — pushes Dagster job failures to Lark (or log stub).

Fires whenever a monitored job transitions to FAILURE. Uses the lark_client
helper which auto-degrades to logging when LARK_ALERT_WEBHOOK is unset.

See plans/260408-1611-fix-serving-db-hang-metabase-lock/plan.md Phase 3.
"""
from dagster import run_failure_sensor, RunFailureSensorContext

from orchestration.notifications.lark_client import send_lark_card


@run_failure_sensor(minimum_interval_seconds=60)
def lark_failure_sensor(context: RunFailureSensorContext):
    """Send failure alert for any job failure in the deployment."""
    run = context.dagster_run
    error_msg = (context.failure_event.message or "")[:500]

    send_lark_card(
        title="🚨 Dagster Job FAILED",
        color="red",
        fields={
            "Job": run.job_name,
            "Run ID": run.run_id,
            "Status": str(run.status),
            "Error": f"```{error_msg}```",
        },
    )
