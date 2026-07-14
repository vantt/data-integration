---
id: S05
type: screen
name: "Inbox (Conversations)"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R6, R12]
regions: [topbar, sidebar, conv_list, preview_pane]
---

# S05 — Inbox (Conversations)

## Purpose

CSKH dùng màn hình này để xử lý hội thoại Messenger inbound. Inbox hiển thị tất cả conversation
từ `crm_conversation` lọc theo assignee/status. Badge unread_count nổi bật. CSKH chọn hội thoại
→ mở Conversation Detail (S06). Có thể gán NV xử lý trực tiếp từ list.

PSID chưa link party → badge amber "Chưa link khách" để CSKH ưu tiên xử lý.
SSE cập nhật real-time khi có tin nhắn mới hoặc conversation được gán.

## Layout

```yaml ui-layout
columns: [1fr, 2fr, 3fr]
areas:
  - [sidebar, topbar, topbar]
  - [sidebar, conv_list, preview_pane]
content:
  sidebar:
    - slot: "C01 Sidebar Nav (global)"
  topbar:
    - row:
        - { h: "Inbox" }
        - { select: "All" }
        - { tabs: ["Open", "Pending", "Closed"], action: A-S05-002 }
        - { btn: "Gán cho tôi", action: A-S05-004 }
  conv_list:
    - list: { item: '● PSID_abc 🟡 Chưa link khách · "Hỏi đơn hàng" · 2 phút trước', rows: 5 }
  preview_pane:
    - text: "Chọn một hội thoại để xem nội dung"
```

<!-- ui-layout:ascii:start -->
```
┌────────────┬───────────────────────────────────────────────────────────────┐
│SIDEBAR     │TOPBAR                                                         │
│· <<C01 Sid…│· Inbox [All v] | Open || Pending || Closed | [Gán cho tôi]    │
│            ├────────────────────────┬──────────────────────────────────────┤
│            │CONV_LIST               │PREVIEW_PANE                          │
│            │· list ×5 {o PSID_abc ?…│· Chọn một hội thoại để xem nội dung  │
└────────────┴────────────────────────┴──────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## States

- ST-INBOX-EMPTY: Không có conversation trong filter hiện tại
- ST-INBOX-UNRESOLVED-PSID: Conversation party_id=null → amber badge
- ST-LOADING: List loading

## Interactions

```yaml crm-contract
interactions:
  - id: A-S05-001
    element: conv_row
    region: conv_list
    trigger: click
    action: navigate
    target: S06
    payload: { conversation_id: "$conv.id" }
  - id: A-S05-002
    element: filter_status
    region: topbar
    trigger: change
    action: mutate
    effects: [conv_list.reload]
  - id: A-S05-003
    element: filter_assignee
    region: topbar
    trigger: change
    action: mutate
    effects: [conv_list.reload]
  - id: A-S05-004
    element: btn_assign_to_me
    region: topbar
    trigger: click
    action: mutate
    effects: [filter_assignee.set_current_user, conv_list.reload]
  - id: A-S05-005
    element: conv_assign_btn
    region: conv_list
    trigger: click
    action: open_overlay
    target: M09
    payload: { conversation_id: "$conv.id" }
  - id: A-S05-LSN01
    listens_to: chat.message.received
    action: mutate
    effects: [conv_list.update_unread, conv_list.reorder_by_recency]
  - id: A-S05-LSN02
    listens_to: conversation.assigned
    action: mutate
    effects: [conv_list.update_assignee]
  - id: A-S05-LSN03
    listens_to: filter_bar.changed
    action: mutate
    effects: [conv_list.reload_with_filters]
  - id: A-S05-LSN04
    listens_to: filter_bar.cleared
    action: mutate
    effects: [conv_list.reload]
