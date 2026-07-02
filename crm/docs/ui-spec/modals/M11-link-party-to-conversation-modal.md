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

```
┌ MODAL — Gắn khách vào hội thoại ──────────────────┐
│  Tìm khách cho: PSID_abc                     [✕]  │
├────────────────────────────────────────────────────┤
│  [🔍 Tìm theo SĐT, tên, email...]                │
│  ┌──────────────────────────────────────────────┐  │
│  │ Nguyễn Văn A   +84901234567   GOLD   active  │  │
│  │ Nguyễn Văn An  +84909876543   NEW    active  │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  Hoặc: [+ Tạo khách mới]                         │
├────────────────────────────────────────────────────┤
│  [Hủy]                      [Gắn khách đã chọn]  │
└────────────────────────────────────────────────────┘
```

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
