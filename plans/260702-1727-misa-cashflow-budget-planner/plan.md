# MISA Cashflow Report + Budget Planner

**Status:** DRAFT — awaiting approval to implement
**Created:** 2026-07-02
**Branch (proposed):** `feature/misa-cashflow-budget`
**Owner decisions locked:**
- Budget source = **Hybrid** (actual từ MISA ledger; budget khởi đầu bằng CSV của ta, thiết kế để sau này đọc từ MISA)
- Cashflow scope = **Vận hành** (thu/chi + số dư quỹ), KHÔNG phải BC lưu chuyển tiền tệ TT200 3 mục
- Account scope = **Toàn bộ sổ cái** (kéo hết chart of accounts, không chỉ 642)

## Vấn đề / Bối cảnh

Pipeline `misa_account_ledger` đang chạy tốt nhưng **chỉ kéo account 642** (overhead) để feed `fact_order_costs`. Cashflow cần tiền (111/112) + số dư quỹ, và ta muốn kéo hết sổ cái làm nền cho P&L / balance sheet sau này.

Hai thiếu hụt bắt buộc lấp:
1. Downloader scoped `642` → mở rộng toàn bộ account (đòn bẩy `row-check-all` đã có).
2. Parser bỏ **số dư đầu/cuối kỳ** → cần bắt để tính số dư quỹ theo thời gian.

Ràng buộc **không được vỡ**: pipeline overhead allocation (642 → `fact_order_costs`) phải tiếp tục chạy đúng sau khi generalize.

## Phases

| # | Phase | File | Phụ thuộc | Ra được gì |
|---|-------|------|-----------|-----------|
| 1 | Full-ledger ingestion + opening balance | `phase-01-full-ledger-ingestion.md` | — | Sổ cái toàn bộ account + số dư đầu kỳ, partition parquet, 642 vẫn chạy |
| 2 | GL modeling (dim/std/fact) | `phase-02-gl-modeling.md` | P1 | `dim_gl_account`, `std_misa_gl_ledger`, `fact_cash_movement`, `fact_account_balance_monthly` |
| 3 | Cashflow report (Metabase) | `phase-03-cashflow-report.md` | P2 | Dashboard vận hành: số dư quỹ, thu/chi theo kỳ, top đối ứng, dòng tiền ròng |
| 4 | Budget layer hybrid + Budget-vs-Actual | `phase-04-budget-hybrid.md` | P3 | `fact_cashflow_budget` (source-swappable), report kế hoạch vs thực tế + dự báo số dư |
| 5 | (Deferred) MISA budget scraper | `phase-05-misa-budget-scraper.md` | P4 | Đọc ngân sách/dự báo MISA → `budget_source='misa'` |

## Tiến độ 2026-07-03 — Phase 01→03 DONE (báo cáo LIVE)

- ✅ **Phase 01 Ingestion**: full-ledger export cơ chế OK (empty search + "Chọn tất cả tài khoản", session mới). Downloader có `--all-accounts` + `--month YYYY-MM`. Scheduled Dagster asset default đổi sang full-ledger. **Backfill Jan–Jun 2026 xong** (37–39 accounts/tháng, cash đủ). 642 lịch sử dịch nhẹ theo MISA hiện tại (user duyệt).
- ✅ **Phase 02 Models**: `dim_gl_account` (281 accounts, 14 cashflow_line), `fact_cash_movement`, `fact_account_balance_monthly` — materialized qua dbt (Dagster auto-wired; 1 lần bootstrap serving views thủ công đã chạy). 6 tháng cash data live.
- ✅ **Phase 03 Report**: dashboard Metabase "Finance Cashflow" (ID 113) deployed từ blueprint. waterfall+pivot native v0.60.2. June recon khớp tuyệt đối (thu 464.4M/chi 434.0M/ròng +30.4M).
- ⏭️ **Phase 04 Budget**: chưa làm — seed_cashflow_budget + fact_cashflow_budget + Budget-vs-Actual + forecast, chồng lên cùng dashboard.

**Insight thật (6 tháng):** dòng tiền âm 3/6 tháng (Jan −100M, Feb −70M, May −23M); dương Mar +85M, Jun +30M; số dư quỹ 72M–165M.

