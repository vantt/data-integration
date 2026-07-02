---
id: C01
type: component
name: "Sidebar Nav"
platforms: [desktop]
hosted_by: [S01, S02, S03, S04, S05, S06, S07, S08, S09, S10, S11, S12, S13]
status: active
design_ref: ""
rules: []
regions: []
---

# C01 — Sidebar Nav

## Purpose

Navigation sidebar cố định hiển thị trên mọi screen. Cung cấp links đến các section chính:
Worklist, Khách hàng, Inbox (badge unread), Tasks, Segments, Chiến dịch, Ads, Cài đặt.
Badge đỏ trên Inbox cập nhật qua SSE `chat.message.received`. Badge trên Dedup hiển thị
pending count. User info + logout ở cuối sidebar.

## Props / API

- `active_screen` (string, required): ID màn hình hiện tại để highlight active item
- `inbox_unread_count` (number): badge count cho Inbox nav item
- `dedup_pending_count` (number): badge count cho Dedup Review nav item

## States

- default: All items rendered, active item highlighted
- collapsed: (future) sidebar thu nhỏ chỉ icons

## Emits

```yaml crm-contract
emits:
  - id: A-C01-001
    element: nav_worklist
    trigger: click
    event: nav.item.selected
    payload: { target: "S01" }
  - id: A-C01-002
    element: nav_customers
    trigger: click
    event: nav.item.selected
    payload: { target: "S02" }
  - id: A-C01-003
    element: nav_inbox
    trigger: click
    event: nav.item.selected
    payload: { target: "S05" }
  - id: A-C01-004
    element: nav_tasks
    trigger: click
    event: nav.item.selected
    payload: { target: "S07" }
  - id: A-C01-005
    element: nav_segments
    trigger: click
    event: nav.item.selected
    payload: { target: "S08" }
  - id: A-C01-006
    element: nav_campaigns
    trigger: click
    event: nav.item.selected
    payload: { target: "S10" }
  - id: A-C01-007
    element: nav_ads
    trigger: click
    event: nav.item.selected
    payload: { target: "S12" }
  - id: A-C01-008
    element: nav_settings
    trigger: click
    event: nav.item.selected
    payload: { target: "S13" }
  - id: A-C01-009
    element: nav_dedup
    trigger: click
    event: nav.item.selected
    payload: { target: "S04" }
