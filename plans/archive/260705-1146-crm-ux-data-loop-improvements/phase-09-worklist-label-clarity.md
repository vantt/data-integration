# Phase 09 — Worklist Label & Badge Clarity

**Status:** DONE  **Priority:** P1  **Depends on:** — (độc lập phase 01–08, không đụng file trùng với phase-08)
**Nguồn:** user report 2026-07-06 — action item hiển thị mã khó hiểu; action button không đồng nhất giữa các dòng.

## Bối cảnh đã xác minh (root cause)

### Vấn đề 1 — mã thô hiển thị cho NV: `[CAL_NOW] Đặng Văn Nhiệm d8835eb2200423e5d3295fc7257379f3`

Đây là 1 ACTION ROW (`_wl_row.html:57-63`), không phải task. 3 mảnh ghép cạnh nhau:

1. **Badge action_type hiển thị mã thô** (`_wl_row.html:60`: `{{ a.action_type }}`) — `badge_catalog.py` (`_CATALOG["action_type"]`) đã có sẵn `BadgeDef(css_mod, hint)` với hint tiếng Việt đầy đủ (vd `"call_now" → "Gọi ngay — khách có nguy cơ rời bỏ cao"`), và `bdg_lookup()` (`badge_catalog.py:139`) tự `.lower()` nên tooltip hover ĐÃ đúng — nhưng **text hiển thị chính** vẫn là `a.action_type` verbatim ("CALL_NOW"), không phải label ngắn. `BadgeDef` chỉ có 2 field (css_mod, hint), thiếu field "label ngắn" để render làm text chính.
2. **`customer_key` là mã kỹ thuật, không phải SĐT** — `_wl_row.html:62`: `<span class="wl-row__phone">{{ a.customer_key }}</span>` — tên class CSS gợi ý "phone" nhưng `customer_key = dbt_utils.generate_surrogate_key(['customer_id'])` (`transformation/models/marts/core/dim_customers_base.sql:34`) — 1 MD5 surrogate key sinh cho join nội bộ warehouse, KHÔNG BAO GIỜ có ý định hiển thị cho người dùng. Luôn render bất kể `customer_name` có hay không.
3. **Bug tương tự lặp lại ở TASK TITLE fallback** (`task_service.py:306` và `:404`): `title = f"[{action.action_type}] {label}"` — khi `rationale_vi` rỗng, `label = action.customer_key` (cùng hash kỹ thuật) → title task cũng lộ mã thô y hệt.

### Vấn đề 2 — action button không đồng nhất

1. **"Dọn" (task row, band 0 quá hạn) = Hủy task, không phải Bỏ qua.** `_wl_row.html:264-267`: nút text "Dọn", tooltip "Hủy task này", gọi `PATCH /tasks/{id}/cancel`. Toàn bộ phần còn lại của app (17 nơi verified: modals, `_wl_row.html:267` tooltip chính nó) đều dùng "Hủy" cho hành động cancel/hủy. "Dọn" là từ lạc điệu duy nhất — dễ hiểu nhầm thành "dọn dẹp"/"bỏ qua".
2. **2 cơ chế dời hạn cùng tồn tại cho TASK rows** theo 2 điều kiện độc lập, có thể cùng hiện trên 1 dòng: (a) `row.band == 0` (bất kể nguồn) → nút text "Dời hạn" mở modal M05 (chọn ngày bất kỳ); (b) `t.source == 'action_queue_claim'` (bất kể band) → dropdown icon ⏰ (1/3/7 ngày cố định). Task vừa quá hạn vừa đã claim → cả 2 nút cùng hiện. **Xác nhận: ACTION rows KHÔNG bị vấn đề này** — action row chỉ có 1 cơ chế duy nhất (⏰ dropdown, `_wl_row.html:132-143`), không có nút "Dời hạn" modal riêng.
3. **"Mở hồ sơ" (task row, `_wl_row.html:293`) vs "Xem 360" (action row, `_wl_row.html:155`)** — cả 2 đều nav đến `/customers/{pid}` (cùng đích), tên khác nhau.
4. **"📞 Gọi chế độ" (action row, `_wl_row.html:161`)** — dài, nên rút gọn thành "📞 Gọi" (giữ tooltip "Vào chế độ gọi với hàng đợi" để không mất ý nghĩa khi hover).

## Quyết định đã chốt (user, 2026-07-06)

1. **Badge + hash:** thêm label ngắn tiếng Việt cho action_type (thay vì mã thô); fallback khi `customer_name` rỗng = **số điện thoại nếu có, không thì "(chưa xác định)"** — KHÔNG bao giờ lộ hash kỹ thuật.
2. **Dời hạn task:** **giữ nguyên cả 2 cơ chế** (modal M05 cho band 0 + dropdown ⏰ cho action_queue_claim) — KHÔNG hợp nhất logic. Chỉ **đổi icon** để 2 nút trông khác biệt rõ khi cùng xuất hiện trên 1 dòng (tránh nhầm chúng là 1 thứ). Việc hợp nhất **không áp dụng cho action-item** (action row vốn đã nhất quán, chỉ 1 cơ chế ⏰).
3. **"Mở hồ sơ" → "Xem 360"** (đổi task row cho khớp action row).
4. **"📞 Gọi chế độ" → "📞 Gọi"** (action row).

## Requirements

