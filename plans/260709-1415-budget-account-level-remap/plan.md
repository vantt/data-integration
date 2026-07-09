# Budget Sheet — Account-Level Mapping cho Recurring Lines

**Status:** DRAFT — chưa implement
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
| 1 | Account taxonomy + BvA join redesign | `phase-01-account-taxonomy-and-join.md` | Tên account đã tra ra từ data (khó khăn #6) — chỉ cần hỏi kế toán 1 câu (quan hệ FGO), không block bắt đầu |
| 2 | `__REF` machine-published dropdown | `phase-02-sheet-ref-dropdown-writeback.md` | Phase 1 (cần `dim_gl_account` mới) |
| 3 | Sync validation: parse + mutual-exclusivity + Lark reject | `phase-03-sync-validation-mutual-exclusivity-notify.md` | Phase 1, 2 |
| 4 | Orphan-actual report | `phase-04-orphan-actual-report.md` | Phase 1 |

Phase 3 và 4 độc lập sau khi Phase 1+2 xong, có thể làm song song (không đụng chung file).

## Tài liệu liên quan (đã cập nhật/đối chiếu)

- `docs/analytics-handbook/domains/finance.md` — 2 dòng đánh dấu "cashflow_line ... provisional, needs finance sign-off" đã được update trỏ về plan này (sign-off = quyết định trong bảng trên, implementation chưa xong).
- `plans/archive/260702-1727-misa-cashflow-budget-planner/phase-06-sheet-to-seed-sync.md` — thêm note đầu file trỏ sang plan này (superseded cho phần recurring-account-mapping; phần one_off/reserve/policy giữ nguyên không đổi).
- `docs/analytics-handbook/guides/finance-budget-user-guide.md` — **CHƯA update** (đây là hướng dẫn vận hành hiện hành cho finance, mô tả behavior đang chạy thật; update vào cuối Phase 3 sau khi ship, tránh finance làm theo hướng dẫn cho tính năng chưa tồn tại).
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

1. Quan hệ "FGO" là gì (xuất hiện lặp lại ở `33682` inflow + `13681` outflow, tổng ~116M) — ảnh hưởng tên account chính thức + quyết định có gộp thành 1 dòng budget "Thanh toán FGO" hay để riêng/ngoài scope CHI THƯỜNG XUYÊN.
2. Xác nhận nhanh tên `642288` (chi phí dịch vụ AI, 1 lần 553K) và `642278` (lệ phí gia hạn, 1 lần 100K) — độ tin cậy thấp vì chỉ có 1 mẫu; hoặc đơn giản bỏ qua, để orphan report bắt vì số tiền quá nhỏ.
3. Orphan-actual report hiển thị ở đâu — tab riêng trong Metabase dashboard 114, hay mart mới độc lập chưa gắn dashboard? (phase-04 đề xuất mart trước, gắn dashboard là việc riêng sau khi có thật dữ liệu orphan để thiết kế card).
