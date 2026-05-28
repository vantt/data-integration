# Playbook: Marketing Weekly Tracker

## Overview

- **Audience:** Marketing Manager, Brand Manager
- **Goal:** Track weekly channel performance, customer acquisition efficiency, and active campaign health.
- **Cadence:** Every Monday, reviewing previous Mon-Sun.
- **Archetype:** Operational Cockpit
- **Collection:** `Marketing & Customers`

## Key Questions

1. **Channel ROI:** Kenh nao mang lai hieu qua tot nhat tuan nay? Ty trong Ecommerce vs Offline thay doi the nao?
2. **Customer Acquisition:** Tuan nay co bao nhieu khach moi? Tu kenh nao? Dong gop doanh thu bao nhieu?
3. **Campaign Health:** Promotion nao dang chay? Hieu qua discount co dang kiem soat duoc khong?
4. **Social Commerce:** Doanh thu tu Facebook/Zalo tuan nay ra sao?
5. **Product-Channel Fit:** San pham nao ban tot tren kenh nao?

## Filters

- **Date Range:** Default = Last 7 Days (prev Mon-Sun). Comparison = Previous 7 Days.
- **Channel Category:** Filter by Online-Ecommerce / Offline / All.
- **Brand (Channel):** Filter by `channel_brand` (JPC, Fine Japan, The Healthy Us, etc.).

## Data Lineage

- **Core Models:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql), [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql)
- **Dimensions:** `dim_channels`, `dim_products`, `dim_customers`, `dim_promotions`

## Tab Structure

### Tab 1: Hieu suat Kenh (Channel Performance)

**Focus:** "Kenh nao hieu qua nhat tuan nay?"

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Weekly Revenue** | Scalar + WoW Trend | [Net Revenue](../domains/sales.md#2-net-revenue) | Hero. WoW % change. |
| **Ecommerce Revenue** | Scalar + WoW Trend | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Filter: `channel_category = 'Online-Ecommerce'`. WoW change. |
| **Offline Revenue** | Scalar + WoW Trend | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Filter: `channel_category = 'Offline'`. WoW change. |
| **Ecom Share %** | Scalar + WoW Trend | _Derived_ | Ecommerce / Total revenue %. WoW pp change. |
| **Ecommerce vs Offline Trend** | Multi-Line Chart | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Daily revenue, 2 lines. 14-day window. |
| **Revenue by Brand** | Donut Chart | _Derived_ | Group by `channel_brand`. Max 5 slices. |
| **Revenue by Platform** | Horizontal Bar | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Ranked by revenue DESC. |
| **Orders by Platform** | Horizontal Bar | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Ranked by orders DESC. Side-by-side with revenue. |
| **Channel Performance Table** | Formatted Table | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Columns: Channel, Orders, Revenue, AOV, WoW Revenue %, WoW Orders %. Highlight > 20% change. |

### Weekly Channel Margin

**Focus:** "Kênh nào đang bị trượt margin — cần dừng offer ngay?"

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Weekly Channel Margin & Delta** | Combo (Bar + Line) + Table footer | [Gross Margin by Channel](../domains/sales.md#gross-margin) | Bar = Net Revenue (left axis), Line = Margin % (right axis). Table footer shows Margin Delta pp WoW. Highlight rows where Margin Delta <= -5pp. Source: `fact_order_economics`. |

**Action:** If Margin Delta pp <= -5 WoW on any channel → pause low-margin offers on that channel. Escalate to Finance if negative 2 weeks running.

### Tab 2: Khach hang & Acquisition (Customers)

**Focus:** "Tuan nay co bao nhieu khach moi va tu dau?"

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **New Customers** | Scalar + WoW Trend | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Hero. WoW % change. |
| **Returning Customers** | Scalar + WoW Trend | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | WoW change. |
| **New Customer Revenue** | Scalar + WoW Trend | _Derived_ | Revenue from first-time buyers. WoW change. |
| **New Customer Share %** | Scalar + WoW Trend | _Derived_ | New customer revenue / total revenue %. WoW pp change. |
| **New Customers by Channel** | Horizontal Bar | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Ranked by new customer count DESC. |
| **New vs Returning Revenue** | Stacked Bar | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Daily stacked bar, 7 days. New (accent) vs Returning (muted). |
| **New Customer Acquisition Trend** | Combo Chart | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | 14-day bars (new customers) + line (new customer AOV). |
| **Customer Type Split** | Donut | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | New vs Returning customer count this week. |

### Tab 3: Promotion & Social Commerce

**Focus:** "Discount co dang kiem soat? Social commerce the nao?"

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Discount Rate %** | Gauge | [Discount Impact](../domains/sales.md#13-discount-impact) | Hero. Zones: Green 0-10%, Yellow 10-15%, Red > 15%. |
| **Discounted Orders %** | Scalar + WoW Trend | [Discount Impact](../domains/sales.md#13-discount-impact) | % don co discount. WoW pp change. |
| **Avg Discount Amount** | Scalar + WoW Trend | [Discount Impact](../domains/sales.md#13-discount-impact) | Trung binh tien discount moi don. WoW change. |
| **Total Discount Given** | Scalar + WoW Trend | [Discount Impact](../domains/sales.md#13-discount-impact) | Tong tien discount da cap. WoW change. Giam = tot. |
| **Discounted vs Full Price** | Donut | [Discount Impact](../domains/sales.md#13-discount-impact) | 2 slices: Discounted / Full Price order count. |
| **Promotion Leaderboard** | Formatted Table | [Promotion Performance](../domains/sales.md#14-promotion-performance) | Top 10 promos: Promo Code, Usage Count, Revenue, Avg Discount %. Highlight > 20% discount. |
| **Social Revenue** | Scalar + WoW Trend | [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) | WoW change. |
| **Social Orders** | Scalar + WoW Trend | [Social Order Count](../domains/customer_support.md#2-social-order-count) | WoW change. |
| **Social AOV** | Scalar + WoW Trend | _Derived_ | AOV kenh social. WoW change. |
| **Social Revenue by Platform** | Horizontal Bar | [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) | Facebook vs Zalo split — revenue + orders. |
| **Top 10 Products This Week** | Formatted Table | [Top Selling Products](../domains/sales.md#9-top-selling-products) | Product, Brand, Units, Revenue. Highlight top 3. |

## Operational Actions

- **Channel Declining WoW > 20%:** Investigate — is it a platform issue (Shopee downtime?), stock-out, or pricing problem?
- **New Customer Acquisition Dropping:** Check if ads are still running. Review social media posting frequency.
- **Discount Rate > 15%:** Review which promotions are active. Consider tightening discount rules.
- **Social Commerce Flat:** Coordinate with CS team on chat response time and closing techniques.
- **New Customer Share < 20%:** Acquisition channels may be underperforming — review marketing spend allocation.
- **Weekly Channel Margin slip > 5pp WoW:** Pause low-margin offers on that channel immediately. Escalate to Finance if margin delta stays negative 2 weeks running.

## Implementation Notes

- **Differs from Daily Ops:** This is a **weekly summary** for strategic channel decisions, not real-time monitoring.
- **Differs from CEO Weekly Pulse:** This dashboard includes **channel drill-downs, brand splits, and promotion detail** that the CEO version intentionally omits.
- Marketing Manager should use this to prepare **weekly channel report** for the CEO's review.
- **3-tab structure:** Tab 1 (Channel) for quick Monday pulse. Tab 2 (Customers) and Tab 3 (Promotion & Social) for deep-dive when needed.
