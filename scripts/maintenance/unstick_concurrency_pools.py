"""Free leaked concurrency slots from terminal runs.

Dagster's QueuedRunCoordinator releases tag-based limits on cancel, but
asset-level concurrency pools (e.g. duckdb_lock from op_tags) can leak slots
when runs are cancelled forcibly or killed by container restart.

This script scans every concurrency pool and releases slots held by runs
that are no longer in a non-terminal state. Safe to run any time — it only
touches slots for runs that have already finished.

Usage:
    docker compose exec data_platform python scripts/maintenance/unstick_concurrency_pools.py
"""
from __future__ import annotations

from dagster import DagsterInstance, DagsterRunStatus

ACTIVE_STATUSES = {
    DagsterRunStatus.QUEUED,
    DagsterRunStatus.NOT_STARTED,
    DagsterRunStatus.STARTING,
    DagsterRunStatus.STARTED,
}


def main() -> None:
    inst = DagsterInstance.get()
    els = inst.event_log_storage

    keys = els.get_concurrency_keys()
    if not keys:
        print("No concurrency pools configured. Nothing to do.")
        return

    total_freed = 0
    for key in sorted(keys):
        info = els.get_concurrency_info(key)
        print(
            f"Pool '{key}': slot={info.slot_count} "
            f"active={info.active_slot_count} pending={info.pending_step_count}"
        )

        # Collect run_ids that hold or wait for this pool
        candidates: set[str] = set()
        candidates.update(info.active_run_ids or set())
        candidates.update(info.pending_run_ids or set())

        for run_id in candidates:
            run = inst.get_run_by_id(run_id)
            if run is None:
                # Run record gone — definitely safe to free
                els.free_concurrency_slots_for_run(run_id)
                print(f"  freed (missing run): {run_id[:8]}")
                total_freed += 1
                continue
            if run.status not in ACTIVE_STATUSES:
                els.free_concurrency_slots_for_run(run_id)
                print(f"  freed ({run.status.value}): {run_id[:8]}")
                total_freed += 1

        info_after = els.get_concurrency_info(key)
        print(
            f"  -> after: active={info_after.active_slot_count} "
            f"pending={info_after.pending_step_count}"
        )

    print(f"\nTotal slots freed: {total_freed}")


if __name__ == "__main__":
    main()