**Cleanup nhỏ deferred:** `fact_account_balance_monthly` có vài dòng 2025 balance NULL (từ export 642 cũ) — thêm `WHERE opening_balance IS NOT NULL` sau. Blueprint dùng header `## Segmentation Scope` (cũ) → warning non-blocking, đổi `## Semantic Contract` sau.

## Tài liệu thiết kế báo cáo (analytics-handbook — nguồn sự thật cho WHAT)

Thiết kế báo cáo dòng tiền KHÔNG nằm trong phase file — sống ở 4 tài liệu handbook chuẩn (tạo 2026-07-02). Phase-03/04 chỉ điều phối thực thi + trỏ vào đây:

- **Domain**: `docs/analytics-handbook/domains/finance.md` § Cashflow (metrics CF1-CF4, dimensions, recon)
- **Playbook**: `docs/analytics-handbook/playbooks/finance_cashflow.md` (audience, câu hỏi, action triggers)
- **Design spec**: `docs/analytics-handbook/designs/finance_cashflow.md` (viz: scorecard·waterfall·pivot·line+forecast·combo·hbar)
- **Blueprint**: `docs/analytics-handbook/blueprints/metabase/finance_cashflow.md` (deployable SQL+viz JSON+layout)

Phase-04 (budget) mở rộng CÙNG dashboard: thêm cột Kế hoạch|Chênh lệch vào pivot + đường forecast (đã đánh dấu "Phase-04 extensions" trong blueprint).

## Acceptance criteria (toàn dự án)

- [ ] Downloader kéo được toàn bộ sổ cái 1 kỳ; overhead 642 allocation **không đổi kết quả** (regression `fact_order_costs`).
- [ ] Có số dư quỹ 111/112 theo tháng (đầu kỳ + phát sinh + cuối kỳ) khớp với MISA.
- [ ] Dashboard cashflow vận hành live trên Metabase, số liệu recon với MISA sổ quỹ.
- [ ] Budget nhập qua CSV, `fact_cashflow_budget` có cột `budget_source` để swap sang MISA không đổi schema report.
- [ ] Report Budget-vs-Actual: variance + dự báo số dư quỹ cuối kỳ.

## Rủi ro chính

- **Vỡ overhead allocation** khi generalize asset 642 → mitigation: giữ std model 642-filtered riêng, thêm regression check `fact_order_costs` trước/sau.
- **Download nặng** khi kéo hết account (nhiều dòng) → có thể phải loop theo lớp TK hoặc phân trang; đo thử 1 kỳ trước.
- **Số dư quỹ cần điểm neo đầu kỳ**: nếu parser bắt được "Số dư đầu kỳ" per account thì đủ; nếu không, cân nhắc kéo thêm report "Sổ quỹ tiền mặt / Sổ tiền gửi" (có running balance sẵn) cho riêng 111/112.
- **Idempotency partition**: export toàn-account theo kỳ phải UPSERT trọn (year, month) — tránh trộn lẫn export 642 cũ với full mới (đổi partition key hoặc versioning).

## Phát hiện từ walking skeleton (2026-07-02, data thật tháng 6/2026)

Đã tải thử `--account 11` (So_chi_tiet_11_202606.xlsx, lưu ở `app_data/analysis/misa-cashflow/`) + probe → xác nhận:

1. **Excel có 10 cột** (parser production đọc 8, BỎ 2 cột cuối):
   `0 Ngày HT | 1 Số CT | 2 Ngày HĐ | 3 Số HĐ | 4 Diễn giải | 5 TK đối ứng | 6 Nợ | 7 Có | 8 Dư Nợ | 9 Dư Có`.
   → **Cột 8/9 = số dư CHẠY từng dòng** (running balance). Có luôn, miễn phí.
