# Playbook: Sales Ops Weekly Review

## Overview

- **Audience:** Sales Operator, Customer Support Lead, Store Manager
- **Goal:** Weekly operational review — order processing health, channel order volumes, social commerce performance, and team productivity.
- **Cadence:** Every Monday, reviewing previous Mon–Sun.
- **Archetype:** Operational Cockpit
- **Collection:** `Operations` > `Periodic Reviews`
- **Design Spec:** [designs/sales_ops_weekly_review.md](../designs/sales_ops_weekly_review.md)
- **Related:** [Daily Sales Operations](./sales_daily_operation.md), [Social Commerce Operations](./customer_support_social_commerce.md)

## Key Questions

1. **Order Volume:** Tuần này xử lý bao nhiêu đơn? So với tuần trước tăng hay giảm?
2. **Order Quality:** Tỷ lệ đơn hoàn thành vs hủy vs trả hàng? Có bất thường không?
3. **Social Commerce:** Doanh thu từ Facebook/Zalo tuần này? Nhân viên nào bán tốt nhất?
4. **Channel Workload:** Đơn hàng phân bổ thế nào giữa các kênh? Kênh nào tăng đột biến cần thêm nhân lực?
5. **Payment Health:** Phương thức thanh toán nào phổ biến? Có đơn nào pending payment lâu không?

## Filters

- **Date Range:** Default = Last 7 Days. Comparison = Previous 7 Days.
- **Branch/Location:** Filter by `dim_branch_location`.
- **Staff:** Filter by `dim_staff` (for team lead view).

## Data Lineage

- **Core Models:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql), [`fact_payments`](../../../transformation/models/marts/sales/fact_payments.sql)
- **Dimensions:** `dim_channels`, `dim_staff`, `dim_branch_location`, `dim_customers`, `dim_payment_methods`

## Visualizations

### Section 1: Weekly Order KPIs (Scalar Row)

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Total Orders** | Scalar + Trend | [Total Orders](../domains/sales.md#4-total-orders) | WoW % change. |
| **Total GMV** | Scalar + Trend | [GMV](../domains/sales.md#1-gmv-gross-merchandise-value) | WoW % change. |
| **AOV** | Scalar + Trend | [AOV](../domains/sales.md#5-aov-average-order-value) | WoW % change. |
| **Completed Orders %** | Scalar | _Derived_ | `COUNT(status='COMPLETED') / COUNT(*)`. Green if > 90%. |

### Section 2: Order Status Breakdown

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Order Status Distribution** | Donut Chart | _Derived from_ [Total Orders](../domains/sales.md#4-total-orders) | Slices: COMPLETED, OPEN, CANCELLED, ARCHIVED. |
| **Fulfilment Status Distribution** | Horizontal Bar | _Derived_ | Count by `fulfillment_status`: DELIVERED, SHIPPING, PACKED, PENDING, RETURNED, CANCELLED. |
| **Cancelled Orders This Week** | Scalar + Trend | _Derived_ | Count where `status = 'CANCELLED'`. WoW change. Flag RED if > 2× previous week. |
| **Return Count** | Scalar + Trend | [Return Rate](../domains/sales.md#3-return-rate--count) | WoW change. Flag RED if > 2× previous week. |

### Section 3: Daily Order Volume Trend

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Daily Orders (14-day)** | Bar Chart | [Total Orders](../domains/sales.md#4-total-orders) | 14-day window. Color: Blue (this week), Grey (last week). Helps spot day-of-week patterns. |
| **Peak Hour Analysis** | Heatmap | [Hourly Heatmap](../domains/sales.md#7-hourly-heatmap-day-of-week-analysis) | Hour × Day of Week for this week. Helps plan shift scheduling. |

### Section 4: Channel Workload

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Orders by Channel** | Horizontal Bar | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Order count (not revenue) by `channel_name`. Operational focus = volume, not money. |
| **Channel Order Table** | Table | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Columns: Channel, Orders, Revenue, AOV, WoW Orders Change %. Sort by Orders DESC. |
| **Orders by Branch** | Horizontal Bar | _Derived_ | From `dim_branch_location`. Shows workload per physical location. |

### Section 5: Social Commerce & Team Performance

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Social Revenue (FB + Zalo)** | Scalar + Trend | [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) | WoW change. |
| **Social Orders** | Scalar + Trend | [Social Order Count](../domains/customer_support.md#2-social-order-count) | WoW change. |
| **Top Staff by Revenue** | Table | _Derived_ | Columns: Staff Name, Orders, Revenue, AOV. From `fact_orders` joined with `dim_staff`. Filter: social channels only. |
| **Staff Revenue Comparison** | Horizontal Bar | _Derived_ | Revenue per staff member this week. All channels (not just social). |

### Section 6: Payment Health

| Chart Title | Visualization Type | Metric Reference (Link to Domain) | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Payment Method Distribution** | Donut Chart | [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution) | Transaction count by method (Cash, Card, Transfer, COD, etc.). |
| **Payment Status Summary** | Table | [Payment Status](../domains/sales.md#12-payment-status) | Columns: Status (paid/pending/refunded), Order Count, Total Amount. Flag if pending > 5% of total. |

## Visualization Configs

### Daily Orders (14-day Bar)

```json
{
  "display": "bar",
  "graph.dimensions": ["order_date"],
  "graph.metrics": ["order_count"],
  "graph.colors": ["#509EE3"]
}
```

### Order Status Donut

```json
{
  "display": "pie",
  "pie.dimension": "status",
  "pie.metric": "order_count",
  "pie.show_legend": true,
  "pie.colors": {
    "COMPLETED": "#84BB4C",
    "OPEN": "#509EE3",
    "CANCELLED": "#EF8C8C",
    "ARCHIVED": "#CCCCCC"
  }
}
```

## Operational Actions

- **Cancelled Orders Spike (> 2× WoW):** Investigate root cause — stock-out? pricing error? system issue?
- **Returns Spike:** Identify top returned products. Check for quality or description mismatch.
- **Channel Volume Shift > 30%:** Notify team leads to adjust staffing. If marketplace order spike, check for flash sale events.
- **Pending Payments > 5%:** Follow up with payment provider. Check for bank transfer orders awaiting confirmation.
- **Social Revenue Declining:** Coordinate with Marketing on posting schedule. Review CS team response time.

## Implementation Notes

- **Differs from Daily Ops Dashboard:** Daily dashboard is **real-time/yesterday**. This is a **weekly aggregate** for trend spotting and team management.
- **Differs from CEO Weekly Pulse:** CEO version is strategic (revenue & growth). This version is **operational** (order processing, team performance, channel workload).
- **Staff Performance Note:** `dim_staff` data comes from Sapo's assigned salesperson field. Not all orders have a staff assignment (especially marketplace orders). Filter to "assigned" orders for meaningful staff comparisons.
