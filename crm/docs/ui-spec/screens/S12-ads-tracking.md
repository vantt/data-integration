---
id: S12
type: screen
name: "Ads Tracking"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R2, R6]
regions: [topbar, sidebar, ad_campaign_list, stats_panel]
---

# S12 — Ads Tracking

## Purpose

Theo dõi hiệu quả quảng cáo Facebook Ads: spend theo ngày (`crm_ad_spend`), lead từ Messenger
ad-referral (`crm_ad_lead`), attribution last-touch (`crm_ad_attribution`). Dữ liệu ingest từ
Python FB Ads API job — warehouse không có module này.

Manager xem KPI: CPC, CPL, revenue attributed per ad campaign. Nhấn vào ad campaign để xem
danh sách lead và attribution chi tiết.

## Layout

```
┌─ C01 SIDEBAR ─┬──────────────────────────────────────────────────────────────┐
│               │  TOPBAR: Ads Tracking  [Date range ▼]  [Ad platform ▼]      │
│               ├──────────────────────────────────────────────────────────────┤
│               │  AD CAMPAIGN LIST                      STATS PANEL           │
│               │  ┌──────────────────────────────────┐  ┌──────────────────┐  │
│               │  │ Summer-2026                       │  │ Tổng spend:      │  │
│               │  │  Spend: 5.200.000đ                │  │ 12.300.000đ      │  │
│               │  │  Leads: 42   Converted: 8         │  │ Tổng leads: 87   │  │
│               │  │  CPC: 123.800đ  CPL: 238.000đ    │  │ Conversion: 9.2% │  │
│               │  ├──────────────────────────────────┤  │ Revenue attr:    │  │
│               │  │ Brand-June-2026                   │  │ 48.000.000đ      │  │
│               │  │  Spend: 7.100.000đ                │  └──────────────────┘  │
│               │  └──────────────────────────────────┘                         │
│               │  refreshed_at: hôm nay 08:12 ICT                             │
└───────────────┴──────────────────────────────────────────────────────────────┘
```

## States

- ST-ADS-NO-DATA: Chưa có data ingest → hướng dẫn chạy Python job
- ST-STALE-CACHE: refreshed_at > 24h → yellow badge
- ST-LOADING: Data loading

## Interactions

```yaml crm-contract
interactions:
  - id: A-S12-001
    element: ad_campaign_row
    region: ad_campaign_list
    trigger: click
    action: mutate
    effects: [stats_panel.load_campaign_detail]
  - id: A-S12-002
    element: filter_date_range
    region: topbar
    trigger: change
    action: mutate
    effects: [ad_campaign_list.reload, stats_panel.reload]
  - id: A-S12-003
    element: filter_platform
    region: topbar
    trigger: change
    action: mutate
    effects: [ad_campaign_list.reload]
  - id: A-S12-004
    element: btn_view_leads
    region: stats_panel
    trigger: click
    action: mutate
    effects: [stats_panel.expand_leads_list]
  - id: A-S12-005
    element: lead_party_link
    region: stats_panel
    trigger: click
    action: navigate
    target: S03
    payload: { party_id: "$lead.party_id" }
