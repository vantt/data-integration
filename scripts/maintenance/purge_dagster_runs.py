import sys
import os
import shutil
import argparse
from datetime import datetime, timedelta
from dagster import DagsterInstance, RunsFilter, DagsterRunStatus
import duckdb

def _get_run_db_dir(instance):
    """Resolve the per-run SQLite directory from the Dagster instance."""
    storage = instance._event_storage
    if hasattr(storage, '_base_dir'):
        return os.path.join(storage._base_dir, 'runs')
    dagster_home = os.environ.get('DAGSTER_HOME', '')
    return os.path.join(dagster_home, 'history', 'runs')


def _get_storage_dir(instance):
    """Resolve the compute-log storage directory (stdout/stderr per run)."""
    dagster_home = os.environ.get('DAGSTER_HOME', '')
    return os.path.join(dagster_home, 'storage')


def _remove_run_db_files(instance, run_id):
    """Delete the per-run .db / .db-wal / .db-shm files for a given run_id."""
    run_dir = _get_run_db_dir(instance)
    removed = 0
    for ext in ('.db', '.db-wal', '.db-shm'):
        path = os.path.join(run_dir, run_id + ext)
        try:
            if os.path.exists(path):
                os.remove(path)
                removed += 1
        except OSError:
            pass
    return removed


def _remove_run_storage(instance, run_id):
    """Delete the storage/{run_id}/ directory (compute logs: stdout/stderr)."""
    storage_dir = _get_storage_dir(instance)
    run_storage = os.path.join(storage_dir, run_id)
    if os.path.isdir(run_storage):
        shutil.rmtree(run_storage, ignore_errors=True)
        return 1
    return 0


def _cleanup_orphans(instance):
    """Remove .db files and storage dirs with no matching run record."""
    known_ids = set(r.run_id for r in instance.get_runs(limit=999999))
    db_removed = 0
    storage_removed = 0

    # Orphan .db files
    run_dir = _get_run_db_dir(instance)
    if os.path.isdir(run_dir):
        for f in os.listdir(run_dir):
            if not f.endswith('.db') or f == 'index.db':
                continue
            run_id = f[:-3]
            if run_id in known_ids:
                continue
            for ext in ('.db', '.db-wal', '.db-shm'):
                path = os.path.join(run_dir, run_id + ext)
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        db_removed += 1
                except OSError:
                    pass

    # Orphan storage dirs
    storage_dir = _get_storage_dir(instance)
    if os.path.isdir(storage_dir):
        for d in os.listdir(storage_dir):
            if d not in known_ids and os.path.isdir(os.path.join(storage_dir, d)):
                shutil.rmtree(os.path.join(storage_dir, d), ignore_errors=True)
                storage_removed += 1

    return db_removed, storage_removed


def _vacuum_index_db(instance):
    """VACUUM the per-run event log index to reclaim space after mass deletion."""
    run_dir = _get_run_db_dir(instance)
    index_path = os.path.join(run_dir, 'index.db')
    if not os.path.exists(index_path):
        return
    size_before = os.path.getsize(index_path) / (1024 * 1024)
    try:
        conn = duckdb.connect()
        conn.execute(f"ATTACH '{index_path}' AS idx (TYPE sqlite)")
        conn.execute("CALL sqlite_execute('idx', 'VACUUM')")
        conn.close()
    except Exception:
        # Fallback: direct sqlite3
        import sqlite3
        c = sqlite3.connect(index_path)
        c.execute('VACUUM')
        c.close()
    size_after = os.path.getsize(index_path) / (1024 * 1024)
    print(f"VACUUM index.db: {size_before:.0f} MB → {size_after:.0f} MB")


