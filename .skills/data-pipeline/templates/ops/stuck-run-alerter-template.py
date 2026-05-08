"""Stuck run alerter sensor — auto-terminate runs with no recent activity.

TEMPLATE: Copy and customize for your project.

Features:
- Activity-based detection (no log output > threshold = stuck)
- Graceful cancel → force fail → free concurrency slots → kill subprocess
- Lark/Slack alert on termination
- Cursor-based dedup (won't re-terminate same run)

Requirements:
- psutil (for subprocess termination)
- Lark client (or replace with your notification system)

See: .skills/data-pipeline/references/dagster-patterns.md Lesson 10
See: .skills/data-pipeline/references/lessons-learned.md L45-L48
See: .skills/data-pipeline/playbooks/05-ops.md (group playbook)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from dagster import (
    DagsterRunStatus,
    RunsFilter,
    SensorEvaluationContext,
    SkipReason,
    sensor,
)

# TODO: Replace with your notification client
# from orchestration.notifications.lark_client import send_lark_card

logger = logging.getLogger(__name__)

# psutil for cross-platform process killing
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil not available — subprocess termination will be best-effort")

# No log activity for this long = stuck
# 5 min is generous since normal dbt runs output every few seconds
INACTIVITY_THRESHOLD = timedelta(minutes=5)

# Minimum runtime before considering termination
# Prevents killing runs still initializing (resource setup, partial_parse, etc.)
MIN_RUNTIME_BEFORE_KILL = timedelta(minutes=10)

# Max run_ids kept in cursor to prevent unbounded growth
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
        result = context.instance.get_records_for_run(
            run_id=run_id,
            limit=1,
            ascending=False,  # newest first
        )
        if result.records:
            return datetime.fromtimestamp(result.records[0].timestamp, tz=timezone.utc)
    except Exception as exc:
        logger.warning("Failed to get last event time for run %s: %s", run_id[:8], exc)
    return None


def _terminate_subprocess_tree(run_id: str) -> bool:
    """Kill subprocess tree associated with a Dagster run.

    Searches for processes with the run_id in their command line,
    then sends SIGTERM followed by SIGKILL.
    """
    if not HAS_PSUTIL:
        return False

    terminated = False
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = " ".join(proc.info.get('cmdline') or [])
                if run_id[:12] in cmdline:
                    logger.info("Terminating subprocess %s (%s) for run %s",
                                proc.pid, proc.info.get('name'), run_id[:8])
                    try:
                        parent = psutil.Process(proc.pid)
                        children = parent.children(recursive=True)
                        for child in children:
                            child.terminate()
                        parent.terminate()
                        # Wait briefly then force kill survivors
                        gone, alive = psutil.wait_procs(children + [parent], timeout=3)
                        for p in alive:
                            p.kill()
                        terminated = True
                    except psutil.NoSuchProcess:
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        logger.warning("Error during subprocess termination for %s: %s", run_id[:8], e)
    return terminated


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

        # 1. Try graceful cancellation (Dagster state only)
        try:
            instance.report_run_canceled(run)
        except Exception as exc:
            logger.debug("Graceful cancel failed for run %s: %s", run.run_id[:8], exc)

        # 2. Force to failed state if still not terminal
        try:
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

        # 3. Free concurrency slots (critical - prevents pool leak)
        try:
            instance.event_log_storage.free_concurrency_slots_for_run(run.run_id)
            logger.info("Freed concurrency slots for run %s", run.run_id[:8])
        except Exception as exc:
            logger.warning("Failed to free concurrency slots: %s", exc)

        # 4. Kill actual subprocess (report_run_canceled doesn't send OS signals)
        subprocess_killed = _terminate_subprocess_tree(run.run_id)
        if subprocess_killed:
            logger.info("Terminated subprocess tree for run %s", run.run_id[:8])

        # 5. Alert (TODO: replace with your notification system)
        # send_lark_card(
        #     title="🔪 Dagster Run AUTO-KILLED (stuck)",
        #     color="red",
        #     fields={
        #         "Job": run.job_name,
        #         "Run ID": run.run_id[:8],
        #         "Runtime": f"{runtime.total_seconds()//60:.0f} min",
        #         "Inactive": f"{inactivity.total_seconds()//60:.0f} min",
        #         "Action": "Auto-terminated, slots freed",
        #     },
        # )

        new_terminations.append(run.run_id)

    if new_terminations:
        combined = terminated_ids + new_terminations
        context.update_cursor(json.dumps(combined[-CURSOR_LIMIT:]))
        return SkipReason(f"Auto-terminated {len(new_terminations)} stuck run(s)")

    return SkipReason("No stuck runs detected")
