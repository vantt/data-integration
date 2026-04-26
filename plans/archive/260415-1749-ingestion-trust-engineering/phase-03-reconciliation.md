# Phase 3 — Source↔Destination Reconciliation

## Context Links
- Parent: [../plan.md](./plan.md)
- Depends on: [phase-01-metadata-contract.md](./phase-01-metadata-contract.md)
- **GATED BY:** [research/sapo-page-metadata-verification.md](./research/sapo-page-metadata-verification.md)
- File-drop DLT: `ingestion/run-shopee-income-file-drop.py`, `ingestion/run-misa-sales-file-drop.py`

## Overview
- **Priority:** P1 (for file drops) / P2 (for Sapo — gated by research)
- **Status:** ✅ DONE (commit `957a599`)
- **Effort:** ~6h
- **Summary:** Daily 04:30 asset group `reconciliation` emits one row per source comparing external truth vs warehouse count. Writes drift into `ingestion_health.metadata_json` + a dedicated asset check so drift > threshold → WARN/ERROR.

## Key Insights
- Two clean cases + one messy case:
  - **File drops (Shopee, MISA)**: Excel = source of truth, warehouse = derived. `source_count` = sum of rows across all NEW files ingested today (tracked via `file_sha256` in Phase 1) or across all archived files. `dest_count` = rows in raw table. Trivial.
  - **Sapo orders/customers**: needs a `total_items` endpoint or paging-metadata from Sapo web API — **unknown schema, blocked on research**.
  - **Sapo products/accounts/history/webhooks**: no obvious count endpoint; Phase 3 skips these (accept risk — covered by trend checks in Phase 2).
- Weekly full-refresh is OFF the table (user explicit) — recon is the replacement.
- Recon result lives in `ingestion_health.ingestion_runs` with `asset_key = 'recon/<source>_daily'`. `metadata_json` carries `{source_count, dest_count, drift_pct, window_start, window_end}`.

## Requirements

### Functional
- Run daily at 04:30 Asia/Ho_Chi_Minh (after 04:00 nightly finishes).
- For each source, compute `drift_pct = (dest_count - source_count) / source_count` over a trailing 7-day comparable window (or "last delivered file" for file drops).
- Abs(drift_pct) > 5% → asset check ERROR; > 1% → WARN.
- Persist to `ingestion_health` with dedicated `asset_key` prefix `recon/`.

### Non-functional
- Recon must NOT write to raw/serving DB. Read-only SQL, plus a row in health DB.
- External API calls (Sapo): single request with `page=1, limit=1` (cheapest possible).
- File hash lookup comes from Phase 1 `file_sha256` — no re-hashing.

## Architecture

```
┌─────────────────────────────────────────────┐
│ Dagster asset group: reconciliation         │
│                                             │
│ @asset recon_sapo_orders_daily   (gated)    │
│ @asset recon_sapo_customers_daily (gated)   │
│ @asset recon_shopee_daily                   │
│ @asset recon_misa_daily                     │
└──────┬──────────────────────┬───────────────┘
       │                      │
       ▼                      ▼
┌──────────────┐      ┌──────────────────────┐
│ Sapo web API │      │ Excel files in       │
│ /orders.json │      │ _archive/ +          │
│   ?limit=1   │      │ raw DuckDB tables    │
└──────────────┘      └──────────────────────┘
       │                      │
       └──────────┬───────────┘
                  ▼
      ingestion_health.duckdb (asset_key='recon/...')
                  ▼
       asset_check (drift threshold)
```

## Related Code Files

### Create
- `orchestration/assets/reconciliation.py` — 4 assets listed above.
- `ingestion/src/sapo/api_count.py` — tiny helper that issues one auth'd GET to the Sapo count endpoint (exact path/field decided by research). Returns `int | None`.
- `orchestration/asset_checks/reconciliation_checks.py` — 1 check per recon asset, reads last recon run and enforces drift thresholds.

### Modify
- `orchestration/definitions.py` — add `recon_daily_job`, `recon_daily_schedule` (cron `30 4 * * *`), register assets.
- `orchestration/asset_checks/__init__.py` — include recon checks in `ALL_CHECKS`.

### Delete
- None.

## Implementation Steps

### 3a. File-drop recon (no external dep — do first)

