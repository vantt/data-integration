# Phase 5 — Pre-fill "Gợi Ý" Suggestions — Implementation Report

Plan: `plans/260705-1459-budget-cashflow-workable-loop/phase-05-prefill-suggestions.md`
Date: 2026-07-05

## Status: DONE_WITH_CONCERNS (code complete + tested; write-path unexercised — hard external blocker)

## Summary

Extended `gsheet_budget_sync.py` with a `--write-suggestions` mode that computes per-item
"Gợi Ý" (suggestion) values for next month and writes ONLY that column, never "Budget". Added
a Dagster asset/job/schedule (1st of month 08:00 ICT, after the 07:00 `ingest_monthly_job`).
The compute + targeting logic is fully implemented, unit-tested (31/31 passing, all mocked, no
real network/DuckDB/Sheets calls), and proven safe to import with zero credentials. The actual
Sheets API write call is implemented but **cannot be exercised end-to-end** — this repo has no
Google write-capable credential anywhere, and creating one requires GCP console access this
agent does not have. See "Unresolved / needs human action" below.

## Files Modified

- `ingestion/src/gsheet_budget_sync.py` (+~280 lines) — new suggestion-computation section:
  `next_month_start`, `_preceding_months`, `compute_recurring_suggestions`,
  `compute_reserve_suggestions`, `build_suggestion_writes`, `_assert_gio_column`,
  `_fetch_recurring_actuals_from_duckdb`, `_fetch_reserve_status_from_duckdb`,
  `_col_num_to_a1`/`_to_a1_cell`, `write_suggestions_to_sheet`, `_write_cells_via_sheets_api`.
  CLI `run()` extended with `--write-suggestions [--target-month YYYY-MM] [--dry-run]`.
  Module docstring extended with the write-mechanism + HARD EXTERNAL BLOCKER section.
- `ingestion/tests/test_gsheet_budget_sync.py` (+~185 lines) — 19 new tests covering the
  formulas, cell-targeting, dry-run diff, Budget-column guard rail, and credential/dependency
  fail-fast behavior. All mocked — no real network, DuckDB file, or Sheets API access.
- `ingestion/requirements.txt` — added `gspread` (not yet installed in the running
  `data_platform` container image — requires a rebuild, see blocker section).
- `orchestration/assets/sheets_assets.py` (+52 lines) — new
  `budget_suggestion_writeback_asset`, following the exact health-recording/
  `load_dlt_configuration`/chdir-to-`DLT_DIR` pattern of `budget_sheet_sync_asset`.
- `orchestration/definitions.py` — new `budget_suggestion_writeback_job` +
  `budget_suggestion_writeback_schedule` (cron `0 8 1 * *`, Asia/Ho_Chi_Minh), registered in
  both `jobs=[...]` and `schedules=[...]` of `Definitions()`.

## Investigation — existing credentials (step 1 of the task)

Grepped `ingestion/src/` for `import gspread`, `from google.oauth2`, `googleapiclient` —
zero matches in actual code. One hit: a prior unrelated plan doc
(`plans/260624-1958-pipeline-hardening-followups/phase-01-gsheets-service-account.md`) that
already flags the READ side of this same problem ("Blocked on: GCP service-account JSON key
(user to provide)") — still unresolved as of today. Confirms: no write-capable (or even
read-capable-via-API) Google credential exists anywhere in this repo. Every other `gsheet_*.py`
script uses the public CSV-export read path (no credentials), consistent with this finding.

## Suggestion logic (implemented exactly per phase-doc table)

| item_type | Implementation |
|---|---|
| recurring | `compute_recurring_suggestions()` — `SUM(amount)` from `fact_cash_movement` over the 3 months immediately preceding target month, per `(cashflow_line, direction)`, divided by 3 (fixed window — a line with actuals in only 2 of 3 months still averages over 3, not 2) |
| reserve, has target_month AND item_target | reads `required_monthly_adj` straight from `mart_cashflow_reserve_status` (no recomputation) |
| reserve, target-only / open-ended | `build_suggestion_writes()` skips — no cell write |
| one_off | `0`, except when the item's own `target_month` equals the write-target month → skipped (finance enters that one by hand) |

## Write mechanism + safety

- `write_suggestions_to_sheet(target_month=None, dry_run=True)` is the single entry point.
  `dry_run=True` (default) does fetch (read-only public CSV, same as existing sync) + compute +
  print the exact cell/value diff — **zero** Sheets API calls, works with **zero** credentials.
- `dry_run=False` calls `_write_cells_via_sheets_api()`, the ONLY function requiring real
  credentials. It:
  1. Reads `GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH` env var — raises `RuntimeError` with a
     clear Vietnamese message if unset (tested).
  2. Checks the key file exists — raises `RuntimeError` if not (tested).
  3. Lazily `import gspread` inside the function (NOT at module top) — so the module and the
     Dagster asset graph import cleanly even with `gspread` not installed. Raises a clear
     `RuntimeError` naming the missing dependency + rebuild command if the import fails.
  4. Re-asserts `_assert_gio_column()` per write as defense-in-depth before calling
     `gc.service_account(...).open_by_url(...).batch_update(...)`.
