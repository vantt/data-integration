---
id: S10
type: screen
name: "Campaigns List"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R1, R10]
regions: [topbar, sidebar, campaign_list]
---

# S10 — Campaigns List

## Purpose

Manager xem danh sách tất cả chiến dịch reactivation/winback/upsell (`crm_campaign`). Mỗi row:
tên, objective, channel, segment gắn, tổng target, converted count, conversion rate, trạng thái.
Manager tạo campaign mới từ đây, hoặc nhấn vào campaign để xem chi tiết/target list.

## Layout

```
┌─ C01 SIDEBAR ─┬──────────────────────────────────────────────────────────────┐
│               │  TOPBAR: Chiến dịch   [+ Tạo chiến dịch]  [Filter status ▼] │
│               ├──────────────────────────────────────────────────────────────┤
│               │  CAMPAIGN LIST                                               │
│               │  ┌──────────────────────────────────────────────────────── │
│               │  │ Tên              Obj.       Targets  Converted  Rate     │
│               │  ├────────────────────────────────────────────────────────  │
│               │  │ Win-back Q3      winback    87       13         14.9%    │
│               │  │ React-Jul-2026   react.     34       0          —        │
│               │  │ Upsell VIP tháng upsell     22       5          22.7%    │
│               │  └──────────────────────────────────────────────────────── │
└───────────────┴──────────────────────────────────────────────────────────────┘
```

## States

- ST-CAMPAIGN-EMPTY: Chưa có campaign nào → CTA tạo đầu tiên
- ST-LOADING: List loading

## Interactions

```yaml crm-contract
interactions:
  - id: A-S10-001
    element: btn_create_campaign
    region: topbar
    trigger: click
    action: open_overlay
    target: M07
  - id: A-S10-002
    element: campaign_row
    region: campaign_list
    trigger: click
    action: navigate
    target: S11
    payload: { campaign_id: "$campaign.id" }
  - id: A-S10-003
    element: filter_status
    region: topbar
    trigger: change
    action: mutate
    effects: [campaign_list.reload]
  - id: A-S10-LSN01
    listens_to: filter_bar.changed
    action: mutate
    effects: [campaign_list.reload_with_filters]
  - id: A-S10-LSN02
    listens_to: filter_bar.cleared
    action: mutate
    effects: [campaign_list.reload]
