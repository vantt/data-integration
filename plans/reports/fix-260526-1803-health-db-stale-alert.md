# Fix Report: Health DB Stale Alert (2026-05-26)

**Alert**: `⚠️ Health DB ngừng ghi — recorder có thể lỗi`  
**Triggered**: 16:48:35 ICT (watchdog detected 2.1h write gap)  
**Resolved**: self-healed via container restart at ~16:48 ICT

---

## Root Cause

**Primary**: Dagster code server crash at **15:03 ICT** with `DagsterInvalidDefinitionError: The following dbt resources are configured with identical Dagster asset keys`.

**Trigger chain**:
1. `14:43` — last successful ingestion run
2. `14:46` — `ingest_sapo_realtime_job` step `sapo_serving_db` crashed in subprocess with `DagsterInvalidDefinitionError` (stale dbt manifest — shopee_raw sources mapped to same keys as `@multi_asset` outputs)
3. `14:46–15:03` — scheduler kept launching runs that all failed immediately (7 failures, each triggered health_alert_failure_sensor)
4. `15:03` — code server itself failed to load the workspace → all ingestion stopped
5. `15:03–16:48` — Dagster daemon down, no ingestion runs, health DB stale
6. `16:48` — container restarted; dbt manifest regenerated cleanly → `DagsterInvalidDefinitionError` gone
7. `16:50` — first successful run; health DB writes resume

**Why it resolved on restart**: The dbt manifest (loaded by `@dbt_assets(manifest=dbt_project.manifest_path)`) was regenerated during startup. Fresh compile cleared the duplicate key state.

**The `record_run()` code itself was fine** — SQLite WAL, proper try/finally, correct paths. The May 20 DuckDB errors in docker logs are from the OLD code (before `8f3cf8d feat(monitoring): migrate ingestion_health from DuckDB to SQLite`).

---

## Secondary Error (Non-Fatal)

`dagster.code_server ERROR` at **16:53 ICT**: `CheckError: Tried to retrieve asset key from an assets definition with multiple asset keys: ["shopee", "order_revenue"], ...`

**Cause**: When Dagster compiles the workspace, it looks up the `AssetsDefinition` for `AssetKey(["shopee", "order_revenue"])` (used as the check anchor for shopee freshness checks) and calls `.key` on the found multi-asset definition, which raises `CheckError`. This happens once per container restart.

**Impact**: Non-fatal — code server loads successfully, all checks run correctly. One-time cosmetic log error per restart.

---

## Bugs Fixed

### 1. `kpi_closure_checks.py` — DuckDB → SQLite (functional bug)

**Was**: `duckdb.connect(db_path, read_only=True)` + DuckDB JSON syntax (`->> 'key'`)  
**Problem**: `get_db_path()` returns SQLite `.db` file; DuckDB cannot read SQLite format → silently returns `(None, None, None)` on every KPI check → KPI drift checks never had real data  
**Fix**: Replaced with `open_readonly()` (SQLite) + `json_extract(col, '$.key')` syntax

### 2. `reconciliation_checks.py` — Stale docstring

**Was**: "Reads the most recent recon row from ingestion_health.duckdb"  
**Fix**: Updated to `ingestion_health.db`

---

## Files Changed

- `orchestration/asset_checks/kpi_closure_checks.py` — DuckDB → SQLite, JSON syntax fix
- `orchestration/asset_checks/reconciliation_checks.py` — docstring update

---

## Tests

All 18 tests pass:
- `orchestration/ops/__tests__/test_ingestion_health_retry.py` — 5/5
- `orchestration/asset_checks/__tests__/test_check_factories_smoke.py` — 13/13

---

## Current Status

- Health DB: writing normally (sapo_webhook_consumer_asset: last success 0.2h ago)
- Watchdog: in 4h cooldown (expires ~20:48 ICT)
- `DagsterInvalidDefinitionError`: not recurring post-restart
- KPI drift checks: now correctly reading SQLite (will show real data on next kpi_revenue_daily run)

---

## Unresolved Questions

1. **Dbt manifest corruption recurrence**: What specific change in the manifest caused the duplicate key error? Was it a stale artifact or a code-triggered issue? If the manifest gets corrupted again (e.g., after a partial dbt compile), the same 2h outage could happen. Consider adding a startup health check that validates the manifest before Dagster launches.

2. **CheckError at startup**: Non-fatal but noisy. Root: `@asset_check(asset=AssetKey(...))` where the key belongs to a multi-asset. Dagster's internal `.key` check doesn't support multi-assets. Low priority to fix but worth tracking.
