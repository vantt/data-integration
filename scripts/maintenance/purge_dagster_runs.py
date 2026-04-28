"""Manual Dagster run purge tool — CLI wrapper around the same logic used by the
automated maintain_purge_runs_op. Reuses all helper functions from the op so
fixes in one place apply everywhere.

Usage:
    docker compose exec data_platform python scripts/maintenance/purge_dagster_runs.py [--keep-days N] [--force]

Without --force: dry-run only (lists runs that would be deleted).
"""
import sys
import os
import logging
import argparse
from datetime import datetime, timedelta

# Allow importing from the orchestration package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dagster import DagsterInstance, RunsFilter
from orchestration.ops.purge_runs import (
    _TERMINATED_STATUSES,
    _delete_run_with_retry,
    _remove_run_db_files,
    _remove_run_storage,
    _cleanup_orphans,
    _cleanup_orphan_event_entries,
    _cleanup_orphan_asset_check_executions,
    _vacuum_index_db,
    _get_run_db_dir,
)

logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Purge Dagster runs manually (mirrors maintain_purge_runs_op logic).")
    parser.add_argument("--keep-days", type=int, default=1, help="Days of history to keep (default: 1).")
    parser.add_argument("--force", action="store_true", help="Actually delete. Without this: dry-run only.")
    args = parser.parse_args()

    if args.keep_days < 1:
        print("Error: --keep-days must be >= 1.")
        sys.exit(1)

    cutoff_date = datetime.now() - timedelta(days=args.keep_days)
    print(f"Keep last {args.keep_days} day(s) — cutoff: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")

    instance = DagsterInstance.get()

    # WAL size early warning (same as op)
    run_dir = _get_run_db_dir(instance)
    wal_path = os.path.join(run_dir, 'index.db-wal')
    if os.path.exists(wal_path):
        wal_mb = os.path.getsize(wal_path) / (1024 * 1024)
        if wal_mb > 100:
            log.warning(f"index.db-wal is {wal_mb:.0f} MB — previous run may have been interrupted")
        else:
            log.info(f"index.db-wal: {wal_mb:.1f} MB")

    # Only purge TERMINATED runs — same guard as the op
    filters = RunsFilter(created_before=cutoff_date, statuses=_TERMINATED_STATUSES)
    records = instance.get_run_records(filters=filters, ascending=True)
    count = len(records)

    if count == 0:
        print("No terminated runs to purge.")
    else:
        print(f"Found {count} runs to {'delete' if args.force else 'delete [DRY RUN]'}:")
        for rec in records[:10]:
            run = rec.dagster_run
            ts = datetime.fromtimestamp(rec.create_timestamp).strftime('%Y-%m-%d %H:%M')
            print(f"  {ts}  {run.run_id[:12]}  [{run.status.name}]  {run.job_name}")
        if count > 10:
            print(f"  ... and {count - 10} more.")

    if not args.force:
        print("\nDry-run — pass --force to actually delete.")
        return

    # Delete runs
    known_run_ids = set(r.run_id for r in instance.get_runs(limit=10000))

    deleted = db_files = storage_dirs = 0
    for i, rec in enumerate(records):
        run_id = rec.dagster_run.run_id
        if _delete_run_with_retry(instance, run_id, log):
            deleted += 1
            db_files += _remove_run_db_files(instance, run_id)
            storage_dirs += _remove_run_storage(instance, run_id)
        if (i + 1) % 100 == 0:
            log.info(f"Progress: {i + 1}/{count}")

    print(f"Deleted {deleted} runs, {db_files} db files, {storage_dirs} storage dirs.")

    # Re-fetch after deletions
    known_run_ids = set(r.run_id for r in instance.get_runs(limit=10000))

    orphan_db, orphan_storage = _cleanup_orphans(instance, known_run_ids)
    if orphan_db or orphan_storage:
        print(f"Orphan cleanup: {orphan_db} db files, {orphan_storage} storage dirs.")

    orphan_events = _cleanup_orphan_event_entries(instance, known_run_ids, log)
    orphan_checks = _cleanup_orphan_asset_check_executions(instance, log)

    size_before, size_after = _vacuum_index_db(instance, log)
    print(f"VACUUM index.db: {size_before:.0f} MB → {size_after:.0f} MB")
    print("Done.")


if __name__ == "__main__":
    main()