| # | Việc | File | Ghi chú | Kết quả |
|---|------|------|---------|---------|
| R1 | Thêm short-label VN cho `action_type` domain (12 giá trị trong `_CATALOG["action_type"]`) — field mới trong `BadgeDef` hoặc dict song song `_ACTION_TYPE_SHORT_LABEL` | `badge_catalog.py` | Không đụng `hint` (tooltip) hiện có — chỉ thêm, không thay | **done:** `crm/src/adapters/inbound/web/badge_catalog.py:137-159` — `_ACTION_TYPE_SHORT_LABEL` dict song song + `bdg_label()` func (chỉ áp dụng domain `action_type`, domain khác fallback về key thô) |
| R2 | Filter/global mới xuất label ngắn (vd `bdg_label_filter`) | `fmt_badge.py` | Theo pattern `bdg_cls_filter`/`bdg_tip_filter` hiện có | **done:** `crm/src/adapters/inbound/web/fmt_badge.py:62-64` (`bdg_label_filter`) + đăng ký filter `bdg_label` trong `crm/src/composition.py:406` |
| R3 | Action row: badge hiển thị label ngắn thay vì `a.action_type` | `_wl_row.html:60` | | **done:** `crm/src/adapters/inbound/web/templates/fragments/_wl_row.html:59-64` — text dùng `a.action_type \| bdg_label('action_type')`, tooltip giữ nguyên `bdg_tip` |
| R4 | Action row: bỏ hiển thị `a.customer_key` thô; fallback = SĐT (đã có sẵn `pref_id` từ `party_extras` load ở đầu macro, dòng 12-13 — KHÔNG cần query mới, lọc `identity_type == 'phone'`) hoặc "(chưa xác định)" | `_wl_row.html:62` | class `wl-row__phone` — đặt tên đúng nghĩa lại nếu đổi | **done:** `_wl_row.html:12-17` (`_phone_val`) + `:59-66` — `customer_key` không còn xuất hiện trong template; hiển thị `customer_name` HOẶC (`_phone_val` hoặc "(chưa xác định)") |
| R5 | `task_service.py:306,404`: dùng cùng short-label + phone-fallback thay vì `action.customer_key` thô trong title fallback | `task_service.py` | Cùng bug, 2 chỗ — sửa đồng thời | **done:** `crm/src/application/task_service.py:33-55` (`_ACTION_TYPE_SHORT_LABEL` local dup — application layer không được import adapter) + `:74-88` (`_customer_fallback_label`) áp dụng ở `claim_action_item` (~L318) và `_process_action` (~L417) |
| R6 | Task row band 0: đổi text "Dọn" → "Hủy" (giữ nguyên endpoint/behavior) | `_wl_row.html:267` | | **done:** `_wl_row.html:267` — text "Hủy", endpoint `PATCH /tasks/{id}/cancel` không đổi |
| R7 | Task row: đổi icon nút "Dời hạn" (band 0, modal M05) để khác biệt trực quan với ⏰ snooze dropdown (vd 📅) — KHÔNG đổi logic/endpoint | `_wl_row.html:260-263` | | **done:** `_wl_row.html:263` — text "📅 Dời hạn" (📅 chưa dùng ở nơi nào khác trong worklist, không đụng nghĩa ⏰), endpoint `GET /modals/m05` không đổi |
| R8 | Task row: "Mở hồ sơ" → "Xem 360" | `_wl_row.html:293` | | **done:** `_wl_row.html:294` |
| R9 | Action row: "📞 Gọi chế độ" → "📞 Gọi" (giữ tooltip) | `_wl_row.html:161` | | **done:** `_wl_row.html:161` — tooltip "Vào chế độ gọi với hàng đợi" giữ nguyên |

## Tests & Validation

- `test_web_templating.py` dùng `action_type="CALL_NOW"` (uppercase) trong fixtures + assert `value="CALL_NOW"` (dòng 327, hidden input filter chip — KHÔNG phải badge text hiển thị, không bị ảnh hưởng bởi R1/R3). Xác nhận trước khi sửa: R3 chỉ đổi text hiển thị trong badge `<span>`, không đổi giá trị `action_type` gửi lên server/filter — filter chips vẫn nhận "CALL_NOW" nguyên trạng.
- Thêm test: badge action_type render label ngắn (không phải mã thô) cho ít nhất 2-3 giá trị tiêu biểu (`call_now`, `reorder_overdue`).
- Thêm test: action row không có customer_name → hiển thị SĐT hoặc "(chưa xác định)", KHÔNG có chuỗi hash 32 ký tự nào trong output.
- Thêm test: task title fallback (`claim_action_item`/`_process_action`) không chứa `action.customer_key` khi rationale rỗng.
- Grep sau khi sửa: `grep -rn "Dọn\b" crm/src/adapters/inbound/web/templates/` → 0 kết quả liên quan cancel task.
- ui-spec: cập nhật `crm/docs/ui-spec/screens/S01-worklist-dashboard.md` (label mapping + nút đổi tên) nếu spec có mô tả các label này.

## Risks & Rollback

- R4 fallback SĐT: nếu `pref_id` không phải type phone (vd chỉ có zalo), fallback về "(chưa xác định)" — không hiển thị zalo id thay thế (giữ đơn giản, đúng scope quyết định).
- Đổi text thuần UI, không đụng schema/API — rollback = revert commit, không rủi ro dữ liệu.
- R7 (đổi icon) có thể trùng icon đã dùng chỗ khác (⏰ dùng cho snooze ở nhiều nơi) — kiểm tra icon set hiện có trước khi chọn icon mới cho "Dời hạn" tránh đụng nghĩa.