1. **`recon_shopee_daily`**:
   - Look up serving raw table name (likely `raw__shopee.order_revenue` or similar — verify in `ingestion/run-shopee-income-file-drop.py`).
   - `dest_count` = `SELECT count(*) FROM <raw_table> WHERE _dlt_load_id IN (last 7 days)`.
   - `source_count` = sum of `rows_fetched` from `ingestion_health` where `asset_key='shopee/shopee_income_file_drop_asset' AND run_started_at >= now()-7d`.
   - Write recon row.
2. **`recon_misa_daily`** — same shape, different table.

### 3b. Sapo recon (blocked until research lands)

3. **`recon_sapo_orders_daily`**:
   - Call `api_count.count_orders(modified_since, modified_before)` — uses auth flow from existing `ingestion/run_orders_batch.py`.
   - `dest_count` = `SELECT count(*) FROM sapo__orders WHERE modified_on BETWEEN ? AND ?`.
   - Compute `drift_pct`. Write recon row with `metadata_json.source_count`, `dest_count`.
4. **`recon_sapo_customers_daily`** — same pattern.

### 3c. Wiring

5. **Asset check `recon_drift`** — one per recon asset:
   ```python
   def _make_recon_check(recon_asset_key):
       @asset_check(asset=..., name="drift_within_threshold", blocking=False)
       def _check():
           last_meta = SELECT metadata_json FROM ingestion_runs
             WHERE asset_key=? ORDER BY run_started_at DESC LIMIT 1
           drift = abs(last_meta["drift_pct"])
           if drift > 0.05: return AssetCheckResult(False, ERROR, ...)
           if drift > 0.01: return AssetCheckResult(False, WARN, ...)
           return AssetCheckResult(True, ...)
   ```
6. **Register job + schedule** in `definitions.py`:
   ```python
   recon_daily_job = define_asset_job(name="recon_daily_job",
       selection=AssetSelection.groups("reconciliation"))
   @schedule(job=recon_daily_job, cron_schedule="30 4 * * *", execution_timezone="Asia/Ho_Chi_Minh")
   def recon_daily_schedule(context): ...  # same self-overlap pattern
   ```
7. **Tag** the schedule with `{"concurrency_group": "dbt_rw"}`? **NO** — recon is read-only on raw DB. Keep it OFF the dbt_rw mutex so it never competes with nightly ingestion.
8. **Smoke test**: run recon manually, verify rows in health DB and check results in UI.

## Todo List

- [ ] Implement `recon_shopee_daily`
- [ ] Implement `recon_misa_daily`
- [ ] Wait for research gate → implement `api_count.py`
- [ ] Implement `recon_sapo_orders_daily`
- [ ] Implement `recon_sapo_customers_daily`
- [ ] Implement `recon_drift` asset check factory
- [ ] Register recon job + schedule in `definitions.py`
- [ ] Smoke test all recon assets; assert drift calculation on known data
- [ ] Document: add to `orchestration/docs/` how recon works + how to investigate WARN

## Success Criteria

- 04:30 each day, one row per source in `ingestion_runs` with `asset_key LIKE 'recon/%'`.
- Query `SELECT asset_key, metadata_json->>'drift_pct' FROM ingestion_runs WHERE asset_key LIKE 'recon/%' ORDER BY run_started_at DESC LIMIT 4` returns all four sources (after research unlocks Sapo).
- Deliberate-drift test: DELETE 10 rows from `sapo__orders` for yesterday → next recon run → check fires ERROR.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Sapo count endpoint doesn't exist / hidden behind paginated scan | High | High | Research gate explicitly captures this unknown. Fallback: compute `dest_count` only + skip drift for Sapo, rely on Phase 2 trend checks |
| Sapo modified_on window off-by-timezone (UTC vs ICT) | High | Med | Always compute windows in UTC; convert to ICT only for display |
| Raw tables renamed in dbt refactor | Low | Med | Load table name from a small constants module; fail loud if missing |
| Drift is legitimately large on sparse days (e.g. Sunday) | High | Low | Compute drift over 7-day rolling window, not 1-day; tolerance 5% generous |
| Recon asset itself fails — silent blind spot | Med | Med | Recon asset also writes `status='failed'` to ingestion_health; Phase 4 Lark digest surfaces it |

## Next Steps

- Consumed by Phase 4 digest (drift line).
- If research shows Sapo count is unreliable, Phase 5 KPI-closure becomes harder — noted there.
