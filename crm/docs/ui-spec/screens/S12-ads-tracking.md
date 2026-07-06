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

```yaml ui-layout
columns: [1fr, 3fr, 2fr]
areas:
  - [sidebar, topbar, topbar]
  - [sidebar, ad_campaign_list, stats_panel]
samples:
  sidebar: "(C01 global nav)"
  topbar: "Ads Tracking  [Date range ▼]  [Ad platform ▼]"
  ad_campaign_list: "Summer-2026 · Spend 5.200.000đ · Leads 42 · Converted 8 · CPC 123.800đ  |  Brand-June-2026 · Spend 7.100.000đ"
  stats_panel: "Tổng spend: 12.300.000đ · Tổng leads: 87 · Conversion: 9.2% · Revenue attr: 48.000.000đ"
elements:
  "Date range ▼": A-S12-002
  "Ad platform ▼": A-S12-003
```

<!-- ui-layout:ascii:start -->
```
┌────────────┬───────────────────────────────────────────────────────────────┐
│SIDEBAR     │TOPBAR                                                         │
│· (C01 glob…│· Ads Tracking  [Date range v]  [Ad platform v]                │
│            ├─────────────────────────────────────┬─────────────────────────┤
│            │AD_CAMPAIGN_LIST                     │STATS_PANEL              │
│            │· Summer-2026 · Spend 5.200.000đ · L…│· Tổng spend: 12.300.000…│
└────────────┴─────────────────────────────────────┴─────────────────────────┘
```
<!-- ui-layout:ascii:end -->

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
