---
id: S03
type: screen
name: "Customer 360 Detail"
platforms: [desktop]
hosts: [P01, P02, P03, P04, P05, P06]
status: active
design_ref: ""
rules: [R2, R3, R6, R7]
regions: [topbar, left_col, right_col, tab_bar]
---

# S03 — Customer 360 Detail

## Purpose

Hồ sơ đầy đủ 360° của một party. Sales Rep mở màn hình này trước khi gọi điện để nắm:
thông tin cơ bản, insight warehouse (RFM, affinity, action_queue), lịch sử đơn hàng, tags, ghi chú cũ,
task đang mở, và activity timeline.

Layout 2 cột: cột trái = thông tin tĩnh (profile, identity, tags, custom fields, owner);
cột phải = tab bar chứa các panel động (Insight P01, Đơn hàng P02, Timeline P03, Tasks P04, Ghi chú P05, Hội thoại P06).

Target: point-lookup ≤ 200ms (view `crm_party_360`). `refreshed_at` hiển thị tại P01.

## Layout

```
┌─ C01 SIDEBAR ─┬──────────────────────────────────────────────────────────────┐
│               │  TOPBAR: [← Quay lại]  Nguyễn Văn A  GOLD · active          │
│               │  SĐT: 0901234567  |  Owner: NV A  |  [Gán NV ▼]  [+ Tag]    │
│               ├──────────────────────────────────────────────────────────────┤
│               │  LEFT COL (30%)           │  RIGHT COL (70%)                 │
│               │  ┌─────────────────────┐  │  [Insight|Đơn|Timeline|Tasks|   │
│               │  │ Thông tin cơ bản    │  │   Ghi chú|Chat]                 │
│               │  │ Tên: Nguyễn Văn A   │  │                                 │
│               │  │ SĐT: +84901234567   │  │  (P01 / P02 / P03 / P04 /      │
│               │  │ Email: —            │  │   P05 / P06 shown here)         │
│               │  │ Sapo ID: 12345      │  │                                 │
│               │  ├─────────────────────┤  │                                 │
│               │  │ Tags: [VIP] [repeat]│  │                                 │
│               │  │ Custom fields...    │  │                                 │
│               │  │ Consent: ✓          │  │                                 │
│               │  └─────────────────────┘  │                                 │
└───────────────┴──────────────────────────────────────────────────────────────┘
```

## States

- ST-360-LOADING: Point-lookup in-flight
- ST-360-NO-PROFILE: Profile chưa tạo → CTA "Tạo hồ sơ"
- ST-360-NO-INSIGHT: Insight chưa có trong cache → placeholder + refreshed_at
- ST-360-MERGED: Party is_merged=true → warning banner + link to surviving party

## Interactions

```yaml crm-contract
interactions:
  - id: A-S03-001
    element: btn_back
    region: topbar
    trigger: click
    action: navigate
    target: S02
  - id: A-S03-002
    element: btn_assign_owner
    region: topbar
    trigger: click
    action: open_overlay
    target: M04
    payload: { party_id: "$party.id" }
  - id: A-S03-003
    element: btn_add_tag
    region: topbar
    trigger: click
    action: open_overlay
    target: M03
    payload: { party_id: "$party.id" }
  - id: A-S03-004
    element: tab_insight
    region: tab_bar
    trigger: click
    action: mutate
    effects: [right_col.show_panel_P01]
  - id: A-S03-005
    element: tab_orders
    region: tab_bar
    trigger: click
    action: mutate
    effects: [right_col.show_panel_P02]
  - id: A-S03-006
    element: tab_timeline
    region: tab_bar
    trigger: click
    action: mutate
    effects: [right_col.show_panel_P03]
  - id: A-S03-007
    element: tab_tasks
    region: tab_bar
    trigger: click
    action: mutate
    effects: [right_col.show_panel_P04]
  - id: A-S03-008
    element: tab_notes
    region: tab_bar
    trigger: click
    action: mutate
    effects: [right_col.show_panel_P05]
  - id: A-S03-009
    element: tab_chat
    region: tab_bar
    trigger: click
    action: mutate
    effects: [right_col.show_panel_P06]
  - id: A-S03-010
    element: btn_edit_custom_fields
    region: left_col
    trigger: click
    action: open_overlay
    target: M06
    payload: { party_id: "$party.id" }
  - id: A-S03-011
    element: btn_log_activity
    region: topbar
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$party.id" }
  - id: A-S03-012
    element: btn_create_task
    region: topbar
    trigger: click
    action: open_overlay
    target: M05
    payload: { party_id: "$party.id" }
  - id: A-S03-LSN01
    listens_to: cache.refreshed
    action: mutate
    effects: [P01.insight.reload]
  - id: A-S03-LSN02
    listens_to: party.merged
    action: mutate
    effects: [topbar.merged_banner.show]
  - id: A-S03-LSN03
    listens_to: tag_chips.add_requested
    action: open_overlay
    target: M03
    payload: { party_id: "$event.party_id" }
  - id: A-S03-LSN04
    listens_to: tag_chips.remove_requested
    action: mutate
    effects: [party_tag.remove, tags_display.reload]
  - id: A-S03-LSN05
    listens_to: tag_chips.chip_clicked
    action: mutate
    effects: [ui.tag_filter.set]
```
