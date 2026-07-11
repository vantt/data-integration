# Phase 02 — `__REF` Machine-Published Dropdown

**Status:** DONE (code) 2026-07-11 — `gsheet_budget_sync.refresh_ref_accounts()` implemented + wired into `budget_sheet_sync_asset` (runs before the BUDGET_ITEMS read, per §3). `.gs` `validateBudgetCrossRows` còn **cần paste thủ công vào Apps Script editor để kích hoạt** (chưa có clasp/API push, xem §Deploy — không đổi từ trước, không cần sửa `.gs` đợt này vì `applyDongTienDropdown` đã đọc `__REF` sống mỗi lần edit, không có static validation rule nào để refresh).

**Lưu ý cosmetic (phát hiện qua review 2026-07-11):** `applyDongTienDropdown` trong `.gs` (dòng `.map(r => String(r[1] || '').trim())`) tự `.trim()` label trước khi build `requireValueInList` — nghĩa là phần padding fixed-width (khoảng trắng đầu) đã bị cắt TRƯỚC KHI người dùng chọn, không phải do Sheets tự trim sau khi chọn. Không ảnh hưởng logic (parse `_ACCOUNT_PREFIX_RE` chấp nhận thiếu khoảng trắng đầu, seed chỉ lưu `account_code` đã parse chứ không lưu label thô) — nhưng có nghĩa mục tiêu "giữ căn lề + sort đúng thứ tự số" của padding không thực sự giữ được ở giá trị cuối cùng trong ô `BUDGET_ITEMS!A`. Cosmetic-only, không đáng sửa `.gs` chỉ vì việc này.

**Quyết định migration (2026-07-11):** Full overwrite — mỗi lần chạy, `refresh_ref_accounts()` XOÁ TOÀN BỘ nội dung cột A:B hiện có (kể cả 10 dòng cashflow_line cũ hand-maintained) và ghi lại từ `dim_gl_account`/`fact_cash_movement`. Hệ quả chấp nhận: bất kỳ dòng recurring nào trong `BUDGET_ITEMS` còn dùng cashflow_line dạng cũ (chưa chuyển sang dropdown account-code) sẽ FAIL validate ở lần sync kế tiếp — phải remap sang account-code trước khi asset này chạy live lần đầu trong Dagster. Không tự động migrate các dòng đó — ngoài phạm vi phase này.
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

- **Done** `ingestion/src/gsheet_budget_sync/duckdb_actuals.py` — `_fetch_ref_accounts_from_duckdb()` (offset_account × direction từ `fact_cash_movement`, join `dim_gl_account`, loại internal-transfer + fallback-name accounts)
- **Done** `ingestion/src/gsheet_budget_sync/ref_accounts.py` (mới) — `build_ref_rows()`, pure targeting logic (child + parent rows, dedupe, fixed-width padding)
- **Done** `ingestion/src/gsheet_budget_sync/sheet_writeback.py` — `_write_ref_accounts()` (full overwrite cột A:B, clear trước khi ghi để tránh sót dòng cũ)
- **Done** `ingestion/src/gsheet_budget_sync/__init__.py` — `refresh_ref_accounts()` orchestration (dry_run mặc định True) + CLI flag `--refresh-ref`
- **Done** `orchestration/assets/sheets_assets.py` — `budget_sheet_sync_asset` gọi `refresh_ref_accounts(dry_run=False)` trước `gsheet_budget_sync.run()`
- **Không đổi** `scripts/budget/validate-budget-sheet.gs` — `applyDongTienDropdown` đã đọc `__REF` live mỗi lần edit (không cache), không có static validation rule nào cần refresh riêng

## Tests / verify

