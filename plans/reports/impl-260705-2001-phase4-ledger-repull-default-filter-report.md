# Phase 4 Implementation Report — Ledger Re-pull + Default Filter

## Executed Phase
- Phase: `plans/260705-1459-budget-cashflow-workable-loop/phase-04-ledger-repull-default-filter.md`
- Status: completed

## Files Modified
- `orchestration/definitions.py` — +26 lines (new schedule fn + registration + comment)
- `docs/analytics-handbook/blueprints/metabase/finance_cashflow_budget.md` — 1 line (`default` token)
- `docs/analytics-handbook/blueprints/metabase/finance_cashflow.md` — NOT modified (already `past6months`, not `thismonth` — left alone per spec)

## 4a. Re-pull schedule
Added `ingest_monthly_repull_schedule` (cron `0 7 10 * *`, ICT, reuses `ingest_monthly_job`, same `_has_active_run` guard pattern), registered in `Definitions(schedules=[...])` right after `ingest_monthly_schedule`. Comment explains MISA books close ~day 5-10 and the download/ingest mechanism fully replaces the target month partition, so re-run is safe.

Verified idempotency claim by reading `orchestration/assets/misa_amis_assets.py` L318-324 — `misa_account_ledger_file_drop_asset` docstring: "Idempotency is ALWAYS ON: touched (year, month) partitions are replaced before write." Confirms UPSERT-by-(year,month), matches phase doc claim.

Verification:
- `docker exec data_platform python -c "..."` → clean import, `len(schedules)==16`, `ingest_monthly_repull_schedule` present.
- `docker exec data_platform dagster schedule list -m orchestration.definitions` → `Schedule: ingest_monthly_repull_schedule [STOPPED]` / `Cron Schedule: 0 7 10 * *`. STOPPED is the same default state as every other schedule in the list (incl. sibling `ingest_monthly_schedule`) — not a defect, matches existing pattern; user/ops enables via Dagit as usual.

## 4b. Dashboard default filter — CONFIRMED TOKEN: `past1months`

Verified live against Metabase v0.60.2 API (`/api/dataset`, native query against `main_marts.mart_cashflow_budget_vs_actual` field_id 2482) before touching any blueprint:
- `"previousmonth"` → **HTTP 500** `Assert failed: (some some? [start end])` — same failure signature as a deliberately bogus token (`totallybogustoken`). **Not a valid Metabase v0.60.2 token.**
- `"past1months"` → HTTP 202, resolved to `2026-06-01` (today = 2026-07-05, so previous month = June). Valid.
- `"lastmonth"` → also HTTP 202, resolved identically to June. Also valid, but not used — `past1months` is already documented in `.skills/metabase-automation/references/filter-date-range-pattern.md` L56, so used it for consistency with existing skill docs.
- Sanity check: `"thismonth"` → resolved to `2026-07-01` as expected (current month), confirming the test harness itself is correct.

**Action for future blueprint authors: use `past1months` for "previous full month" defaults on date/all-options filters — `previousmonth` is NOT a valid Metabase token (fails silently as a 500, easy to miss in a deploy that doesn't validate at write time).**

Changed `finance_cashflow_budget.md` filter block:
```json
{ "slug": "period_month", "type": "date/all-options", "default": "past1months", "field_id": "2482" }
```
(was `"thismonth"`).

`finance_cashflow.md` already uses `"default": "past6months"` (not `thismonth`) — left untouched per instructions, not redeployed.

## Redeploy
```
node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/metabase/finance_cashflow_budget.md
```
Ran successfully — "Deployment Complete", dashboard 114 now has 26 cards synced, no errors (one pre-existing informational warning about `cashflow_line` not referenced in the "Chu ky bao cao" card's SQL — unrelated to this change, not a new regression).

`finance_cashflow.md` NOT redeployed (no changes made to it).

## Post-deploy verification
- `GET /api/dashboard/114` → `period_month` parameter `default` = `"past1months"` (confirmed persisted).
- Queried `main_marts.mart_cashflow_budget_vs_actual` with the deployed default filter applied: previous month (June 2026) returns 7 rows, `actual_sum = 898,371,697` (populated, not empty) — confirms opening dashboard 114 with no filter chosen now shows a month with real actuals instead of a near-empty current month.
- Note (out of scope, not a regression from this change): `planned_sum = 0` for June in that same query — budget/plan seed data for June appears absent or zero; this is a data-completeness question for the budget seed pipeline, not the `period_month` default-filter fix. Flagging for awareness, no action taken here per file-ownership/scope limits.

## Tests Status
- Type check: N/A (no TS/JS changed beyond blueprint markdown; Python syntax validated via `ast.parse` with `utf-8-sig` — file has a pre-existing BOM per known lesson L155, not introduced by this change)
- Unit tests: N/A (no test suite covers Dagster schedule registration or Metabase blueprint content directly; validated via live container import + Metabase API probes instead, per phase doc's own verify steps)
- Integration: Dagster container import + `dagster schedule list` pass; Metabase API round-trip (deploy + GET dashboard + dataset query) pass

## Issues Encountered
None. `data_platform` container was stable (running, RestartCount=0) throughout, no concurrent dbt operations conflicted.

## Deviations from phase doc
- Phase doc suggested candidate tokens `"previousmonth"` / `"past1months"` — empirically verified `previousmonth` is invalid (500 error) and `past1months` is the correct token. Used `past1months`.
- `finance_cashflow.md` (dashboard 113) was NOT changed — it already defaults to `past6months`, not `thismonth`, so the "mid-month empty" problem doesn't apply there in the same way; phase doc said to sync only "if today (thismonth)".

## Next Steps / Unresolved Questions
- None blocking. Optional follow-up (out of scope): investigate why June `planned_sum = 0` in `mart_cashflow_budget_vs_actual` — may need a separate budget-seed-sync check, unrelated to this phase's file ownership.

Status: DONE
Summary: Added ingest_monthly_repull_schedule (day-10 07:00 ICT re-pull of MISA account ledger, reuses ingest_monthly_job, guarded); confirmed live via Metabase API that `previousmonth` token is invalid and `past1months` is correct, fixed finance_cashflow_budget.md default filter to past1months and redeployed (finance_cashflow.md needed no change — already past6months).
Concerns/Blockers: none. Minor unrelated observation: June budget/plan amount is 0 in the mart — data-completeness item, not part of this phase's scope.
