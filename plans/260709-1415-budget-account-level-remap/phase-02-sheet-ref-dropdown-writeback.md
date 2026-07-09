# Phase 02 — `__REF` Machine-Published Dropdown

**Status:** PARTIAL — 33 account-level rows đã append thủ công (one-off script, không phải Dagster asset) vào `__REF!A12:B44` ngày 2026-07-09, additive bên dưới 10 dòng cashflow_line cũ (không đụng, 4 dòng recurring đang live vẫn hoạt động bình thường). `ref_gl_accounts.csv` đã bổ sung `3335`, `642273`. `.gs` đã thêm `validateBudgetCrossRows` (cha/con collision, theo tháng+chiều) — **cần paste thủ công vào Apps Script editor của sheet để kích hoạt** (chưa có clasp/API push, xem §Deploy). Phần còn lại của phase này (asset Dagster tự động refresh `__REF` mỗi đêm) — CHƯA làm, one-off script hiện tại đủ dùng tạm cho tới khi cần refresh lại (vd thêm account mới).
**Depends on:** Phase 01 (`dim_gl_account.parent_account_code`/`parent_account_name`) — cho việc TỰ ĐỘNG hoá; one-off lần này build list bằng script Python độc lập, không qua dbt.

## Deploy `.gs` (thủ công — bắt buộc để check cha/con hoạt động)

1. Mở Google Sheet → Extensions → Apps Script.
2. Copy toàn bộ nội dung `scripts/budget/validate-budget-sheet.gs` (đã cập nhật) → paste đè vào project Apps Script hiện tại.
3. Save → chạy `installTriggers()` 1 lần nếu trigger `onEdit` chưa có (kiểm tra menu "Budget Tools" đã xuất hiện là đủ, không cần chạy lại nếu đã cài trước đó — chỉ code bên trong đổi, trigger wiring không đổi).
4. Test nhanh: vào `BUDGET_ITEMS`, chọn cùng lúc 2 dòng recurring có account cha+con (vd `"   334  ..."` và `"  3341  ..."`) cùng 1 tháng cùng Chiều Chi, điền Budget cả 2 → phải thấy toast "⚠️ Cha/con trùng" xuất hiện khi edit ô cuối cùng.

## Context

- `__REF` tab hiện tại: **hand-maintained**, cột A = Chiều, cột B = tên `cashflow_line` (text tự do do finance/kỹ thuật gõ tay theo hướng dẫn FAQ trong `finance-budget-user-guide.md`).
- Write access tới Google Sheet **đã có sẵn**, Editor-level, credential đã hoạt động thật (không phải dry-run) — xem `plans/archive/260707-1201-google-sheets-service-account/plan.md` (DONE, commit `af41ffd9`) và `ingestion/src/gsheet_budget_sync/sheet_writeback.py` (dùng cho cột "Gợi Ý", cùng cơ chế `gsheet_auth.get_gspread_client()`).
- Quyết định chốt: mọi line có account-prefix **bắt buộc** chọn qua dropdown (data validation), không gõ tay — xem plan.md §Khó khăn #2, #3.

## Requirements

### 1. Nguồn danh sách dropdown

Query `dim_gl_account` (sau phase-01) cho mọi `account_code` **đã từng xuất hiện thật** trong `fact_cash_movement.offset_account` (không liệt kê toàn bộ COA lý thuyết — chỉ account có giao dịch thật, tránh dropdown dài vô nghĩa), loại account chưa có tên thật (fallback `"TK <code>"` — xem phase-01 blocking dependency).

Với mỗi account, sinh **2 dòng lựa chọn khi có cha thật**:
- Dòng cha (nếu `parent_account_name` không NULL): `account_code = parent_account_code`, tên = `parent_account_name` — cho phép Chế độ A (budget cả family qua 1 dòng).
- Dòng con (chính account_code đó): tên = `account_name` riêng — cho phép Chế độ B.

Cả 2 loại dòng cùng có mặt trong list; finance tự chọn cha hoặc con lúc nhập (mutual-exclusivity validate ở phase-03, không phải việc của tab `__REF`).

### 2. Format hiển thị — fixed-width prepend-space

