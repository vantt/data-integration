---
id: M08
type: modal
name: "Log Activity Modal"
platforms: [desktop]
hosted_by: [S03, S01, S06, S15, P02, P03, P04, P05]
status: active
design_ref: ""
rules: [R6]
regions: [header, contact_pref_banner, body, actions]
---

# M08 — Log Activity Modal

## Purpose

Ghi log activity (`crm_activity`) sau tương tác với khách, hoặc tạo/sửa note (`crm_note`).
Dùng từ Customer 360 (S03), Worklist (S01), Conversation Detail (S06), Tasks Panel (P04), các panels.

**Modes:**
- `log` (default): ghi crm_activity — hình thức → kênh → kết quả → follow-up → nội dung
- `note_only`: tạo crm_note mới
- `edit_note`: sửa crm_note đã có (cần `note_id`)

**URL signature:**
```
GET  /modals/m08?party_id=<id>&mode=log|note_only|edit_note
                &note_id=<id>        (edit_note only)
                &party_name=<str>    (display label)
                &task_id=<id>        (log mode — optional, từ P04)
```

## Contact Pref Banner

Nếu party có `crm_note.note_type='contact_pref'` và `pinned=true` → banner vàng nhạt trước form:

```
⚠ Lưu ý liên hệ: Chỉ nhắn Zalo sau 8pm, không nghe số lạ
```

## Layout

