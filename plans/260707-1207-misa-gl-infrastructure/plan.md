# MISA GL Infrastructure — Full-Ledger Ingestion + Modeling

**Status:** DONE (2026-07-03)
**Created:** 2026-07-02 (as part of `260702-1727-misa-cashflow-budget-planner`)
**Split out:** 2026-07-07 — Phases 1-2 (infra build) extracted from `plans/260702-1727-misa-cashflow-budget-planner` into their own plan for management clarity. That plan's Phases 3-10 (cashflow report + budget planner, later merged with the workable-loop close) are a *consumer* of this infra, not the infra itself.
**Owner decision locked:** Account scope = **toàn bộ sổ cái** (kéo hết chart of accounts, không chỉ 642).

## Objective

Ingest the *entire* MISA general ledger (all accounts, not just the 642-overhead subset already feeding `fact_order_costs`) and model it into reusable dim/fact tables — the foundation for cashflow reporting, budget planning, and any future P&L/balance-sheet work.

## Vấn đề / Bối cảnh

Pipeline `misa_account_ledger` đang chạy tốt nhưng **chỉ kéo account 642** (overhead) để feed `fact_order_costs`. Cần tiền (111/112) + số dư quỹ, và muốn kéo hết sổ cái làm nền cho P&L / balance sheet sau này.

Hai thiếu hụt bắt buộc lấp:
1. Downloader scoped `642` → mở rộng toàn bộ account (đòn bẩy `row-check-all` đã có).
2. Parser bỏ **số dư đầu/cuối kỳ** → cần bắt để tính số dư quỹ theo thời gian.

Ràng buộc **không được vỡ**: pipeline overhead allocation (642 → `fact_order_costs`) phải tiếp tục chạy đúng sau khi generalize.

## Phases

| # | Phase | File | Ra được gì |
|---|-------|------|-----------|
| 1 | Full-ledger ingestion + opening balance | `phase-01-full-ledger-ingestion.md` | Sổ cái toàn bộ account + số dư đầu kỳ, partition parquet, 642 vẫn chạy |
| 2 | GL modeling (dim/std/fact) | `phase-02-gl-modeling.md` | `dim_gl_account`, `std_misa_gl_ledger`, `fact_cash_movement`, `fact_account_balance_monthly` |

## Tiến độ 2026-07-03 (báo cáo LIVE, verbatim từ plan gốc)

- ✅ **Phase 01 Ingestion**: full-ledger export cơ chế OK (empty search + "Chọn tất cả tài khoản", session mới). Downloader có `--all-accounts` + `--month YYYY-MM`. Scheduled Dagster asset default đổi sang full-ledger. **Backfill Jan–Jun 2026 xong** (37–39 accounts/tháng, cash đủ). 642 lịch sử dịch nhẹ theo MISA hiện tại (user duyệt).
- ✅ **Phase 02 Models**: `dim_gl_account` (281 accounts, 14 cashflow_line), `fact_cash_movement`, `fact_account_balance_monthly` — materialized qua dbt (Dagster auto-wired; 1 lần bootstrap serving views thủ công đã chạy). 6 tháng cash data live.

**Cleanup nhỏ deferred:** `fact_account_balance_monthly` có vài dòng 2025 balance NULL (từ export 642 cũ) — thêm `WHERE opening_balance IS NOT NULL` sau.

## Phát hiện từ walking skeleton (2026-07-02, data thật tháng 6/2026)

Đã tải thử `--account 11` (So_chi_tiet_11_202606.xlsx, lưu ở `app_data/analysis/misa-cashflow/`) + probe → xác nhận:

1. **Excel có 10 cột** (parser production đọc 8, BỎ 2 cột cuối):
   `0 Ngày HT | 1 Số CT | 2 Ngày HĐ | 3 Số HĐ | 4 Diễn giải | 5 TK đối ứng | 6 Nợ | 7 Có | 8 Dư Nợ | 9 Dư Có`.
   → **Cột 8/9 = số dư CHẠY từng dòng** (running balance). Có luôn, miễn phí.
2. **"Số dư đầu kỳ" CÓ sẵn** — dòng ngay sau marker "Tài khoản:", số dư ở cột 8/9. → KHÔNG cần report "Sổ quỹ" riêng.
3. **`--account` search khớp SUBSTRING** — "11" kéo cả TK chứa "11" (33311, 51111, 8112…). → Lọc tiền phải làm ở model bằng `account LIKE '111%'/'112%'`, KHÔNG tin prefix download.
4. **Chuyển nội bộ giữa TK tiền** (offset ∈ 111/112, vd 11221↔11212 149.5M) phải **net = 0**, loại khỏi thu/chi thật.
5. **Số dư chạy (Dư Nợ) là closing chuẩn per account** — đừng recompute; recompute lệch khi loại transfer.
6. **Đối ứng (offset account) = chiều phân tích chính** cho nguồn thu/khoản chi; cần lookup tên TK để đọc được (131→Phải thu KH, 3341→Lương, 3383→BHXH, 642172→Ads).
7. Recon thật: đầu kỳ 134.2M → thu 464.4M → chi 434.0M → ròng +30.4M → cuối kỳ 164.6M (khớp).

