# Phase 01 — M05/M08 không còn phá ngữ cảnh sau khi Lưu

## Bối cảnh

Spec gốc (`crm/docs/ui-spec/modals/M05-create-edit-task-modal.md` A-M05-003,
`M08-log-activity-modal.md` A-M08-003) định nghĩa hành vi Lưu là `close_overlay, target:
return_to_invoker` — đóng modal, quay lại đúng nơi đã mở nó. Code hiện tại luôn trả
`HX-Redirect` cố định:

- `POST /customers/{party_id}/tasks` → `HX-Redirect /customers/{pid}` (`screen_modal_task.py:184`
  qua `redirect_to_customer()` trong `screen_modal_shared.py:36-38`)
- `PATCH /tasks/{task_id}/edit` → `HX-Redirect /customers/{pid}?tab=tasks` hoặc `/tasks`
  (`screen_modal_task.py:138-139`)
- `POST /customers/{party_id}/log-activity` → `HX-Redirect /customers/{pid}?tab=timeline`
  (`screen_customer_360_activity.py:386`), trừ nhánh `source=call_cockpit` (dòng 375-385) — **nhánh
  này hiện KHÔNG còn caller nào set `source=call_cockpit`** (disposition-strip v2 đã bỏ code path cũ,
  xem "Known accepted gap" trong `S14-call-mode-cockpit.md` Phase 03) → M08 mở từ cockpit qua
  "⋯ Ghi thủ công"/"⋯ Chi tiết" **cũng đang bị redirect phá context**, không chỉ worklist.

Cơ chế đóng modal hiện có **không cần** custom JS event: form của cả M05 lẫn M08 đã có
`hx-target="#modal-root" hx-swap="innerHTML"` — trả về `HTMLResponse("", status_code=200)` (không có
`HX-Redirect`) sẽ tự động swap `#modal-root` thành rỗng → modal biến mất. Không cần thêm listener mới.

## Thiết kế fix

Thêm field `return_to` (giá trị `"redirect"` mặc định | `"stay"`) đi xuyên suốt GET (query param) →
form (hidden input) → POST/PATCH (Form field) → nhánh response. Backward compatible: caller không gửi
`return_to` → mặc định `"redirect"` → hành vi y hệt hiện tại.

Khi `return_to == "stay"`:
- Trả `HTMLResponse("", status_code=200)` — **không** có header `HX-Redirect`.
- Kèm header `HX-Trigger: '{"worklistRefresh": true}'` — vô hại nếu trang hiện tại không có phần tử
  nào lắng nghe event này (cockpit/S15 không có, worklist có).

## Files to modify

1. `crm/src/adapters/inbound/web/screens/modals/screen_modal_task.py`
2. `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py`
3. `crm/src/adapters/inbound/web/templates/fragments/modal_m05_create_task.html`
4. `crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html`
5. `crm/src/adapters/inbound/web/templates/fragments/worklist_fragment.html`
6. `crm/src/adapters/inbound/web/templates/worklist.html`
7. `crm/src/adapters/inbound/web/templates/fragments/_wl_row.html`
8. `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html`

## Implementation steps

### 1. `screen_modal_task.py` — 3 handler

**`get_modal_m05`** (dòng ~39-111): thêm param `return_to: str = "redirect"`, truyền vào context dict:
```python
"return_to": return_to,
```

**`patch_task_edit`** (dòng ~113-139): thêm param `return_to: str = Form("redirect")`. Thay khối cuối:
```python
redirect = f"/customers/{party_id}?tab=tasks" if party_id else "/tasks"
return Response(status_code=200, headers={"HX-Redirect": redirect})
```
thành:
```python
if return_to == "stay":
    return Response(status_code=200, headers={"HX-Trigger": '{"worklistRefresh": true}'})
redirect = f"/customers/{party_id}?tab=tasks" if party_id else "/tasks"
return Response(status_code=200, headers={"HX-Redirect": redirect})
```

**`post_task`** (dòng ~141-184): thêm param `return_to: str = Form("redirect")`. Thay dòng cuối
`return redirect_to_customer(party_id)` thành:
```python
if return_to == "stay":
    return HTMLResponse("", status_code=200, headers={"HX-Trigger": '{"worklistRefresh": true}'})
return redirect_to_customer(party_id)
```

### 2. `screen_customer_360_activity.py::handle_log_activity` (dòng ~221-386)

Thêm param:
```python
return_to: str = Form(default="redirect"),
```
Sửa khối trả về cuối (dòng ~375-386), giữ nguyên nhánh `source=call_cockpit` hiện có (dead nhưng vô
hại — không xóa để tránh phá test `test_quick_outcome_cockpit_post.py` đang assert HTML string của
nhánh này), thêm nhánh mới NGAY TRƯỚC dòng redirect cuối:
```python
if source.strip() == "call_cockpit":
    ...  # giữ nguyên
if return_to == "stay":
    return HTMLResponse("", status_code=200, headers={"HX-Trigger": '{"worklistRefresh": true}'})
return HTMLResponse(content="", headers={"HX-Redirect": f"/customers/{party_id}?tab=timeline"})
```

