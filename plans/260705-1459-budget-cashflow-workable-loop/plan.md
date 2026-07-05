# Budget & Cashflow — Close the Workable Loop

**Status:** IMPLEMENTED — code done, reviewed, regression-tested (8/8 pass). 2 open items require human action (see below), not code.
**Created:** 2026-07-05
**Implemented:** 2026-07-05
**Context:** Đánh giá 2026-07-05 kết luận: pipeline actuals + dashboard 114 chạy tốt, nhưng vòng budget đứt ở giữa — sheet matrix (source of truth, đã build + Apps Script validator) không có đường vào seed CSV; user guide mô tả sai layout; scorecard so sánh lệch phạm vi. Budget bắt đầu từ T7/2026.

**Nguồn sự thật:**
- Sheet matrix 3 tabs (BUDGET_ITEMS gid=0 / ALLOCATION_POLICY gid=1662021004 / __REF gid=2061002942): `https://docs.google.com/spreadsheets/d/15hba6bzrTRXUDXBeUg5_DhefrETX9kLGG8SnPJZzTfA/edit` — layout đúng theo `scripts/budget/validate-budget-sheet.gs`, đã verify CSV export hoạt động (link-shared, không cần creds)
- Seed schema: `transformation/seeds/seed_cashflow_budget.csv` + `seed_cash_allocation_policy.csv` (long format)
- Thiết kế gốc: `plans/260702-1727-misa-cashflow-budget-planner/phase-04-budget-hybrid.md`

## Phases

| # | Phase | File | Ưu tiên | Phụ thuộc | Ra được gì |
|---|-------|------|---------|-----------|-----------|
| 1 | Sheet→seed sync script | `phase-01-sheet-to-seed-sync.md` | P0 | — | Script + Dagster asset: matrix sheet → 2 seed CSV, validate, scheduled |
| 2 | Viết lại user guide | `phase-02-user-guide-rewrite.md` | P0 | P1 xong (quy trình mới) | Guide khớp sheet thật, quy trình 1 bước cho finance |
| 3 | Sửa scorecard scope | `phase-03-scorecard-scope-fix.md` | P1 | — | Attainment/variance chỉ tính `coverage='both'` + card "ngoài kế hoạch" |
| 4 | Ledger re-pull ngày 10 + default filter | `phase-04-ledger-repull-default-filter.md` | P1 | — | Số tháng trước khớp sổ chốt; landing view luôn có số |
| 5 | Pre-fill "Gợi ý" | `phase-05-prefill-suggestions.md` | P2 | P1 | Ghi rolling avg 3 tháng actual ngược vào sheet |

Phase 3+4 độc lập với 1+2, làm song song được.

**Trạng thái tất cả phase: DONE** (code xong, review DONE_WITH_CONCERNS → 3 finding đã fix, regression test 8/8 pass). Chi tiết mỗi phase xem file `phase-0N-*.md` tương ứng.

## Acceptance criteria (toàn plan)

- [x] Finance edit sheet → số xuất hiện trên dashboard 114 mà không cần đụng CSV/docker (chậm nhất T+1 qua nightly build 02:30+03:00 ICT; lệnh manual refresh ngay = materialize asset `sheets/budget_sheet_sync_asset` hoặc `python -m ingestion.src.gsheet_budget_sync`).
- [x] Sync script reject dữ liệu sai (line không khớp `__REF`/`dim_gl_account`, policy gap/overlap) với thông báo rõ — verified qua 31 unit test + reject-case test.
- [x] Guide mô tả đúng sheet matrix; làm theo từng bước không fail — rewritten, verified khớp `validate-budget-sheet.gs`.
- [x] Card "Tỷ lệ thực hiện"/"Chênh lệch" chỉ so kế-hoạch-vs-thực-tế cùng phạm vi (`coverage='both'`); thực tế ngoài kế hoạch hiển thị riêng ở card "Ngoài kế hoạch" — deployed + verified số khớp (192M + 5.9B = tổng cũ).
- [x] Actuals tháng trước được re-pull sau khi sổ MISA chốt (~ngày 10) — `ingest_monthly_repull_schedule` cron `0 7 10 * *` ICT; mở dashboard mặc định thấy tháng có số đầy đủ — filter default `past1months` (verified valid token, `previousmonth` KHÔNG hợp lệ trên Metabase v0.60.2).
- [x] Không regression: `fact_order_costs`, `fact_cash_movement`, dashboard 113 — confirmed zero diff qua code review + regression test.

## Open items cần hành động của người (không phải lỗi code)

1. **Sheet ALLOCATION_POLICY thiếu dòng `remainder`** — sync sẽ reject cho tới khi finance/kỹ thuật thêm dòng priority cuối, bucket tự do, rule_type=`remainder`, value trống, vào sheet thật (xem phase-01 open question 5). Đây là bước bắt buộc TRƯỚC khi lần sync đầu tiên chạy thành công.
2. **Phase 5 (pre-fill gợi ý) code xong nhưng CHƯA kích hoạt** — cần tạo Google service account, share sheet quyền Editor, set `GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH`, rebuild `data_platform` để cài `gspread`. Chi tiết: `plans/reports/impl-260705-2010-phase5-prefill-suggestions-report.md`. Tới khi đó lịch `budget_suggestion_writeback_schedule` sẽ fail loud mỗi lần chạy (by design, không silent).

## Rủi ro chính

- Mapping `cashflow_line` cho dòng one_off/reserve (col A là label tự do, không phải line) — cần chốt trước khi code transform (xem phase-01 open question).
- Sheet gid/tab đổi tên → sync fail: script phải fail loud, không ghi seed rỗng đè seed cũ.
- Seed ghi từ container cần mount `transformation/seeds/` writable — verify trước.
