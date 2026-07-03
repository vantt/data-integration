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

```
┌ MODAL — Ghi nhận tiếp xúc ────────────────────────────────────────┐
│  Ghi nhận tiếp xúc · Nguyễn Văn A                           [✕]  │
├────────────────────────────────────────────────────────────────────┤
│  [banner contact_pref nếu có]                                     │
│                                                                    │
│  [task context banner nếu task_id có]                             │
│  📋 Task: "Follow-up sau cuộc gọi"                                │
│                                                                    │
│  HÌNH THỨC *                                                       │
│  [📞 Cuộc gọi                                              ▾]    │
│                                                                    │
│  SỐ ĐIỆN THOẠI  (section động theo hình thức)                     │
│  [● 0901234567 (chính)]  [Dùng số khác]                           │
│                                                                    │
│  KẾT QUẢ *  (set động theo hình thức)                             │
│  [Đã nghe] [Không bắt] [Hẹn lại] [Từ chối]                      │
│                                                                    │
│  [HẸN GỌI LẠI LÚC] — hiện nếu kết quả = Hẹn lại + call          │
│  [datetime-local]  ☑ Tạo task nhắc tự động                       │
│                                                                    │
│  [LÊN LỊCH THEO DÕI] — hiện nếu kết quả dương (Đã nghe/Gặp được/Đã phản hồi)
│  ☐ Lên lịch theo dõi → [date]  [+7 ngày] [+14 ngày] [+30 ngày]  │
│                                                                    │
│  NỘI DUNG  (placeholder + required thay đổi theo hình thức/kết quả)
│  [textarea]                                                        │
│                                                                    │
│  ☐ Lưu thành ghi chú hồ sơ — thông tin lâu dài, tách khỏi timeline
│    [LOẠI GHI CHÚ ▼]  [HIỂN THỊ ▼]  [GHIM ●/○]                  │
│                                                                    │
│  ──────────────────────────────────────────────────────────       │
│  THỜI GIAN                    ĐƠN LIÊN QUAN                       │
│  [datetime-local, ICT now]    [ORD-… tùy chọn]                   │
│                                                                    │
│  [☐/☑ Đánh dấu task "Follow-up…" hoàn thành] — chỉ khi task_id  │
├────────────────────────────────────────────────────────────────────┤
│  [Hủy]                                       [Lưu hoạt động]     │
└────────────────────────────────────────────────────────────────────┘
```

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

## Task Context Feature (khi `task_id` có)

- Hiển thị banner xanh nhạt: `📋 Task: "[task.title]"`
- Cuối form (trên footer): checkbox **"Đánh dấu task hoàn thành"**
- Default theo outcome:
  - `answered`, `met`, `replied`, `refused` → ☑ checked
  - `no_answer`, `callback`, `not_met`, `pending`, `no_reply` → ☐ unchecked
- NV có thể override
- Khi save + checkbox checked → `crm_task.status = done`, `completed_at = now`

## Layout — Mode: note_only / edit_note

```
┌ MODAL — Thêm ghi chú / Sửa ghi chú ──────────────────────────────┐
│  [title] · [party_name]                                      [✕]  │
├────────────────────────────────────────────────────────────────────┤
│  LOẠI GHI CHÚ  [Chung ▼]                                          │
│  -- Chung / Sở thích / Ưu tiên liên lạc / Cảnh báo / Kết quả /  │
│     Nội bộ                                                         │
│                                                                    │
│  NỘI DUNG *                                                        │
│  [textarea]                                                        │
│                                                                    │
│  GHIM GHI CHÚ  [● Không ghim  ○ Ghim]                            │
│                                                                    │
│  HIỂN THỊ  [Team ▼]  (Team / Manager / Riêng tư)                 │
├────────────────────────────────────────────────────────────────────┤
│  [Hủy]                                         [Lưu ghi chú]     │
└────────────────────────────────────────────────────────────────────┘
```

## Save Effects

| Mode | POST endpoint | crm writes | Side effects |
|------|---------------|------------|--------------|
| `log` | `/customers/<party_id>/log-activity` | `crm_activity` | timeline.reload; nếu callback → `crm_task` nhắc; nếu complete_task → task.done |
| `log` + `save_as_note=1` | same | `crm_activity` + `crm_note` | timeline.reload + notes.reload |
| `note_only` | `/customers/<party_id>/notes` | `crm_note` | notes.reload |
| `edit_note` | `/customers/<party_id>/notes/<note_id>` | `crm_note` UPDATE | notes.reload |

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
