# Purge Dagster Runs

Clean up old Dagster run history from the SQLite database in the Docker environment.

## Steps

1. **Determine Retention**: If the user doesn't specify, default to keeping **1 day**.

2. **Execute Cleanup**:
   ```bash
   docker compose exec data_platform python scripts/maintenance/purge_dagster_runs.py --keep-days <N> --force
   ```
   The `--force` flag is required to actually perform deletion (without it, dry-run only).

3. **Report**: Inform the user of the cutoff date and number of runs deleted.

## User Arguments

Keep days: $ARGUMENTS
