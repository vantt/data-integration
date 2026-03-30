import sys
import argparse
from datetime import datetime, timedelta
from dagster import DagsterInstance, RunsFilter, DagsterRunStatus

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
        for i, rec in enumerate(records):
            run_id = rec.dagster_run.run_id
            try:
                # Delete run metadata and event logs separately to handle SQLite datetime issues
                instance._run_storage.delete_run(run_id)
                try:
                    instance._event_storage.delete_events(run_id)
                except TypeError:
                    pass  # SQLite datetime conversion issue in event storage, run record already deleted
                deleted_count += 1
                if (i + 1) % 10 == 0:
                    print(f"Deleted {i + 1}/{count} (up to {format_ts(rec.create_timestamp)})...")
            except Exception as e:
                print(f"Failed to delete run {run_id}: {e}")

        print(f"\nCompleted. Deleted {deleted_count} runs.")

if __name__ == "__main__":
    main()
