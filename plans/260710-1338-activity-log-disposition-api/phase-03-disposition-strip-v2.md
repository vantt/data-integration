# Phase 3 (P2) — Disposition Strip v2 (state machine T0-T3)

## Context
Nguồn: [ux-design report](../reports/ux-design-260710-1313-activity-log-api-cockpit-integration-report.md) mục IV + IV.b (state machine, sheet-up, phím tắt, phương án B đã cân nhắc và loại bỏ), quyết định đã chốt #2-#4. Phụ thuộc Phase 2 (cần draft/PATCH/finalize API sống).

M08 xuống vai ngăn kéo/ngoại lệ hoàn toàn ở phase này (`[⋯ Chi tiết]` mở M08 pre-filled từ draft).

## Requirements

1. Outcome_bar hiện tại (`c360_call_cockpit_panel.html` dòng 781-820, 1 hàng tĩnh) → thay bằng disposition strip 3 pha, đổi nội dung theo state:
   - **T0 TRƯỚC** (1 hàng ~52px): `[📞 Gọi <số> ▾ số khác] [⋯ Ghi thủ công]` — bấm 📞 = `POST /api/parties/{id}/call-sessions` (Phase 2) + start timer client-side; `[⋯]` mở M08 (ngoại lệ).
   - **T1 TRONG** (1 hàng, KHÔNG có outcome pills): `⏱ <mm:ss> · [nháp autosave PATCH body…] ☑Zalo [■ Kết thúc]` — mỗi commit textarea → PATCH `body`; checkbox Zalo → PATCH `custom_fields.zalo_connected`.
   - **T2 SAU — disposition** (2 hàng ~96px): 7 pill (Nghe/Mua/Hẹn lại/Không bắt/Bận/Từ chối/Sai số). Pill cần thêm info → **sheet mọc LÊN TRÊN** (~180px, che vùng talk_track/guardrails/trust_footer cột trái — hợp lệ vì cuộc gọi đã kết thúc lúc này) chứ KHÔNG dùng "phương án B — takeover cột trái" (đã loại bỏ vì phá điểm neo mắt qua 50 call/tuần + vi phạm Invariant §9 re-render vùng lớn).
   - **T3 ĐÃ CHỐT** (1 hàng): `✓ Đã lưu: <outcome> (<reason nếu có>) · <duration> [Khách kế → N/M]`. KHÔNG auto-advance sau finalize — nút to + phím Enter nhưng phải chủ động bấm (quyết định đã chốt).
