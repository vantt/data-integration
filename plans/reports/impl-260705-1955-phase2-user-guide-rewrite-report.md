# Phase Implementation Report

### Executed Phase
- Phase: phase-02-user-guide-rewrite
- Plan: plans/260705-1459-budget-cashflow-workable-loop/
- Status: completed

### Files Modified
- `docs/analytics-handbook/guides/finance-budget-user-guide.md` (full §2 rewrite, FAQ updates, §4 rewrite, top note added — net +~50 lines)

### Tasks Completed
- [x] Top-of-file note added pointing to `scripts/budget/validate-budget-sheet.gs` as source of truth
- [x] §2 Bước 1 rewritten: matrix layout (cột A-F fixed + `[Gợi Ý][Budget]` pairs from col G), column names/order verified 1:1 against `BI_COL` in `.gs` (Dòng Tiền/Chiều/Type/Tháng Cần/Tuần TT/Tổng Cần); clarified only `Budget` col is read by sync, `Gợi Ý` is manual/not-yet-automated; "thêm tháng mới" = add column pair (or check if 12 months pre-built)
- [x] §2 Bước 2 rewritten: deleted "Download CSV → lưu đè seed" entirely; replaced with auto-sync explanation (02:30 ICT nightly), manual-refresh-now via Dagster UI materialize `sheets/budget_sheet_sync_asset` or `python ingestion/src/gsheet_budget_sync.py [--dry-run]`
- [x] §2 Bước 3 reduced to "muốn thấy ngay" fallback note; nightly build (03:00 ICT) is now the default, no manual dbt step required
- [x] FAQ "Thêm dòng tiền mới" rewritten: explains `__REF` is not free-add — new `recurring` line must exist in `dim_gl_account.cashflow_line` (MISA taxonomy) first, else sync rejects the whole sheet; correct order = confirm/add taxonomy via tech team → add to `__REF` → add to BUDGET_ITEMS
- [x] §4 schedule table aligned to new cadence: entry anytime → auto-sync 02:30 → dbt build 03:00 → visible T+1; day 5-10 MISA close-then-review kept (phrased as "sổ MISA thường chốt xong trong khoảng này", not claiming a deployed re-pull cron since `ingest_monthly_repull_schedule` doesn't exist in `orchestration/definitions.py` yet)
- [x] §1 and read-only FAQ (data-freshness card, allocation-policy column table, month-detail filter) left unchanged
- [x] Bonus consistency fixes (not explicitly in phase table but same-file, same-issue): "Chi phí phát sinh đột ngột" FAQ example rewritten from old flat CSV fields (`cashflow_line:`/`period_month:`/etc.) to real matrix columns; "Dòng tiền thực tế vượt/thiếu hụt" FAQs' `planned_amount`/`payment_week` references swapped for actual column names (Budget col / Tuần TT col E); "Dashboard trống" FAQ step 3 swapped `dbt seed đã chạy chưa?` for checking the `sheets/budget_sheet_sync_asset` Dagster run status — left without touching the ALLOCATION_POLICY rule_type enum table (pre-existing, unrelated to this migration)

### Tests Status
- Type check: N/A (markdown only)
- Unit tests: N/A
- Grep verification: zero hits for "Download" as an instruction and "lưu đè" as an instruction (1 hit is the negation sentence "Không còn bước Download CSV → lưu đè seed", intentional)
- Column name cross-check: `Dòng Tiền/Chiều/Type/Tháng Cần/Tuần TT/Tổng Cần` and column letters A-F match `BI_COL` in `scripts/budget/validate-budget-sheet.gs` exactly, order preserved; asset key `sheets/budget_sheet_sync_asset` and cron `30 2 * * *` (Asia/Ho_Chi_Minh) verified against `orchestration/definitions.py` line 168-173, 485-494, and `orchestration/assets/sheets_assets.py` line 266-267
- Literal walkthrough of rewritten §2 as a non-engineer finance user: Bước 1 (edit Budget column) → Bước 2 (nothing, or optional manual trigger via Dagster UI) → Bước 3 (optional dbt fallback, requires tech) → Bước 4 (check dashboard) — no step depends on removed functionality (no CSV export, no manual seed overwrite as primary path)

### Issues Encountered
None. `--dry-run` flag confirmed present in `ingestion/src/gsheet_budget_sync.py` (`run()` checks `"--dry-run" in argv`). `ingest_monthly_repull_schedule` confirmed NOT present in `orchestration/definitions.py` — §4 phrased to avoid overclaiming a deployed cron for the MISA re-pull, describing only the observed close cadence.

### Next Steps
Phase-02 done. Phase-04 (ledger re-pull ngày 10 + default filter) will formalize the MISA re-pull schedule mentioned loosely in §4 — once that lands, §4's "Ngày 5-10" row could be tightened with the actual cron, but that's out of this phase's scope.

Status: DONE
Summary: Rewrote finance-budget-user-guide.md §2 to describe the real matrix-sheet + auto-sync process (zero manual CSV/seed step), fixed FAQ "Thêm dòng tiền mới" to warn about the dim_gl_account/__REF taxonomy gate, realigned §4 schedule to the new nightly cadence, added top-of-file pointer to validate-budget-sheet.gs as source of truth, and cleaned up a few adjacent FAQ examples that still referenced the old flat CSV schema.
Concerns/Blockers: None.
