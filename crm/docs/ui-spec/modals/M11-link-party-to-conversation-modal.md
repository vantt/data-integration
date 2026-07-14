---
id: M11
type: modal
name: "Link Party to Conversation Modal"
platforms: [desktop]
hosted_by: [S06]
status: active
design_ref: ""
rules: [R5]
regions: [header, body, actions]
---

# M11 — Link Party to Conversation Modal

## Purpose

Resolve PSID → party cho hội thoại chưa có party_id (ST-CONV-NO-PARTY). CSKH tìm khách theo
SĐT/tên/email (FTS), chọn party phù hợp, xác nhận → thêm identity `type=psid` vào party được
chọn. Nếu không tìm thấy party, có thể tạo mới inline (mở M02).

## Layout

```yaml ui-layout
columns: [1fr]
areas:
  - [header]
  - [body]
  - [actions]
content:
  header:
    - row:
        - { h: "Tìm khách cho: PSID_abc" }
        - { btn: "✕", action: A-M11-001 }
  body:
    - input: "🔍 Tìm theo SĐT, tên, email..."
    - list: { item: "Nguyễn Văn A +84901234567 GOLD active", rows: 2 }
    - row:
        - { text: "Hoặc:" }
        - { btn: "+ Tạo khách mới", action: A-M11-006 }
  actions:
    - row:
        - { btn: "Hủy", action: A-M11-002 }
        - { btn: "Gắn khách đã chọn", action: A-M11-005, primary: true }
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Tìm khách cho: PSID_abc [x]                                               │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· [input: (?) Tìm theo SĐT, tên, email...] · list ×2 {Nguyễn Văn A +8490123…│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy] [Gắn khách đã chọn]                                                 │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## States

- default: Search empty, results empty
- searching: FTS query in-flight
- selected: One party highlighted
- submitting: Link save in-flight

## Interactions

```yaml crm-contract
interactions:
  - id: A-M11-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M11-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M11-003
    element: search_input
    region: body
    trigger: input
    action: mutate
    effects: [party_results.reload_fts]
  - id: A-M11-004
    element: party_result_row
    region: body
    trigger: click
    action: mutate
    effects: [selected_party.set]
  - id: A-M11-005
    element: btn_link_party
    region: actions
    trigger: click
    guard: "selected_party_id != null"
    action: mutate
    effects: [party_identity.add_psid, conversation.party_id.update, modal.close, ui.toast.show]
  - id: A-M11-006
    element: btn_create_new_party
    region: body
    trigger: click
    action: open_overlay
    target: M02
