---
name: Purge Dagster Runs
description: A skill to easily clean up and purge old Dagster runs from the SQLite database running in the local Docker environment.
---

# Purge Dagster Runs Skill

## Overview
As the data integration pipelines run, Dagster accumulates run history in its underlying SQLite database. Over time, this can lead to bloated databases, lock contention, and reduced performance. This skill provides the standard operating procedure for the AI Assistant to clean up old runs.

## Prerequisites
- The Data Platform project must be running via Docker Compose (specifically the `data_platform` container).
- The `scripts/maintenance/purge_dagster_runs.py` script must exist in the repository.

## Instructions for the Assistant

When the user requests to clean, purge, or delete old Dagster runs, follow these precise steps:

### 1. Identify the Retention Period
If the user does not specify a timeframe, **default to keeping `1` day**.
If the user specifies a different number of days (e.g., 3 days, 7 days), adjust the `--keep-days` parameter accordingly.

### 2. Execute the Cleanup Command
You **must** execute the maintenance script from *inside* the `data_platform` Docker container, as that environment has `dagster` installed and properly configured.

Use the `run_command` tool to execute the following:
```bash
docker compose exec data_platform python scripts/maintenance/purge_dagster_runs.py --keep-days <NUMBER_OF_DAYS> --force
```

*(Note: The `--force` flag is mandatory to actually perform the deletion, otherwise it will only do a dry-run).*

### 3. Report the Outcome
After the command completes, carefully read the stdout output and inform the user of:
- The cutoff date used for deletion.
- How many runs were successfully deleted.
- If no runs were found (e.g., "No runs found matching the criteria.").