## Tiến độ Bước A+B (2026-07-02 tối)

**Đã xong (durable):**
- ✅ **Parser enhancement** (`account-ledger-parser.py`): thêm cột 8/9 (Dư Nợ/Dư Có = số dư chạy) + `opening_balance` (từ dòng "Số dư đầu kỳ") + `debit_balance`/`credit_balance`. Additive. **642 regression PASS** (116 rows, 104,945,218, mismatches=[]).
- ✅ **Models**: `dim_gl_account.sql` (marts/core, self-populating từ ledger + seed tên + cashflow_line CASE + is_cash), `fact_cash_movement.sql` (marts/finance, line-grain cash 111/112, direction thu/chi, is_internal_transfer, running/opening balance), seed `ref_gl_accounts.csv`. **Validated end-to-end trên data thật** (DuckDB cô lập): T6/2026 thu 464.4M / chi 434.0M / ròng +30.4M; chi lương 237.9M, BHXH 96.7M, NCC 14M.
- ✅ **Downloader** `--all-accounts` flag thêm vào; source `misa_raw` đã có `union_by_name=true` → cột parser mới KHÔNG vỡ overhead pipeline (partition cũ nhận NULL).

**Đã giải quyết (từng "chặn"):**
- Full-ledger export mechanism (open question #1 dưới) — resolved 2026-07-03, xem "Tiến độ" ở trên.

**⚠️ SỰ CỐ + KHÔI PHỤC (bài học):** Dagster file-drop sensor ĐANG CHẠY — file thử `So_chi_tiet__202606.xlsx` để trong input dir bị sensor tự nuốt lúc 21:57, UPSERT-clear partition T6 → **xóa 642 tháng 6**. Đã khôi phục bằng re-ingest file 642 archived (642 debit=104,945,218 OK). **Bài học: TUYỆT ĐỐI không để file thử trong `app_data/input_source/misa-account-ledger/` — sensor tự ingest + UPSERT-by-month xóa account khác.** Xem `[[reference_misa_account_ledger_excel_format]]`.

## Acceptance criteria

- [x] Downloader kéo được toàn bộ sổ cái 1 kỳ; overhead 642 allocation **không đổi kết quả** (regression `fact_order_costs`).
- [x] Có số dư quỹ 111/112 theo tháng (đầu kỳ + phát sinh + cuối kỳ) khớp với MISA.

## Rủi ro chính

- **Vỡ overhead allocation** khi generalize asset 642 → mitigation: giữ std model 642-filtered riêng, thêm regression check `fact_order_costs` trước/sau.
- **Download nặng** khi kéo hết account (nhiều dòng) → có thể phải loop theo lớp TK hoặc phân trang; đo thử 1 kỳ trước.
- **Số dư quỹ cần điểm neo đầu kỳ**: parser bắt được "Số dư đầu kỳ" per account → đủ, không cần report "Sổ quỹ tiền mặt / Sổ tiền gửi" riêng.
- **Idempotency partition**: export toàn-account theo kỳ phải UPSERT trọn (year, month) — tránh trộn lẫn export 642 cũ với full mới.

## Câu hỏi đã chốt (giữ lại làm history)

1. **Full-ledger export cơ chế nào?** → resolved 2026-07-03: empty-search + "Chọn tất cả tài khoản" hoạt động với session mới (MISA nhớ tham số report server-side theo session cũ, không phải theo report).
2. **Chốt taxonomy "dòng thu/chi" cho `dim_gl_account.cashflow_line`** → resolved: map theo prefix tài khoản (14 cashflow_line), confirmed dùng được cho budget grain (xem `plans/260702-1727-misa-cashflow-budget-planner` — "Grain budget vận hành").

## Consumers của hạ tầng này

- `plans/260702-1727-misa-cashflow-budget-planner` Phases 3-10 (cashflow report + budget planner, gồm cả workable-loop close đã merge vào) — nguyên nhân ra đời của plan này, giờ tách riêng.
- `plans/260706-1519-balance-sheet-liquidity-ratios` — dùng `fact_account_balance_monthly` + `dim_gl_account` làm nền cho Current Ratio/Quick Ratio/DSO.
- `plans/archive/260609-1107-gl-accounting-entries` (superseded) — Phase 5 absorbed vào balance-sheet-liquidity-ratios, cũng build trên cùng hạ tầng này.
