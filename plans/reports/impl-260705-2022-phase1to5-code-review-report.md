# Code Review — Budget & Cashflow Workable Loop (Phases 1-5)

Plan: `plans/260705-1459-budget-cashflow-workable-loop/plan.md`
Reviewed independently against actual diffs; phase "Status: DONE" self-reports treated as unverified claims, not evidence.

## Verdict: DONE_WITH_CONCERNS

No blocking defect found in the runtime-critical paths (validation, historical merge, seed write, mart WHERE clause, schedule registration, credential-free import). Two Medium findings (file-size/modularization violation, stale user-guide claim) and one process-hygiene observation (undocumented scope in phase self-reports) should be fixed before this is called fully clean, but none of them break the workable loop.

---

## Acceptance Criteria — PASS/FAIL

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | Sheet matrix (3 tabs) → 2 seed CSVs; bad data rejected loud, no seed overwrite on failure | **PASS** | `gsheet_budget_sync.py` L940-993 (`fetch_transform_and_save`): validation errors collected, seeds only written after `all_errors` check; `_write_csv_atomic` uses tmp-file + `os.replace` (no partial writes). Confirmed via `test_full_sync_aborts_and_does_not_write_seed_on_validation_failure` — seed file byte-identical after a rejected sync. |
| 2 | `mart_cashflow_budget_vs_actual.sql` budget CTE adds `WHERE item_type = 'recurring'` as the ONLY change; forecast/reserve marts untouched | **PASS** | `git diff` shows exactly one added `WHERE` line + a comment. `git status --short` confirms zero diff on `mart_cashflow_forecast.sql` / `mart_cashflow_reserve_status.sql`. |
| 3 | Blueprint: 3 scorecards scoped `coverage='both'`, new "Ngoài kế hoạch" card, A3 shows coverage distinction, `period_month` default = `past1months` (not `previousmonth`) | **PASS** | Diff L130-225 (Thuc_te/Chenh_lech/Ti_le_pct all gain `WHERE coverage = 'both'`; new "A1 - Ngoai ke hoach" card `WHERE coverage='actual_only'`); L326-340 (A3 adds `coverage` column + `ORDER BY CASE coverage WHEN 'both' THEN 0 ELSE 1`); L67 (`"default": "past1months"`). Phase-04's report documents a live Metabase v0.60.2 probe proving `previousmonth` 500s — token choice is evidence-backed, not guessed. |
| 4 | User guide: zero remaining references to "Download CSV → overwrite seed" | **PASS** (with a caveat, see Medium-2 below) | Full diff of `finance-budget-user-guide.md` replaces every CSV-export/`dbt seed` manual step with the nightly-sync description; grep for "Download" / "lưu đè" against the new text returns nothing. |
| 5 | `ingest_monthly_repull_schedule` cron `0 7 10 * *` ICT, reuses `ingest_monthly_job`, has `_has_active_run` guard | **PASS** | `definitions.py` L500-508: `job=ingest_monthly_job`, cron matches, guard identical pattern to sibling schedules. |
| 6a | Phase 5 write-back never writes "Budget", only "Gợi Ý" — real guard, not just a comment | **PASS** | `_assert_gio_column()` (L697-706) is a real `assert` gating every write path: called once in `build_suggestion_writes` (targeting) and again per-cell in `_write_cells_via_sheets_api` (defense-in-depth, right before the actual API call). `test_assert_gio_column_rejects_the_budget_column` proves it raises on the adjacent column. |
| 6b | Module-level import doesn't require Google credentials; no duplicate imports/name collisions across the 3 sequentially-added schedules/assets | **PASS** | `import gspread` is local to `_write_cells_via_sheets_api` only (grep confirms zero top-level `gspread`/`google.oauth2`/`googleapiclient` imports). Live check: `docker exec data_platform python -c "import orchestration.definitions"` → clean, 21 jobs / 17 schedules, no exceptions. Grepped all new symbol names (`budget_sheet_sync_asset`, `budget_suggestion_writeback_asset`, `*_job`, `*_schedule`) — each defined exactly once. |
| 7 | Historical merge: past-month rows preserved verbatim, current+future replaced | **PASS** | `merge_historical_budget()` (L600-615): `old_kept` = existing rows `< current_month_start`, `new_kept` = fresh rows `>= current_month_start`, concatenated. `test_merge_historical_preserves_past_months_keeps_current_and_future` uses a 3-month fixture with a deliberately stale current-month row and a preserved historical `notes` field — not a trivial single-fixture rubber stamp. |
| 8 | No auto-commit of seed CSVs anywhere | **PASS** | `grep -rn "git commit\|git add"` against `gsheet_budget_sync.py` and `sheets_assets.py` → zero matches. |

