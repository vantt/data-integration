# MISA Cashflow Report + Budget Planner

**Status:** DONE — Wave 1 (report + budget layer, P03-P05: 2026-07-02/04) và Wave 2 (workable loop close, P06-P10: 2026-07-05/07) đều hoàn thành. Phase 10 kích hoạt xong (2026-07-07) — không còn open item nào.
**Created:** 2026-07-02
**Merged (2026-07-07):** `plans/260705-1459-budget-cashflow-workable-loop` sáp nhập vào đây làm Phase 6-10 (đóng các gap vận hành phát sinh sau khi Wave 1 chạy thật) — cùng 1 sản phẩm, 1 vòng đời, tách plan riêng trước đây chỉ vì lý do thời điểm.
**Split (2026-07-07, trước khi merge):** Phases 1-2 (full-ledger ingestion + GL modeling — hạ tầng) đã tách sang `plans/archive/260707-1207-misa-gl-infrastructure/`.
**Branch (proposed):** `feature/misa-cashflow-budget`
**Owner decisions locked:**
- Budget source = **Hybrid** (actual từ MISA ledger; budget khởi đầu bằng CSV của ta, thiết kế để sau này đọc từ MISA)
- Cashflow scope = **Vận hành** (thu/chi + số dư quỹ), KHÔNG phải BC lưu chuyển tiền tệ TT200 3 mục

## Vấn đề / Bối cảnh

Cashflow cần tiền (111/112) + số dư quỹ theo kỳ, báo cáo Budget-vs-Actual so kế hoạch với thực tế lấy từ GL. (Phần ingest/modeling nền tảng — xem `plans/archive/260707-1207-misa-gl-infrastructure/`.)

Sau khi Wave 1 (report + budget layer) chạy thật, đánh giá 2026-07-05 phát hiện vòng budget đứt ở giữa: sheet matrix (nguồn sự thật, đã build + Apps Script validator) không có đường vào seed CSV; user guide mô tả sai layout; scorecard so sánh lệch phạm vi. Wave 2 (Phase 6-10) đóng các gap này. Budget bắt đầu từ T7/2026.

**Nguồn sự thật (Wave 2 — sheet matrix):**
- Sheet matrix 3 tabs (BUDGET_ITEMS gid=0 / ALLOCATION_POLICY gid=1662021004 / __REF gid=2061002942): `https://docs.google.com/spreadsheets/d/15hba6bzrTRXUDXBeUg5_DhefrETX9kLGG8SnPJZzTfA/edit` — layout đúng theo `scripts/budget/validate-budget-sheet.gs`, verify CSV export hoạt động (link-shared, không cần creds)
- Seed schema: `transformation/seeds/seed_cashflow_budget.csv` + `seed_cash_allocation_policy.csv` (long format)

## Phases

| # | Phase | File | Phụ thuộc | Ra được gì |
|---|-------|------|-----------|-----------|
| 3 | Cashflow report (Metabase) | `phase-03-cashflow-report.md` | `plans/archive/260707-1207-misa-gl-infrastructure/` | Dashboard vận hành: số dư quỹ, thu/chi theo kỳ, top đối ứng, dòng tiền ròng |
| 4 | Budget layer hybrid + Budget-vs-Actual | `phase-04-budget-hybrid.md` | P3 | `fact_cashflow_budget` (source-swappable), report kế hoạch vs thực tế + dự báo số dư |
| 5 | ~~MISA budget scraper~~ **DROPPED** | `phase-05-misa-budget-scraper.md` | — | Finance không dùng MISA budget module → không có gì để scrape (2026-07-03) |
| 6 | Sheet→seed sync script (P0) | `phase-06-sheet-to-seed-sync.md` | P4 | Script + Dagster asset: matrix sheet → 2 seed CSV, validate, scheduled |
| 7 | Viết lại user guide (P0) | `phase-07-user-guide-rewrite.md` | P6 xong | Guide khớp sheet thật, quy trình 1 bước cho finance |
| 8 | Sửa scorecard scope (P1) | `phase-08-scorecard-scope-fix.md` | P4 | Attainment/variance chỉ tính `coverage='both'` + card "ngoài kế hoạch" |
| 9 | Ledger re-pull ngày 10 + default filter (P1) | `phase-09-ledger-repull-default-filter.md` | P4 | Số tháng trước khớp sổ chốt; landing view luôn có số |
| 10 | Pre-fill "Gợi ý" (P2) | `phase-10-prefill-suggestions.md` | P6 | Ghi rolling avg 3 tháng actual ngược vào sheet |

