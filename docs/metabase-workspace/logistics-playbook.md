# Logistics & Operations Playbook

## 🎯 Overview

This playbook monitors the physical flow of goods, order fulfillment efficiency, and staff performance:

- **Fulfillment Performance** → [logistics-blueprint-fulfillment.md] _(coming soon)_
- **Shipping & Delivery** → [logistics-blueprint-shipping.md] _(coming soon)_

## 📊 Business Context

### Target Users

- **Operations Manager**: Fulfillment speed and efficiency
- **Warehouse Manager**: Staff productivity and shipping accuracy
- **Customer Service**: Order status visibility and return handling

### Update Frequency

- **Real-time**: Order status pipeline (Pending -> Shipped)
- **Hourly**: Fulfillment throughput
- **Daily**: SLA compliance, carrier performance
- **Weekly**: Staff performance, return analysis

## 🎯 Key Operational Metrics

### Fulfillment Metrics

| Metric                 | Formula                        | Business Rule    | Target    |
| ---------------------- | ------------------------------ | ---------------- | --------- |
| **Fulfillment Rate**   | Shipped / Total Orders × 100%  | Daily batch      | >99%      |
| **Order Cycle Time**   | Shipped TS - Created TS        | Processing speed | <24 hours |
| **Same-Day Ship Rate** | Shipped same day / Total       | Cutoff time 4PM  | >85%      |
| **Perfect Order Rate** | On-time & Complete & No Return | Quality metric   | >95%      |

### Shipping & Returns

| Metric                  | Formula                       | Business Rule     | Target  |
| ----------------------- | ----------------------------- | ----------------- | ------- |
| **Avg Delivery Time**   | Delivered TS - Shipped TS     | Transit time      | <3 days |
| **On-Time Delivery**    | Delivered <= Promised         | Carrier SLA       | >95%    |
| **Return Rate**         | Returns / Shipped Orders      | Reverse logistics | <5%     |
| **Shipping Cost/Order** | Total Shipping Spend / Orders | Cost efficiency   | Monitor |

## 📈 Dashboard Designs

### 1. Operations Center Dashboard

**Purpose**: Real-time view of order processing pipeline

**Layout**:

```
┌───────────────────────────────────────────────────────┐
│  STATUS FUNNEL                                        │
│  Pending (50) -> Processing (20) -> Shipped (300)     │
└───────────────────────────────────────────────────────┘
┌─────────────────────────┬─────────────────────────┐
│ Fulfillment Speed (Hr)  │ Issues / Holds          │
│ (Line Chart)           │ (Alert Table)           │
└─────────────────────────┴─────────────────────────┘
┌─────────────────────────┬─────────────────────────┐
│ Staff Productivity      │ Hourly Throughput       │
│ (Bar Chart)            │ (Heatmap)               │
└─────────────────────────┴─────────────────────────┘
```

### 2. Shipping & Returns Dashboard

**Purpose**: Monitor carrier performance and return reasons

**Layout**:

```
┌─────────────────────────┬─────────────────────────┐
│ Delivery Time Dist      │ Carrier Success Rate    │
│ (Histogram)            │ (Bar Chart)             │
└─────────────────────────┴─────────────────────────┘
┌─────────────────────────┬─────────────────────────┐
│ Return Rate Trend       │ Return Reasons          │
│ (Line Chart)           │ (Pareto Chart)          │
└─────────────────────────┴─────────────────────────┘
```

## 🔧 SQL Library

### Order Status Funnel

```sql
SELECT
    status,
    COUNT(*) as order_count,
    SUM(total) as total_value
FROM orders
WHERE created_on >= CURRENT_DATE - INTERVAL '24 hours'
GROUP BY status
ORDER BY
    CASE status
        WHEN 'draft' THEN 1
        WHEN 'pending' THEN 2
        WHEN 'confirmed' THEN 3
        WHEN 'processing' THEN 4
        WHEN 'completed' THEN 5
        WHEN 'cancelled' THEN 6
    END
```

### Fulfillment Performance

```sql
SELECT
    DATE_TRUNC('day', f.created_on) as date,
    COUNT(*) as total_fulfillments,
    AVG(EXTRACT(EPOCH FROM (f.shipped_on - f.created_on))/3600) as avg_processing_hours,
    COUNT(CASE WHEN f.status = 'shipped' THEN 1 END) * 100.0 / COUNT(*) as fulfillment_rate,
    COUNT(CASE WHEN f.shipped_on <= f.created_on + INTERVAL '24 hours' THEN 1 END) * 100.0 /
        COUNT(*) as same_day_fulfillment_rate
FROM fulfillments f
GROUP BY date
ORDER BY date DESC
```

### Carrier Performance & Delivery Time

```sql
SELECT
    dsp.provider_name,
    COUNT(*) as total_shipments,
    AVG(EXTRACT(DAY FROM (s.delivered_at - s.created_on))) as avg_delivery_days,
    COUNT(CASE WHEN s.status = 'delivered' THEN 1 END) * 100.0 / COUNT(*) as success_rate,
    AVG(s.delivery_fee) as avg_shipping_cost
FROM shipments s
JOIN delivery_service_providers dsp
    ON s.delivery_service_provider_id = dsp.provider_id
GROUP BY dsp.provider_id, dsp.provider_name
ORDER BY total_shipments DESC
```

### Returns & Refunds Analysis

```sql
-- Chart: Return Rate Trend
SELECT
    DATE_TRUNC('week', created_on) as week,
    COUNT(DISTINCT order_id) as total_orders,
    COUNT(DISTINCT CASE WHEN return_status != 'unreturned'
          THEN order_id END) as orders_with_returns,
    COUNT(DISTINCT CASE WHEN return_status != 'unreturned'
          THEN order_id END) * 100.0 / COUNT(DISTINCT order_id) as return_rate
FROM orders
GROUP BY week
ORDER BY week
```

```sql
-- Table: Return Reasons
SELECT
    reason,
    COUNT(*) as return_count,
    SUM(refund_amount) as total_refunded,
    AVG(refund_amount) as avg_refund
FROM order_returns
GROUP BY reason
ORDER BY return_count DESC
```

### Staff Performance (Packers/Sales)

```sql
SELECT
    a.account_name,
    a.role,
    COUNT(DISTINCT o.order_id) as total_orders,
    SUM(o.total) as total_revenue,
    AVG(o.total) as avg_order_value,
    COUNT(DISTINCT o.customer_id) as unique_customers
FROM orders o
JOIN accounts a ON o.account_id = a.account_id
WHERE o.created_on >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY a.account_id, a.account_name, a.role
ORDER BY total_revenue DESC
```

## 🚀 Implementation Notes

### Best Practices

1. **Status Mapping**: Ensure ERP status codes map cleanly to analytics stages
2. **Timezones**: Standardize timestamps (UTC) for duration calculations
3. **Shift Analysis**: Compare performance across AM/PM shifts
4. **SLA Alerts**: Alert on orders stuck in 'Processing' > 24h

### Common Pitfalls

1. Counting cancelled orders in fulfillment metrics
2. Not excluding weekends/holidays from "Days to Ship" calculation
3. Blaming carriers for warehouse processing delays (start clock correctly)
