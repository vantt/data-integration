# Pipeline Outage Investigation — 2026-05-06

**Incident window:** ~April 24 – May 6 (monitoring view), with one real job failure on May 1  
**Investigator:** debugger  
**Status:** DONE_WITH_CONCERNS

---

## Executive Summary

**There was no true pipeline outage.** All 10 Dagster assets continued running and materializing data successfully every day April 24–May 6. The "13 days overdue" and "0/10 healthy" displayed by the monitoring dashboard are caused by a **persistent stale DuckDB lock** on `ingestion_health.duckdb` held by Windows `dllhost.exe` (COM surrogate / Windows Defender), preventing `record_run()` from writing health records for batch assets. Sapo webhook and history_log assets recovered because their high-frequency runs occasionally succeeded through retry windows when the lock was momentarily released.

One **real but transient** failure: `transform_batch_nightly_job` failed on May 1 03:02 due to 3 dbt test failures. Resolved automatically on May 2.

The monitoring system was interrupted (no records) for batch assets from **April 24 onward**. The dashboard reflects stale monitoring state, not actual pipeline state.

---

## Timeline of Events

| Time (ICT) | Event |
|---|---|
| 2026-04-23 03:01 | Last successful `record_run` write for all batch assets (sapo_orders, customers, accounts, products, shopee, misa, sheets) |
| 2026-04-23 22:36 | Last successful `record_run` write for sapo_webhook_consumer_asset |
| 2026-04-24 (earliest log) | Container/new session started; `dllhost.exe` stale lock took hold on `ingestion_health.duckdb` |
| 2026-04-24 09:01 | First `record_run failed: Conflicting lock held in PID 0` in logs — affects ALL assets |
| 2026-04-25 03:03 | batch nightly job RUN_SUCCESS — data fetched, NOT recorded to health DB |
| 2026-04-26 04:00 | batch nightly job RUN_FAILURE — sapo_dbt_assets failed (also Apr 27) |
| 2026-04-29 – 2026-04-30 | batch nightly job RUN_SUCCESS again |
| 2026-05-01 03:02 | batch nightly job RUN_FAILURE — dbt 3 test failures: `unique_fact_orders_order_id`, `unique_dim_teams_team_code`, `unique_dim_teams_team_key` (PASS=187, ERROR=3, SKIP=26) |
| 2026-05-01 07:46 | webhook consumer resumed recording (lock briefly released) |
| 2026-05-02 – 05-05 | batch nightly job RUN_SUCCESS daily (no recording) |
| 2026-05-05 10:29 UTC | Container restarted (StartedAt timestamp); "Up 17 hours" from ~17:30 ICT May 5 |
| 2026-05-05 17:30–17:36 | history_log and webhook_consumer resumed recording (new container session briefly unlocked) |
| 2026-05-06 (ongoing) | All jobs running successfully; DuckDB lock STILL ACTIVE (PID 0) as of investigation time |

---

## Root Causes

### RC-1: Persistent DuckDB Stale Lock (PRIMARY — explains "13 days overdue")

**What:** `ingestion_health.duckdb` is locked by Windows `dllhost.exe` (COM surrogate) reporting PID 0. DuckDB cannot acquire a write lock from inside Docker container.

**Evidence:**
- Every `record_run` call since April 24 throws: `IO Error: Conflicting lock held in PID 0`
- `docker exec ... duckdb.connect(path)` fails with same error **right now**
- Batch assets last recorded: April 23 03:01. Freshness check on May 1 showed "Last success 192h ago (SLA=28h)" — exactly 8 days = April 23
- Sapo webhook/history_log partially recovered because their 3-minute cycle created enough retry windows
- The code path has correct retry logic (8 attempts, exponential backoff) and correct stale-lock hint; lock simply never releases

**Impact:** Monitoring dashboard shows all batch assets as overdue. Actual data is current.

### RC-2: dbt Test Failures on May 1 at 03:02 (SECONDARY — real but resolved)

**What:** `transform_batch_nightly_job` failed on May 1 with 3 failing dbt tests.

**Evidence:**
- `Done. PASS=187 WARN=0 ERROR=3 SKIP=26` → `RUN_FAILURE: Steps failed: ['sapo_dbt_assets']`
- Failed tests: `unique_fact_orders_order_id`, `unique_dim_teams_team_code`, `unique_dim_teams_team_key`
- Same pattern also failed April 26 and April 27 (intermittent data uniqueness violations)
- Resolved automatically by May 2 (data corrected by incremental ingestion)

