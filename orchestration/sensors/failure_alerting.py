"""Run failure sensor — pushes Dagster job failures to Lark (or log stub).

Fires whenever a monitored job transitions to FAILURE. Uses the lark_client
helper which auto-degrades to logging when LARK_ALERT_WEBHOOK is unset.

See plans/260408-1611-fix-serving-db-hang-metabase-lock/plan.md Phase 3.
"""
import os

from dagster import run_failure_sensor, RunFailureSensorContext

from orchestration.notifications.lark_client import send_lark_card

_DAGSTER_BASE = os.getenv("DAGSTER_URL", f"http://localhost:{os.getenv('DAGSTER_PORT', '3001')}")


@run_failure_sensor(minimum_interval_seconds=60)
def health_alert_failure_sensor(context: RunFailureSensorContext):
    """Send failure alert for any job failure in the deployment."""
    run = context.dagster_run
    error_msg = (context.failure_event.message or "")[:500]
    run_link = f"[{run.run_id[:8]}]({_DAGSTER_BASE}/runs/{run.run_id})"

    send_lark_card(
        title="ChợPulse BI — 🚨 Job FAILED",
        color="red",
        fields={
            "Job": run.job_name,
            "Run": run_link,
            "Error": f"```{error_msg}```",
        },
    )
