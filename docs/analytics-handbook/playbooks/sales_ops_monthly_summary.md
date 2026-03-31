# Playbook: Sales Ops Monthly Summary

## Overview

- **Audience:** Sales Operator, Customer Support Lead, Operations Manager
- **Goal:** Monthly operational summary — order processing efficiency, social commerce results, team KPIs, and channel operational health for the closed month.
- **Cadence:** 2nd–3rd of each month, reviewing the closed month.
- **Archetype:** Operational Cockpit + Analytical
- **Metabase Collection:** `Daily Operations` > `Monthly Reports`
- **Related:** [Sales Ops Weekly Review](./sales_ops_weekly_review.md), [Social Commerce Operations](./customer_support_social_commerce.md), [Orders Reconciliation](./orders_list_reconciliation.md)

## Key Questions

1. **Processing Efficiency:** Tỷ lệ hoàn thành đơn hàng tháng này? Thời gian xử lý trung bình cải thiện hay tệ hơn?
2. **Order Quality:** Return rate và cancellation rate tháng này ra sao? So với tháng trước?
3. **Social Commerce Results:** Tổng doanh thu social commerce tháng này? Mỗi nhân viên CS đóng góp bao nhiêu?
4. **Channel Operations:** Kênh nào chiếm nhiều workload nhất? Kênh nào có tỷ lệ vấn đề cao nhất?
5. **Payment Reconciliation:** Tổng thanh toán đã thu vs pending? Phương thức nào phổ biến nhất?
6. **Staff Productivity:** Nhân viên nào xử lý nhiều đơn nhất? AOV trung bình mỗi nhân viên?

## Filters

- **Date Range:** Default = Last Closed Month. Comparison = Previous Month.
- **Branch/Location:** Filter by `dim_branch_location`.
- **Channel Category:** Ecommerce / Offline / All.

## Data Lineage

- **Core Models:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql), [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql), [`fact_payments`](../../../transformation/models/marts/sales/fact_payments.sql)
- **Dimensions:** `dim_channels`, `dim_staff`, `dim_branch_location`, `dim_customers`, `dim_payment_methods`, `dim_order_status`

## Visualizations

