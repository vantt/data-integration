# Budget & Cashflow — Closed the Workable Loop

**Date**: 2026-07-05 20:47  
**Severity**: Low (P0 feature completed; 2 blocking human items remain)  
**Component**: Finance (transformation/, ingestion/, orchestration/, Metabase dashboard 114)  
**Status**: Code-complete; regression-tested 8/8 pass; deployed

## What Happened

Closed the budget/cashflow "workable loop"—the part where finance can edit a Google Sheet budget matrix and see updated numbers on the dashboard without manual CSV downloads or Docker commands. 5 phases delivered in parallel: sheet→seed sync script (P0), user guide rewrite (P0), scorecard scope fix (P1), ledger re-pull scheduling (P1), and suggestion write-back code (P2, gated on GCP setup). All code done, reviewed, and tested. Commit: `6a2a3084`.

## The Brutal Truth

The most frustrating part: this loop was already *almost* working—we had the seed CSVs, the dbt models, the dashboard. But the **bridge was missing**: no code existed to push finance's sheet data into the seeds. So either finance would manually download CSVs (breaking workflow), or the sheet was write-only. We just built that bridge.

The real incident: while verifying mart SQL changes with `docker exec data_platform dbt deps`, the command **raced against the container's own startup-time `dbt deps`** (Dagster's `DbtProject.prepare_if_dev()` reinstalls deps on every restart). The overlap corrupted `transformation/dbt_packages/`, spawning a genuine crash loop (140+ restarts over ~15 minutes) that **did NOT self-heal**. Fixed by `docker compose stop`, deleting `dbt_packages/` from the host, and restarting. Lesson: never run manual dbt commands against a dev container without first checking `docker inspect --format '{{.State.Status}} {{.RestartCount}}'`—if it's mid-restart, wait.

## Technical Details

**Phase 1 — Sheet→Seed Sync (P0):** Built `ingestion/src/gsheet_budget_sync/` (new package). Syncs a 3-tab Google Sheet matrix (BUDGET_ITEMS / ALLOCATION_POLICY / __REF) directly into 2 dbt seed CSVs (`seed_cashflow_budget.csv`, `seed_cash_allocation_policy.csv`), replacing a broken bridge. Validates hard, aborts loud, never overwrites seeds on bad data. New Dagster asset + schedule (02:30 ICT daily). 31 unit tests cover parse, validate, merge, suggestions, dry-run, credential gating.

**Phase 2 — User Guide (P0):** Rewrote `docs/analytics-handbook/guides/finance-budget-user-guide.md`. Old guide described a nonexistent manual CSV-download process that would fail if followed. New guide matches the real sheet layout and 1-step sync workflow.

**Phase 3 — Scorecard Scope (P1):** Fixed dashboard 114 bug: budget covers only 5/15 cashflow lines, but scorecards ("Tỷ lệ thực hiện", "Chênh lệch") were summing ALL rows, making attainment % meaningless. Scoped to `coverage='both'` (lines with both budget + actual); added "Ngoài kế hoạch" card so excluded money stays visible (192M + 5.9B verified to sum correctly).

**Phase 4 — Ledger Re-Pull + Default Filter (P1):** Added day-10 MISA ledger re-pull (books close ~day 5-10; day-1 pull was stale). Fixed dashboard default period filter: discovered `previousmonth` is NOT valid on Metabase v0.60.2 (returns 500; plausible guess but wrong). Correct token: `past1months`. Worth remembering for future blueprint work.

**Phase 5 — Suggestion Write-Back (P2, Code-Complete, Not Activated):** Built (unit-tested) a feature that computes rolling-3-month average actuals and reserve-gap math, writes them into the sheet's "Gợi Ý" column. Blocked on Google service-account credential (GCP setup required—human step, not a code bug).

## Root Cause: Missing Data Bridge

The seed CSVs and dbt models existed. The dashboard existed. But nothing pushed finance's sheet edits into the seeds. The gap was architectural—no one had built the sync layer that bridges Google Sheets (source of truth) → seed CSV (pipeline input). So the budget system was write-locked: users could only edit the sheet, not see it affect the pipeline. Phase 1 closes that gap.

## Lessons Learned

1. **Don't run `dbt deps` manually against a dev container:** Dagster's `DbtProject.prepare_if_dev()` re-runs `dbt deps` on every restart. Running it in parallel corrupts the cache (140+ restarts, won't self-heal). Before touching the container: verify it's stable (`docker inspect --format '{{.State.Status}}'` should be "running" with low restart count). If restarting: wait for it to settle.

2. **Sheet matrix validation must be strict:** The sync script rejects gaps/overlaps in ALLOCATION_POLICY, unknown lines in BUDGET_ITEMS, missing "remainder" row. By design, it fails loud and never writes an invalid seed. This prevents silent data corruption.

3. **Default filter tokens are version-specific:** Metabase v0.60.2 doesn't recognize `previousmonth` (500 error); `past1months` is correct. Plausible-looking guesses don't transfer between Metabase versions—verify via docs or test before deploying.

## Next Steps

1. **[BLOCKER] Add `remainder` row to sheet ALLOCATION_POLICY** — finance/technical team must add the final priority row (bucket=free, rule_type=remainder, value=blank) before the first successful sync. Sync will reject without it (by design). See `plans/260705-1459-budget-cashflow-workable-loop/phase-01-sheet-to-seed-sync.md` Q5.

2. **[BLOCKER] GCP service-account setup for Phase 5** — create service account, share sheet with Editor permission, set `GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH`, rebuild `data_platform` to install `gspread`. Details: `plans/reports/impl-260705-2010-phase5-prefill-suggestions-report.md`. Until then, `budget_suggestion_writeback_schedule` fails loudly on each run (by design, not silent).

3. Monitor first live sync run (02:30 ICT tomorrow) — verify seed files update, no stale dbt cache, dashboard reflects new numbers by 03:00 ICT.
