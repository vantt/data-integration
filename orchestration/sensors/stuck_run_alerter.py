"""Stuck run sensor — detects runs in STARTED state longer than threshold.

Fills the gap left by run_failure_sensor, which only fires on terminal FAILURE.
A hung run (e.g. subprocess deadlock) remains in STARTED indefinitely with no
failure event. This sensor polls every 10 minutes, alerts once per run_id via
cursor dedup, and does NOT auto-kill — operator decides recovery action.

See plans/260408-1611-fix-serving-db-hang-metabase-lock/plan.md Phase 3.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from dagster import (
    DagsterRunStatus,
    RunsFilter,
    SensorEvaluationContext,
    SkipReason,
    sensor,
)

from orchestration.notifications.lark_client import send_lark_card

# A run older than this while still STARTED is considered stuck.
# Must be larger than SERVING_TIMEOUT_SEC (1800s = 30min) to avoid firing
# before the subprocess timeout path can raise naturally.
STUCK_THRESHOLD = timedelta(minutes=45)

# Max run_ids kept in cursor to prevent unbounded growth. Oldest entries
# drop off FIFO — they won't re-alert because they're no longer STARTED.
CURSOR_LIMIT = 100


def _parse_cursor(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        val = json.loads(raw)
        if isinstance(val, list):
            return [str(x) for x in val]
    except (ValueError, TypeError):
        pass
    return []


@sensor(minimum_interval_seconds=600)  # tick every 10 minutes
def health_alert_stuckrun_sensor(context: SensorEvaluationContext):
    """Alert on any run that has been STARTED longer than STUCK_THRESHOLD."""
    alerted = _parse_cursor(context.cursor)
    alerted_set = set(alerted)

    instance = context.instance
    # Use get_run_records (not get_runs) — only RunRecord exposes start_time.
    # DagsterRun (returned by get_runs) has no start_time attribute in dagster 1.x+.
    started_records = instance.get_run_records(
        filters=RunsFilter(statuses=[DagsterRunStatus.STARTED])
    )
    now = datetime.now(timezone.utc)
    new_alerts: list[str] = []

    for rec in started_records:
        run = rec.dagster_run
        if run.run_id in alerted_set:
            continue
        if not rec.start_time:
            continue
        start_dt = datetime.fromtimestamp(rec.start_time, tz=timezone.utc)
        age = now - start_dt
        if age < STUCK_THRESHOLD:
            continue

        send_lark_card(
            title="⏱️ Dagster Run STUCK (no auto-kill)",
            color="orange",
            fields={
                "Job": run.job_name,
                "Run ID": run.run_id,
                "Started": start_dt.isoformat(timespec="seconds"),
                "Age": str(age).split(".")[0],
                "Action": "Operator manual investigation required",
            },
        )
        new_alerts.append(run.run_id)

    if new_alerts:
        combined = alerted + new_alerts
        # Keep most-recent CURSOR_LIMIT ids
        context.update_cursor(json.dumps(combined[-CURSOR_LIMIT:]))
        return SkipReason(f"Alerted {len(new_alerts)} stuck run(s)")

    return SkipReason("No stuck runs detected")
