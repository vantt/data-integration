# Playbook: Marketing Weekly Tracker

## Overview

- **Audience:** Marketing Manager, Brand Manager
- **Goal:** Track weekly channel performance, customer acquisition efficiency, and active campaign health.
- **Cadence:** Every Monday, reviewing previous Mon–Sun.
- **Archetype:** Operational Cockpit
- **Metabase Collection:** `Marketing` > `Weekly Reports`

## Key Questions

1. **Channel ROI:** Kênh nào mang lại hiệu quả tốt nhất tuần này? Tỷ trọng Ecommerce vs Offline thay đổi thế nào?
2. **Customer Acquisition:** Tuần này có bao nhiêu khách mới? Chi phí trung bình mỗi khách mới (nếu có marketing spend)?
3. **Campaign Health:** Promotion nào đang chạy? Hiệu quả discount có đang kiểm soát được không?
4. **Social Commerce:** Doanh thu từ Facebook/Zalo tuần này ra sao?
5. **Product-Channel Fit:** Sản phẩm nào bán tốt trên kênh nào?

## Filters

- **Date Range:** Default = Last 7 Days. Comparison = Previous 7 Days.
- **Channel Category:** Filter by Ecommerce / Offline / All.
- **Brand (Channel):** Filter by `channel_brand` (JPC, Fine Japan, The Healthy Us, etc.).

## Data Lineage

- **Core Models:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql), [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql), [`fact_marketing_spend`](../../../transformation/models/marts/sales/fact_marketing_spend.sql)
- **Dimensions:** `dim_channels`, `dim_products`, `dim_customers`

## Visualizations

### Section 1: Weekly Channel KPIs (Scalar Row)

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Weekly Revenue** | Scalar + Trend | [GMV](../domains/sales.md#1-gmv-gross-merchandise-value) | WoW % change. |
| **Ecommerce Revenue** | Scalar + Trend | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Filter: `channel_category = 'Ecommerce'`. WoW change. |
| **Offline Revenue** | Scalar + Trend | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Filter: `channel_category = 'Offline'`. WoW change. |
| **New Customers** | Scalar + Trend | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | WoW change. |

### Section 2: Channel Deep Dive

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Revenue by Platform** | Horizontal Bar | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Group by `platform` (Shopee, Lazada, TikTok, Facebook, POS, Web, etc.). |
| **Channel Performance Table** | Table | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Columns: Channel Name, Orders, Revenue, AOV, WoW Revenue %, WoW Orders %. Sort Revenue DESC. |
| **Ecommerce vs Offline Trend** | Line Chart (Dual) | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Daily revenue, 2 lines: Ecommerce (Blue) vs Offline (Orange). 14-day window. |
| **Revenue by Channel Brand** | Donut Chart | _Derived_ | Group by `channel_brand`. Shows brand portfolio split. |

### Section 3: Customer Acquisition

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **New Customer Acquisition Trend** | Bar Chart | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Daily new customer count over last 14 days. |
| **New Customers by Channel** | Horizontal Bar | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Which channels are bringing in new customers? Group by `channel_name`. |
| **New vs Returning Revenue Split** | Stacked Bar | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Revenue contribution: New (Light Blue) vs Returning (Dark Blue). |

### Section 4: Promotion & Discount Monitoring

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Discount Rate % (This Week)** | Scalar | [Discount Impact](../domains/sales.md#13-discount-impact) | `Total Discount / GMV × 100`. Flag RED if > 15%. |
| **Discounted vs Non-Discounted Orders** | Donut Chart | [Discount Impact](../domains/sales.md#13-discount-impact) | 2 slices: Discounted / Non-Discounted order count. |
| **Promotion Leaderboard** | Table (Top 5) | [Promotion Performance](../domains/sales.md#14-promotion-performance) | Columns: Promo Code, Usage Count, Revenue, Avg Discount %. Active promos this week. |

### Section 5: Social Commerce Performance

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Social Revenue (FB + Zalo)** | Scalar + Trend | [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) | WoW change. |
| **Social Orders** | Scalar + Trend | [Social Order Count](../domains/customer_support.md#2-social-order-count) | WoW change. |
| **Social Revenue by Platform** | Horizontal Bar | [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) | Facebook vs Zalo split. |

### Section 6: Product-Channel Insights

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Top 10 Products This Week** | Table | [Top Selling Products](../domains/sales.md#9-top-selling-products) | Columns: Product Name, Units, Revenue, Top Channel. From `fact_sales` joined with `dim_channels`. |
| **Brand Performance** | Table | _Derived from_ [Top Selling Products](../domains/sales.md#9-top-selling-products) | Group by `brand_name`. Columns: Brand, Units, Revenue, WoW Change %. |

## Visualization Configs

### Ecommerce vs Offline Trend

```json
{
  "display": "line",
  "graph.dimensions": ["order_date"],
  "graph.metrics": ["ecommerce_revenue", "offline_revenue"],
  "graph.colors": ["#509EE3", "#F9A825"],
  "graph.x_axis.title_text": "",
  "graph.y_axis.title_text": "Revenue (VND)"
}
```

### Channel Performance Table

```json
{
  "display": "table",
  "table.pivot": false,
  "column_settings": {
    "revenue": { "number_style": "currency", "currency": "VND" },
    "wow_change": { "number_style": "percent" }
  }
}
```

## Operational Actions

- **Channel Declining WoW > 20%:** Investigate — is it a platform issue (Shopee downtime?), stock-out, or pricing problem?
- **New Customer Acquisition Dropping:** Check if ads are still running. Review social media posting frequency.
- **Discount Rate > 15%:** Review which promotions are active. Consider tightening discount rules.
- **Social Commerce Flat:** Coordinate with CS team on chat response time and closing techniques.

## Implementation Notes

- **Differs from Daily Ops:** This is a **weekly summary** for strategic channel decisions, not real-time monitoring.
- **Differs from CEO Weekly Pulse:** This dashboard includes **channel drill-downs, brand splits, and promotion detail** that the CEO version intentionally omits.
- Marketing Manager should use this to prepare **weekly channel report** for the CEO's review.
