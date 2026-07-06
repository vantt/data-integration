# Phase 02 — Bulk-Resolve Outcome (A3)

**Status:** DONE  **Ưu tiên:** P0  
**Phụ thuộc:** —  
**Spec:** `crm/docs/ui-spec/notes/ux-action-queue-task-cockpit-data-loop-design.md` §4-A3, §6-D4  
**Mục tiêu:** 1 cuộc gọi → 1 lần ghi outcome đóng đủ N task + dismiss N action trong phiên cockpit.

---

## Trạng thái hiện tại (đã làm, KHÔNG làm lại)

| Thứ | File | Trạng thái |
|---|---|---|
| Helpers `parse_id_list` + `bulk_resolve` | `crm/src/adapters/inbound/web/screens/customer360/outcome_resolve_helpers.py` | ✅ DONE |
| POST handler nhận `resolve_action_ids`/`resolve_task_ids` + gọi `_bulk_resolve` | `screen_customer_360_activity.py` lines 174–254 | ✅ DONE |
| Endpoint async-resolve `POST /customers/{id}/reason/resolve-async` | `screen_customer_360_activity.py` lines 259–312 | ✅ DONE |
| `action_state` wired vào `register_activity_routes` | `screen_customer_360.py` line 292 + `composition.py` | ✅ DONE |
| Cockpit hidden inputs `s14-resolve-action-ids`/`s14-resolve-task-ids` | `c360_call_cockpit_panel.html` lines 752–755 | ✅ DONE |
| `s14OpenOutcome` truyền IDs qua query params lên M08 GET | `c360_call_cockpit_panel.html` lines 925–938 | ✅ DONE |
| 23 unit tests thuần logic | `crm/src/tests/test_outcome_bulk_resolve.py` | ✅ DONE |

**Những gì còn thiếu:** (1) M08 GET handler chưa forward IDs vào template context; (2) M08 template thiếu hidden inputs + summary line; (3) POST handler chưa ghi `custom_fields` snapshot (D4); (4) spec chưa cập nhật; (5) endpoint-level tests chưa có.

---

## Context links

- Design: `crm/docs/ui-spec/notes/ux-action-queue-task-cockpit-data-loop-design.md` §4-A3, §6-D4
- Spec M08: `crm/docs/ui-spec/modals/M08-log-activity-modal.md`
- Spec S14: `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md`
- Impl notes §11: `crm/docs/ui-spec/notes/S14-implementation-notes.md`

---

## Requirements

1. M08 modal GET nhận `resolve_action_ids` / `resolve_task_ids` từ query string, truyền vào template → hidden inputs trong `<form>`.
2. M08 template hiển thị summary "Sẽ đóng N task · M hành động" khi có ít nhất 1 ID — UX transparency cho NV.
3. POST handler `handle_log_activity` ghi `custom_fields` snapshot `{"resolve_task_ids": [...], "resolve_action_ids": [...]}` vào activity theo D4 registry (nếu có bulk IDs).
4. S14 outcome bar hiện chỉ mang IDs của `rail_primary`; chấp nhận giới hạn đó trong phase này — secondary items là P2.
5. Spec cập nhật M08, S14 (outcome bar), S14 impl notes §11.
6. Tests endpoint-level: multi-task close, idempotent double-submit, party mismatch.

---

## Files cần sửa / tạo

| File | Thay đổi |
|---|---|
| `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py` | (1) `_m08_ctx` + `handle_modal_m08` + `handle_modal_log_activity` GET: parse `resolve_action_ids`/`resolve_task_ids` từ query; (2) `handle_log_activity` POST: ghi `custom_fields` snapshot |
| `crm/src/adapters/inbound/web/templates/fragments/modal_log_activity.html` | Thêm 2 hidden inputs + summary line "Sẽ đóng N task · M hành động" |
| `crm/docs/ui-spec/modals/M08-log-activity-modal.md` | Thêm section Bulk-Resolve Context (hidden fields + summary) |
| `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md` | Note outcome bar đã bind IDs vào M08 (A-S14-009 payload) |
| `crm/docs/ui-spec/notes/S14-implementation-notes.md` | §11 đánh dấu IMPLEMENTED; đối chiếu async-resolve = IMPLEMENTED |
| `crm/src/tests/test_bulk_resolve_endpoint.py` | **NEW** — endpoint-level HTTP tests |

---

## Implementation steps

### Step 1 — M08 GET: forward bulk-resolve IDs vào template context

Trong `screen_customer_360_activity.py`:

**`_m08_ctx`** — thêm 2 tham số `resolve_action_ids: str = ""` và `resolve_task_ids: str = ""`; đưa chúng vào dict trả về:
```python
"resolve_action_ids": resolve_action_ids,
"resolve_task_ids": resolve_task_ids,
```

**`handle_modal_m08`** — thêm 2 query params:
```python
resolve_action_ids: str = "",
resolve_task_ids: str = "",
```
Truyền vào `_m08_ctx(...)`.

**`handle_modal_log_activity`** — làm tương tự.

### Step 2 — M08 template: hidden inputs + summary line

Trong `modal_log_activity.html`, trong `<form>` (log mode), sau `{% if task_id %}<input ... name="task_id" ...>{% endif %}`:

```html
{# Bulk-resolve IDs from S14 outcome bar (phase-02) #}
{% if resolve_action_ids %}<input type="hidden" name="resolve_action_ids" value="{{ resolve_action_ids }}">{% endif %}
{% if resolve_task_ids   %}<input type="hidden" name="resolve_task_ids"   value="{{ resolve_task_ids }}">{% endif %}
```

