# Phase 2 — Asset Checks: Completion Report

**Date:** 2026-04-15
**Commit:** `97cee41`
**Branch:** main (pushed)

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `orchestration/config/ingestion_sla.yaml` | 35 | SLA thresholds for all 10 ingestion assets |
| `orchestration/asset_checks/health_db.py` | 98 | Read-only DuckDB helpers (open_readonly, last_success, rows_by_day, consecutive_empty_with_cursor_move, count_zero_row_runs_last_24h) |
| `orchestration/asset_checks/sla_loader.py` | 67 | YAML loader with defaults-merge, module-level cache, missing-key fallback |
| `orchestration/asset_checks/freshness_checks.py` | 67 | `make_freshness_check` factory — ERROR severity on SLA breach |
| `orchestration/asset_checks/row_trend_checks.py` | 103 | `make_not_empty_check` + `make_row_trend_check` factories |
| `orchestration/asset_checks/cursor_checks.py` | 82 | `make_cursor_stall_check` factory — Sapo assets only, returns None for others |
| `orchestration/asset_checks/__init__.py` | 84 | Registry: iterates YAML, builds ALL_CHECKS list |
| `orchestration/asset_checks/__tests__/test_check_factories_smoke.py` | 213 | 13 pytest smoke tests |

## Files Modified

- `orchestration/definitions.py` — added `from orchestration.asset_checks import ALL_CHECKS`, `ingestion_health_checks_job`, `ingestion_health_checks_schedule` (2h cron), registered in `Definitions(asset_checks=ALL_CHECKS, ...)`

## Checks Registered (per asset)

| Asset | freshness | not_empty | row_trend | cursor_stall |
|-------|-----------|-----------|-----------|--------------|
| sapo_webhook_consumer | ✓ | ✓ | ✓ | ✓ |
| sapo_history_log | ✓ | ✓ | ✓ | ✓ |
| sapo_orders_batch | ✓ | ✓ | ✓ | ✓ |
| sapo_customers_batch | ✓ | ✓ | ✓ | ✓ |
| sapo_accounts_batch | ✓ | ✓ | ✓ | — |
| sapo_products_batch | ✓ | ✓ | ✓ | ✓ |
| shopee_income_file_drop | ✓ | ✓ | — (null) | — |
| misa_sales_file_drop | ✓ | ✓ | — (null) | — |
| sheets_targets | ✓ | ✓ | — (null) | — |
| sheets_marketing_spend | ✓ | ✓ | — (null) | — |

Total: 33 checks registered.

## Test Results

- Import smoke (`from orchestration import definitions`): PASS (verified in Docker container)
- pytest 13/13 passed

## Acceptance Criteria Check

- [x] ≥1 @asset_check per ingestion asset, registered in Definitions
- [x] Checks read from ingestion_health.duckdb via standalone SQL, no heavy asset imports at check runtime
- [x] SLA from YAML only — one-file edit to tighten
- [x] not_empty_when_expected, row_count_within_trend, freshness as generic factories
- [x] Import smoke passes
- [x] No-rows-yet → WARN not ERROR, no crash

## Notes

- `sapo_accounts_batch_asset` excluded from cursor check (not in CURSOR_CHECK_ASSET_KEYS per spec)
- Trend check requires ≥7 days baseline; fires WARN with "insufficient history" until then
- `ingestion_health_checks_schedule` runs every 2h (Asia/Ho_Chi_Minh), same self-overlap guard as other schedules
