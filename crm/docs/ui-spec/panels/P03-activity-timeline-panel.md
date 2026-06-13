---
id: P03
type: panel
name: "Activity Timeline Panel"
platforms: [desktop]
hosts: [S03]
status: active
design_ref: ""
rules: [R6]
regions: [toolbar, timeline]
---

# P03 — Activity Timeline Panel

## Purpose

Panel tab "Timeline" trong Customer 360 (S03). Hiển thị tất cả activity (`crm_activity`) +
task completed gắn party này, sort `occurred_at` DESC (ICT display). Activity types: call, note,
visit, email, chat, other. Chat activity được tạo tự động khi đóng conversation. NV có thể thêm
activity thủ công (ghi log cuộc gọi, ghi chú nhanh) từ toolbar.

## Layout

```
┌ TOOLBAR ──────────────────────────────────────────────────────────┐
│  Activity Timeline   [+ Ghi log]  [Filter type ▼]                │
├ TIMELINE ─────────────────────────────────────────────────────────┤
│                                                                    │
│  ● 13/06/2026 10:32 ICT  [call]                                   │
│    NV A: "Khách xác nhận sẽ đặt tuần tới. Gợi ý SP mới."        │
│    Đơn liên quan: —                                               │
│                                                                    │
│  ● 01/06/2026 15:00 ICT  [chat]                                   │
│    CSKH B: Đóng conversation PSID_abc — "Đã giải quyết"          │
│                                                                    │
│  ● 15/05/2026 09:00 ICT  [note]                                   │
│    NV C: "Khách thích SP X, không thích chiết khấu thấp"         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## States

- ST-LOADING: Timeline fetch in-flight
- ST-EMPTY: Chưa có activity nào → "Chưa có hoạt động nào. Ghi log đầu tiên."

## Interactions

```yaml crm-contract
interactions:
  - id: A-P03-001
    element: btn_log_activity
    region: toolbar
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$party.id" }
  - id: A-P03-002
    element: filter_type
    region: toolbar
    trigger: change
    action: mutate
    effects: [timeline.reload_filtered]
  - id: A-P03-003
    element: activity_chat_link
    region: timeline
    trigger: click
    action: navigate
    target: S06
    payload: { conversation_id: "$activity.conversation_id" }