`_m08_ctx()` (dòng ~85-180) cần nhận và truyền `return_to` vào context dict trả về (thêm param
`return_to: str = "redirect"`, thêm `"return_to": return_to,` vào dict). Cả 2 GET handler
(`handle_modal_m08` dòng ~182-201, `handle_modal_log_activity` dòng ~203-219) thêm param
`return_to: str = "redirect"` và truyền xuống `_m08_ctx(...)`.

### 3. `modal_m05_create_task.html`

Đầu file, sau dòng 14 (`{% set due_time_val = ... %}`), thêm:
```jinja
{% set return_to = return_to | default('redirect') %}
```
Trong CẢ 2 nhánh `<form>` (dòng 38 edit_mode và dòng 41 create), ngay sau `<input type="hidden"
name="party_id" ...>`, thêm:
```html
<input type="hidden" name="return_to" value="{{ return_to }}">
```

### 4. `modal_log_activity.html`

Đầu file, cùng nhóm với các `{% set ... | default(...) %}` hiện có (dòng 5-26), thêm:
```jinja
{% set return_to = return_to | default('redirect') %}
```
Trong `<form>` (dòng 110), ngay sau `<input type="hidden" name="party_id" ...>` (dòng 111), thêm:
```html
{% if return_to != 'redirect' %}<input type="hidden" name="return_to" value="{{ return_to }}">{% endif %}
```
(Chỉ render khi khác default để không lẫn với `note`/`edit_activity` mode vốn có redirect riêng — giữ
nguyên hành vi các mode đó, chỉ mode `log` mới cần `stay`.)

### 5. Worklist container — lắng nghe `worklistRefresh`

`worklist.html` dòng 36 và `worklist_fragment.html` dòng 21, đổi:
```html
hx-trigger="claimSuccess from:body"
```
thành:
```html
hx-trigger="claimSuccess from:body, worklistRefresh from:body"
```
(Tiện thể kích hoạt luôn trigger `claimSuccess` vốn đã tồn tại nhưng chưa ai emit — không bắt buộc
sửa nơi emit nó, ngoài phạm vi phase này.)

### 6. Cập nhật các nơi GỌI M05/M08 cần `return_to=stay`

Trong `_wl_row.html`:
- Macro `contact_btn()` (dòng 26-49) — cả 4 nhánh `hx-get="/modals/m08?party_id={{ party_id }}&mode=contact_attempt..."`:
  thêm `&return_to=stay` vào URL.

Trong `worklist.html` dòng 25-30 (topbar "+ Tạo task"):
```html
hx-get="/modals/m05"
```
→
```html
hx-get="/modals/m05?return_to=stay"
```

Trong `_wl_row.html` dòng 288 (overdue "[📅 Dời hạn]"):
```html
hx-get="/modals/m05?task_id={{ t.task_id }}"
```
→
```html
hx-get="/modals/m05?task_id={{ t.task_id }}&return_to=stay"
```

Trong `c360_call_cockpit_panel.html`:
- Idbar "Tạo task" (dòng ~262): `htmx.ajax('GET','/modals/m05?party_id={{ party_id }}',...)` →
  thêm `&return_to=stay` vào URL string.
- Idbar "Zalo" (dòng ~256): `htmx.ajax('GET','/modals/m08?party_id={{ party_id }}&mode=log&hinh_thuc=chat',...)` →
  thêm `&return_to=stay`.
- R14 banner "Tạo task xác minh" (dòng ~311-313): `hx-get="/modals/m05?party_id={{ party_id }}&source=verify_account&prefill_title=..."` →
  thêm `&return_to=stay`.
- Rail "Đặt lịch" primary (dòng ~619) và secondary (dòng ~666) — JS build URL
  `'/modals/m05?party_id={{ party_id }}&source=action_queue&source_ref='+r+'&prefill_title='+t` →
  đổi thành `... + '&return_to=stay'`.
- `s14StripOpenManual()` (dòng ~1080-1083): `htmx.ajax('GET', '/modals/m08?party_id=' +
  encodeURIComponent(PARTY_ID) + '&mode=log&hinh_thuc=call', ...)` → thêm `&return_to=stay` vào URL.
- `s14StripOpenDetail()` (dòng ~1086-1091): tương tự, thêm `&return_to=stay`.

**KHÔNG sửa** (giữ `redirect` — đúng phạm vi, xem plan.md "Ngoài phạm vi"):
- `customer_360.html` topbar "Ghi log" (dòng 27) và "Task" (dòng 32) — caller LÀ S03, redirect về
  chính nó vô hại.
- `task_detail.html` (S15) "Sửa" (dòng 215) và closebar "Ghi log & hoàn thành" (dòng 472).

## Tests

- Chạy lại toàn bộ: `docker compose exec -T crm sh -c "cd /app/crm/src && python -m pytest -q"`.
- Đặc biệt: `test_quick_outcome_cockpit_post.py` (assert HTML string nhánh `source=call_cockpit` —
  không được đổi), `test_bulk_resolve_endpoint.py` (đếm số `@router.get`/`@router.post` đăng ký theo
  thứ tự — kiểm tra thêm param không phá thứ tự route registration).