Plan-level acceptance criteria (§ plan.md):
- Finance edit → dashboard 114 without touching CSV/docker: **PASS** (nightly 02:30 sync + 03:00 dbt build wired; manual Dagit "Materialize" documented as the T+0 path in the guide).
- Sync rejects bad data loudly: **PASS** (see #1).
- Guide describes real sheet matrix, step-by-step: **PASS**, with the phase-5-drift caveat below.
- Scorecard scope fix: **PASS** (see #3).
- Ledger re-pull day 10 + non-empty default landing view: **PASS** (see #5, #3).
- No regression `fact_order_costs` / `fact_cash_movement` / dashboard 113: **PASS** — `git status --short` shows zero diff on `fact_order_costs`, `fact_cash_movement`, and on the Metabase blueprint `docs/analytics-handbook/blueprints/metabase/finance_cashflow.md` (dashboard 113 proper).

---

## Findings

### Medium — `gsheet_budget_sync.py` is 1013 lines, 3.5-5x every sibling script, contradicting both the global modularization rule and the phase's own spec
`ingestion/src/gsheet_budget_sync.py:1-1013`. Sibling `gsheet_*.py` scripts are 216-289 LOC (`gsheet_targets.py`=259, `gsheet_marketing_spend.py`=216, `gsheet_overhead_classification.py`=289). `phase-01-sheet-to-seed-sync.md` L32 explicitly asked for "~dưới 200 LOC mỗi concern, tách file nếu vượt" (split by concern if it exceeds ~200 LOC/concern), and the user's global `CLAUDE.md` has a standing "if a file exceeds 200 lines, consider modularizing" rule. The file cleanly separates into 5 concerns already (fetch, budget parse/validate, policy parse/validate, historical merge, suggestion compute/write-back) that were never split into modules — this was ignored entirely, not just under-applied. Recommend splitting along the module's own section-comment boundaries (e.g. `budget_sync/fetch.py`, `parse_validate_budget.py`, `parse_validate_policy.py`, `merge.py`, `suggestions.py`, keeping a thin `gsheet_budget_sync.py` as the CLI entrypoint) in a follow-up — not a functional bug, but a repeat-offender maintainability risk given this repo already has a lesson (L156) about parallel subagents colliding inside oversized/ambiguous module boundaries.

### Medium — User guide still claims the suggestion auto-fill "chưa triển khai" (not yet implemented) after Phase 5 implemented it
`docs/analytics-handbook/guides/finance-budget-user-guide.md:76`: *"Số gợi ý — hiện tại nhập tay hoặc để trống, KHÔNG được sync đọc. Việc tự động điền gợi ý (rolling avg thực tế 3 tháng) là hạng mục riêng chưa triển khai."* This was accurate when Phase 2 (guide rewrite) ran, since Phase 2 depends only on Phase 1 and Phase 5 (P2, lowest priority) ran later in the same day. Phase 5 did land `--write-suggestions` + `budget_suggestion_writeback_asset` (scheduled 1st-of-month 08:00 ICT, currently `STOPPED` by default per the repo's schedule-off-by-default convention). The claim is *functionally* still true today only by accident (the feature can't actually write until a human sets up `GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH`), but the doc text asserts the feature doesn't exist in the codebase at all, which is now false and will silently mislead finance the moment credentials are configured and the schedule is turned on. No phase closed this loop — neither phase-2's nor phase-5's self-report mentions touching the guide's Gợi Ý row. Needs a one-line update in a follow-up (e.g. "auto-fill exists but is not yet turned on — ask kỹ thuật before relying on it").

### Low — `GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH` not added to `.env.example` / `.env.docker.example`
Every other env var this plan introduces (`SOURCES__SPREADSHEET_URL__BUDGET`) got a placeholder line in both files; the write-back credential path (referenced in the module docstring, `sheets_assets.py`, and `definitions.py` comments) has no corresponding placeholder, making it harder for ops to discover the exact variable name when they eventually do the GCP setup. Cosmetic — the docstring is a reasonable secondary source of truth — but a 1-line inconsistency with the plan's own convention.

### Informational — Phase self-reports understate the actual diff on `finance_cashflow_budget.md`
Phase-3's report says "only file touched, as scoped" and lists A1/A3/Source-Freshness-BvA edits + an emoji-parser fix; Phase-4's report says "1 line" changed in this file. The actual cumulative diff also silently converts every remaining Vietnamese-diacritic label across A2/A4/B1-B4 (previously mojibake, e.g. `Kế hoạch` → garbled `�` bytes at HEAD) into ASCII (`Ke_hoach`). Verified this is *not* a regression — it brings the file in line with the repo's own documented convention (lesson L155: "Always use ASCII column aliases... when the display name contains Vietnamese") and matches the sibling dashboard 113 blueprint (`finance_cashflow.md`, which already uses `graph.metrics: ["Tong thu", "Tong chi", ...]` with no diacritics). So the *change itself is correct and beneficial* (fixes leftover corruption from a partial prior fix, commit `e77b1403`, which explicitly said it only fixed "4 cards"). Flagging only because neither phase report discloses this scope, which is exactly the kind of drift the task asked to independently verify rather than trust.

### Non-issue (verified, not a defect in this plan's diff) — `docs/analytics-handbook/blueprints/evidence/finance_cashflow.md` and `evidence/pages/finance-cashflow/index.md` both have uncommitted diffs
The task brief asked me to confirm dashboard 113's blueprint has no diff. The **Metabase** blueprint (`docs/analytics-handbook/blueprints/metabase/finance_cashflow.md`) is confirmed untouched (`git status --short` shows nothing). The **Evidence** blueprint variant (`docs/analytics-handbook/blueprints/evidence/finance_cashflow.md`) does have an unrelated diff (adds a client-side `<Dropdown>` period filter + converts the waterfall to a Sankey diagram) — but this is unambiguously not part of the 5-phase plan: no phase doc mentions Evidence, Sankey, or dropdowns, `git log` shows the Evidence dashboard was built in 3 separate prior commits unrelated to this plan, and the task's own out-of-scope list already excludes `evidence/` broadly (this file just lives one directory over, in `docs/.../blueprints/evidence/`, not `evidence/` itself). Calling this out per the explicit check-(b) instruction, but treating it as unrelated concurrent work, not a regression from this plan.

---

## Test / Build Verification

- `python -m pytest ingestion/tests/test_gsheet_budget_sync.py -q` → **31 passed** (matches expected count). Tests are substantive, not phantom: they exercise real fixtures with deliberately-planted stale/edge data (e.g. a stale-current-month row that must be overwritten, a reserve item deliberately absent from the recurring map to prove the "skip when no data" branch, an `_assert_gio_column` boundary test at the exact adjacent column).
- `docker exec data_platform python -c "import orchestration.definitions as d; print(len(d.defs.jobs), len(d.defs.schedules))"` → `21 jobs`, `17 schedules`, clean import, no exceptions. No duplicate asset/job/schedule names found via grep across `sheets_assets.py` + `definitions.py`.
- `python -c "import py_compile; py_compile.compile('ingestion/src/gsheet_budget_sync.py', doraise=True)"` → compiles clean. No linter config present in `ingestion/` to run against.
- Did not run `dbt build` or any dbt command against the container per task instruction (avoid concurrent dbt ops).

---

## Scope Note

`orchestration/assets/sapo_v2_assets.py` (unrelated watchdog fix) and everything under `crm/`, `.skills/pkf/`, `.agents/skills/pkf/`, `evidence/` were excluded from this review per the task's explicit out-of-scope list, and were not inspected beyond confirming they weren't accidentally required by the in-scope diffs (they aren't — `sheets_assets.py`/`definitions.py` diffs are additive only, no edits near the watchdog code).

## Unresolved Questions

1. Should `budget_suggestion_writeback_schedule` be given an explicit `default_status=DefaultScheduleStatus.STOPPED` (matching every non-`crm_backup` schedule) documented inline, so a future operator doesn't accidentally flip it on before the GCP service-account setup is done and get a monthly `RuntimeError` alert? (Currently relies on the implicit off-by-default convention, which is correct today but undocumented at the point of definition.)
2. Is the Phase-1 spec's secondary validation ("cross-check recurring `cashflow_line` ∈ distinct `dim_gl_account.cashflow_line` nếu chạy trong container") intentionally dropped in favor of relying solely on `__REF` (which is *supposed* to already mirror `dim_gl_account`), or was it missed? If `__REF` ever drifts from `dim_gl_account` (e.g. someone edits one without the other), the sync would accept a line that doesn't actually join to real MISA actuals, producing a silent `budget_only` row instead of a rejection. Worth a follow-up ticket even if intentionally deferred as YAGNI for now.
