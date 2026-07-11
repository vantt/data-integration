# Phase 1 (P0) — M08 form lightening + quick-outcome pills trên cockpit

## Context

Nguồn: [ux-design report](../reports/ux-design-260710-1313-activity-log-api-cockpit-integration-report.md) mục I (chẩn đoán), V (sửa M08), VI (P0 row), quyết định đã chốt #1-#4.

Đọc trước khi implement:
- `crm/src/domain/entities/activity.py` dòng 37-73 — `CONTACT_OUTCOMES_CALL` đã có `busy`, `wrong_number` (KHÔNG thiếu ở tầng enum) nhưng thiếu `purchased`. `REASON_REQUIRED_OUTCOMES = {"refused"}` — `purchased` không cần reason, không đổi set này.
- `crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html` — Step 3 outcome pills khởi tạo tĩnh dòng ~256 (`[('answered','Đã nghe'),('no_answer','Không bắt'),('callback','Hẹn lại'),('refused','Từ chối')]`) VÀ JS `OUTCOMES.call` dòng ~491 (cùng thiếu busy/wrong_number/purchased) — 2 nơi phải sửa đồng bộ (Jinja init + JS rebuild khi đổi hình thức).
- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py` — `handle_log_activity` (dòng 165-309): POST luôn trả `HTMLResponse(..., headers={"HX-Redirect": ...})` (dòng 309) — không phân biệt nguồn gọi. Cockpit hiện GỌI MODAL (`s14OpenOutcome`, dòng 1025-1039 của `c360_call_cockpit_panel.html`) chứ CHƯA POST thẳng — đây là gap cần vá ở (c).
- `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` dòng 781-820 (outcome_bar hiện tại: 4 nút answered/no_answer/callback/purchased — `purchased` ĐÃ có UI nhưng enum backend CHƯA có, đây là bug treo, phải vá cùng lúc với (a)) và dòng 1024-1039 (`s14OpenOutcome` JS — mở modal, không POST trực tiếp).
- `crm/src/tests/test_outcome_reason_enum.py` — test pattern cho enum; `crm/src/tests/test_bulk_resolve_endpoint.py` — test pattern cho endpoint không dùng FastAPI TestClient (mock closure).

## Requirements

### (a) Thêm pill busy/wrong_number/purchased + enum `purchased`
1. `activity.py`: thêm `"purchased"` vào `CONTACT_OUTCOMES_CALL` (giữ thứ tự, không đổi `VALID_OUTCOME_REASONS`/`REASON_REQUIRED_OUTCOMES`).
2. `modal_log_activity.html` Jinja init pills: thêm `('busy','Bận')`, `('wrong_number','Sai số')`, `('purchased','Đã mua')` vào list Step 3.
3. JS `OUTCOMES.call` (rebuild khi đổi hình thức): thêm 3 entry tương ứng `{v:'busy',l:'Bận'}`, `{v:'wrong_number',l:'Sai số'}`, `{v:'purchased',l:'Đã mua'}`.
4. `purchased` là outcome dương: thêm vào mảng `positive` (dòng ~615, hiện `['answered','met','replied']`) để mở Step 3c (lên lịch theo dõi), và vào `COMPLETE_TASK_OUTCOMES` (dòng ~672) để auto-tick hoàn thành task.
5. KHÔNG thêm `purchased` vào `REASON_SHOW_OUTCOMES`/`REASON_REQUIRED_OUTCOMES_JS` — không cần lý do.
6. (tuỳ chọn, không bắt buộc P0) thêm key `call_purchased` vào `BODY_PH` gợi ý nhập mã đơn — nếu bỏ qua thì fallback về placeholder mặc định vẫn hoạt động đúng.

### (b) Đảo outcome-first + gộp accordion "Nâng cao"
1. **Reorder thuần DOM** (không đổi field name/id, không đổi JS logic): di chuyển block "Step 3 — KẾT QUẢ" (`#m08-outcome-sec`) + "Step 3b1 — LÝ DO" + "Step 3b — HẸN LẠI" + "Step 3c — LÊN LỊCH THEO DÕI" lên TRƯỚC block "Step 1 — HÌNH THỨC" và "Step 2 — KÊNH CỤ THỂ". An toàn vì: (i) toàn bộ JS thao tác qua `getElementById`, không phụ thuộc thứ tự DOM; (ii) HT mặc định `call` đã được set qua `m08PickHT(firstOpt)` ở init IIFE (chạy sau khi DOM ready, không phụ thuộc vị trí hiển thị) nên outcome pills hiển thị đúng ngay từ đầu.
2. Bọc "Step 5 — LƯU THÀNH GHI CHÚ HỒ SƠ" + block insight (`<details class="m08-insight-promo">` hiện có) + "Step 6 — THỜI GIAN & ĐƠN LIÊN QUAN" vào 1 `<details>` mới, class ví dụ `m08-advanced`, `<summary>Nâng cao</summary>`, **đóng mặc định** (không có `open` attribute). Insight `<details>` hiện tại giữ nguyên bên trong (nested `<details>` hợp lệ HTML).
3. Giữ "Step 4 — NỘI DUNG" (textarea `body`) VÀ block "Đánh dấu task hoàn thành" (`{% if task_id %}`) NGOÀI accordion — đây là field/action quan trọng cần luôn thấy, không nằm trong scope "Nâng cao" theo quyết định đã chốt.
4. Field `occurred_at` và `related_order_code` (trong Step 6) nay nằm trong accordion đóng mặc định — chấp nhận được vì giá trị mặc định (`occurred_at` = now ICT qua JS `ictPlus(0)`) vẫn được set kể cả khi accordion đóng (input vẫn tồn tại trong DOM, `hidden` bởi `<details>` không phải `display:none`, JS set `.value` vẫn chạy bình thường lúc init).