```yaml ui-layout
columns: [1fr]
areas:
  - [header]
  - [body]
  - [actions]
floating:
  - region: contact_pref_banner
    when: "party has crm_note(note_type='contact_pref', pinned=true)"
samples:
  header: "Ghi nhận tiếp xúc · Nguyễn Văn A [✕]"
  contact_pref_banner: "⚠ Lưu ý liên hệ: Chỉ nhắn Zalo sau 8pm, không nghe số lạ"
  body: "📋 Task: Follow-up sau cuộc gọi · HÌNH THỨC * [📞 Cuộc gọi ▾] · SỐ ĐIỆN THOẠI [● 0901234567 (chính)] [Dùng số khác] · KẾT QUẢ * [Đã nghe] [Không bắt] [Hẹn lại] [Từ chối] · NỘI DUNG [textarea] · THỜI GIAN [datetime ICT]  ĐƠN LIÊN QUAN [ORD-…]"
  actions: "[Hủy]  [Lưu hoạt động]"
elements:
  "✕": A-M08-001
  "Đã nghe": A-M08-005
  "Không bắt": A-M08-005
  "Hẹn lại": A-M08-005
  "Từ chối": A-M08-005
  "Hủy": A-M08-002
  "Lưu hoạt động": A-M08-003
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Ghi nhận tiếp xúc · Nguyễn Văn A [x]                                      │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· # Task: Follow-up sau cuộc gọi · HÌNH THỨC * [> Cuộc gọi v] · SỐ ĐIỆN THO…│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy]  [Lưu hoạt động]                                                    │
└────────────────────────────────────────────────────────────────────────────┘

[STOP variant — when: party has crm_note(note_type='contact_pref', pinned=true)]
┌────────────────────────────────────────────────────────────────────────────┐
│CONTACT_PREF_BANNER                                                         │
│when: party has crm_note(note_type='contact_pref', pinned=true)             │
│· ! Lưu ý liên hệ: Chỉ nhắn Zalo sau 8pm, không nghe số lạ                  │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## Layout — Mode: log (default)

6 bước tuần tự; các section phụ hiện/ẩn theo JS.

## Hình Thức & Outcome Sets

| Hình thức | Kênh hiện | Outcomes |
|-----------|-----------|----------|
| Cuộc gọi | SỐ ĐIỆN THOẠI | Đã nghe / Không bắt / Hẹn lại / Từ chối |
| Zalo | TÀI KHOẢN ZALO | Đã phản hồi / Chưa phản hồi / Không phản hồi |
| Facebook | TÀI KHOẢN FACEBOOK | Đã phản hồi / Chưa phản hồi / Không phản hồi |
| Email | ĐỊA CHỈ EMAIL | Đã phản hồi / Chưa phản hồi / Không phản hồi |
| Viếng thăm | _(không có)_ | Gặp được / Không gặp được |
| Khác | _(không có)_ | _(ẩn section kết quả)_ |

**Outcomes dương** (triggers Lên lịch theo dõi): `answered`, `met`, `replied`

## Outcome Enum (D2) — Phase 03

Field `contact_outcome` (DB column, replaces free-text `outcome` for new rows) uses structured per-channel enums.

### contact_outcome per channel_type

| channel_type | Enum values |
|---|---|
| `call` | `answered`, `no_answer`, `busy`, `wrong_number`, `callback`, `refused` |
| `zalo` / `fb` / `email` | `replied`, `no_reply`, `pending_reply`, `refused`, `blocked` |
| `visit` | `met`, `not_met` |

### outcome_reason values (D2 pilot)

`outcome_reason` is nullable. Required by server when `contact_outcome = 'refused'`. Optional but shown when `contact_outcome = 'answered'`.

> **Pilot note:** enum set is under field review — values may be extended or relabelled after 2-week NV field trial (design §8.3). Do not lock mart mappings until review is complete.

| Value | Label (VI) | Ghi chú |
|---|---|---|
| `budget` | Giá/ngân sách | |
| `wait_promo` | Chờ khuyến mãi | Khác `budget`: đủ tiền, chờ giá tốt → trigger liên hệ lại khi có promo |
| `timing` | Chưa tới lúc | Bận/để sau — không nói gì về lượng hàng còn |
| `still_stocked` | Chưa dùng hết | Lý do #1 replenishment call → điều chỉnh chu kỳ gợi ý mua lại |
| `product_fit` | Không hợp nhu cầu | |
| `irritation` | Kích ứng/không hợp da | Tín hiệu chất lượng → escalate; không upsell cùng dòng |
| `competitor` | Đã mua chỗ khác | |
| `stock` | Hết hàng | Phía mình hết hàng/chờ hàng |
| `trust` | Nghi ngại | |
| `no_need` | Hết nhu cầu | |
| `other` | Khác | |

> 3 giá trị `still_stocked` / `wait_promo` / `irritation` pre-seed 2026-07-06 theo kinh nghiệm CSKH mỹ phẩm (giảm dồn vào `other` trong pilot). Pilot review ~2026-07-20 vẫn giữ.

### 2-step UI flow (log mode)

1. Staff selects outcome pill → `contact_outcome` hidden input updated via `m08OnOutcome`.
2. If outcome is in `['refused', 'answered']` → LÝ DO section appears below outcome pills.
   - Label shows **"LÝ DO *"** (required) for `refused`, **"LÝ DO (tùy chọn)"** for `answered`.
   - Staff selects reason pill → `outcome_reason` hidden input updated via `m08OnReason`.
3. On submit: client validates `outcome_reason` is set when `contact_outcome = 'refused'` (alert + cancel). Server re-validates independently (returns HTTP 400 on violation).

## Bulk-Resolve Context (from S14) — phase-02

Khi M08 được mở từ outcome bar S14 (A-S14-009), caller truyền thêm hai query params:

| Param | Type | Description |
|-------|------|-------------|
| `resolve_action_ids` | `str` | Comma-separated action_id values — mỗi cái sẽ được dismiss sau khi log |
| `resolve_task_ids` | `str` | Comma-separated task_id values — mỗi cái sẽ được chuyển status→done |

GET handler forwarded → `_m08_ctx` → template context.

**Template effects:**
- Hai `<input type="hidden">` ẩn (name=`resolve_action_ids` / `resolve_task_ids`) trong `<form>`.
- Summary banner xanh nhạt hiện khi ít nhất một ID có mặt: `"✓ Sẽ đóng N task · M hành động"`.
- Banner chỉ hiện ở mode `log` (ẩn ở `edit_note` / `note_only`).

**POST behavior (A3):**
- `act_data["custom_fields"]` được ghi snapshot `{resolve_task_ids: [...], resolve_action_ids: [...]}` **trước** khi gọi `activity_log.log_activity()`.
- Sau đó `_bulk_resolve()` thực sự dismiss/close các IDs.

## Task Context Feature (khi `task_id` có)

- Hiển thị banner xanh nhạt: `📋 Task: "[task.title]"`
- Cuối form (trên footer): checkbox **"Đánh dấu task hoàn thành"**
- Default theo outcome:
  - `answered`, `met`, `replied`, `refused` → ☑ checked
  - `no_answer`, `callback`, `not_met`, `pending`, `no_reply` → ☐ unchecked
- NV có thể override
- Khi save + checkbox checked → `crm_task.status = done`, `completed_at = now`

## Layout — Mode: note_only / edit_note

## Save Effects

| Mode | POST endpoint | crm writes | Side effects |
|------|---------------|------------|--------------|
| `log` | `/customers/<party_id>/log-activity` | `crm_activity` (`contact_outcome`, `outcome_reason`) | timeline.reload; nếu callback → `crm_task` nhắc; nếu complete_task → task.done |
| `log` + `save_as_note=1` | same | `crm_activity` + `crm_note` | timeline.reload + notes.reload |
| `note_only` | `/customers/<party_id>/notes` | `crm_note` | notes.reload |
| `edit_note` | `/customers/<party_id>/notes/<note_id>` | `crm_note` UPDATE | notes.reload |

**D2 field notes:**
- `contact_outcome`: structured per-channel enum; server rejects unknown values.
- `outcome_reason`: nullable; server raises HTTP 400 when `contact_outcome='refused'` and `outcome_reason` is absent.
- `last_contact` snapshot uses `contact_outcome` (preferred) falling back to legacy `outcome`.

## States

- default: form pre-filled từ caller context
- submitting: save in-flight
- error: outcome chưa chọn (log mode) / nội dung trống (note mode)

## ICT Prefill

`occurred_at` pre-fill = ICT now. `callback_at` pre-fill = ICT now + 2h.
Tính bằng `Date.now() + 7*3600000` (UTC+7 offset hardcoded cho VN, per R6).

## Interactions

```yaml crm-contract
interactions:
  - id: A-M08-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M08-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M08-003
    element: btn_save
    region: actions
    trigger: click
    guard: "mode=='log' ? outcome!=null : form.body!=''"
    action: mutate
    effects: [activity_or_note.save, modal.close, ui.toast.show, timeline_or_notes.reload]
  - id: A-M08-004
    element: hinh_thuc_select
    region: body
    trigger: change
    guard: "mode == 'log'"
    action: mutate
    effects: [select_trigger.update_icon_label, channel_section.show_active, outcome_pills.rebuild, callback_sec.hide, body_placeholder.update]
  - id: A-M08-005
    element: outcome_pills
    region: body
    trigger: click
    guard: "mode == 'log'"
    action: mutate
    effects: [callback_sec.toggle, followup_sec.toggle, body_required.update, complete_task_checkbox.smart_default]
  - id: A-M08-006
    element: schedule_followup_checkbox
    region: body
    trigger: click
    action: mutate
    effects: [followup_date_opts.toggle]
  - id: A-M08-007
    element: save_as_note_checkbox
    region: body
    trigger: click
    action: mutate
    effects: [note_opts.toggle]
  - id: A-M08-008
    element: create_callback_task_checkbox
    region: body
    trigger: click
    guard: "outcome == 'callback'"
    action: mutate
    effects: [create_callback_task.toggle]
```

## Implementation Notes (Phase 06)

- **Item 2 — Promote insight (`★ Đúc kết`)**: collapsible `<details>` section appended in `mode=log` only. Fields: `insight_type` (select), `insight_body` (textarea), `insight_confidence` (low/medium/high radio pills), `promote_insight` hidden flag (0/1 toggled by `details.toggle` event). POST handler wires `party_insights` (`SQLitePartyRepository`, injected via `composition.py`) into `register_activity_routes`: when `promote_insight == "1"` and both `insight_type` and `insight_body` are non-empty, it calls `party_insights.add_insight(...)`, inserting a new row into `crm_party_insight` (party_id, insight_type, insight_body, insight_confidence, created_at). Wired as of commit `5dce0c37` — no longer a no-op. If `party_insights` were ever omitted from the factory call, the handler falls back to a warning log and silently skips (defensive, not the current runtime path).
