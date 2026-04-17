"""Stuck run sensor — detects and auto-terminates runs with no recent activity.

Detects runs in STARTED state that have no log activity for INACTIVITY_THRESHOLD.
Unlike a fixed timeout, this approach:
- Won't kill legitimate long-running jobs (they have continuous output)
- Will kill hung processes (they produce no output)

Auto-terminates stuck runs and frees concurrency slots to unblock the queue.
Alerts via Lark after termination.

See: plans/260408-1611-fix-serving-db-hang-metabase-lock/plan.md Phase 3.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from dagster import (
    DagsterEventType,
    DagsterRunStatus,
    EventRecordsFilter,
    RunsFilter,
    SensorEvaluationContext,
    SkipReason,
    sensor,
)

from orchestration.notifications.lark_client import send_lark_card

logger = logging.getLogger(__name__)

# No log activity for this long = stuck. 5 minutes is generous since normal
# dbt runs output every few seconds.
INACTIVITY_THRESHOLD = timedelta(minutes=5)

# Minimum runtime before we consider terminating. Prevents killing runs
# that are still initializing (resource setup, partial_parse, etc.).
MIN_RUNTIME_BEFORE_KILL = timedelta(minutes=10)

# Max run_ids kept in cursor to prevent unbounded growth.
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


def _get_last_event_time(context: SensorEvaluationContext, run_id: str) -> datetime | None:
    """Get timestamp of the most recent event for a run."""
    try:
        records = context.instance.get_event_records(
            EventRecordsFilter(
                event_type=DagsterEventType.ENGINE_EVENT,
                after_cursor=None,
            ),
            limit=1,
            ascending=False,
        )
        # Filter for this run_id since EventRecordsFilter doesn't support run_id directly
        # Fall back to checking all recent events
        records = context.instance.get_event_records(
            EventRecordsFilter(),
            limit=100,
            ascending=False,
        )
        for rec in records:
            if rec.dagster_run and rec.dagster_run.run_id == run_id:
                return datetime.fromtimestamp(rec.timestamp, tz=timezone.utc)
    except Exception as exc:
        logger.warning("Failed to get last event time for run %s: %s", run_id[:8], exc)
    return None


@sensor(minimum_interval_seconds=300)  # check every 5 minutes
def health_alert_stuckrun_sensor(context: SensorEvaluationContext):
    """Detect and auto-terminate runs with no recent activity."""
    terminated_ids = _parse_cursor(context.cursor)
    terminated_set = set(terminated_ids)

    instance = context.instance
    now = datetime.now(timezone.utc)
    new_terminations: list[str] = []

    # Get all STARTED runs
    started_records = instance.get_run_records(
        filters=RunsFilter(statuses=[DagsterRunStatus.STARTED])
    )

    for rec in started_records:
        run = rec.dagster_run
        if run.run_id in terminated_set:
            continue
        if not rec.start_time:
            continue

        start_dt = datetime.fromtimestamp(rec.start_time, tz=timezone.utc)
        runtime = now - start_dt

        # Skip if run hasn't been running long enough
        if runtime < MIN_RUNTIME_BEFORE_KILL:
            continue

        # Check last activity time
        last_event_time = _get_last_event_time(context, run.run_id)

        # If we can't get last event time, fall back to start time
        if last_event_time is None:
            last_event_time = start_dt

        inactivity = now - last_event_time

        # Only terminate if inactive for threshold
        if inactivity < INACTIVITY_THRESHOLD:
            continue

        # This run is stuck - terminate it
        logger.warning(
            "Auto-terminating stuck run %s (%s) - no activity for %s, runtime %s",
            run.run_id[:8], run.job_name, inactivity, runtime
        )

        try:
            # Try graceful termination first
            instance.report_run_canceled(run)
        except Exception:
            pass

        try:
            # Force to failed state if still not terminal
            updated_run = instance.get_run_by_id(run.run_id)
            if updated_run and updated_run.status not in [
                DagsterRunStatus.SUCCESS,
                DagsterRunStatus.FAILURE,
                DagsterRunStatus.CANCELED,
            ]:
                instance.report_run_failed(
                    run,
                    f"Auto-terminated: no activity for {inactivity.total_seconds()//60:.0f} minutes"
                )
        except Exception as exc:
            logger.warning("Failed to mark run as failed: %s", exc)

        # Free concurrency slots
        try:
            instance.event_log_storage.free_concurrency_slots_for_run(run.run_id)
            logger.info("Freed concurrency slots for run %s", run.run_id[:8])
        except Exception as exc:
            logger.warning("Failed to free concurrency slots: %s", exc)

        # Alert
        send_lark_card(
            title="🔪 Dagster Run AUTO-KILLED (stuck)",
            color="red",
            fields={
                "Job": run.job_name,
                "Run ID": run.run_id[:8],
                "Runtime": f"{runtime.total_seconds()//60:.0f} min",
                "Inactive": f"{inactivity.total_seconds()//60:.0f} min",
                "Action": "Auto-terminated, slots freed",
            },
        )
        new_terminations.append(run.run_id)

    if new_terminations:
        combined = terminated_ids + new_terminations
        context.update_cursor(json.dumps(combined[-CURSOR_LIMIT:]))
        return SkipReason(f"Auto-terminated {len(new_terminations)} stuck run(s)")

    return SkipReason("No stuck runs detected")
