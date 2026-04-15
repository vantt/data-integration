# Phase 2 — Asset Checks

## Context Links
- Parent: [../plan.md](./plan.md)
- Depends on: [phase-01-metadata-contract.md](./phase-01-metadata-contract.md)
- Dagster asset_check docs: https://docs.dagster.io/concepts/assets/asset-checks

## Overview
- **Priority:** P1
- **Status:** pending
- **Effort:** ~5h
- **Summary:** For each ingestion asset, register 2–3 `@asset_check` functions reading from `ingestion_health.duckdb`. Thresholds driven by a single YAML. First failing signal becomes the user's "glance once" surface in Dagster UI.

## Key Insights
- Asset checks live NEXT to assets but don't run inline — Dagster runs them on asset materialization or on schedule, so they can cheaply query the health DB.
- All thresholds in one YAML → future SLA tightening is a one-file edit (user's explicit preference).
- "Silent dropout" (cursor advances, rows=0 repeatedly) is THE failure mode the user cares about. `row_count_within_trend` is the check that catches it.
- We only emit WARN (not ERROR) for trend-based checks to avoid alarm fatigue while SLAs are still loose.

## Requirements

### Functional
- Per ingestion asset, the following checks where applicable:
  1. **`freshness`** — last `status='success'` run must be within SLA window. ERROR if exceeded.
  2. **`not_empty_when_expected`** — if asset ran in last 24h and every run had `rows_written=0`, WARN. (Suppressed outside business hours for batch assets.)
  3. **`row_count_within_trend`** — 24h-sum-of-rows_written ≥ 50% of trailing-7-day median. WARN below threshold.
  4. **`cursor_advanced_but_empty`** (Sapo realtime/incremental only) — N=3 consecutive runs with `cursor_after != cursor_before` but `rows_written=0`. WARN.
- SLA + thresholds loaded from `orchestration/config/ingestion_sla.yaml`. One edit tightens the whole fleet.

### Non-functional
- Each check query < 200ms against the health DB.
- Checks must be idempotent and side-effect free (no writes).
- Failure of a check must not block asset materialization.

## Architecture

```
orchestration/config/ingestion_sla.yaml
        │
        ▼
orchestration/asset_checks/
  ├─ __init__.py              (exports ALL_CHECKS for definitions.py)
  ├─ health_db.py             (read-only helper: connect + common queries)
  ├─ freshness_checks.py
  ├─ row_trend_checks.py
  └─ cursor_checks.py
        │
        ▼
orchestration/definitions.py  (asset_checks=ALL_CHECKS)
```

Checks query `ingestion_health.ingestion_runs` — read-only, separate DB so no contention with writers or Metabase.

## Related Code Files

### Create
- `orchestration/config/ingestion_sla.yaml` — schema below.
- `orchestration/asset_checks/__init__.py` — aggregates `ALL_CHECKS: list[AssetChecksDefinition]`.
- `orchestration/asset_checks/health_db.py` — `open_readonly()`, `last_success(asset_key)`, `rows_by_day(asset_key, n_days)`, `consecutive_empty_with_cursor_move(asset_key, n)`.
- `orchestration/asset_checks/freshness_checks.py` — one `@asset_check` per asset key.
- `orchestration/asset_checks/row_trend_checks.py`
- `orchestration/asset_checks/cursor_checks.py`

### Modify
- `orchestration/definitions.py` — add `asset_checks=ALL_CHECKS` to `Definitions(...)`; add a `@schedule` that runs checks every 2h (Dagster does not auto-run unattached checks) — use `define_asset_job(name="ingestion_health_checks_job", selection=AssetSelection.all_asset_checks())`.

## SLA YAML schema

```yaml
# orchestration/config/ingestion_sla.yaml
defaults:
  trend_window_days: 7
  trend_min_ratio: 0.5         # current-24h >= 50% of 7-day median
  empty_check_min_age_hours: 1 # don't complain until asset has run at least once
  cursor_empty_streak: 3
assets:
  sapo/sapo_webhook_consumer_asset:
    freshness_hours: 1         # realtime; 3min schedule but tolerate 60min
    business_hours_only: false
  sapo/sapo_history_log_asset:
    freshness_hours: 12
  sapo/sapo_orders_batch_asset:
    freshness_hours: 28
  sapo/sapo_customers_batch_asset:
    freshness_hours: 28
  sapo/sapo_accounts_batch_asset:
    freshness_hours: 28
  sapo/sapo_products_batch_asset:
    freshness_hours: 28
  shopee/shopee_income_file_drop_asset:
    freshness_hours: 48
    trend_min_ratio: null      # file-drop cadence irregular; skip trend check
  misa_amis/misa_sales_file_drop_asset:
    freshness_hours: 192       # 8 days
    trend_min_ratio: null
  sheets/sheets_targets_asset:
    freshness_hours: 48
    trend_min_ratio: null
  sheets/sheets_marketing_spend_asset:
    freshness_hours: 48
    trend_min_ratio: null
```

## Implementation Steps

1. **Create SLA YAML** with the table above.
2. **Create `health_db.py`**:
   ```python
   def open_readonly() -> duckdb.DuckDBPyConnection:
       return duckdb.connect(ingestion_health.get_db_path(), read_only=True)

   def last_success(conn, asset_key: str) -> datetime | None: ...
   def rows_by_day(conn, asset_key: str, n_days: int) -> list[tuple[date, int]]: ...
   def consecutive_empty_with_cursor_move(conn, asset_key: str, n: int) -> int: ...
   ```
3. **Implement freshness checks** — factory function:
   ```python
   def _make_freshness_check(asset_def, asset_key_str, sla_hours):
       @asset_check(asset=asset_def, name="freshness", blocking=False)
       def _check(context):
           with open_readonly() as c:
               last = last_success(c, asset_key_str)
           age_h = (now_utc() - last).total_seconds()/3600 if last else math.inf
           passed = age_h <= sla_hours
           return AssetCheckResult(
               passed=passed,
               severity=AssetCheckSeverity.ERROR if not passed else AssetCheckSeverity.WARN,
               description=f"last success {age_h:.1f}h ago (SLA={sla_hours}h)",
               metadata={"age_hours": age_h, "sla_hours": sla_hours},
           )
       return _check
   ```
4. **Implement trend checks** — skip where `trend_min_ratio` is null. SQL:
   ```sql
   WITH daily AS (
     SELECT date_trunc('day', run_started_at) d, SUM(rows_written) r
     FROM ingestion_runs
     WHERE asset_key = ? AND status='success'
     GROUP BY 1 ORDER BY 1 DESC LIMIT 8
   )
   SELECT
     (SELECT r FROM daily ORDER BY d DESC LIMIT 1) AS today,
     median(r) OVER () AS med7
   FROM daily OFFSET 1 LIMIT 1;
   ```
5. **Implement cursor check** — only for `sapo_webhook_consumer`, `sapo_history_log`, `sapo_orders_batch`, `sapo_customers_batch`, `sapo_products_batch`. Requires Phase 1 to populate `cursor_before`/`cursor_after` (follow-up in Phase 1 if not yet wired — add TODO).
6. **Wire up `asset_checks/__init__.py`** to iterate SLA YAML and build the check list.
7. **Register in `definitions.py`**:
   ```python
   from orchestration.asset_checks import ALL_CHECKS
   defs = Definitions(..., asset_checks=ALL_CHECKS)
   ```
8. **Add schedule** `ingestion_health_checks_schedule` — `cron="0 */2 * * *"`, runs all checks.
9. **Smoke test**: manually run the check job; confirm each check appears in Dagster UI under the asset's "Checks" tab.

## Todo List

- [ ] Create `orchestration/config/ingestion_sla.yaml`
- [ ] Create `asset_checks/health_db.py`
- [ ] Implement freshness check factory
- [ ] Implement row-trend check factory
- [ ] Implement cursor-stall check factory (Sapo only)
- [ ] Aggregate via `asset_checks/__init__.py`
- [ ] Register in `definitions.py`
- [ ] Add 2h schedule for check job
- [ ] Smoke test each check manually — force a freshness fail by backdating `run_started_at`
- [ ] Compile check: `python -c "import orchestration.definitions"` exits 0

## Success Criteria

- Dagster UI → each ingestion asset shows ≥1 asset check in the "Checks" tab.
- Force-test: `UPDATE ingestion_runs SET run_started_at = run_started_at - INTERVAL 2 DAY WHERE asset_key='sapo/sapo_orders_batch_asset'` then re-run check → freshness check fails ERROR.
- Editing `trend_min_ratio: 0.5 → 0.8` in YAML, restarting Dagster webserver, produces stricter WARN output.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| DuckDB read-only conflict with writer on same file | Low | Low | DuckDB permits concurrent readers + single writer; open `read_only=True` |
| YAML syntax error silently drops checks | Med | Med | On load, if an asset is registered in code but missing from YAML, fall back to `defaults` and log a warning |
| Trend check noise in low-volume periods | High | Low | Require ≥7 non-null days of history before firing; else return `passed=True, description="insufficient history"` |
| `cursor_before`/`cursor_after` not populated by Phase 1 | Med | Low | Cursor-stall check gracefully returns `passed=True, description="cursor field not yet instrumented"` if columns null |

## Next Steps

- Phase 4 consumes check results for the Lark digest. No direct dependency beyond Phase 1.
