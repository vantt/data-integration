---
id: S06
type: screen
name: "Conversation Detail"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R6, R12]
regions: [topbar, message_thread, input_bar, customer_sidebar]
---

# S06 — Conversation Detail

## Purpose

Xem toàn bộ thread tin nhắn của một hội thoại Messenger. CSKH đọc nội dung, link khách nếu PSID chưa
khớp, ghi note, đóng hội thoại. Sidebar phải hiển thị Customer 360 tóm tắt nếu party đã link
(tên, SĐT, value_group, action_queue ngắn gọn). v1 read-only — không gửi tin nhắn từ CRM.

## Layout

```
┌─ C01 SIDEBAR ─┬────────────────────────────────────┬───────────────────────┐
│               │  TOPBAR                             │  CUSTOMER SIDEBAR     │
│               │  [← Inbox]  PSID_abc  🟡 Pending   │  ┌─────────────────┐  │
│               │  Assignee: CSKH B  [Đổi NV]        │  │ Chưa link khách │  │
│               │  [Đóng hội thoại]  [Ghi note]       │  │ [🔍 Tìm khách]  │  │
│               ├────────────────────────────────────┤  └─────────────────┘  │
│               │  MESSAGE THREAD                     │  (sau khi link:)      │
│               │  ┌──────────────────────────────┐   │  ┌─────────────────┐  │
│               │  │ [Khách] "Tôi muốn hỏi..."    │   │  │ Nguyễn Văn A    │  │
│               │  │              10:32 ICT        │   │  │ GOLD · active   │  │
│               │  │ [NV] "Dạ, đơn số ..."        │   │  │ Mua gần: 3 ngày │  │
│               │  │              10:35 ICT        │   │  │ [Mở hồ sơ đầy] │  │
│               │  └──────────────────────────────┘   │  └─────────────────┘  │
│               │  INPUT BAR (disabled — read-only v1)│                       │
└───────────────┴────────────────────────────────────┴───────────────────────┘
```

## States

- ST-CONV-NO-PARTY: party_id=null → sidebar link-party CTA
- ST-CONV-CLOSED: status=closed → input disabled, re-open option
- ST-CONV-LOADING: Messages loading

## Interactions

```yaml crm-contract
interactions:
  - id: A-S06-001
    element: btn_back
    region: topbar
    trigger: click
    action: navigate
    target: S05
  - id: A-S06-002
    element: btn_close_conversation
    region: topbar
    trigger: click
    action: open_overlay
    target: M10
    payload: { conversation_id: "$conv.id" }
  - id: A-S06-003
    element: btn_log_note
    region: topbar
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$conv.party_id", conversation_id: "$conv.id" }
  - id: A-S06-004
    element: btn_change_assignee
    region: topbar
    trigger: click
    action: open_overlay
    target: M09
    payload: { conversation_id: "$conv.id" }
  - id: A-S06-005
    element: btn_link_party
    region: customer_sidebar
    trigger: click
    action: open_overlay
    target: M11
    payload: { conversation_id: "$conv.id" }
  - id: A-S06-006
    element: btn_open_full_profile
    region: customer_sidebar
    trigger: click
    action: navigate
    target: S03
    payload: { party_id: "$conv.party_id" }
  - id: A-S06-LSN01
    listens_to: chat.message.received
    action: mutate
    effects: [message_thread.append_message]
  - id: A-S06-LSN02
    listens_to: conversation.assigned
    action: mutate
    effects: [topbar.assignee.update]