- Thêm test mới (tùy chọn, khuyến nghị): 1 test cho `post_task` với `return_to=stay` → assert response
  status 200, header `HX-Trigger` chứa `worklistRefresh`, KHÔNG có header `HX-Redirect`. Tương tự cho
  `handle_log_activity` với `return_to=stay`.

## Verify thủ công (theo `/verify` skill)

1. Mở worklist, bấm 📞 quick-log trên 1 task row → Lưu → phải VẪN Ở worklist, thấy danh sách tự
   refresh (không có full page reload nhấp nháy giống redirect).
2. Vào cockpit 1 khách, bắt đầu gọi (T0→T1), bấm rail "Đặt lịch" → Lưu task → phải quay lại ĐÚNG
   cockpit đang gọi dở, timer vẫn chạy, draft vẫn còn (không reset về T0).
3. Từ S03 topbar bấm "Ghi log" → Lưu → vẫn về S03 tab timeline như cũ (không đổi hành vi).

## Risks / rollback

- Rủi ro thấp: thay đổi additive (param mới, default giữ nguyên hành vi cũ). Rollback = revert diff.
- Nếu 1 template quên thêm `&return_to=stay` → hành vi y hệt hiện tại (an toàn, không tệ hơn).

## Amendment (2026-07-11) — 2 gaps tìm thấy qua red-team review độc lập của `plans/260711-0838-worklist-claim-call-log-flow-fixes`

Một plan khác (`260711-0838`) chạy song song đã cover cùng 4 điểm P0 này, chạy qua adversarial
red-team (4 reviewer: Security/Failure-Mode/Assumption/Scope). Design của plan đó cho phase 1 kém hơn
(thread `caller`/`source` qua nhánh `source=call_cockpit` cũ) — plan này (`0933`) đúng hơn (đường
`return_to` độc lập, không đụng nhánh dead code). Nhưng 2 phát hiện của review đó vẫn áp dụng cho plan
này, verify lại trực tiếp trên code (không copy mù):

**Gap 1 — `s14StripOpenDetail()` call site's `return_to=stay` là no-op.** Call site này mở M08
`mode=edit_activity`, form submit qua `hx-patch="/api/activities/{activity_id}"` →
`handle_patch_activity` (`screen_customer_360_activity.py:533-588`) — verify lại (2026-07-11): handler
này KHÔNG có param `return_to` nào cả, và khi `edit_mode=="1"` luôn `return HTMLResponse(content="",
headers={"HX-Redirect": f"/customers/{activity.party_id}?tab=timeline"})` (dòng 586-587) vô điều kiện.
Thread `return_to=stay` vào GET call site này (mục 6, dòng ~172) sẽ tạo hidden field nhưng
`handle_patch_activity` không đọc — vẫn redirect như cũ. **Fix cần bổ sung**: thêm param `return_to:
str = Form(default="redirect")` vào `handle_patch_activity`, và khi `edit_mode=="1" and return_to ==
"stay"`: trả `HTMLResponse("", status_code=200, headers={"HX-Trigger": '{"activitySaved": true}'})`
thay vì redirect (giữ nguyên nhánh `edit_mode=="1"` mặc định `return_to=redirect` — hành vi cũ không
đổi). Thêm `handle_patch_activity` vào "Files to modify" mục 2 (`screen_customer_360_activity.py`) và
implementation steps.

**Gap 2 — worklist header "+ Tạo task" (no `party_id`) có thể đã 404 độc lập với fix này.**
`worklist.html:25-30`'s nút "+ Tạo task" gọi `hx-get="/modals/m05"` KHÔNG có `party_id`.
`modal_m05_create_task.html`'s field "Khách hàng" render `disabled`/không có picker khi `party_id`
rỗng → form vẫn `hx-post="/customers/{{ party_id }}/tasks"` → route thành `POST /customers//tasks`
(path segment rỗng). FastAPI/Starlette route matching mặc định KHÔNG match segment rỗng cho
`{party_id}` — plausibly 404 TRƯỚC KHI request chạm tới `return_to` logic của phase này. Đây là bug
tiền tồn tại (pre-existing), KHÔNG do phase 1 gây ra — nhưng verify thủ công mục 1 ("Bấm 📞/💬
quick-log... phải VẪN Ở worklist") KHÔNG cover case "+ Tạo task" cụ thể. Thêm vào "Verify thủ công":
**4. Bấm "+ Tạo task" ở worklist header (không chọn khách trước) → Lưu → xác nhận có 404 hay không.
Nếu có: đây là bug tiền tồn tại, KHÔNG thuộc scope phase 1 (không sửa route ở đây) — chỉ cần confirm
và document, không block phase 1 vì lý do này.** Nếu route thực ra hoạt động (có cơ chế picker chưa
được trace ở review này), bỏ qua ghi chú này.
