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
import os
import signal
from datetime import datetime, timedelta, timezone

from dagster import (
    DagsterRunStatus,
    RunsFilter,
    SensorEvaluationContext,
    SkipReason,
    sensor,
)

from orchestration.notifications.lark_client import send_lark_card

logger = logging.getLogger(__name__)

# Import psutil for cross-platform process killing (works in Docker)
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil not available — subprocess termination will be best-effort")

# No log activity for this long = stuck. 5 minutes is generous since normal
# dbt runs output every few seconds.
INACTIVITY_THRESHOLD = timedelta(minutes=5)

# Minimum runtime before we consider terminating. Prevents killing runs
# that are still initializing (resource setup, partial_parse, etc.).
MIN_RUNTIME_BEFORE_KILL = timedelta(minutes=10)

# Runs stuck in NOT_STARTED/QUEUED/STARTING for this long indicate the queue
# coordinator daemon never picked them up (daemon crashed, disk full, frozen
# by SQLite lock storm, etc.).
#
# Sizing: realtime/incremental max runtime ~10 min; _long_dbt_rw_holder in
# definitions.py skips new ticks while nightly is STARTED, so NOT_STARTED
# accumulation during the nightly ~60 min window no longer happens. 20 min
# covers the max legitimate wait (one job ahead in the dbt_rw=1 queue) with
# a 10 min buffer for initialization overhead.
QUEUE_STUCK_THRESHOLD = timedelta(minutes=20)

# Max run_ids kept in cursor to prevent unbounded growth.
CURSOR_LIMIT = 100


def _terminate_subprocess_tree(run_id: str) -> bool:
    """Kill any subprocess tree associated with a Dagster run.

    Searches for processes with the run_id in their environment (DAGSTER_RUN_JOB_NAME
    or similar) or command line, then sends SIGTERM followed by SIGKILL.

    Returns True if any process was terminated.
    """
    if not HAS_PSUTIL:
        return False

    terminated = False
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'environ']):
            try:
                # Check if this process belongs to the run
                cmdline = " ".join(proc.info.get('cmdline') or [])
                env = proc.info.get('environ') or {}

                # Look for run_id in command line or environment
                if run_id[:12] in cmdline or run_id[:12] in str(env):
                    logger.info("Terminating subprocess %s (%s) for run %s",
                                proc.pid, proc.info.get('name'), run_id[:8])

                    # Kill entire process tree (dbt may spawn child processes)
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
    """Get timestamp of the most recent event for a run.

    Uses get_records_for_run() which filters server-side by run_id.
    This is more efficient and correct than fetching global events
    and filtering client-side (which could miss events).
    """
    try:
        # get_records_for_run filters by run_id server-side — correct API
        # ascending=False → newest first → limit=1 gets most recent event
        result = context.instance.get_records_for_run(
            run_id=run_id,
            limit=1,
            ascending=False,  # CRITICAL: newest first, not oldest
        )
        if result.records:
            return datetime.fromtimestamp(result.records[0].timestamp, tz=timezone.utc)
    except Exception as exc:
        logger.warning("Failed to get last event time for run %s: %s", run_id[:8], exc)
    return None


@sensor(minimum_interval_seconds=60)  # check every 60s
# Cheap: each tick lists runs filtered by status (small set, indexed query).
# Tighter than the 5-min INACTIVITY_THRESHOLD so detection latency for Pass 1
# is bounded (a stuck run is caught within ~6 min total instead of ~10 min).
# Pass 2 (queue-stuck >2h) sees negligible benefit but pays no extra cost.
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

        # If we can't read the event log (e.g. SQLite locked by purge_runs VACUUM),
        # skip this run for this tick — don't false-positive kill a healthy job.
        if last_event_time is None:
            continue

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
        except Exception as exc:
            logger.debug("Graceful cancel failed for run %s: %s", run.run_id[:8], exc)

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

        # Kill actual subprocess — Dagster state update doesn't send OS signals
        subprocess_killed = _terminate_subprocess_tree(run.run_id)
        if subprocess_killed:
            logger.info("Terminated subprocess tree for run %s", run.run_id[:8])

        # Alert
        send_lark_card(
            title="ChợPulse BI — 🔪 Run AUTO-KILLED (stuck)",
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

    # --- Pass 2: queue-stuck runs (never dequeued) ---
    # Catches runs frozen in NOT_STARTED/QUEUED/STARTING because the run
    # coordinator daemon was unable to dequeue (most often from SQLite I/O
    # errors during disk-full, daemon OOM, or grpc code server crash).
    # Pass 1 misses these entirely because they never reach STARTED.
    queue_records = instance.get_run_records(
        filters=RunsFilter(statuses=[
            DagsterRunStatus.NOT_STARTED,
            DagsterRunStatus.QUEUED,
            DagsterRunStatus.STARTING,
        ])
    )
    for rec in queue_records:
        run = rec.dagster_run
        if run.run_id in terminated_set:
            continue
        if not rec.create_timestamp:
            continue

        create_dt = rec.create_timestamp
        if isinstance(create_dt, (int, float)):
            create_dt = datetime.fromtimestamp(create_dt, tz=timezone.utc)
        elif create_dt.tzinfo is None:
            create_dt = create_dt.replace(tzinfo=timezone.utc)

        age = now - create_dt
        if age < QUEUE_STUCK_THRESHOLD:
            continue

        logger.warning(
            "Auto-canceling queue-stuck run %s (%s) — status %s, age %s",
            run.run_id[:8], run.job_name, run.status.value, age
        )

        try:
            instance.report_run_canceled(run)
        except Exception as exc:
            logger.warning("Cancel failed for queue-stuck %s: %s", run.run_id[:8], exc)
            try:
                instance.report_run_failed(
                    run, f"Auto-canceled: stuck in {run.status.value} for {age}"
                )
            except Exception as exc2:
                logger.warning("Failed-state fallback also failed: %s", exc2)

        try:
            instance.event_log_storage.free_concurrency_slots_for_run(run.run_id)
        except Exception as exc:
            logger.debug("Free slots failed (often expected for never-started runs): %s", exc)

        send_lark_card(
            title="ChợPulse BI — 🪦 Run AUTO-CANCELED (queue-stuck)",
            color="orange",
            fields={
                "Job": run.job_name,
                "Run ID": run.run_id[:8],
                "Status was": run.status.value,
                "Age": f"{age.total_seconds()//60:.0f} min",
                "Action": "Auto-canceled (daemon never dequeued)",
            },
        )
        new_terminations.append(run.run_id)

    if new_terminations:
        combined = terminated_ids + new_terminations
        context.update_cursor(json.dumps(combined[-CURSOR_LIMIT:]))
        return SkipReason(f"Auto-terminated {len(new_terminations)} stuck run(s)")

    return SkipReason("No stuck runs detected")