Phase 8+9 độc lập với 6+7, làm song song được.

## Tiến độ — Phase 03→10 DONE (báo cáo LIVE)

- ✅ **Phase 03 Report**: dashboard Metabase "Finance Cashflow" (ID 113) deployed từ blueprint. waterfall+pivot native v0.60.2. June recon khớp tuyệt đối (thu 464.4M/chi 434.0M/ròng +30.4M).
- ✅ **Phase 04 Budget**: seed + 6 dbt models + serving views DONE (2026-07-04). Dashboard "Finance Budget vs Actual" (ID 114) deployed — 15 cards, 2 tabs, Apps Script dynamic dropdown, variance + forecast. Blueprint garbled SQL fixed (2026-07-04).
- ✅ **Phase 06-09**: code xong, review DONE_WITH_CONCERNS → 3 finding đã fix, regression test 8/8 pass (2026-07-05).
- ✅ **Phase 10**: kích hoạt xong (2026-07-07) — service account thiết lập qua `plans/260707-1201-google-sheets-service-account` (3 phase, commit `af41ffd9`). Ghi thật đầu tiên tháng 2026-08: 8 ô "Gợi Ý", verify Budget column không bị đụng, re-run idempotent.

**Insight thật (6 tháng, từ hạ tầng GL):** dòng tiền âm 3/6 tháng (Jan −100M, Feb −70M, May −23M); dương Mar +85M, Jun +30M; số dư quỹ 72M–165M.

**Cleanup nhỏ deferred:** Blueprint dùng header `## Segmentation Scope` (cũ) → warning non-blocking, đổi `## Semantic Contract` sau. (`fact_account_balance_monthly` NULL-balance cleanup → tracked in `plans/archive/260707-1207-misa-gl-infrastructure/`.)

## Kiến thức domain & Thực hành (cập nhật khi có learnings mới)

- **SME Budget Planning Practices**: `docs/context/sme-budget-planning-practices.md`
  - Kiến trúc rolling 13-week forecast, zero-based nhẹ, Tier 1/2/3 chi tiêu
  - Schema `fact_cashflow_budget`, variance mart SQL, cash forecast model
  - Sai lầm phổ biến + KPIs dashboard cho CFO
  - **Quy tắc:** Khi phase phát sinh learnings mới → cập nhật tài liệu này trước, rồi dẫn chiếu lại từ phase file

## Tài liệu thiết kế báo cáo (analytics-handbook — nguồn sự thật cho WHAT)

Thiết kế báo cáo dòng tiền KHÔNG nằm trong phase file — sống ở 4 tài liệu handbook chuẩn (tạo 2026-07-02). Phase-03/04 chỉ điều phối thực thi + trỏ vào đây:

- **Domain**: `docs/analytics-handbook/domains/finance.md` § Cashflow (metrics CF1-CF4, dimensions, recon)
- **Playbook**: `docs/analytics-handbook/playbooks/finance_cashflow.md` (audience, câu hỏi, action triggers)
- **Design spec**: `docs/analytics-handbook/designs/finance_cashflow.md` (viz: scorecard·waterfall·pivot·line+forecast·combo·hbar)
- **Blueprint**: `docs/analytics-handbook/blueprints/metabase/finance_cashflow.md` (deployable SQL+viz JSON+layout)

Phase-04 (budget) mở rộng CÙNG dashboard: thêm cột Kế hoạch|Chênh lệch vào pivot + đường forecast (đã đánh dấu "Phase-04 extensions" trong blueprint).

## Acceptance criteria

**Wave 1 (report + budget layer):**
- [x] Dashboard cashflow vận hành live trên Metabase, số liệu recon với MISA sổ quỹ.
- [x] Budget nhập qua CSV, `fact_cashflow_budget` có cột `budget_source` để swap sang MISA không đổi schema report.
- [x] Report Budget-vs-Actual: variance + dự báo số dư quỹ cuối kỳ.

