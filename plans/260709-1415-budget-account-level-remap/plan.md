# Budget Sheet — Account-Level Mapping cho Recurring Lines

**Status:** Phase 1, 2, 3, 4 DONE — Phase 2 hoàn thành + E2E verify thật 2026-07-11 (`refresh_ref_accounts()` chạy thật trong container `data_platform` với sheet + DuckDB thật, ghi 35 dòng `__REF`, xem phase-02 §Tests/verify để biết chi tiết). Migration quyết định 2026-07-11 (full-overwrite `__REF`) hoá ra KHÔNG có hệ quả gì — kiểm tra thật cho thấy không còn dòng cashflow_line cũ nào tồn tại (đã tự migrate hết trước đó). `.gs` `validateBudgetCrossRows` vẫn cần paste thủ công vào Apps Script editor (chưa tự động hoá deploy .gs) — không đổi từ trước.

**⚠️ Phát hiện mới ngoài phạm vi plan này (2026-07-11):** nightly `budget_sheet_sync_asset` nhiều khả năng đang FAIL liên tục — 15 lỗi validate trên `BUDGET_ITEMS` thật (8 dòng recurring dùng account_code cấp cha `112`/`334`/`641`/`642`/`1121` không tồn tại trong `dim_gl_account` vì chưa từng được post trực tiếp). Xem phase-02 §Tests/verify để biết chi tiết + hướng remap đề xuất. Cần theo dõi riêng, không tự sửa trong phiên này.

Xem thêm §Addendum cuối file (cột Ghi chú + đảo thứ tự tháng, thêm sau khi phase 1-3 xong) và §Cập nhật trạng thái 2026-07-10 cuối file.
**Bối cảnh:** Thảo luận thiết kế 2026-07-09 (không có report riêng — nội dung đầy đủ nằm trong các phase file). Mở rộng `plans/archive/260702-1727-misa-cashflow-budget-planner` (đặc biệt phase-06) sau khi phát hiện `cashflow_line` (bucket ~20 giá trị tự chế trong `dim_gl_account.sql`) quá thô để finance track chi tiết — xem `docs/analytics-handbook/domains/finance.md` dòng "cashflow_line ... provisional — needs finance sign-off", tài liệu này chính là sign-off đó.

## Mục tiêu

`BUDGET_ITEMS.Dòng Tiền` (cột A) cho item_type=`recurring` chuyển từ chọn `cashflow_line` (bucket tự chế) sang chọn **account_code MISA thật** (cha hoặc con, tuỳ finance) — hiển thị dạng `"<code padded><tên account>"` trong dropdown, join actual theo prefix-match thay vì exact-equality text.

## Quyết định đã chốt (tổng hợp từ thảo luận)

| # | Quyết định |
|---|---|
| 1 | THU: `recurring` bắt buộc map account; `one_off` free-form giống Chi (symmetric — sửa lại phát biểu sai lúc thảo luận rằng "THU luôn strict") |
| 2 | CHI THƯỜNG XUYÊN (`recurring`): bắt buộc map account_code, cha hoặc con |
| 3 | CHI ĐẶC BIỆT/DỰ PHÒNG (`one_off`/`reserve`): free-form, không map account — không đổi so với rule 2026-07-05 |
| 4 | Naming: dùng tên account cha **thật** (từ `ref_gl_accounts`) khi hiển thị/gộp, không tự chế label mới |
| 5 | Multi-account 1 family: luôn tách dòng, 1 account_code/dòng — không nhét nhiều code vào 1 cell |
| 6 | Hiển thị: `<account_code fixed-width, prepend space><space><account_name>` — CHỈ qua dropdown (data validation từ `__REF`), không cho gõ tay |
| 7 | Join actual↔budget: prefix-match (`actual.account_code LIKE budget.account_code \|\| '%'`), không exact-equality — để cha tự roll-up con |
| 8 | Cha + con cùng family **không được cùng tồn tại** trong cùng (period_month, direction) — pipeline reject cứng + Lark notify; sheet cảnh báo chi tiết ngay khi phát hiện |
| 9 | Actual không khớp budget nào (orphan) → hiển thị **riêng** trong report, không âm thầm mất, không tự động gộp vào biến động của dòng khác |
| 10 | Hỗ trợ 2 chế độ: A = 1 dòng cha (rollup mọi con), B = nhiều dòng con (con nào thiếu → rơi vào orphan report). **Không** hỗ trợ chế độ lai (cha + 1 vài con chọn lọc cùng lúc) — orphan report đã thay thế nhu cầu đó, tránh residual-join phức tạp |
| 11 | Notification channel: Lark bot, tái dùng `orchestration/notifications/lark_client.send_lark_card` (đã có sẵn, dùng cho failure alerting khác) |