2. **"Số dư đầu kỳ" CÓ sẵn** — dòng ngay sau marker "Tài khoản:", số dư ở cột 8/9. → KHÔNG cần report "Sổ quỹ" riêng (open-q #2 RESOLVED).
3. **`--account` search khớp SUBSTRING** — "11" kéo cả TK chứa "11" (33311, 51111, 8112…). → Lọc tiền phải làm ở model bằng `account LIKE '111%'/'112%'`, KHÔNG tin prefix download.
4. **Chuyển nội bộ giữa TK tiền** (offset ∈ 111/112, vd 11221↔11212 149.5M) phải **net = 0**, loại khỏi thu/chi thật.
5. **Số dư chạy (Dư Nợ) là closing chuẩn per account** — đừng recompute; recompute lệch khi loại transfer.
6. **Đối ứng (offset account) = chiều phân tích chính** cho nguồn thu/khoản chi; cần lookup tên TK để đọc được (131→Phải thu KH, 3341→Lương, 3383→BHXH, 642172→Ads).
7. Recon thật: đầu kỳ 134.2M → thu 464.4M → chi 434.0M → ròng +30.4M → cuối kỳ 164.6M (khớp).

**Grain budget vận hành (open-q #4 RESOLVED):** budget theo **dòng thu/chi = nhóm tài khoản đối ứng**, không theo TK tiền. Ví dụ line: `Thu bán hàng (131)`, `Chi lương (334x)`, `Chi BHXH (338x)`, `Chi NCC (331x)`, `Chi ads (642172)`. Đây là grain finance nhập budget dễ hiểu + join được actual từ `fact_cash_movement`.

## Tiến độ Bước A+B (2026-07-02 tối)

**Đã xong (durable):**
- ✅ **Parser enhancement** (`account-ledger-parser.py`): thêm cột 8/9 (Dư Nợ/Dư Có = số dư chạy) + `opening_balance` (từ dòng "Số dư đầu kỳ") + `debit_balance`/`credit_balance`. Additive. **642 regression PASS** (116 rows, 104,945,218, mismatches=[]).
- ✅ **Models**: `dim_gl_account.sql` (marts/core, self-populating từ ledger + seed tên + cashflow_line CASE + is_cash), `fact_cash_movement.sql` (marts/finance, line-grain cash 111/112, direction thu/chi, is_internal_transfer, running/opening balance), seed `ref_gl_accounts.csv`. **Validated end-to-end trên data thật** (DuckDB cô lập): T6/2026 thu 464.4M / chi 434.0M / ròng +30.4M; chi lương 237.9M, BHXH 96.7M, NCC 14M.
- ✅ **Downloader** `--all-accounts` flag thêm vào; source `misa_raw` đã có `union_by_name=true` → cột parser mới KHÔNG vỡ overhead pipeline (partition cũ nhận NULL).

**Chưa xong / chặn:**
- ❌ **Full-ledger export KHÔNG hoạt động**: empty-search + "Chọn tất cả tài khoản" trả về đúng bộ account của lần chạy trước (MISA nhớ tham số report server-side), KHÔNG phải toàn sổ cái. → cần **debug account-picker ở chế độ headed**. open-q #1 vẫn mở.
- ❌ **Chưa ingest được cash vào production** an toàn (phụ thuộc full-ledger export). Report Metabase/Evidence chờ bước này.

**⚠️ SỰ CỐ + KHÔI PHỤC (bài học):** Dagster file-drop sensor ĐANG CHẠY — file thử `So_chi_tiet__202606.xlsx` để trong input dir bị sensor tự nuốt lúc 21:57, UPSERT-clear partition T6 → **xóa 642 tháng 6**. Đã khôi phục bằng re-ingest file 642 archived (642 debit=104,945,218 OK). **Bài học: TUYỆT ĐỐI không để file thử trong `app_data/input_source/misa-account-ledger/` — sensor tự ingest + UPSERT-by-month xóa account khác.** Xem [[reference_misa_account_ledger_excel_format]].

## Câu hỏi chưa chốt

1. **Full-ledger export cơ chế nào?** empty-search fail. Options: (a) headed-debug account picker để clear selection + chọn tất; (b) đổi idempotency key sang (account-prefix, month) để ingest từng nhóm không xóa nhau; (c) bảng `cash_ledger` riêng cho 111/112. → cần quyết định trước khi ingest production.
2. Finance có thực sự dùng module ngân sách trong MISA chưa? (quyết định P5).
3. Chốt taxonomy "dòng thu/chi" cho budget (hiện `dim_gl_account.cashflow_line` map theo prefix — cần finance xác nhận).