**Wave 2 (workable loop close):**
- [x] Finance edit sheet → số xuất hiện trên dashboard 114 mà không cần đụng CSV/docker (chậm nhất T+1 qua nightly build 02:30+03:00 ICT; lệnh manual refresh ngay = materialize asset `sheets/budget_sheet_sync_asset` hoặc `python -m ingestion.src.gsheet_budget_sync`).
- [x] Sync script reject dữ liệu sai (line không khớp `__REF`/`dim_gl_account`, policy gap/overlap) với thông báo rõ — verified qua 31 unit test + reject-case test.
- [x] Guide mô tả đúng sheet matrix; làm theo từng bước không fail — rewritten, verified khớp `validate-budget-sheet.gs`.
- [x] Card "Tỷ lệ thực hiện"/"Chênh lệch" chỉ so kế-hoạch-vs-thực-tế cùng phạm vi (`coverage='both'`); thực tế ngoài kế hoạch hiển thị riêng ở card "Ngoài kế hoạch" — deployed + verified số khớp (192M + 5.9B = tổng cũ).
- [x] Actuals tháng trước được re-pull sau khi sổ MISA chốt (~ngày 10) — `ingest_monthly_repull_schedule` cron `0 7 10 * *` ICT; mở dashboard mặc định thấy tháng có số đầy đủ — filter default `past1months` (verified valid token, `previousmonth` KHÔNG hợp lệ trên Metabase v0.60.2).
- [x] Không regression: `fact_order_costs`, `fact_cash_movement`, dashboard 113 — confirmed zero diff qua code review + regression test.

(Ingestion/modeling acceptance criteria — downloader toàn sổ cái, số dư quỹ đúng — ở `plans/archive/260707-1207-misa-gl-infrastructure/plan.md`.)

**Grain budget vận hành:** budget theo **dòng thu/chi = nhóm tài khoản đối ứng**, không theo TK tiền. Ví dụ line: `Thu bán hàng (131)`, `Chi lương (334x)`, `Chi BHXH (338x)`, `Chi NCC (331x)`, `Chi ads (642172)`. Đây là grain finance nhập budget dễ hiểu + join được actual từ `fact_cash_movement`.

## Open items cần hành động của người (không phải lỗi code)

1. ~~Sheet ALLOCATION_POLICY thiếu dòng `remainder`~~ → **DONE (2026-07-07)**: verified row 9 "Tiền Mặt Tự Do", rule_type=`remainder`, value trống, hiệu lực từ 2026-07-01. Sync đầu tiên vẫn fail thêm 1 lỗi khác (bug code, không phải hành động người): cell `pct_remaining` value "20%" — Google Sheets export CSV theo display format (Percent) nên `%` leak vào text export; `_parse_vnd()` (`ingestion/src/gsheet_budget_sync/fetch.py`) chưa strip `%` nên parse ra `None`. Đã fix (strip `%` trong `_parse_vnd`) + verify: dry-run sạch, `ALLOCATION_POLICY: 9 row(s)` không lỗi, dòng "Mua Laptop 3" parse đúng `value=20`. Sync đầu tiên giờ chạy được.
2. ~~Phase 10 (pre-fill gợi ý) code xong nhưng CHƯA kích hoạt~~ → **DONE (2026-07-07)**: service account thiết lập qua `plans/260707-1201-google-sheets-service-account` (3 phase). `budget_suggestion_writeback_schedule` giờ chạy thật, không còn fail-loud. Chi tiết code Phase 10: `plans/reports/impl-260705-2010-phase5-prefill-suggestions-report.md`.

## Rủi ro chính

- Mapping `cashflow_line` cho dòng one_off/reserve (col A là label tự do, không phải line) — cần chốt trước khi code transform (xem phase-06 open question).
- Sheet gid/tab đổi tên → sync fail: script phải fail loud, không ghi seed rỗng đè seed cũ.
- Seed ghi từ container cần mount `transformation/seeds/` writable — verify trước.

## Câu hỏi chưa chốt

1. Finance có thực sự dùng module ngân sách trong MISA chưa? (quyết định P5 — đã DROPPED, câu hỏi đóng theo).

(Ingestion-mechanism questions, walking-skeleton findings, và infra incident notes ở `plans/archive/260707-1207-misa-gl-infrastructure/plan.md`.)
