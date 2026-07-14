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
row_heights: [auto, "minmax(280px,auto)"]
areas:
  - [sidebar, topbar, topbar]
  - [sidebar, ad_campaign_list, stats_panel]
content:
  sidebar:
    - slot: "C01 Sidebar Nav (global)"
  topbar:
    - row:
        - { h: "Ads Tracking" }
        - { select: "Date range: 30 ngày" }
        - { select: "Ad platform: Facebook" }
  ad_campaign_list:
    - table: { cols: ["Chiến dịch", "Spend", "Leads", "Converted", "CPC"], rows: 4 }
  stats_panel:
    - row:
        - { kpi: { label: "Tổng spend", value: "12.300.000đ" } }
        - { kpi: { label: "Tổng leads", value: "87" } }
        - { kpi: { label: "Conversion", value: "9.2%" } }
        - { kpi: { label: "Revenue attr.", value: "48.000.000đ" } }
    - { btn: "Xem leads", action: A-S12-004 }
    - list: { item: "Nguyễn Văn A · Facebook lead", rows: 3 }
```

<!-- ui-layout:ascii:start -->
```
┌────────────┬───────────────────────────────────────────────────────────────┐
│SIDEBAR     │TOPBAR                                                         │
│· <<C01 Sid…│· Ads Tracking [Date range: 30 ngày v] [Ad platform: Facebook …│
│            ├─────────────────────────────────────┬─────────────────────────┤
│            │AD_CAMPAIGN_LIST                     │STATS_PANEL              │
│            │· tbl(Chiến dịch | Spend | Leads | C…│· Tổng spend: 12.300.000…│
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