def main():
    parser = argparse.ArgumentParser(description="Purge Dagster runs based on retention policy.")
    parser.add_argument("--keep-days", type=int, default=1, help="Number of days of run history to keep (default: 1).")
    parser.add_argument("--status", type=str, help="Filter by run status (e.g., FAILURE, SUCCESS). If not set, all statuses are considered.")
    parser.add_argument("--force", action="store_true", help="Actually delete the runs. Without this, runs are only listed (dry-run).")
    
    args = parser.parse_args()
    
    # Validation
    if args.keep_days < 0:
        print("Error: --keep-days must be non-negative.")
        sys.exit(1)

    # Calculate cutoff
    cutoff_date = datetime.now() - timedelta(days=args.keep_days)
    
    print(f"--- Dagster Run Purge Tool ---")
    print(f"Policy: Keep last {args.keep_days} days.")
    print(f"Cutoff: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
    if args.status:
        print(f"Filter: Status = {args.status}")
    
    # Connect to instance
    try:
        instance = DagsterInstance.get()
    except Exception as e:
        print(f"Error loading Dagster instance: {e}")
        sys.exit(1)
        
    print(f"Connected to Dagster storage: {instance.run_storage}")

    # Build Filters
    status_filter = None
    if args.status:
        try:
            status_filter = DagsterRunStatus[args.status.upper()]
        except KeyError:
            print(f"Error: Invalid status '{args.status}'. Valid statuses: {[s.name for s in DagsterRunStatus]}")
            sys.exit(1)

    filters = RunsFilter(
        created_before=cutoff_date,
        statuses=[status_filter] if status_filter else None
    )

    # Fetch run records sorted oldest-first (RunRecord has create_timestamp, DagsterRun does not)
    print("Fetching runs to purge (this may take a moment)...")
    records = instance.get_run_records(filters=filters, ascending=True)
    count = len(records)

    if count == 0:
        print("No runs found matching the criteria.")
        if args.force:
            print("\nCleaning orphans (files/dirs with no matching run record)...")
            orphan_db, orphan_storage = _cleanup_orphans(instance)
            if orphan_db or orphan_storage:
                print(f"Cleaned {orphan_db} orphan db files, {orphan_storage} orphan storage dirs.")
            else:
                print("No orphans found.")
            print("\nVacuuming index.db...")
            _vacuum_index_db(instance)
        return

    print(f"Found {count} runs created before {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}.")

    def format_ts(ts):
        """Format create_timestamp which may be datetime or float."""
        if isinstance(ts, datetime):
            return ts.strftime('%Y-%m-%d %H:%M:%S')
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

    if not args.force:
        print("\n[DRY RUN] No runs were deleted.")
        print("Use --force to actually delete these runs.")
        print("\nRuns that would be deleted (oldest first):")
        for rec in records[:10]:
            run = rec.dagster_run
            print(f"  {format_ts(rec.create_timestamp)}  {run.run_id[:12]}  [{run.status.name}]  {run.job_name}")
        if count > 10:
            print(f"  ... and {count - 10} more.")
    else:
        print(f"\n[EXECUTING] Deleting {count} runs (oldest first)...")
        deleted_count = 0
        db_files_removed = 0
        storage_dirs_removed = 0
        for i, rec in enumerate(records):
            run_id = rec.dagster_run.run_id
            try:
                instance._run_storage.delete_run(run_id)
                try:
                    instance._event_storage.delete_events(run_id)
                except TypeError:
                    pass
                deleted_count += 1
                db_files_removed += _remove_run_db_files(instance, run_id)
                storage_dirs_removed += _remove_run_storage(instance, run_id)

                if (i + 1) % 100 == 0:
                    print(f"  {i + 1}/{count} (up to {format_ts(rec.create_timestamp)})...")
            except Exception as e:
                print(f"Failed to delete run {run_id}: {e}")

        print(f"\nDeleted {deleted_count} runs, {db_files_removed} db files, {storage_dirs_removed} storage dirs.")

        print("\nCleaning orphans (files/dirs with no matching run record)...")
        orphan_db, orphan_storage = _cleanup_orphans(instance)
        if orphan_db or orphan_storage:
            print(f"Cleaned {orphan_db} orphan db files, {orphan_storage} orphan storage dirs.")
        else:
            print("No orphans found.")

        print("\nVacuuming index.db...")
        _vacuum_index_db(instance)

if __name__ == "__main__":
    main()
