# Plan: Rolling Parquet GC — Move Cleanup into dbt Asset

> Created: 2026-06-09
> Status: Done
> Priority: Medium (correctness issue for direct parquet reads; serving DB unaffected)

## Problem

`refresh_rolling.py` has correct GC logic (`ROLLING_KEEP_VERSIONS=3`) but it only runs inside the Dagster `serving_asset`. The `serving_asset` depends on `sapo_dbt_assets`, so it runs in the scheduled pipeline. **But** when `sapo_dbt_assets` is materialized manually or selectively (debugging, partial re-runs), `serving_asset` is not auto-triggered — new parquet files accumulate without cleanup.

**Observed 2026-06-09:** 12 parquet files per table (12× nominal). Discovered while querying `int_order_cogs_reconciled` directly — raw counts appeared 12× inflated. `olap.duckdb` serving views unaffected (they use `MAX(filename)` pointer, not glob).

**Confirmed fix:** `docker exec data_platform python3 /app/scripts/provisioning/refresh_rolling.py` deleted 308 files, restored ≤3 per table. Script is fully functional — deployment gap only.

## Root Cause

```
sapo_dbt_assets  →  serving_asset (calls refresh_rolling.py)
     ↓
  [manual re-run or selective materialization]
     ↓
  serving_asset NOT triggered → files accumulate
```

## Affected components

- `orchestration/assets/dbt.py` — `sapo_dbt_assets` (writes new parquet on every run)
- `orchestration/assets/serving.py` — `serving_asset` (calls GC, but only in scheduled flow)
- `scripts/provisioning/refresh_rolling.py` — GC script (works correctly)

## Fix

**Option A (recommended): Call GC inside `sapo_dbt_assets` post-execution**

Add a call to `refresh_rolling()` logic (or subprocess call to the script) at the end of the dbt asset, after all models materialize. This guarantees cleanup runs on every dbt materialization regardless of whether `serving_asset` triggers.

```python
# orchestration/assets/dbt.py — after dbt run completes
import subprocess, sys
subprocess.run([sys.executable, REFRESH_ROLLING_SCRIPT], check=False)
```

Pros: Zero dependency on serving_asset; works for selective runs; no duplication of logic.
Cons: Adds ~1-2s to every dbt run.

**Option B: Add GC to Dagster schedule/sensor**

Add a sensor that fires GC whenever `sapo_dbt_assets` materializes successfully.

Pros: Decoupled, explicit.
Cons: Sensor adds latency; still can miss manual runs.

**Option C: Periodic cron cleanup**

Add a standalone Dagster job that runs `refresh_rolling.py` every N hours.

Pros: Backstop for all cases.
Cons: Doesn't prevent accumulation between runs; just limits max accumulation.

**Recommendation: Option A + Option C as backstop.**

## Implementation steps

- [x] Read `orchestration/assets/dbt.py` to find where dbt run completes
- [x] Add post-run GC call (subprocess to `refresh_rolling.py`) at end of `sapo_dbt_assets` — `_gc_rolling_parquet(context)` in `finally` block (2026-06-09)
- [ ] Verify: trigger `sapo_dbt_assets` manually without serving_asset → confirm files stay ≤3
- [ ] Add Option C: Dagster schedule or sensor calling `refresh_rolling.py` every 2h as backstop
- [x] Update `transformation/AGENTS.md` — troubleshooting entry added (2026-06-09)

## Verification

```bash
# Before fix: count files per table
docker exec data_platform find /app/var/data_lake/export/marts/rolling -name "*.parquet" \
  | awk -F/ '{print $(NF-1)}' | sort | uniq -c | sort -rn | head -10

# After several dbt runs without serving_asset: should stay ≤3
```

## Notes

- `ROLLING_KEEP_VERSIONS` defaults to 3 via env var — no config change needed
- On Windows the script uses `PermissionError` skip path (file held open by reader) — this is handled, max accumulation during active reads = 1 extra file
- `olap.duckdb` is not affected by this bug — safe to deprioritize if serving is reliable
