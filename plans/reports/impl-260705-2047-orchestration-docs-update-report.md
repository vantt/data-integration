# Orchestration Docs Update Report

**Date:** 2026-07-05  
**Scope:** Document 5 new Dagster objects from budget-cashflow-workable-loop plan (all phases code-complete)

---

## Summary

Updated 3 documentation files to record the 5 new Dagster objects added to the orchestration layer. All entries follow existing format, structure, and prose level-of-detail.

---

## Objects Documented

### Assets (2 new)
1. **`budget_sheet_sync_asset`** (group `sheets_ingestion`, key_prefix `sheets`)
   - Daily sync of Google Sheet budget matrix → dbt seed CSVs (not gsheet_raw data lake)
   - Scheduled 02:30 ICT, 30 min before nightly dbt build
   - Strict validation: fails on sheet structure issues, missing refs, ALLOCATION_POLICY gaps

2. **`budget_suggestion_writeback_asset`** (group `sheets_ingestion`, key_prefix `sheets`)
   - Monthly write-back of "Gợi Ý" (suggestion) column to BUDGET_ITEMS tab
   - Computes rolling 3-month avg for recurring, required_monthly_adj for reserves, 0 for one-off
   - HARD BLOCKER: requires `GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH` env var (GCP service account w/ Editor access)
   - Fails loud at RUNTIME only, not at code-load (asset graph safe with missing credential)

### Jobs (2 new)
1. **`budget_sheet_sync_job`** + **`budget_sheet_sync_schedule`** (cron `30 2 * * *` ICT)
   - Selects only `budget_sheet_sync_asset`
   - Daily at 02:30 ICT (30 min before nightly dbt build)

2. **`budget_suggestion_writeback_job`** + **`budget_suggestion_writeback_schedule`** (cron `0 8 1 * *` ICT)
   - Selects only `budget_suggestion_writeback_asset`
   - Monthly on 1st of month at 08:00 ICT (after ingest_monthly_job at 07:00 lands fresh MISA actuals)

### Schedule (1 new, reuses existing job)
1. **`ingest_monthly_repull_schedule`** (cron `0 7 10 * *` ICT)
   - Re-pulls MISA account ledger on day 10 after books close (~day 5-10)
   - Reuses existing `ingest_monthly_job` (no new job)
   - Safe/idempotent: UPSERT by year/month, no double-counting

---

## Files Modified

### `orchestration/docs/ASSETS.md`
- Updated `sheets_ingestion` table to include 7 assets (was 2)
  - Added: `sheets_team_config_asset`, `sheets_us_shipment_prices_asset`, `sheets_overhead_classification_asset`
  - Added: `budget_sheet_sync_asset`, `budget_suggestion_writeback_asset`
- Added 5 new asset definition sections (after `sheets_marketing_spend_asset`)
  - Each includes purpose, group, schedule, and operational caveats where applicable

### `orchestration/docs/JOBS.md`
- Updated "Active Jobs" table (6 rows, was 4)
  - Corrected realtime/incremental cron schedule patterns (was using regex escape sequences)
  - Added 2 new jobs: `budget_sheet_sync_job`, `budget_suggestion_writeback_job`
- Added 2 new job definition sections (after `ingest_sheets_sync_job`)
  - `budget_sheet_sync_job`: daily at 02:30, writes to dbt seeds
  - `budget_suggestion_writeback_job`: monthly at 08:00, includes Google service-account caveat

### `orchestration/docs/SCHEDULES.md`
- Updated "Schedule Overview" table (11 rows, was 6)
  - Added `ingest_weekly_schedule`, `ingest_monthly_schedule`, `ingest_monthly_repull_schedule`
  - Added `budget_sheet_sync_schedule`, `budget_suggestion_writeback_schedule`
- Added 5 new schedule definition sections (after `pipeline_batch_nightly_schedule`)
  - Each includes cron, timing, assets, and operational notes
  - `ingest_monthly_repull_schedule`: documents MISA book-closing timing + idempotency
  - `budget_suggestion_writeback_schedule`: includes full GCP setup caveat + why 08:00 timing

---

## Verification

All documentation entries verified against source code:
- **sheets_assets.py** (lines 267-381): `budget_sheet_sync_asset`, `budget_suggestion_writeback_asset` implementations
- **definitions.py** (lines 168-184, 514-539): job + schedule definitions
- **definitions.py** (lines 500-509): `ingest_monthly_repull_schedule` implementation

Format and structure matched to existing entries:
- Prose level-of-detail: 1-3 sentences + key operational context
- Cron notation: ISO standard (e.g., `0 7 10 * *` for day 10 at 07:00)
- Timezone: All explicit `Asia/Ho_Chi_Minh`
- Operational caveats: Documented prominently (Google service account, ALLOCATION_POLICY validation)

---

## Notes

- `ingest_monthly_repull_schedule` is a schedule-only addition; it reuses the existing `ingest_monthly_job` (defined at line 159), so no new job was added to definitions.py
- `budget_suggestion_writeback_asset` includes prominent caveat about missing Google service-account credential (by design: expected to fail at runtime until credential is manually created, but failure is safe and loud)
- Updated tables preserve alphabetical/logical grouping; new entries inserted in correct semantic position within each group