## Khó khăn tiềm ẩn & cách khắc phục (trọng tâm — đọc trước khi implement)

Đây là các vấn đề **không hiển nhiên** phát hiện trong lúc thiết kế, không phải rủi ro chung chung:

1. **Orphan-actual report xung đột với rule "reserve chi ra rơi vào account nào cũng đúng"** (2026-07-05). Cùng 1 sự kiện (mua SSD từ quỹ để dành) vừa "đúng kế hoạch" (rule cũ) vừa "chưa được cover" (rule mới orphan). **Khắc phục:** không tự động phân biệt 2 case — orphan report là 1 checklist người xem hàng tháng, tự phân loại bằng mắt. Rủi ro noise thấp vì reserve-spend là giao dịch 1 lần, orphan chỉ nổi đúng 1 tháng rồi hết (không lặp lại như 1 account recurring thật sự bị thiếu). Xem phase-04.
2. **Google Sheets có thể tự trim khoảng trắng đầu dòng khi gõ tay** — phá vỡ toàn bộ kỹ thuật fixed-width padding. **Khắc phục:** cấm gõ tay hoàn toàn cho line có account-prefix — bắt buộc chọn từ dropdown (`data validation` nguồn `__REF`); giá trị dropdown được Sheets copy nguyên văn, không qua bàn phím nên không bị auto-trim. Xem phase-02.
3. **Gõ nhầm mã hợp lệ nhưng sai cấp** (vd gõ `338` thay vì định gõ `3383` — cả 2 đều "tồn tại thật", validate exists-in-ref-gl-accounts không bắt được). **Khắc phục:** cùng cơ chế dropdown-only ở #2 — finance chỉ chọn, không gõ, nên lớp lỗi này biến mất theo thiết kế.
4. **Rule "cha+con reject" đụng rule merge lịch sử** (seed giữ nguyên tháng đã đóng). Nếu validate cha+con chạy global trên toàn seed, 1 thay đổi granularity hợp lệ giữa các tháng (tháng 7 budget ở cha, tháng 8 đổi sang con) sẽ bị reject nhầm. **Khắc phục:** scope validate nghiêm ngặt theo `(period_month, direction)`, không xét chéo qua các tháng khác — khớp với cách BvA join vốn cũng luôn filter theo period_month. Xem phase-03.
5. **"1 dòng 642 cha hay nhiều dòng 642xx" — thực ra có 3 chế độ khả dĩ, không phải 2.** Chế độ lai (1-2 con quan trọng tách riêng + 1 dòng cha "phần còn lại") cần join kiểu residual/exclusion (cha = actual thuộc prefix TRỪ actual đã bị con nhận) — phức tạp, dễ sai, khó validate. **Khắc phục:** không xây chế độ lai; orphan-actual report (#1) giải quyết đúng nhu cầu đó theo cách đơn giản hơn — phần dư nhỏ không tách dòng thì cứ hiện orphan, finance tự quyết bỏ qua hay tách thêm dòng.
6. **Dữ liệu thật cho thấy taxonomy hiện tại còn thiếu tên** cho 1 số account thực sự phát sinh (`33682`, `3335`, `642273/642286/642288/642278`). **Khắc phục:** tra `description` (Diễn giải) của giao dịch thật trong sổ cái (`fact_cash_movement`) — suy ra được tên với độ tin cậy cao cho hầu hết (`3335`=Thuế TNCN, `642273`=phí tạp vụ recurring rõ ràng) mà không cần hỏi ai. Chỉ còn đúng 1 câu cần kế toán: quan hệ "FGO" (xuất hiện ở `33682` và `13681`) là gì — ảnh hưởng tên + quyết định scope, không phải cả 8 mục như đánh giá ban đầu. `6351` (chênh lệch tỷ giá, bút toán tự động) khuyến nghị loại khỏi dropdung budget luôn, không cần đặt tên. Chi tiết đầy đủ xem phase-01 §1.

## Phases

| # | Phase | File | Phụ thuộc |
|---|-------|------|-----------|
| 1 | Account taxonomy + BvA join redesign | `phase-01-account-taxonomy-and-join.md` | **DONE 2026-07-09** |
| 2 | `__REF` machine-published dropdown | `phase-02-sheet-ref-dropdown-writeback.md` | **DONE 2026-07-11** (code + E2E thật) — Phase 1 (cần `dim_gl_account` mới) |
| 3 | Sync validation: parse + mutual-exclusivity + Lark reject | `phase-03-sync-validation-mutual-exclusivity-notify.md` | **DONE 2026-07-09** |
| 4 | Orphan-actual report | `phase-04-orphan-actual-report.md` | **DONE 2026-07-09** |

Phase 3 và 4 độc lập sau khi Phase 1+2 xong, có thể làm song song (không đụng chung file).

## Tài liệu liên quan (đã cập nhật/đối chiếu)

- `docs/analytics-handbook/domains/finance.md` — 2 dòng đánh dấu "cashflow_line ... provisional, needs finance sign-off" đã được update trỏ về plan này (sign-off = quyết định trong bảng trên, implementation chưa xong).
- `plans/archive/260702-1727-misa-cashflow-budget-planner/phase-06-sheet-to-seed-sync.md` — thêm note đầu file trỏ sang plan này (superseded cho phần recurring-account-mapping; phần one_off/reserve/policy giữ nguyên không đổi).
- `docs/analytics-handbook/guides/finance-budget-user-guide.md` — **Cập nhật một phần** (2026-07-09): bảng cột A-G + thứ tự tháng đã update theo Addendum dưới. **Còn thiếu:** FAQ "Thêm dòng tiền mới" (mục §2) vẫn mô tả quy trình `cashflow_line` cũ, chưa viết lại theo flow account_code dropdown mới — cần làm riêng, ngoài phạm vi yêu cầu hôm nay.
- `transformation/models/marts/finance/mart_cashflow_budget_vs_actual.sql`, `dim_gl_account.sql` — đổi trong Phase 1 (xem chi tiết phase file, không lặp lại ở đây).

## Acceptance criteria (tổng, chi tiết từng phase xem phase file)

- [ ] `ref_gl_accounts.csv` không còn account nào dùng trong dropdown bị fallback `"TK <code>"`
- [ ] Budget 1 dòng ở cha → actual mọi con tự roll-up đúng (Chế độ A)
- [ ] Budget nhiều dòng con → actual từng con match đúng dòng nó, con thiếu → xuất hiện ở orphan report (Chế độ B)
- [ ] Cha+con cùng (period_month, direction) → sync reject, Lark card gửi, sheet hiện cảnh báo cụ thể ô nào
- [ ] Đổi granularity giữa các tháng (vd tháng 7 cha, tháng 8 con) → sync KHÔNG reject nhầm
- [ ] `__REF` sinh tự động, không cần finance/kỹ thuật gõ tay padding
- [ ] Orphan-actual report tồn tại, hiển thị riêng biệt, không lẫn vào bảng BvA chính

## Câu hỏi mở

1. Quan hệ "FGO" là gì (xuất hiện lặp lại ở `33682` inflow + `13681` outflow, tổng ~116M) — ảnh hưởng tên account chính thức + quyết định có gộp thành 1 dòng budget "Thanh toán FGO" hay để riêng/ngoài scope CHI THƯỜNG XUYÊN. **Cập nhật 2026-07-10:** `ref_gl_accounts.csv` đã có tên `33682,Phải trả nội bộ - FGO` (uncommitted trong working tree) — nhưng không tìm thấy report/note nào ghi lại xác nhận thật từ kế toán, chỉ đặt tên theo suy đoán. Coi câu hỏi này **CHƯA đóng** cho tới khi có xác nhận; quyết định gộp/tách dòng budget vẫn chưa làm.
2. Xác nhận nhanh tên `642288` (chi phí dịch vụ AI, 1 lần 553K) và `642278` (lệ phí gia hạn, 1 lần 100K) — độ tin cậy thấp vì chỉ có 1 mẫu; hoặc đơn giản bỏ qua, để orphan report bắt vì số tiền quá nhỏ. **Cập nhật 2026-07-10:** `642288,Chi phí dịch vụ AI/phần mềm` đã thêm vào seed (uncommitted) — cùng tình trạng #1, chưa rõ nguồn xác nhận. `642278` vẫn chưa thêm (đúng khuyến nghị ban đầu — để orphan report bắt).
3. Orphan-actual report hiển thị ở đâu — tab riêng trong Metabase dashboard 114, hay mart mới độc lập chưa gắn dashboard? (phase-04 đề xuất mart trước, gắn dashboard là việc riêng sau khi có thật dữ liệu orphan để thiết kế card). **Trạng thái:** phương án (b) đã triển khai — `mart_cashflow_unmapped_actuals.sql` tồn tại, chưa gắn dashboard nào. Vẫn mở cho tới khi có dữ liệu orphan thật để thiết kế card.

## Addendum — Cột Ghi chú + đảo thứ tự tháng (2026-07-09, sau khi Phase 1-3 xong)

**Vấn đề phát sinh:** nhiều khoản recurring riêng biệt cùng map 1 account_code (vd "Internet" và các khoản khác đều lên `642282 Chi phí dịch vụ mua ngoài`) — tính toán BvA vẫn đúng (mart tự SUM đúng), nhưng sheet không có cách nào phân biệt các dòng cùng account bằng mắt. Thực tế: khi kiểm tra sheet thật phát hiện finance đã tự dùng cột "Gợi Ý" làm chỗ ghi note tạm ("Cước internet 06.2026") vì không có chỗ khác — xác nhận nhu cầu này có thật, không phải giả định.

**Đã làm:**
- Chèn cột **B "Ghi chú"** vào `BUDGET_ITEMS` (ngay sau Dòng Tiền) — tự do, không parse cho logic gì, chỉ hiển thị + lưu vào seed `notes`. Toàn bộ cột dịch phải 1 (Chiều giờ ở C, Type ở D, Tháng Cần ở E, Tuần TT ở F, Tổng Cần ở G, tháng bắt đầu từ H).
- **Đảo thứ tự cột tháng — tháng gần nhất bên trái**, giảm dần sang phải (H-I=tháng mới nhất, ...). Trước đó tháng cũ ở bên trái. Quy trình thêm tháng mới đổi theo: **chèn cột mới ngay sau G**, không còn "thêm ở cuối".
- Update: `budget_transform.py` (`BI_COL_*` + đọc/populate `notes`), `validate-budget-sheet.gs` (`BI_COL` block), `seed_cashflow_budget.csv` header, `finance-budget-user-guide.md` (bảng cột + quy trình thêm tháng).
- Xác nhận bằng code review: `parse_budget_matrix`/`build_suggestion_writes`/`.gs` đều match cột tháng theo GIÁ TRỊ header (vd "2026-07"), không giả định thứ tự vật lý — nên đảo cột không cần sửa logic parse, chỉ sửa `BI_COL_*` cho khối metadata cố định.

**Verify:** fixture CSV viết lại qua helper `_insert_col` CSV-aware, tránh đếm dấu phẩy tay. Live dry-run trước/sau đảo cột cho kết quả giống hệt nhau (3 dòng tháng 6, 9 policy rows) — xác nhận order-independence đúng như code review. **Sửa 2026-07-10:** con số "52/52 test" ghi ở đây trước đó SAI — chạy lại `pytest ingestion/tests/test_gsheet_budget_sync.py` thật cho **41 passed** (khớp con số phase-03, không phải 52). Không rõ 52 từ đâu ra (có thể đếm nhầm hoặc aspirational) — sửa lại theo số đo được.

**Rủi ro đã cân nhắc:** ghi đè cột H:M bằng values thay vì Sheets API `moveDimension` — an toàn vì cột tháng không có data-validation nào gắn (`setupBudgetDropdowns` chỉ áp dụng cột A/C/D/F), nên rewrite giá trị thuần không làm mất validation nào. Đã verify sau khi ghi: header + data thật (Lương/BHXH/Internet tháng 6) di chuyển đúng vị trí L-M, không mất dữ liệu.

**Còn thiếu:** `finance-budget-user-guide.md` §2 FAQ "Thêm dòng tiền mới" chưa viết lại theo flow account_code — vẫn mô tả quy trình `cashflow_line` cũ.

## Cập nhật trạng thái 2026-07-10 (review độc lập)

Đối chiếu claim trong plan/phase file với code + test thật:

- **Đúng như claim:** `dim_gl_account.parent_account_code/name` (nearest-named-ancestor), `mart_cashflow_budget_vs_actual` prefix-match join + legacy fallback, `mart_cashflow_unmapped_actuals.sql` (phase-04) + `schema.yml` đều tồn tại và khớp thiết kế trong phase-01/04. `budget_transform.py` có `_parse_account_prefixed_label` + `_validate_no_prefix_collision` khớp phase-03.
- **Sai lệch đã sửa (xem inline ở trên):** header top-of-file ghi "Phase 1-4 DONE — toàn bộ plan hoàn thành" nhưng phase-02 tự ghi PARTIAL (Dagster auto-refresh `__REF` chưa làm) — 2 chỗ mâu thuẫn nhau, đã sửa header cho khớp phase file. Con số "52/52 test" ở Addendum sai, thật ra là 41/41 (`pytest ingestion/tests/test_gsheet_budget_sync.py` chạy lại hôm nay, 41 passed, 0 fail).
- **Chưa rõ nguồn:** `ref_gl_accounts.csv` có thêm tên cho `33682` (FGO) và `642288` trong working tree (uncommitted, không có trong commit `d2837ec9`) — không tìm thấy report nào ghi lại đây là xác nhận thật từ kế toán hay chỉ là suy đoán được điền thêm. Coi Câu hỏi mở #1, #2 là chưa đóng cho tới khi có xác nhận rõ nguồn.
- **Chưa verify được (ngoài phạm vi review này):** `dbt build` cho 3 model finance đổi (`dim_gl_account`, `mart_cashflow_budget_vs_actual`, `mart_cashflow_unmapped_actuals`) — không chạy lại trong lần review này (cần container `data_platform`, không invoke vì không phải yêu cầu). Các con số "6,088,709,276"/"6,089,208,876" trong phase-01/04 chưa re-verify.
- **Toàn bộ thay đổi liên quan plan này (seed, SQL, `.gs`, `budget_transform.py`, docs) vẫn UNCOMMITTED** — commit gần nhất chạm plan này là `d2837ec9` ("draft budget account-level remap seeds + plan"); mọi việc sau đó (bao gồm addendum cột Ghi chú + đảo tháng, và 2 tên account 2026-07-10) chưa có commit riêng.
