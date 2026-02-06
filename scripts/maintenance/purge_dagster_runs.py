import sys
import argparse
import time
from datetime import datetime, timedelta
from dagster import DagsterInstance, RunsFilter, DagsterRunStatus

def main():
    parser = argparse.ArgumentParser(description="Purge Dagster runs based on retention policy.")
    parser.add_argument("--keep-days", type=int, default=1, help="Number of days of run history to keep (default: 30).")
    parser.add_argument("--status", type=str, help="Filter by run status (e.g., FAILURE, SUCCESS). If not set, all statuses are considered.")
    parser.add_argument("--force", action="store_true", help="Actually delete the runs. Without this, runs are only listed (dry-run).")
    
    args = parser.parse_args()
    
    # Validation
    if args.keep_days < 0:
        print("Error: --keep-days must be non-negative.")
        sys.exit(1)

    # Calculate cutoff
    cutoff_date = datetime.now() - timedelta(days=args.keep_days)
    cutoff_timestamp = cutoff_date.timestamp()
    
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

    # Fetch runs
    print("Fetching runs to purge (this may take a moment)...")
    runs_to_delete = instance.get_runs(filters=filters)
    count = len(runs_to_delete)
    
    if count == 0:
        print("No runs found matching the criteria.")
        return

    print(f"Found {count} runs created before {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}.")

    if not args.force:
        print("\n[DRY RUN] No runs were deleted.")
        print("Use --force to actually delete these runs.")
        # Print sample
        print("\nSample of runs that would be deleted:")
        print("\nSample of runs that would be deleted:")
        for run in runs_to_delete[:5]:
            print(f" - {run.run_id} [{run.status}]")
        if count > 5:
            print(f" ... and {count - 5} more.")
    else:
        print(f"\n[EXECUTING] Deleting {count} runs...")
        deleted_count = 0
        for i, run in enumerate(runs_to_delete):
            try:
                instance.delete_run(run.run_id)
                deleted_count += 1
                if (i + 1) % 10 == 0:
                    print(f"Deleted {i + 1}/{count}...")
            except Exception as e:
                print(f"Failed to delete run {run.run_id}: {e}")
        
        print(f"\nCompleted. Deleted {deleted_count} runs.")

if __name__ == "__main__":
    main()
