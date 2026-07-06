---
id: P06
type: panel
name: "Conversations Panel"
platforms: [desktop]
hosted_by: [S03]
status: active
design_ref: ""
rules: [R6, R12]
regions: [toolbar, conv_list]
---

# P06 — Conversations Panel

## Purpose

Panel tab "Chat" trong Customer 360 (S03). Hiển thị tất cả `crm_conversation` gắn party này
(qua party_id), sort `last_message_at` DESC (ICT). NV có thể mở conversation detail (S06) để xem
toàn bộ thread. v1 read-only — chỉ ingest + hiển thị (R12).

## Layout

```yaml ui-layout
areas:
  - [toolbar]
  - [conv_list]
samples:
  toolbar: "Hội thoại (Messenger)  [Filter: status ▼]"
  conv_list: "Messenger • 13/06/2026 10:30 ICT • CSKH B • closed · Đã giải quyết thắc mắc về đơn hàng [Xem →]"
elements:
  "Filter: status ▼": A-P06-002
  "Xem →": A-P06-001
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│TOOLBAR                                                                     │
│· Hội thoại (Messenger)  [Filter: status v]                                 │
├────────────────────────────────────────────────────────────────────────────┤
│CONV_LIST                                                                   │
│· Messenger • 13/06/2026 10:30 ICT • CSKH B • closed · Đã giải quyết thắc m…│
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## States

- ST-LOADING: Conversations fetch in-flight
- ST-EMPTY: Chưa có hội thoại nào gắn khách này

## Interactions

```yaml crm-contract
interactions:
  - id: A-P06-001
    element: conv_view_btn
    region: conv_list
    trigger: click
    action: navigate
    target: S06
    payload: { conversation_id: "$conv.id" }
  - id: A-P06-002
    element: filter_status
    region: toolbar
    trigger: change
    action: mutate
    effects: [conv_list.reload_filtered]
