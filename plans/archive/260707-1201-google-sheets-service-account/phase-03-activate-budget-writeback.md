# Phase 3 — Activate Budget Suggestion Write-Back

**Depends on:** phase-01 (SA key live, Editor share on budget sheet)
**Blocks:** none (independent of phase-02)

## Context

Code is already done (`ingestion/src/gsheet_budget_sync/sheet_writeback.py`, `suggestions.py`, Dagster `budget_suggestion_writeback_asset`/`_job`/`_schedule`) — see `plans/260702-1727-misa-cashflow-budget-planner/phase-10-prefill-suggestions.md` (merged in 2026-07-07 from the former `260705-1459-budget-cashflow-workable-loop/phase-05-prefill-suggestions.md`) and `plans/reports/impl-260705-2010-phase5-prefill-suggestions-report.md` for the original design. This phase only removes the credential blocker and does the first real (non-dry-run) execution.

## Steps

1. Confirm phase-01's SA has **Editor** access on the budget sheet (`SOURCES__SPREADSHEET_URL__BUDGET`) specifically — verify by listing sheet permissions, don't assume from phase-01 notes alone.
2. `sheet_writeback.py` currently reads a budget-specific env var `GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH` (see `GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH_ENV` constant). Since phase-01 introduces one shared credential for everything, replace this with the generic `GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH` from `gsheet_auth.py` — delete the budget-specific env var and its bespoke `gspread.service_account(filename=key_path)` call in `_write_cells_via_sheets_api`, call `gsheet_auth.get_gspread_client()` instead. One credential path everywhere, no duplicate env var.
3. Rebuild `data_platform` (`docker compose build data_platform`) so `gspread` installs (already in `requirements.txt`, never actually installed since nothing imported it for real until now).
4. Remove `GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH` from `.env.example`/`.env.docker.example` (superseded by phase-01's `GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH`, already added there).
5. Run `python -m ingestion.src.gsheet_budget_sync --write-suggestions --target-month <next-month>` for real (not `--dry-run`) — first live write.

## Validation

- Column "Gợi ý" in the budget sheet shows the expected rolling-3-month-avg values for the target month (hand-check 2 lines against `fact_cash_movement`, per the original phase-05 doc's verify step).
- Budget column (finance-entered values) untouched — diff the sheet before/after, only "Gợi ý" column cells changed.
- Re-run same target month again — idempotent, same values written (no duplication, no drift).
- `budget_suggestion_writeback_schedule` runs on its normal schedule (day 1, 08:00 ICT) without the fail-loud `RuntimeError` it's been raising by design.

## Risks

- Writing to the wrong column if the sheet's "Gợi ý" header ever moves — `sheet_writeback.py` already resolves by exact header match (`_assert_gio_column`), not fixed column index; re-verify this guard still fires correctly against the live sheet, not just against mocks (tests so far are mocked, no real API call).
- First real write is irreversible in the sense that finance may see it as odd numbers if the rolling-avg computation has any date-window bug — dry-run diff one more time immediately before the first real run, compare cell-by-cell against what dry-run printed.

## Files touched

- `ingestion/src/gsheet_budget_sync/sheet_writeback.py` (edit — swap credential source to `gsheet_auth.get_gspread_client()`)
- `.env.example`, `.env.docker.example` (edit — remove budget-specific SA env var)