2. Sheet reason (VD "Lý do từ chối") — pill bắt buộc/tuỳ chọn theo bảng report mục IV; nút `[🚫 Đừng gọi nữa]` set `outcome_reason='do_not_contact'` (REFERENCE plan 260709-1638 câu hỏi mở #5 — suppression filter runtime, KHÔNG tự thêm cột party ở đây).
3. Đa kênh 1 phiên = 2 activity riêng (quyết định #3): sau khi chốt `no_answer`, strip hiện nút phụ `[＋Nhắn Zalo]` (tái dùng endpoint `POST /customers/{id}/reason/resolve-async` đã có, KHÔNG viết mới) → tạo activity thứ 2 riêng biệt, không gộp vào activity call vừa chốt.
4. Phím tắt: `1-7` chọn outcome pill theo thứ tự hiển thị, `Enter` = "Lưu & Khách kế →" khi đang ở trạng thái đã chọn outcome hợp lệ (không phá phím tắt khác đang có trong cockpit — kiểm tra xung đột với `s14ToggleTP`, `s14ToggleObj` trước khi bind global keydown).
5. Van xả màn hẹp: pills wrap 2 hàng khi không đủ ~700-750px (S14 vốn desktop-only ≥1200px, trường hợp hiếm — chỉ cần CSS `flex-wrap`, không cần logic riêng).
6. `[⋯ Chi tiết]` (mọi pha) → `GET /modals/m08?...&mode=edit_activity&activity_id=<draft.id>` (Phase 2) — pre-filled từ draft, không tạo activity mới.

## Files to modify
- `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` — thay outcome_bar bằng disposition strip; JS state machine T0→T1→T2→T3 (thay `s14OpenOutcome` hiện tại).
- `crm/src/adapters/inbound/web/screens/customer360/screen_call_cockpit.py` (hoặc file tương đương truyền context cockpit) — truyền `draft_activity` hiện tại (nếu có) vào template context để strip biết state khởi tạo đúng (VD reload trang giữa chừng cuộc gọi).
- `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md` — cập nhật region `outcome_bar` → `disposition_strip` (dòng 10, 52, 75, 191, entry A-S14-009 dòng 249-259) khớp state machine mới. **Cập nhật CÙNG COMMIT với template** (quyết định VI — "cập nhật spec S14 + M08 cùng commit").
- CSS mới cho sheet-up (~180px), timer display, pill wrap — vị trí file CSS theo convention hiện có của cockpit (kiểm tra `ds-extra.css` hay inline `<style>` trong fragment, theo pattern R14 banner đã làm inline ở đầu file).
- Test JS/manual cho state machine (repo có thể chưa có JS unit test harness cho CRM — xác nhận trước; nếu không có, dựa vào manual test theo kịch bản trong mục Tests).

## Implementation steps (outline — chi tiết hoá khi bắt đầu phase này)
1. Xác nhận Phase 2 đã ship và ổn định (draft/PATCH/finalize hoạt động qua M08 `edit_activity` trước khi cắm vào strip).
2. Thiết kế lại `outcome_bar` HTML thành 4 sub-template/state ẩn-hiện bằng JS (giữ 1 fragment, KHÔNG tách route riêng — theo đúng Invariant §9, chỉ swap sub-region).
3. Viết state machine JS: T0 (idle) → bấm Gọi → T1 (timer + PATCH autosave) → bấm Kết thúc → T2 (7 pill) → chọn pill cần info → sheet → Lưu → T3.
4. Bind phím tắt 1-7 + Enter, guard theo state hiện tại (chỉ active ở T2/sheet).
5. Wire `[＋Nhắn Zalo]` sau `no_answer` — gọi endpoint async-resolve có sẵn.
6. Cập nhật spec S14 (`docs/ui-spec/screens/S14-call-mode-cockpit.md`) khớp state machine — region tên, action id, ví dụ ASCII trong report mục IV.b.
7. Xoá code `s14OpenOutcome`/nút outcome_bar cũ sau khi strip mới thay thế hoàn toàn (không giữ 2 đường song song).

## Tests
- Manual kịch bản đủ 4 state theo thứ tự T0→T1→T2→T3, xác nhận đúng nội dung/kích thước mỗi pha (không tràn quá ~180px ở T2 sheet).
- Reload trang giữa T1 (đang gọi) → cockpit phải nhận diện draft đang mở và khôi phục đúng state (không tạo draft thứ 2).
- Phím tắt 1-7 chọn đúng pill tương ứng thứ tự hiển thị; Enter chỉ trigger "Lưu & Khách kế" khi outcome đã chọn hợp lệ (không trigger khi đang gõ trong textarea nháp — kiểm tra `document.activeElement`).
- `[＋Nhắn Zalo]` sau `no_answer` tạo đúng 1 activity thứ 2 riêng (không gộp field vào activity call).
- Không auto-advance: sau finalize, cockpit KHÔNG tự chuyển khách kế; `[Khách kế →]` phải bấm chủ động.
- Spec S14 (`S14-call-mode-cockpit.md`) và template không lệch nhau (region/id khớp) — review chéo khi merge.

## Rollback
- Strip mới là 1 fragment độc lập trong `#s14-panel-root`; rollback bằng cách revert file `c360_call_cockpit_panel.html` về outcome_bar cũ (git revert đơn giản, không có migration DB ở phase này).
- Spec S14 revert cùng commit với template nếu rollback — không để spec đi trước code hoặc ngược lại (đã ghi rõ trong report quyết định VI).