### (c) Cockpit outcome_bar: 3 pill POST thẳng, không modal
1. `c360_call_cockpit_panel.html` outcome_bar (dòng 781-820): đổi nút "Không nghe" (hiện `onclick="s14OpenOutcome('no_answer')"`) SANG POST trực tiếp; thêm 2 nút mới "☎ Bận" (busy) và "☠ Sai số" (wrong_number) cùng cơ chế. Giữ nguyên "✓ Gọi được" (answered) và "🛒 Đã mua" (purchased) mở modal (cần note/mã đơn) và "⏳ Hẹn lại" (callback) mở modal (cần chọn giờ).
2. Cơ chế POST: dùng `hx-post="/customers/{{ party_id }}/log-activity"` (endpoint hiện có, KHÔNG tạo endpoint mới ở P0) với `hx-vals` mang default: `hinh_thuc=call`, `contact_outcome=<no_answer|busy|wrong_number>`, `occurred_at` = ICT hiện tại (tính JS, cùng công thức `ictPlus(0)` đã có trong M08), `channel_identity_id`/`channel_value` = identity chính (`pref_phone`, đã resolve sẵn trong template dòng ~132-143 — cần thêm `identity_id` tương ứng, hiện chỉ có `pref_phone` giá trị chuỗi, không có id; lấy từ `identities` list lọc `is_preferred` để lấy `identity_id`), cộng `resolve_action_ids`/`resolve_task_ids` từ 2 hidden field đã có (`#s14-resolve-action-ids`, `#s14-resolve-task-ids`) và `body` = nội dung `#s14-quick-note` nếu có, cộng field mới `source=call_cockpit`.
3. `hx-target` trỏ vào 1 vùng nhỏ MỚI bên trong outcome_bar (VD `<span id="s14-outcome-status">`), `hx-swap="innerHTML"` — tuyệt đối KHÔNG target `#s14-panel-root` hay re-render cả panel (Invariant §9 của S14, đã ghi rõ trong spec).
4. Backend `handle_log_activity` (`screen_customer_360_activity.py`): thêm `Form` field `source: str = Form(default="")`. Khi `source.strip() == "call_cockpit"`: bỏ qua `HX-Redirect`, trả `HTMLResponse` với fragment nhỏ dạng text (VD `✓ Đã lưu: {label outcome}`) status 200. Giữ nguyên toàn bộ side-effect hiện có (auto-claim, bulk-resolve) — chỉ đổi response shape ở cuối handler (dòng 309), giữ `HX-Redirect` làm mặc định cho mọi nguồn khác (M08 modal/timeline) để không phá hành vi cũ.
5. KHÔNG đổi hành vi `resolve_action_ids`/`resolve_task_ids` bulk-resolve — quick-outcome vẫn phải đóng được rail item đang mở (giữ tính năng D4 hiện có).