- **Done** Unit (`ingestion/tests/test_gsheet_budget_sync.py`): `build_ref_rows` — child+parent rows cùng width, dedupe parent dùng chung bởi nhiều con, account không cha, input rỗng, cùng account_code xuất hiện cả 2 chiều (không collision), account cha vừa là chính nó vừa là cha của account khác (dedupe đúng 1 dòng); `refresh_ref_accounts` dry-run không gọi Sheets API, non-dry-run gọi `_write_ref_accounts` đúng rows; `_write_ref_accounts` credential guard (thiếu env var → RuntimeError). 61/61 `pytest ingestion/tests` pass (2026-07-11, sau khi áp dụng fix từ code-reviewer độc lập — xem ghi chú dưới).
- **Sửa theo code review độc lập 2026-07-11:** `_write_ref_accounts` đổi thứ tự write-trước/clear-sau (thay vì clear-trước/write-sau) — tránh trường hợp `update()` fail giữa chừng để lại `__REF` HOÀN TOÀN RỖNG (dropdown + `.gs` cha/con validation cùng mất hết option) cho tới lần chạy thành công kế tiếp; giờ fail giữa chừng chỉ để lại state stale (còn tốt hơn rỗng).
- **Done — E2E thật, 2026-07-11** (chạy trong container `data_platform`, sheet + DuckDB thật):
  - Dry-run trước: 35 dòng tính đúng từ `dim_gl_account`/`fact_cash_movement` thật (cả dòng cha lẫn dòng con, cả 2 chiều Thu/Chi cho account xuất hiện cả 2 chiều — vd `131`, `331`, `333`, `5111`, `33311`, `51111`).
  - **Xác nhận không còn dòng cashflow_line cũ nào trong `__REF` HAY trong `BUDGET_ITEMS`** trước khi ghi thật — kiểm tra trực tiếp: `__REF` hiện tại (trước khi ghi) đã 100% là account-code label (79 dòng, không dòng nào plain-text); toàn bộ 34 dòng recurring active trong `BUDGET_ITEMS` cũng đã 100% dùng account-code label. Rủi ro "vỡ 4 dòng legacy" nêu ở quyết định migration ban đầu **hoá ra không còn áp dụng** — hệ thống đã tự migrate hết từ trước, ghi chú cũ trong plan/phase-02 (dòng cũ, giờ đã xoá) bị stale.
  - Ghi thật: `refresh_ref_accounts(dry_run=False)` → 35 dòng, verify lại qua `get_all_values()`: đúng 35 dòng non-empty, không sót dòng cũ (confirm write-then-clear-trailing hoạt động đúng).
  - **Verify lo ngại #2 (plan.md):** đọc lại 1 label mẫu qua Sheets API sau khi ghi — khoảng trắng đầu (`"   131  Phải thu khách hàng"`) giữ nguyên nguyên vẹn qua round-trip ghi/đọc thật (không bị Sheets tự trim).
- **Phát hiện mới, NGOÀI phạm vi phase-02 (2026-07-11):** chạy thử `validate_and_build_budget_rows` với `BUDGET_ITEMS` + `dim_gl_account` thật → **15 lỗi validate** — 8 dòng recurring dùng account_code cấp cha KHÔNG BAO GIỜ được post trực tiếp trong sổ cái (`112`, `334`, `641`, `642`, `1121`) nên không tồn tại trong `dim_gl_account` (model chỉ nhận code đã từng post thật hoặc là nearest-ancestor thật của 1 code đã post — xem `dim_gl_account.sql`). Vì `fetch_transform_and_save` abort TOÀN BỘ sync khi có bất kỳ lỗi nào (không partial-write), **nightly `budget_sheet_sync_asset` (02:30 ICT) nhiều khả năng đã fail liên tục** kể từ khi finance nhập các dòng này — `seed_cashflow_budget.csv` có thể đang stale. Root cause: script one-off cũ (populate `__REF` trước khi có `refresh_ref_accounts`) đã từng cho phép chọn các code cấp cha rộng hơn rule chính thức (chỉ code thật-sự-được-post) — finance chọn theo dropdown cũ đó, hợp lý tại thời điểm chọn nhưng không khớp thiết kế Phase 1. **Không tự sửa 8 dòng này trong phiên làm việc này** — cần finance/kỹ thuật remap sang code con thật (`641`→`6421` hoặc con cụ thể, `334`→`3341`/`3348`, `112`→`1121`/`11212`, `642`→`6422` hoặc con cụ thể, `1121`→`11212`/`11219`) — xem plan.md để mở thành 1 theo dõi riêng nếu cần.

## Risks & rollback

- Ghi đè toàn bộ `__REF` mỗi lần chạy — nếu finance đã thêm ghi chú/format riêng vào các cột khác (C, D...) của tab đó, cần xác nhận trước là chỉ ghi cột B, không đụng cột khác.
- Rollback: `__REF` là generated output, không phải input — revert về hand-maintained bằng cách tắt bước `refresh_ref_tab` trong Dagster asset, tab vẫn giữ nguyên nội dung cuối cùng đã ghi.