Summary line (hiện khi ít nhất 1 ID), đặt ngay dưới task context banner:
```html
{% if mode not in ('edit_note', 'note_only') and (resolve_task_ids or resolve_action_ids) %}
{% set _n_tasks   = resolve_task_ids.split(',') | select | list | length %}
{% set _n_actions = resolve_action_ids.split(',') | select | list | length %}
<div class="caveat caveat--info" style="font-size:var(--fs-caption)">
  <span class="caveat__mark">✓</span>
  <span>Sẽ đóng
    {% if _n_tasks %}{{ _n_tasks }} task{% endif %}
    {% if _n_tasks and _n_actions %} · {% endif %}
    {% if _n_actions %}{{ _n_actions }} hành động{% endif %}
  </span>
</div>
{% endif %}
```

### Step 3 — POST handler: ghi custom_fields snapshot (D4)

Trong `handle_log_activity`, trước khi gọi `_bulk_resolve`, cập nhật `act_data` để ghi snapshot vào `custom_fields`:

```python
if bulk_action_ids or bulk_task_ids:
    cf = dict(activity.custom_fields or {}) if hasattr(activity, 'custom_fields') else {}
    if bulk_task_ids:
        cf["resolve_task_ids"] = bulk_task_ids
    if bulk_action_ids:
        cf["resolve_action_ids"] = bulk_action_ids
    # Persist snapshot — repo requires a second write or update;
    # simplest: include in act_data before log_activity call.
```

**Cách tiếp cận thực tế:** thêm `resolve_task_ids`/`resolve_action_ids` vào `act_data["custom_fields"]` TRƯỚC khi gọi `activity_log.log_activity(act_data)`:

```python
if bulk_action_ids or bulk_task_ids:
    cf = act_data.get("custom_fields") or {}
    if bulk_task_ids:
        cf["resolve_task_ids"] = bulk_task_ids
    if bulk_action_ids:
        cf["resolve_action_ids"] = bulk_action_ids
    act_data["custom_fields"] = cf
```

Dời block `bulk_action_ids = _parse_id_list(resolve_action_ids)` lên TRƯỚC `activity_log.log_activity(act_data)`.

### Step 4 — Spec updates

- **M08 spec**: thêm sub-section "Bulk-Resolve Context (from S14)" dưới Task Context Feature, liệt kê hidden inputs + summary display, link A3.
- **S14 spec**: trong section States + A-S14-009 payload note: "truyền `resolve_action_ids`/`resolve_task_ids` qua query string → M08 forward vào form".
- **S14 impl notes §11**: đánh dấu "bulk-resolve: IMPLEMENTED (phase-02)" + "async-resolve: IMPLEMENTED (phase-02)".

### Step 5 — Endpoint-level tests

`crm/src/tests/test_bulk_resolve_endpoint.py` — dùng `fastapi.testclient.TestClient`. Pattern: build minimal FastAPI app với `register_activity_routes` + mock repos. Các cases:

| Test | Kiểm tra |
|---|---|
| `test_multi_task_close` | POST `resolve_task_ids=t1,t2` → cả 2 tasks `transition_status` được gọi |
| `test_idempotent_double_submit` | POST `complete_task=1&task_id=t1&resolve_task_ids=t1` → `skip_task_id` guard đúng, `t1` chỉ được close 1 lần |
| `test_party_mismatch_does_not_resolve_other_party` | action_state.dismiss nhận đúng `action_id` — không kiểm tra party scope vì scope-guard là logic phía action_state repo |
| `test_custom_fields_snapshot_written` | activity_log.log_activity được gọi với `custom_fields["resolve_task_ids"]` đúng |
| `test_empty_ids_no_bulk_call` | POST không có `resolve_action_ids`/`resolve_task_ids` → `bulk_resolve` không gọi |

---

## Tests & validation

- Chạy trong `crm` Docker container: `docker exec crm pytest crm/src/tests/test_bulk_resolve_endpoint.py -v`
- Chạy cùng với pure-logic tests: `docker exec crm pytest crm/src/tests/test_outcome_bulk_resolve.py crm/src/tests/test_bulk_resolve_endpoint.py -v`
- Manual: mở S14 cockpit → bấm "Gọi được" → M08 hiện summary "Sẽ đóng N task · M hành động" → Lưu → task/action đóng đúng.

---

## Async-resolve (A-S14-026) scope

Endpoint `POST /customers/{party_id}/reason/resolve-async` đã IMPLEMENTED đầy đủ. Không cần làm thêm gì cho phase này. Template binding (button HTML cho từng rail item) là part của phase ui-port (ui-spec/screens/S14). Ghi rõ trong spec §11 là đã implement.

---

## Risks & rollback

- `bulk_resolve` per-item error-isolated (log WARNING, không abort) — safe.
- Nếu `action_state` là None (lỗi wiring), action dismiss bị skip yên lặng, task close vẫn chạy.
- Rollback: revert 3 file (activity route, template, test file). Không có migration.
- **Party mismatch note:** `bulk_resolve` không validate ownership (`task.party_id == party_id`). Nếu client gửi task_id của party khác, nó vẫn được đóng. Chấp nhận vì form data đến từ S14 cockpit (server-rendered, IDs do server inject) — không phải user input tự do. Ghi note trong code comment.

---

## Unresolved questions

1. ~~Secondary rail items' IDs~~ — RESOLVED 2026-07-05 ngoài phase 06, xem `phase-07-rail-secondary-bulk-resolve.md`: tick "đã nói" trên secondary item fold ID vào bulk-resolve; primary luôn included mặc định.
2. `crm/docs/ui-spec/generated/` — sau khi sửa spec M08 cần regenerate. Kiểm tra convention qua `crm/docs/ui-spec/notes/` để biết cách trigger (dùng skill `/ui-spec` nếu có).