### Section 1: Monthly Operations KPIs (Scalar Row)

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Total Orders** | Scalar + Trend | [Total Orders](../domains/sales.md#4-total-orders) | MoM % change. |
| **Total GMV** | Scalar + Trend | [GMV](../domains/sales.md#1-gmv-gross-merchandise-value) | MoM % change. |
| **Completion Rate** | Scalar | _Derived_ | `COMPLETED / Total Orders × 100%`. Green if > 90%. |
| **Avg Time to Complete** | Scalar + Trend | _Derived from `fact_orders.time_to_complete_hours`_ | Average hours from order creation to completion. MoM comparison. |

### Section 2: Order Quality Analysis

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Order Status Breakdown (MoM)** | Grouped Bar | _Derived_ | X: Status (Completed, Cancelled, Open, Archived). 2 bars per group: This Month (Blue) vs Last Month (Grey). |
| **Cancellation Rate Trend (6M)** | Line Chart | _Derived_ | Monthly `CANCELLED / Total × 100`. Shows if cancellation is trending up. |
| **Return Rate Trend (6M)** | Line Chart | [Return Rate](../domains/sales.md#3-return-rate--count) | Monthly `RETURNED / Total × 100`. 6-month window. |
| **Top Returned Products** | Table (Top 10) | _Derived_ | Columns: Product Name, Return Count, Return Revenue, % of Total Returns. From `fact_orders` where `fulfillment_status = 'RETURNED'`. |
| **Cancellation by Channel** | Horizontal Bar | _Derived_ | Cancellation count per channel. Identifies problematic channels. |

### Section 3: Social Commerce Monthly Results

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Social Revenue (Monthly)** | Scalar + Trend | [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) | MoM change. |
| **Social Orders (Monthly)** | Scalar + Trend | [Social Order Count](../domains/customer_support.md#2-social-order-count) | MoM change. |
| **Social Revenue Trend (6M)** | Line Chart | [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) | Monthly social revenue over 6 months. |
| **Social Revenue by Platform** | Donut Chart | [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) | Facebook vs Zalo monthly split. |
| **CS Staff Leaderboard** | Table | _Derived_ | Columns: Staff Name, Social Orders, Social Revenue, AOV, % Contribution. Ranked by Revenue DESC. Filter: Social channels. |

### Section 4: Channel Operational Health

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Orders by Channel (Monthly)** | Horizontal Bar | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Order count by channel. Operational workload view. |
| **Channel Operations Matrix** | Table | _Derived_ | Columns: Channel, Orders, Revenue, Completion %, Cancel %, Return %, Avg Time to Complete. Identifies channels with operational issues. |
| **Orders by Branch** | Horizontal Bar | _Derived_ | Monthly order count per branch location. |
| **Branch Performance Table** | Table | _Derived_ | Columns: Branch, Orders, Revenue, Completion %, Cancel %. |

### Section 5: Payment Operations

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Payment Method Mix** | Donut Chart | [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution) | Monthly transaction count by payment method. |
| **Payment Method Trend (6M)** | Stacked Area | [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution) | Monthly transaction count stacked by method. Shows shift in payment preferences. |
| **Payment Status Summary** | Table | [Payment Status](../domains/sales.md#12-payment-status) | Columns: Status, Order Count, Total Amount, % of Total. Flag pending > 5%. |

### Section 6: Staff Productivity (All Channels)

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Staff Performance Table** | Table | _Derived_ | Columns: Staff Name, Total Orders, Total Revenue, AOV, Completion %, MoM Orders Change. All channels. Sort by Revenue DESC. |
| **Staff Revenue Distribution** | Horizontal Bar | _Derived_ | Revenue per staff. Identifies top performers and those needing support. |
| **Orders per Staff per Day** | Scalar | _Derived_ | `Total Assigned Orders / Staff Count / Working Days`. Productivity benchmark. |

## Visualization Configs

### Cancellation Rate Trend

```json
{
  "display": "line",
  "graph.dimensions": ["month"],
  "graph.metrics": ["cancellation_rate"],
  "graph.colors": ["#EF8C8C"],
  "graph.y_axis.title_text": "Cancellation Rate %",
  "graph.goal_value": 5,
  "graph.show_goal": true,
  "graph.goal_label": "Target < 5%"
}
```

### Channel Operations Matrix

```json
{
  "display": "table",
  "table.pivot": false,
  "column_settings": {
    "revenue": { "number_style": "currency", "currency": "VND" },
    "completion_pct": { "number_style": "percent", "decimals": 1 },
    "cancel_pct": { "number_style": "percent", "decimals": 1 },
    "return_pct": { "number_style": "percent", "decimals": 1 }
  }
}
```

## Operational Actions

- **Completion Rate < 90%:** Deep dive into OPEN and stuck orders. Check fulfillment pipeline bottleneck.
- **Cancellation Rate > 5%:** Analyze top cancellation reasons by channel. If marketplace-heavy, check stock sync issues.
- **Return Rate > 3%:** Review top returned products. Escalate to product team if quality issue. Update product descriptions if mismatch issue.
- **Staff Productivity Imbalance (> 3× between highest and lowest):** Review order assignment fairness. Consider workload redistribution.
- **Pending Payments > 5%:** Escalate to finance team. Check bank transfer confirmation delays.

## Implementation Notes

- **Differs from Sales Ops Weekly Review:** Weekly is a quick operational check. Monthly adds **6-month trends, staff leaderboard, and channel health matrix** for management decisions.
- **Differs from CEO Monthly Scorecard:** CEO sees strategic metrics (revenue, growth, segments). This shows **operational metrics** (completion rate, processing time, staff productivity, payment health).
- **`time_to_complete_hours`:** Calculated in `fact_orders` as `DATEDIFF(hour, order_timestamp, completed_at)`. NULL for non-completed orders — exclude from average.
- **Staff Data Caveat:** Not all orders have assigned staff (marketplace auto-orders). Filter to `staff_key IS NOT NULL` for meaningful staff comparisons.
- Max ~20 visual elements. Operations Manager reviews in detail (20–30 min).