```python
width = max(len(code) for code in all_selectable_codes)   # tính động, không hardcode
label = f"{code.rjust(width)}  {account_name}"
```
Ví dụ (width=6): `"   111  Tiền mặt"`, `"  3383  Bảo hiểm xã hội"`, `"338     Phải trả phải nộp khác"` — right-justify bằng `rjust` (space đứng trước digit trong ASCII nên sort text vẫn đúng thứ tự số, đã verify lý thuyết ở phần thảo luận trước).

### 3. Ghi tab `__REF` qua Sheets API

Mở rộng `ingestion/src/gsheet_budget_sync/sheet_writeback.py` (đã có pattern `_write_cells_via_sheets_api`, `_col_num_to_a1`) thêm hàm ghi toàn bộ cột B của `__REF` (gid có sẵn, xem `fetch.py` — `GID_REF` hoặc tương đương, kiểm tra tên biến thật trong `fetch.py` trước khi thêm). Ghi đè toàn bộ range mỗi lần chạy (không diff cell-by-cell — đơn giản hơn, list dropdown không lớn ~50-80 dòng).

**Thời điểm chạy:** cùng lịch với `budget_sheet_sync_asset` (02:30 ICT) nhưng chạy **trước** bước đọc `BUDGET_ITEMS` — nếu `__REF` chưa cập nhật thì validate ở phase-03 dùng list cũ, không sai nhưng có thể thiếu account mới. Thêm 1 bước riêng trong Dagster asset (không phải asset mới — mở rộng `budget_sheet_sync_asset` với 1 op con `refresh_ref_tab`).

### 4. Data validation (dropdown) trên cột A của `BUDGET_ITEMS`

Cấu hình 1 lần qua Google Sheets UI (không phải code) hoặc Apps Script (`scripts/budget/validate-budget-sheet.gs`) — set data validation rule cho cột A, tất cả dòng `item_type=recurring`, nguồn = range cột B của `__REF`. `item_type=one_off/reserve` giữ nguyên free-text (không set validation).

**Giới hạn kỹ thuật cần biết:** Google Sheets data validation "list from range" không tự động phân biệt Thu/Chi theo dòng — dropdown sẽ hiện cả 2 chiều trộn lẫn (finance có thể chọn account Thu vào dòng Chi). Chấp nhận rủi ro này ở Phase 02 (validate ở phase-03 sẽ bắt qua `direction`/`account_code` mismatch nếu account đó chưa từng xuất hiện ở chiều đó — không phải lỗi cú pháp nhưng vẫn có 1 lớp an toàn); không đầu tư conditional dropdown (Apps Script onEdit trigger để lọc theo Chiều) trong phase này — YAGNI, thêm nếu thực tế xảy ra nhầm lẫn.

## Files

- **Modify** `ingestion/src/gsheet_budget_sync/sheet_writeback.py` — thêm `_write_ref_accounts()`
- **Modify** `ingestion/src/gsheet_budget_sync/fetch.py` — nếu cần thêm hằng số GID/range cho `__REF` (kiểm tra đã có chưa trước khi thêm mới)
- **Modify** `orchestration/assets/sheets_assets.py` (hoặc file asset budget tương ứng — xác nhận tên file thật lúc code) — thêm bước refresh `__REF` trước bước đọc `BUDGET_ITEMS`
- **Modify** `scripts/budget/validate-budget-sheet.gs` — set/refresh data validation rule cột A theo `__REF`

## Tests / verify

- Unit: `_write_ref_accounts()` build đúng label fixed-width cho tập account_code độ dài khác nhau (3, 4, 5, 6 số) — test sort order đúng bằng cách so sánh list đã sort text vs sort numeric.
- E2E thủ công 1 lần: chạy asset, mở sheet thật, xác nhận `__REF` cột B có dòng cha + dòng con, xác nhận chọn dropdown giữ nguyên khoảng trắng đầu khi đọc lại qua CSV export (đúng lo ngại #2 trong plan.md — test thực tế, không giả định).

## Risks & rollback

- Ghi đè toàn bộ `__REF` mỗi lần chạy — nếu finance đã thêm ghi chú/format riêng vào các cột khác (C, D...) của tab đó, cần xác nhận trước là chỉ ghi cột B, không đụng cột khác.
- Rollback: `__REF` là generated output, không phải input — revert về hand-maintained bằng cách tắt bước `refresh_ref_tab` trong Dagster asset, tab vẫn giữ nguyên nội dung cuối cùng đã ghi.