## Files to modify
- `crm/src/domain/entities/activity.py`
- `crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html`
- `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html`
- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py`
- `crm/src/tests/test_outcome_reason_enum.py` (thêm test purchased)
- `crm/src/tests/test_bulk_resolve_endpoint.py` hoặc file test mới `crm/src/tests/test_quick_outcome_cockpit_post.py` (endpoint quick-outcome)

## Implementation steps
1. Sửa `activity.py` — thêm `"purchased"`.
2. Sửa 2 nơi outcome pill list trong `modal_log_activity.html` (Jinja + JS) đồng bộ nhãn tiếng Việt: Bận / Sai số / Đã mua.
3. Cập nhật `positive` array + `COMPLETE_TASK_OUTCOMES` thêm `'purchased'`.
4. Di chuyển block outcome (Step 3 + 3b1 + 3b + 3c) lên trước block hình thức/kênh (Step 1 + 2) trong `modal_log_activity.html` — thuần cắt/dán HTML, không sửa id/name.
5. Bọc Step 5 + insight `<details>` + Step 6 vào `<details class="m08-advanced"><summary>Nâng cao</summary>...</details>` mới.
6. Sửa `c360_call_cockpit_panel.html`: đổi nút "Không nghe" thành `hx-post`, thêm 2 nút "Bận"/"Sai số"; thêm span target trạng thái; đảm bảo lấy được `identity_id` của `pref_phone` (grep block dòng 132-143, mở rộng vòng lặp lưu cả `identity_id`).
7. Sửa `screen_customer_360_activity.py` — thêm `source` Form field + nhánh response fragment khi `source=="call_cockpit"`.
8. Chạy test suite hiện có, sửa nếu response shape assertion nào phụ thuộc `HX-Redirect` bị ảnh hưởng (không nên, vì nhánh mặc định không đổi).

## Tests
- `crm/src/tests/test_outcome_reason_enum.py`: thêm `test_call_has_purchased` (`assert "purchased" in CONTACT_OUTCOMES_CALL`), thêm case `ActivityService.log_activity` với `contact_outcome="purchased"` không raise và không yêu cầu `outcome_reason`.
- Test endpoint mới (theo pattern `test_bulk_resolve_endpoint.py` — mock closure, không cần FastAPI TestClient nếu repo chưa có sẵn TestClient fixture; kiểm tra trước khi viết mới): POST `/customers/{id}/log-activity` với `source="call_cockpit"` → response KHÔNG có header `HX-Redirect`, body chứa xác nhận; POST không có `source` → vẫn có `HX-Redirect` (regression guard).
- Test form cũ (`test_claim_context_snooze_r14.py` nếu đụng M08 context) chạy lại đảm bảo không đổi field name nào bị vỡ.
- Manual: mở M08 qua `/modals/m08`, xác nhận 7 pill hiển thị đúng thứ tự yêu cầu, accordion "Nâng cao" đóng mặc định và mở được.

## Rollback
- Template/JS: revert riêng từng file (không phụ thuộc lẫn nhau ngoài CRM app) — không có migration DB.
- Enum `purchased` thêm mới KHÔNG phá dữ liệu cũ (list bổ sung phần tử, không đổi/xoá giá trị hiện có); rollback = xoá phần tử khỏi list, không cần backfill vì chưa có activity nào dùng giá trị này trước khi ship.
- Response fragment mới cho `source=call_cockpit` là nhánh CÓ ĐIỀU KIỆN — rollback bằng cách bỏ điều kiện, endpoint quay lại hành vi `HX-Redirect` 100% như cũ.
