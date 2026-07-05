# Review Fixes — Budget & Cashflow Workable Loop (3 findings)

Source review: `plans/reports/impl-260705-2022-phase1to5-code-review-report.md`

## Finding 1 (Medium) — modularize `gsheet_budget_sync.py`

Converted `ingestion/src/gsheet_budget_sync.py` (1013 lines) into a package
`ingestion/src/gsheet_budget_sync/` split along its existing concern boundaries, all files
comfortably under 200 LOC:

| File | LOC | Concern |
|---|---|---|
| `fetch.py` | 137 | CSV tab fetch, `_parse_vnd`/`_fmt_num`, `ValidationError`, env/URL/gid constants |
| `budget_transform.py` | 199 | BUDGET_ITEMS parse + validate + build |
| `policy_transform.py` | 196 | ALLOCATION_POLICY parse + validate + build |
| `merge.py` | 37 | Historical merge + atomic seed CSV write |
| `suggestions.py` | 156 | Suggestion targeting/compute logic (pure, no I/O) |
| `duckdb_actuals.py` | 56 | Serving-DB reads feeding suggestion computation |
| `sheet_writeback.py` | 81 | A1-cell helpers + credentialed Sheets API write |
| `__init__.py` | 192 | Re-exports + orchestration (`fetch_transform_and_save`, `write_suggestions_to_sheet`, `run`) |
| `__main__.py` | 8 | CLI entrypoint (`python -m ...`) |

Split into 7 concern modules (vs. the review's suggested 5) because `suggestions.py` alone
was still 274 lines after the first pass — split its DuckDB reads (`duckdb_actuals.py`) and
its credentialed Sheets-API write path (`sheet_writeback.py`) out separately to keep every
file well under 200.

Design constraint discovered: `ingestion/tests/test_gsheet_budget_sync.py` does
`monkeypatch.setattr(sync, "_fetch_tab_csv", ...)` (and similarly for `SEEDS_DIR`,
`_fetch_recurring_actuals_from_duckdb`, `_fetch_reserve_status_from_duckdb`,
`_write_cells_via_sheets_api`) then calls `sync.fetch_transform_and_save(...)` /
`sync.write_suggestions_to_sheet(...)`. Python resolves a function's global names against
its *own* defining module's `__dict__`, not the importer's — so patching `sync.X` (the
package `__init__`) only affects calls made *from code defined in `__init__.py`*. Kept
`fetch_transform_and_save`, `write_suggestions_to_sheet`, and `run` in `__init__.py` itself
(importing the mockable names into its own namespace via `from .submodule import name`)
specifically so the existing tests' monkeypatches keep working unmodified — no test call
sites needed to change.

`import gsheet_budget_sync` (used by `orchestration/assets/sheets_assets.py`) works
unchanged — verified both locally (sys.path simulation) and inside the `data_platform`
container. No behavior change: same functions, same signatures, same validation/merge/
write-back logic, byte-identical docstring content (redistributed across modules).

**Side effect requiring a doc fix**: the flat-file → package conversion means
`python ingestion/src/gsheet_budget_sync.py` (documented in the user guide as the manual
kỹ thuật refresh command) no longer resolves to an existing path. Added `__main__.py` and
updated the doc to `python -m ingestion.src.gsheet_budget_sync` — verified working
end-to-end inside the container (`docker exec data_platform sh -c "cd /app && python -m
ingestion.src.gsheet_budget_sync --dry-run"`; it fetched the live sheet and hit a real
pre-existing ALLOCATION_POLICY validation error unrelated to this refactor, proving the
full pipeline executes correctly through the new package).

## Finding 2 (Medium) — stale "chưa triển khai" doc claim

`docs/analytics-handbook/guides/finance-budget-user-guide.md` line 76 (Gợi Ý column row):
replaced the blanket "chưa triển khai" (not implemented) claim with an accurate
built-but-not-activated framing — states the rolling-avg auto-fill exists and is scheduled
(1st of month, 08:00 ICT) but is not yet live pending a technical setup step (Google
service-account write credential), and that finance must still self-estimate/leave blank
until then.

## Finding 3 (Low) — missing env placeholder

Added `GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH` placeholder line (with a 3-line comment
pointing at `sheet_writeback.py` for setup steps) directly after
`SOURCES__SPREADSHEET_URL__BUDGET` in both `.env.example` (quoted value, matching file
convention) and `.env.docker.example` (unquoted value, matching file convention).

## Files Modified

- `ingestion/src/gsheet_budget_sync.py` → deleted, replaced by
  `ingestion/src/gsheet_budget_sync/` (9 new files, see table above)
- `docs/analytics-handbook/guides/finance-budget-user-guide.md` — 2 lines (Gợi Ý claim +
  CLI invocation)
- `.env.example`, `.env.docker.example` — 4 lines each (1 var + 3-line comment)
- `ingestion/tests/test_gsheet_budget_sync.py` — untouched (no import/call-site changes
  needed; all `sync.X` references resolve via `__init__.py` re-exports)
- `orchestration/assets/sheets_assets.py` — untouched (`import gsheet_budget_sync` resolves
  to the package unchanged; the `M` status in git is pre-existing Phase 1-5 uncommitted work,
  not from this session — confirmed via `git diff --stat` showing only prior +118 insertions)

## Verification

- `python -m pytest ingestion/tests/test_gsheet_budget_sync.py -q` → **31 passed** (same
  count as baseline).
- `docker exec data_platform python -c "import orchestration.definitions as d; print(len(d.defs.jobs), len(d.defs.schedules))"` → **21 jobs, 17 schedules** (matches baseline), clean
  import, `hasattr` checks confirm `run`/`write_suggestions_to_sheet`/`fetch_transform_and_save`
  all resolve on the package.
- `py_compile` on all 9 new package files (inside container) → all compile clean.
- `python -m ingestion.src.gsheet_budget_sync --dry-run` inside container → executes the full
  fetch → parse → validate pipeline against the live sheet (hits a real, pre-existing
  ALLOCATION_POLICY data issue unrelated to this refactor — confirms the CLI path works).
- `grep "chưa triển khai"` in the user guide → no longer present; replaced with an accurate
  "CHƯA kích hoạt" (not yet activated) framing.
- Both env example files confirmed to have the new placeholder in the correct format.

## Unresolved Questions

None.

Status: DONE
Summary: Split gsheet_budget_sync.py into a 9-file package (all <200 LOC) preserving all 31 tests + import compatibility; fixed the stale Gợi Ý doc claim + the CLI invocation line the package conversion broke; added the missing GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH env placeholder to both example files.
Concerns/Blockers: None.