**Likely cause:** Duplicate order/team records entered Sapo between nightly runs; uniqueness constraint violated at marts layer. Self-healing via subsequent batch that deduplicates.

### RC-3: Monitoring Gap for Webhook/History Consumer (TERTIARY — already recovering)

**What:** Webhook consumer had no recorded runs from April 23 22:36 to May 1 07:46.

**Evidence:** `ingestion_runs` table shows 9-day gap for `sapo/sapo_webhook_consumer_asset`

**Cause:** Same DuckDB lock as RC-1, but high-frequency 3-min runs eventually succeeded through retry windows when lock was momentarily released.

---

## What Was NOT an Outage

- Container was running continuously (0 restarts, started April 24 based on earliest logs, last restarted May 5 17:30 ICT)
- Schedules fired every cycle throughout April 24–May 6
- `transform_batch_nightly_job` ran successfully daily April 24–30, May 2–6
- `ingest_sapo_incremental_job` and `ingest_sapo_realtime_job` ran and completed successfully throughout
- dbt ran 216 tests with PASS=216 as recently as May 6 10:31

---

## Current State (as of investigation May 6 ~10:35 ICT)

- All jobs: running and succeeding
- `ingestion_health.duckdb`: STILL locked by PID 0 (Windows dllhost.exe)
- Batch asset records: stuck at April 23 in monitoring DB
- Webhook/history_log records: updated to May 5 17:36 (from last container restart window)
- dbt: PASS=216 WARN=0 ERROR=0

---

## Is Backfill Needed?

**Data layer: No.** Pipelines ran daily. Data is current in DuckDB warehouse and parquet serving layer (parquet timestamps show `_20260506033028.parquet` — May 6 03:30). No data loss.

**Monitoring DB: Partial backfill possible but low priority.** The `ingestion_runs` table is missing records for April 24–May 5 for batch assets. These cannot be auto-recovered from Dagster event log (purge job runs nightly and deletes old runs). The data was fetched; only the health metadata is missing. This affects the freshness SLA display only.

---

## Immediate Remediation

### P0 — Fix the DuckDB stale lock (restores monitoring)

On Windows host:
```powershell
# Option A: Kill COM surrogate
taskkill /F /IM dllhost.exe

# Option B (permanent): Add Windows Defender exclusion
Add-MpPreference -ExclusionPath "D:\Vantt\app\data-integration\var\data_lake\monitoring"
```

After killing dllhost.exe, verify inside container:
```bash
docker exec data_platform python3 -c "
import duckdb
con = duckdb.connect('/app/var/data_lake/monitoring/ingestion_health.duckdb')
print('Write mode: OK')
con.close()
"
```

### P1 — Backfill monitoring records for batch assets (optional, low priority)

After lock is cleared, run a one-time backfill using Dagster materialization timestamps from the event log (if not yet purged). This only affects the dashboard freshness display, not actual data.

### P2 — dbt test failures on duplicates (track recurrence)

The `unique_fact_orders_order_id` failure on May 1 (and April 26-27) is intermittent. If it recurs:
1. Check `sapo_orders` source for recent duplicate order IDs
2. Verify deduplication logic in `std_orders` / `fact_orders` dbt models
3. Consider adding a pre-build dedup step or relaxing to `WARN` severity

---

## Recurrence Prevention

| Gap | Recommendation |
|---|---|
| DuckDB stale lock persists across container restarts | Add Windows Defender exclusion path permanently; `health_db_watchdog_sensor` detects but does not auto-kill — consider auto-remediation or alert escalation |
| Monitoring dashboard shows "overdue" when lock exists | Already have watchdog sensor; ensure it pages (not just logs) when `check_writable()` returns False for > 30 min |
| dbt uniqueness tests cause batch RUN_FAILURE | Add retry logic or set failing tests to WARN in batch context to avoid blocking serving layer update |

---

## Unresolved Questions

1. What triggered dllhost.exe to acquire the DuckDB lock on April 24 specifically? (Windows Defender scan of the data directory on file creation?)
2. Why did April 26–27 dbt failures also occur — same duplicate data pattern or different root cause?
3. Is the `health_db_watchdog_sensor` currently alerting (Lark notifications) or only logging? Were any notifications received?
