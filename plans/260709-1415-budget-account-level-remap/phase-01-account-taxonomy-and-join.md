# Phase 01 — Account Taxonomy + BvA Join Redesign

**Status:** NOT STARTED
**Blocking dependency:** đã thu hẹp qua tra `description` trong sổ cái thật (xem §1) — chỉ còn 1 câu cần hỏi kế toán (quan hệ "FGO"), không còn block toàn phase.

## Context

- `transformation/models/marts/core/dim_gl_account.sql` — grain 1 row/account_code, tự động phát hiện từ `src_misa_account_ledger` (posting + counterpart), enrich tên từ `ref_gl_accounts.csv` (fallback `"TK " || code` khi thiếu).
- `transformation/seeds/ref_gl_accounts.csv` — 49 accounts có tên, chuẩn TT200 (3-6 chữ số).
- `transformation/models/marts/finance/mart_cashflow_budget_vs_actual.sql` — hiện join `budget.cashflow_line = actual.cashflow_line` (exact text), grain `(cashflow_line, period_month, direction)`.
- `transformation/models/marts/finance/fact_cash_movement.sql` — actual grain, có `offset_account` (= account_code cần match), `direction`, `period_month`, `is_internal_transfer`.
- Query thật (2026-01 → 07, xem plan.md §Khó khăn #6) xác nhận: 334/338-family không bao giờ post ở cấp cha (chỉ con); 331 post phẳng (không con); 131 chiếm 99% THU.

## Requirements

### 1. `ref_gl_accounts.csv` — bổ sung tên thiếu

Đã tra `description` (Diễn giải) của các giao dịch thật trong `fact_cash_movement` (2026-01→07) cho từng account thiếu tên — suy ra được tên/ý nghĩa cho hầu hết, không cần hỏi kế toán mù (query: filter `offset_account = <code>`, đọc mẫu description). Còn lại 1 điểm thật sự cần business context (quan hệ FGO), không phải tên account.

| account_code | Description mẫu (thật) | Tên đề xuất | Độ tin cậy | Hành động |
|---|---|---|---|---|
| `3335` | "Nộp thuế TNCN Q4/2025", "...Q1/2026" | **Thuế thu nhập cá nhân** | Cao — mã chuẩn TT200 | Điền thẳng vào `ref_gl_accounts.csv`, không cần hỏi |
| `642273` | "Phí tạp vụ tháng 12.2025/01.2026/..." lặp đều mỗi tháng | **Chi phí tạp vụ/vệ sinh** | Cao — recurring rõ, cùng người/cùng mô tả 6 tháng liền | Điền thẳng — ưu tiên đưa vào dropdown vì thực sự recurring |
| `642286` | "Chi phí ăn uống hóa đơn..." | Chi phí tiếp khách/ăn uống | Trung bình — 1 mẫu | Điền, nhưng có thể không đáng tách dòng riêng (4.5M, 1 lần) — để orphan report bắt cũng được |
| `642288` | "Thanh toán tiền mở tài khoản AI" | Chi phí dịch vụ phần mềm | Thấp — 1 lần, không chắc recurring | Confirm nhanh với kế toán trước khi đặt tên chính thức, hoặc bỏ qua (553K, để orphan) |
| `642278` | "Chi lệ phí gia hạn định danh FG Care" | Lệ phí đăng ký/gia hạn | Thấp — 1 lần, 100K | Bỏ qua, để orphan report bắt (quá nhỏ, không đáng dropdown) |
| `33682` | "FGO trả tiền thu hộ đơn hàng khách chuyển nhầm" | Liên quan related-party "FGO" | — | **Cần hỏi kế toán: FGO là quan hệ gì** (công ty liên kết? chi nhánh?) — ảnh hưởng tên chính thức |

Đã **không còn là anomaly** (description xác nhận rõ, chỉ còn quyết định scope):

| account_code | Tên hiện có | Description mẫu | Kết luận |
|---|---|---|---|
| `13681` | Phải thu nội bộ khác (đã đúng) | "Trả tiền FGO hóa đơn 33 34 và 294" × 3 lần rải rác Feb/Mar/Jun, tổng 109.7M | Thanh toán định kỳ-ish cho related-party FGO — tên KHÔNG cần đổi, chỉ cần quyết: có đưa vào dropdown CHI THƯỜNG XUYÊN hay để ngoài scope (phụ thuộc câu trả lời FGO ở trên) |
| `6351` | (không có tên chính thức) | "Xử lý chênh lệch tỷ giá" × nhiều lần, mỗi lần <300K | Bút toán chênh lệch tỷ giá tự động (không phải chi tiêu vận hành thật) — **khuyến nghị loại khỏi dropdown budget hoàn toàn**, không map, không tốn công đặt tên |

**Chỉ cần hỏi kế toán 1 câu thật sự** (không phải 8 câu như đánh giá ban đầu): FGO là quan hệ gì, có nên gộp `33682`+`13681` thành 1 dòng budget "Thanh toán FGO" hay để riêng/bỏ qua. Các account còn lại điền thẳng theo bảng trên, không block phase.

### 2. `dim_gl_account.sql` — thêm cột hỗ trợ hiển thị "tên cha thật"

Thêm cột `parent_account_code`/`parent_account_name` — **KHÔNG dùng fixed 3-digit truncation** (đã chứng minh sai bằng data thật, xem cảnh báo dưới). Phải dùng thuật toán "nearest named ancestor": dò các tiền tố ngắn dần (`code[:-1], code[:-2], ...`, dừng ở độ dài 3), trả về tiền tố DÀI NHẤT có tên thật trong `ref_gl_accounts`.

> **Bug đã bắt được lúc build thử danh sách thật (2026-07-09):** `642172` (Chi phí bán hàng) và `642273`/`642282` (Chi phí quản lý DN) đều bắt đầu bằng `642`, nhưng thuộc 2 account cha KHÁC NHAU — `6421` và `6422` — vì digit thứ 4 mới là điểm rẽ nhánh thật (`6421xx` vs `6422xx`), không phải cắt cứng 3 số. `LEFT(code, 3)` sẽ gộp nhầm cả 2 nhóm chi phí khác bản chất vào chung 1 "cha" ảo `"642"`. DuckDB không có recursive string-prefix lookup built-in gọn — implement bằng 1 loạt `LEFT(code, N)` thử từ dài xuống ngắn (N từ `LENGTH(code)-1` xuống 3), `COALESCE` lấy match đầu tiên có tên trong `ref_gl_accounts`, hoặc join qua 1 CTE liệt kê tất cả `(code, candidate_prefix)` rồi `QUALIFY ROW_NUMBER() OVER (PARTITION BY code ORDER BY LENGTH(candidate_prefix) DESC) = 1`. Script Python tham khảo (đã chạy thử, cho kết quả đúng) — xem `nearest_named_ancestor()` trong lịch sử phiên làm việc, cùng logic áp vào SQL.

```sql
-- Ý tưởng SQL (CTE, không phải LEFT(code,3) cố định):
WITH prefixed AS (
    SELECT a.account_code, n2.account_code AS candidate, n2.account_name
    FROM distinct_accounts a
    JOIN ref_gl_accounts n2
      ON n2.account_code != a.account_code
     AND a.account_code LIKE n2.account_code || '%'
     AND LENGTH(n2.account_code) >= 3
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY account_code ORDER BY LENGTH(candidate) DESC) AS rn
    FROM prefixed
)
SELECT account_code, candidate AS parent_account_code, account_name AS parent_account_name
FROM ranked WHERE rn = 1
```

Giữ nguyên `cashflow_line` CASE hiện tại — vẫn cần cho: (a) dòng `one_off`/`reserve` (pseudo cashflow_line = item_label, không đụng dim_gl_account), (b) các bucket gộp nhiều cha thật (vd "Doanh thu & thu nhập" = 511+515+71) không có 1 account cha đại diện.

### 3. `mart_cashflow_budget_vs_actual.sql` — đổi grain + join

**Đổi grain:** `(cashflow_line, period_month, direction)` → `(account_code, period_month, direction)`.

**Đổi join actual↔budget:** từ exact-equality `a.cashflow_line = b.cashflow_line` sang prefix-match:
```sql
ON  b.account_code IS NOT NULL
AND (a.account_code = b.account_code OR a.account_code LIKE b.account_code || '%')
AND a.period_month = b.period_month
AND a.direction = b.direction
```
- `budget.account_code` NULL (item_type=one_off/reserve) → không join theo cơ chế này, giữ nguyên logic cũ (planned-only, không match MISA).
- `cashflow_line` giữ lại trong mart làm **cột hiển thị derived** (không phải join key nữa) — join `dim_gl_account.cashflow_line` theo `account_code` để dashboard filter "Cashflow Line" hiện có (xem `finance_cashflow.md` design spec) không vỡ.

**Rủi ro cụ thể cần test:** `a.account_code LIKE b.account_code || '%'` chỉ đúng khi `budget.account_code` luôn là prefix hợp lệ (validate ở phase-03, không phải việc của mart này) — mart tự nó KHÔNG validate, chỉ join; double-count nếu upstream cho lọt cha+con cùng lúc (đó là lý do phase-03 phải reject trước khi seed tới đây).

### 4. Seed schema — `seed_cashflow_budget.csv` thêm cột `account_code`

Thêm cột `account_code` (nullable) vào `SEED_BUDGET_COLUMNS` trong `ingestion/src/gsheet_budget_sync/budget_transform.py`. Populate:
- `item_type=recurring`: bắt buộc có (parse từ cột A đã chọn qua dropdown — xem phase-03 cho cơ chế parse).
- `item_type=one_off|reserve`: để trống, không đổi behavior hiện tại.

`cashflow_line` column giữ nguyên trong seed cho tương thích ngược (dashboard cũ đọc trực tiếp), nhưng với `recurring` giờ **derive** từ `account_code` (lookup `dim_gl_account`) thay vì finance tự chọn — sync script tự điền, không phải input của finance nữa.

## Files

- **Modify** `transformation/seeds/ref_gl_accounts.csv` — thêm tên (sau khi có xác nhận kế toán)
- **Modify** `transformation/models/marts/core/dim_gl_account.sql` — thêm `parent_account_code`/`parent_account_name`
- **Modify** `transformation/models/marts/finance/mart_cashflow_budget_vs_actual.sql` — đổi grain + join
- **Modify** `ingestion/src/gsheet_budget_sync/budget_transform.py` — thêm `account_code` vào `SEED_BUDGET_COLUMNS`
- **Modify** `transformation/seeds/seed_cashflow_budget.csv` — không sửa tay, seed sẽ ghi lại qua sync (phase-03); chỉ cần đảm bảo header mới tương thích merge lịch sử (`merge.py` dùng `SEED_BUDGET_COLUMNS` — tự động theo)

## Tests / verify

- `dbt test` hiện có cho `dim_gl_account`/`fact_cash_movement` phải xanh sau khi thêm cột (không phải rename, chỉ additive).
- Query thủ công: budget 1 dòng account_code=`338` (cha) → actual `3383`+`33881` roll-up đúng tổng.
- Query thủ công: budget dòng `3341`+`3348` (2 con của 334) → actual mỗi con match đúng dòng của nó, không lẫn.
- `dashboard 114` (Metabase, filter "Cashflow Line") vẫn hoạt động — verify derived `cashflow_line` column không NULL cho các dòng recurring hiện có.

## Risks & rollback

- Đổi grain mart là **breaking change** cho bất kỳ card Metabase nào query trực tiếp `mart_cashflow_budget_vs_actual` theo `cashflow_line` làm PK — audit trước (grep blueprint `docs/analytics-handbook/blueprints/metabase/finance_cashflow.md`) xem card nào cần sửa SQL card.
- Rollback: revert 3 file SQL + seed column addition qua git; seed cũ (`cashflow_line`-only) vẫn đọc được nếu revert cả `budget_transform.py`.
