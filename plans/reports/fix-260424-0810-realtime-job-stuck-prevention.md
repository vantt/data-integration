# Fix Report: Realtime Job Stuck Prevention

**Date:** 2026-04-24  
**Issue:** Multiple `ingest_sapo_realtime_job` runs stuck (14+ min inactive, auto-terminated)

---

## Root Cause Analysis

### Primary: No dbt subprocess timeout
`dbt.cli(["build"]).stream()` at `orchestration/assets/dbt.py:136` had no timeout. When dbt subprocess enters DuckDB WAL checkpoint hang (I/O pressure from backup or Metabase reads), Dagster blocks indefinitely.

### Secondary: Stuck alerter didn't kill subprocess
`stuck_run_alerter.py` only updated Dagster state (`report_run_canceled`), never sent OS signals. The dbt subprocess survived "termination", holding DuckDB file handles.

### Contributing: Backup I/O pressure
`maintain_backup_platform_job` copies `sapo_warehouse.duckdb` while dbt is writing, causing kernel I/O competition during WAL checkpoint.

---

## Fixes Implemented

### Fix 1: dbt subprocess timeout watchdog
**File:** `orchestration/assets/dbt.py`

Added 15-minute (configurable via `DBT_TIMEOUT_SEC` env var) watchdog timer that kills the dbt subprocess if it exceeds timeout.

```python
DBT_TIMEOUT_SEC = int(os.environ.get("DBT_TIMEOUT_SEC", "900"))

# In sapo_dbt_assets:
invocation = dbt.cli(["build"], context=context)
watchdog = threading.Timer(DBT_TIMEOUT_SEC, lambda: invocation.process.kill())
watchdog.daemon = True
watchdog.start()
try:
    yield from invocation.stream()
finally:
    watchdog.cancel()
```

### Fix 2: Subprocess tree termination in stuck alerter
**File:** `orchestration/sensors/stuck_run_alerter.py`

Added `_terminate_subprocess_tree()` using `psutil` to find and kill processes associated with a stuck run. Searches by run_id in command line/environment, then sends SIGTERM → SIGKILL to entire process tree.

Called after `free_concurrency_slots_for_run()` to ensure actual subprocess is killed, not just Dagster state updated.

### Fix 3: Backup concurrency lock
**File:** `orchestration/ops/system_backup.py`

Added `"dagster/concurrency_key": "duckdb_lock"` to backup op. This ensures backup waits for dbt to finish before copying DuckDB files, preventing I/O competition during WAL checkpoint.

---

## Testing

- Python syntax verified: all 3 files compile successfully
- Fixes are defensive (graceful degradation if psutil unavailable)
- Timeout configurable via environment variable

### Dependency: psutil
**File:** `ingestion/requirements.txt`

Added `psutil` for cross-platform process tree termination.

---

## Deployment

Rebuild Docker image to include psutil, then restart:
```bash
docker compose build data_platform
docker compose up -d data_platform
```

## Monitoring

After deployment, verify:
1. Next `ingest_sapo_realtime_job` completes in <2 min (normal)
2. No stuck runs in the following 24h
3. Backup job waits if dbt is running (check Dagster run queue)
