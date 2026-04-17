"""Concurrency pool janitor — auto-cleans leaked slots from terminal/crashed runs.

Dagster's QueuedRunCoordinator releases tag-based limits on cancel, but
asset-level concurrency pools (e.g. duckdb_lock from op_tags) can leak slots
when runs are cancelled forcibly or killed by container restart.

This sensor runs every 5 minutes and:
1. Scans all concurrency pools
2. Finds slots held by runs in terminal state (SUCCESS, FAILURE, CANCELED)
3. Automatically frees those slots
4. Logs cleanup actions (no alert spam — this is housekeeping)

See: scripts/maintenance/unstick_concurrency_pools.py for manual version.
"""
from __future__ import annotations

import logging

from dagster import (
    DagsterRunStatus,
    SensorEvaluationContext,
    SkipReason,
    sensor,
)

logger = logging.getLogger(__name__)

# Runs in these states are still active — don't free their slots.
ACTIVE_STATUSES = {
    DagsterRunStatus.QUEUED,
    DagsterRunStatus.NOT_STARTED,
    DagsterRunStatus.STARTING,
    DagsterRunStatus.STARTED,
}


@sensor(minimum_interval_seconds=300)  # every 5 minutes
def health_concurrency_pool_janitor(context: SensorEvaluationContext):
    """Free leaked concurrency slots from terminal runs."""
    instance = context.instance
    els = instance.event_log_storage

    # Get all concurrency pool keys
    try:
        keys = els.get_concurrency_keys()
    except Exception as exc:
        logger.warning("Could not get concurrency keys: %s", exc)
        return SkipReason(f"Error getting concurrency keys: {exc}")

    if not keys:
        return SkipReason("No concurrency pools configured")

    total_freed = 0
    details = []

    for key in keys:
        try:
            info = els.get_concurrency_info(key)
        except Exception as exc:
            logger.warning("Could not get info for pool '%s': %s", key, exc)
            continue

        # Collect run_ids that hold or wait for this pool
        candidates: set[str] = set()
        if info.active_run_ids:
            candidates.update(info.active_run_ids)
        if info.pending_run_ids:
            candidates.update(info.pending_run_ids)

        freed_this_pool = 0
        for run_id in candidates:
            run = instance.get_run_by_id(run_id)

            should_free = False
            reason = ""

            if run is None:
                # Run record gone — definitely safe to free
                should_free = True
                reason = "missing"
            elif run.status not in ACTIVE_STATUSES:
                # Run is terminal — slot should have been freed
                should_free = True
                reason = run.status.value

            if should_free:
                try:
                    els.free_concurrency_slots_for_run(run_id)
                    freed_this_pool += 1
                    logger.info(
                        "Freed leaked slot in pool '%s' from run %s (%s)",
                        key, run_id[:8], reason
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to free slot for run %s in pool '%s': %s",
                        run_id[:8], key, exc
                    )

        if freed_this_pool > 0:
            details.append(f"{key}:{freed_this_pool}")
            total_freed += freed_this_pool

    if total_freed > 0:
        msg = f"Freed {total_freed} leaked slot(s): {', '.join(details)}"
        logger.info(msg)
        return SkipReason(msg)

    return SkipReason("No leaked slots found")