- `_assert_gio_column(col)` is the hard guard: `assert (col - BI_COL_DATA_START) % 2 == 0`
  (never the odd-offset "Budget" column). Called both when resolving the target column in
  `build_suggestion_writes()` and per-cell in `_write_cells_via_sheets_api()`. Unit-tested
  (`test_assert_gio_column_rejects_the_budget_column`) — proves col 7 (H, "Budget") raises,
  col 6 (G, "Gợi Ý") does not.
- Idempotency: `write_suggestions_to_sheet` is a pure recompute-and-overwrite per run for a
  fixed `target_month` — same underlying actuals + same formulas ⇒ same values ⇒ re-running
  produces no drift/duplication. No stateful counters or append-only writes involved.

## Dagster asset/job/schedule

- `budget_suggestion_writeback_asset` (in `sheets_assets.py`) follows the exact
  health-recording + `load_dlt_configuration` + chdir-to-`DLT_DIR` pattern as
  `budget_sheet_sync_asset`. Calls `gsheet_budget_sync.write_suggestions_to_sheet(dry_run=False)`.
- `budget_suggestion_writeback_job` / `budget_suggestion_writeback_schedule`
  (`0 8 1 * *`, Asia/Ho_Chi_Minh) registered in `definitions.py` exactly like
  `budget_sheet_sync_job`/`ingest_monthly_repull_schedule` (no `default_status` override — same
  convention as those siblings).
- Verified `docker exec data_platform python -c "import orchestration.definitions"` succeeds
  cleanly — code-load does NOT depend on `gspread` being installed or any credential existing.
  Container stayed `running`, `RestartCount 0` before and after all exec calls.
- **Once this schedule is enabled and ticks**, it WILL fail loudly every month
  (`RuntimeError: GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH chưa được cấu hình...`) until the
  human GCP setup below is completed — `health_alert_failure_sensor` will alert on it. This is
  the intended fail-loud behavior per the task spec, not a bug.

## Tests

`pytest ingestion/tests/test_gsheet_budget_sync.py -q` → **31 passed** (12 pre-existing + 19 new).
New tests cover: `next_month_start` year rollover, `_preceding_months` window + year rollover,
`compute_recurring_suggestions` (fixed-window averaging, not present-count averaging),
`compute_reserve_suggestions` (skips NULL `required_monthly_adj`), `build_suggestion_writes`
(all 3 item_type branches incl. open-ended-reserve skip and one_off's-own-month skip, target-
month-column-missing → empty), `_assert_gio_column` (accept/reject), `_col_num_to_a1`/
`_to_a1_cell`, full dry-run pipeline (mocked fetch + mocked DuckDB fetch, asserts the real
Sheets-write function is never called), structural-validation-abort, and the two credential/
dependency guard-rail RuntimeErrors. All mocked — zero real network, DuckDB file, or Sheets API
access in the test suite.

`python -m py_compile` clean on all 3 modified Python files. `docker exec data_platform python -c
"import orchestration.definitions"` clean.

## Unresolved / needs human action (HARD EXTERNAL BLOCKER)

This phase's write path is **implemented but not functionally live** — it cannot be, without a
credential this agent has no ability to create (no browser/GCP console access, explicitly
out of scope per task instructions). A human must, outside this repo:

1. Create (or reuse) a GCP project; enable the **Google Sheets API**.
2. Create a **service account**; generate + download its JSON key.
3. Share the budget Google Sheet (`https://docs.google.com/spreadsheets/d/15hba6bzrTRXUDXBeUg5_DhefrETX9kLGG8SnPJZzTfA/edit`)
   with the service account's email as **Editor** (stronger than the existing read-side
   "Anyone with link" — that's not sufficient to write).
4. Place the downloaded JSON key somewhere the `data_platform` container can read (e.g. a
   secrets volume, or bind-mount into `ingestion/.dlt/` — **never commit it to git**), and set
   `GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH` to that path in the container's environment.
5. Run `docker compose build data_platform` (not just `restart`) so the newly-added `gspread`
   dependency in `ingestion/requirements.txt` actually gets installed in the image.
6. After that, manually verify once with:
   `docker exec data_platform python -c "import sys; sys.path.insert(0,'ingestion/src'); import gsheet_budget_sync as s; s.write_suggestions_to_sheet(dry_run=True)"`
   — confirm the printed cell/value diff looks sane — before flipping to `dry_run=False` for a
   real write, or before relying on the monthly schedule.

Until steps 1-5 are done, the monthly schedule will tick and fail loudly (by design) — this is
expected, not an error in this implementation.

## Status: DONE_WITH_CONCERNS
## Summary: Suggestion-computation + write-back code complete, unit-tested (31/31), Dagster asset/job/schedule registered and import-clean with zero credentials; the actual Sheets-write call is correctly gated behind a runtime credential check but genuinely unexercised end-to-end.
## Concerns/Blockers: HARD EXTERNAL BLOCKER — no Google write-capable credential exists in this repo (verified via import grep + a prior unresolved plan doc flagging the same gap on the read side). Human must do GCP service-account setup (steps above) + `docker compose build data_platform` before this phase is functionally live. The monthly schedule will fail loudly every tick until then — intended behavior, not a defect.
