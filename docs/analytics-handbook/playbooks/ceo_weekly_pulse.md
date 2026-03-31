# Playbook: CEO Weekly Pulse

## Overview

- **Audience:** CEO, Co-Founders
- **Goal:** 5-minute weekly check-in — answer "Are we on track this week?" across Sales, Customers, and Operations.
- **Cadence:** Every Monday morning, reviewing the previous Mon–Sun.
- **Archetype:** Executive Pulse
- **Metabase Collection:** `Executive` > `Weekly Reports`

## Key Questions

1. **Revenue:** Tổng doanh thu tuần này so với tuần trước và cùng kỳ? Có đang on-track để đạt target tháng không?
2. **Growth Drivers:** Kênh nào tăng, kênh nào giảm so với tuần trước?
3. **Customer Health:** Có bao nhiêu khách mới? Tỷ lệ New vs Returning thay đổi thế nào?
4. **Operational Flags:** Có gì bất thường cần chú ý (hoàn trả tăng đột biến, discount quá nhiều)?

## Filters

- **Date Range:** Default = Last 7 Days (Mon–Sun). Comparison = Previous Week.
- **No drill-down filters** — CEO sees the full picture, no store/channel filter.

## Data Lineage

- **Core Models:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql), [`fact_targets`](../../../transformation/models/marts/core/fact_targets.sql)
- **Dimensions:** `dim_channels`, `dim_customers`, `dim_products`

## Visualizations

### Section 1: Weekly Headline KPIs (Scalar Row)

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Weekly GMV** | Scalar + Trend | [GMV](../domains/sales.md#1-gmv-gross-merchandise-value) | Show WoW % change. Color: Green if +, Red if −. |
| **Weekly Net Revenue** | Scalar + Trend | [Net Revenue](../domains/sales.md#2-net-revenue) | Show WoW % change. |
| **Total Orders** | Scalar + Trend | [Total Orders](../domains/sales.md#4-total-orders) | Show WoW % change. |
| **AOV** | Scalar + Trend | [AOV](../domains/sales.md#5-aov-average-order-value) | Show WoW % change. |

### Section 2: Monthly Target Pace

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **MTD Revenue vs Target** | Progress Bar / Gauge | [Target Achievement Rate](../domains/sales.md#15-target-achievement-rate) | Show % achieved of monthly target. Highlight red if pace < expected (e.g., < week_number/4 × 100%). |
| **Revenue Pace Indicator** | Scalar | _Derived_ | `MTD Actual / (Monthly Target × Days Elapsed / Days in Month)`. If > 1.0 = "Ahead", < 1.0 = "Behind". |

### Section 3: Weekly Trends & Channel Mix

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Daily Revenue Trend (Last 14 Days)** | Line Chart | [GMV](../domains/sales.md#1-gmv-gross-merchandise-value) | 2-week window so CEO sees current week vs previous week side-by-side. Color: Blue (this week), Grey (last week). |
| **Revenue by Channel Category** | Horizontal Bar | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Group by `channel_category` (Ecommerce / Offline / Internal). Show WoW change per category. |
| **Top 5 Channels by Revenue** | Table | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Columns: Channel Name, This Week Revenue, Last Week Revenue, WoW Change %. Sort by Revenue DESC. |

### Section 4: Customer Health Pulse

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **New Customers This Week** | Scalar + Trend | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Count of customers with `first_order_date` in this week. WoW comparison. |
| **New vs Returning Orders** | Stacked Bar | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Daily breakdown: New (Blue) vs Returning (Grey) order count. |
| **Returning Customer Revenue %** | Scalar | _Derived from_ [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | % of weekly revenue from returning customers. Healthy benchmark > 60%. |

### Section 5: Operational Red Flags

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Return Count** | Scalar + Trend | [Return Rate](../domains/sales.md#3-return-rate--count) | Flag RED if > 2× previous week. |
| **Discount Rate %** | Scalar | [Discount Impact](../domains/sales.md#13-discount-impact) | `Total Discount / GMV × 100`. Flag RED if > 15%. |
| **Cancelled Orders** | Scalar | _Derived from_ [Total Orders](../domains/sales.md#4-total-orders) | Count where `status = 'CANCELLED'`. WoW comparison. |

## Visualization Configs

### Daily Revenue Trend (14-day)

```json
{
  "display": "line",
  "graph.dimensions": ["order_date"],
  "graph.metrics": ["gmv"],
  "graph.colors": ["#509EE3"],
  "graph.x_axis.title_text": "",
  "graph.y_axis.title_text": "Revenue (VND)"
}
```

### Channel Category Bar

```json
{
  "display": "bar",
  "graph.dimensions": ["channel_category"],
  "graph.metrics": ["revenue"],
  "graph.x_axis.axis_enabled": true,
  "graph.y_axis.axis_enabled": true
}
```

## Implementation Notes

- **Max 10–12 visual elements** on this dashboard. CEO scans, doesn't drill.
- Use **Metabase "compare to previous period"** feature on all scalar KPIs for automatic WoW arrows.
- Consider **auto-subscription**: Email/Slack push every Monday 8:00 AM.
- This dashboard does NOT replace the daily ops dashboard — it provides the "so what?" summary.
