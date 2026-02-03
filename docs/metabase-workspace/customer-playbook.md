# Customer Analytics Playbook

## 🎯 Overview

This playbook covers customer behavior, segmentation, and lifetime value analytics:

- **Customer Segmentation** → [customer-blueprint-segmentation.md] _(coming soon)_
- **Lifetime Value Analysis** → [customer-blueprint-ltv.md] _(coming soon)_
- **Churn & Retention** → [customer-blueprint-retention.md] _(coming soon)_

## 📊 Business Context

### Target Users

- **Marketing Team**: Campaign targeting and personalization
- **Customer Success**: Retention and upsell opportunities
- **Product Team**: Feature adoption and user behavior
- **Sales Team**: Lead scoring and opportunity identification

### Update Frequency

- **Real-time**: Customer activity, engagement metrics
- **Daily**: Segmentation updates, churn predictions
- **Weekly**: Cohort analysis, retention curves
- **Monthly**: LTV calculations, segment migration

## 🎯 Key Customer Metrics

### Acquisition Metrics

| Metric                        | Formula                                | Business Rule          | Target      |
| ----------------------------- | -------------------------------------- | ---------------------- | ----------- |
| **Customer Acquisition Cost** | Marketing Spend / New Customers        | By channel             | <$50        |
| **New Customer Rate**         | New Customers / Total Customers × 100% | Growth indicator       | >5% monthly |
| **Activation Rate**           | Activated / Registered × 100%          | Within 7 days          | >60%        |
| **Channel Efficiency**        | LTV / CAC                              | By acquisition channel | >3:1        |

### Engagement Metrics

| Metric                       | Formula                               | Business Rule   | Target  |
| ---------------------------- | ------------------------------------- | --------------- | ------- |
| **Monthly Active Users**     | Unique users with activity in 30d     | Core engagement | Growing |
| **Engagement Rate**          | Active Users / Total Users × 100%     | Monthly basis   | >40%    |
| **Average Session Duration** | Total Time / Sessions                 | User stickiness | >5 min  |
| **Feature Adoption**         | Users of Feature / Total Users × 100% | Key features    | >30%    |

### Retention Metrics

| Metric                   | Formula                                      | Business Rule   | Target |
| ------------------------ | -------------------------------------------- | --------------- | ------ |
| **Retention Rate**       | Customers at End / Customers at Start × 100% | Monthly cohorts | >90%   |
| **Churn Rate**           | Lost Customers / Total Customers × 100%      | Monthly         | <5%    |
| **Repeat Purchase Rate** | Customers with >1 Order / Total × 100%       | Within 90 days  | >40%   |
| **Win-back Rate**        | Reactivated / Churned × 100%                 | 6-month window  | >10%   |

### Value Metrics

| Metric                       | Formula                         | Business Rule | Target   |
| ---------------------------- | ------------------------------- | ------------- | -------- |
| **Customer Lifetime Value**  | AOV × Purchase Freq × Lifespan  | 3-year window | >$500    |
| **Average Revenue Per User** | Total Revenue / Active Users    | Monthly       | Growing  |
| **Customer Profitability**   | Revenue - (COGS + Service Cost) | By segment    | Positive |
| **Net Promoter Score**       | Promoters% - Detractors%        | Survey-based  | >50      |

## 📈 Dashboard Designs

### 1. Customer Segmentation Dashboard

**Purpose**: Visualize customer segments and their characteristics

**Layout**:

```
┌─────────────────────────┬─────────────────────────┐
│ Total Customers         │ Segment Distribution    │
│ (Scalar + Trend)       │ (Donut Chart)          │
├─────────────────────────┴─────────────────────────┤
│ Segment Migration Sankey Diagram                  │
├─────────────────────────┬─────────────────────────┤
│ Segment Profiles        │ Segment Performance     │
│ (Radar Chart)          │ (Table)                 │
└─────────────────────────┴─────────────────────────┘
```

### 2. Retention & Churn Dashboard

**Purpose**: Track customer retention and identify churn risks

**Layout**:

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ Retention % │ Churn Rate  │ At Risk     │ Win-backs   │
├─────────────┴─────────────┴─────────────┴─────────────┤
│ Cohort Retention Curves (Multi-line Chart)            │
├───────────────────────────────────────────────────────┤
│ Churn Reasons          │ Risk Score Distribution      │
│ (Bar Chart)            │ (Histogram)                  │
└────────────────────────┴──────────────────────────────┘
```

## 💾 Data Requirements

### Source Tables

| Table               | Update Frequency | Key Fields                         | Data Quality Checks |
| ------------------- | ---------------- | ---------------------------------- | ------------------- |
| `dim_customers`     | Real-time        | customer_id, created_date, segment | Valid email         |
| `fact_events`       | Real-time        | customer_id, event_type, timestamp | No future dates     |
| `fact_orders`       | Real-time        | customer_id, order_id, amount      | Positive amounts    |
| `fact_interactions` | Daily            | customer_id, channel, outcome      | Valid channels      |

## 🔧 SQL Library

### RFM Segmentation Query

```sql
-- Calculate RFM scores and assign segments
WITH rfm_calc AS (
    SELECT
        customer_id,
        DATEDIFF('day', MAX(order_date), CURRENT_DATE) as recency,
        COUNT(DISTINCT order_id) as frequency,
        SUM(order_total) as monetary,
        -- Score each dimension 1-5
        NTILE(5) OVER (ORDER BY DATEDIFF('day', MAX(order_date), CURRENT_DATE) DESC) as r_score,
        NTILE(5) OVER (ORDER BY COUNT(DISTINCT order_id)) as f_score,
        NTILE(5) OVER (ORDER BY SUM(order_total)) as m_score
    FROM fact_orders
    WHERE order_date >= CURRENT_DATE - INTERVAL '2 years'
    GROUP BY customer_id
)
SELECT
    customer_id,
    recency,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal Customers'
        WHEN r_score >= 3 AND f_score <= 2 THEN 'Potential Loyalists'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score >= 3 THEN 'Cant Lose Them'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'New Customers'
        ELSE 'Need Attention'
    END as segment
FROM rfm_calc;
```

### Cohort Retention Analysis

```sql
-- Monthly cohort retention rates
WITH cohorts AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', first_order_date) as cohort_month
    FROM dim_customers
),
cohort_activity AS (
    SELECT
        c.cohort_month,
        DATE_TRUNC('month', o.order_date) as activity_month,
        COUNT(DISTINCT c.customer_id) as customers
    FROM cohorts c
    JOIN fact_orders o ON c.customer_id = o.customer_id
    GROUP BY 1, 2
),
cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT customer_id) as cohort_size
    FROM cohorts
    GROUP BY cohort_month
)
SELECT
    ca.cohort_month,
    DATEDIFF('month', ca.cohort_month, ca.activity_month) as months_since_join,
    ca.customers,
    cs.cohort_size,
    ROUND(ca.customers * 100.0 / cs.cohort_size, 2) as retention_rate
FROM cohort_activity ca
JOIN cohort_sizes cs ON ca.cohort_month = cs.cohort_month
WHERE ca.cohort_month >= CURRENT_DATE - INTERVAL '12 months'
ORDER BY ca.cohort_month, months_since_join;
```

### Customer Lifetime Value

```sql
-- Calculate CLV by customer segment
WITH customer_metrics AS (
    SELECT
        c.customer_id,
        c.segment,
        COUNT(DISTINCT o.order_id) as order_count,
        SUM(o.order_total) as total_revenue,
        DATEDIFF('day', c.first_order_date, c.last_order_date) as customer_lifespan_days,
        DATEDIFF('day', c.last_order_date, CURRENT_DATE) as days_since_last_order
    FROM dim_customers c
    LEFT JOIN fact_orders o ON c.customer_id = o.customer_id
    WHERE c.first_order_date >= CURRENT_DATE - INTERVAL '3 years'
    GROUP BY c.customer_id, c.segment, c.first_order_date, c.last_order_date
),
clv_calc AS (
    SELECT
        customer_id,
        segment,
        total_revenue,
        order_count,
        CASE
            WHEN customer_lifespan_days = 0 THEN 1
            ELSE customer_lifespan_days
        END as lifespan_days,
        -- Simple CLV: AOV × Purchase Frequency × Expected Lifespan
        (total_revenue / NULLIF(order_count, 0)) * -- AOV
        (order_count * 365.0 / NULLIF(lifespan_days, 1)) * -- Annual frequency
        3 as clv_3_year -- 3-year projection
    FROM customer_metrics
    WHERE days_since_last_order < 365 -- Active customers only
)
SELECT
    segment,
    COUNT(*) as customer_count,
    ROUND(AVG(clv_3_year), 2) as avg_clv,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY clv_3_year), 2) as median_clv,
    ROUND(SUM(clv_3_year), 2) as total_clv
FROM clv_calc
GROUP BY segment
ORDER BY avg_clv DESC;
```

### Detailed CLV Analysis (Per Customer)

```sql
WITH customer_metrics AS (
    SELECT
        c.customer_id,
        c.name as customer_name,
        c.segment as customer_group,
        MIN(o.order_date) as first_order_date,
        MAX(o.order_date) as last_order_date,
        COUNT(o.order_id) as total_orders,
        SUM(o.order_total) as total_spent,
        AVG(o.order_total) as avg_order_value,
        DATEDIFF('day', MIN(o.order_date), MAX(o.order_date)) as customer_age_days
    FROM dim_customers c
    JOIN fact_orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.name, c.segment
)
SELECT
    *,
    total_spent / NULLIF(customer_age_days, 0) * 365 as annualized_value,
    total_orders * 1.0 / NULLIF(customer_age_days, 0) * 365 as purchase_frequency,
    CASE
        WHEN total_spent > 5000 THEN 'VIP'
        WHEN total_spent > 1000 THEN 'High Value'
        WHEN total_spent > 500 THEN 'Medium Value'
        ELSE 'Low Value'
    END as value_segment
FROM customer_metrics
ORDER BY total_spent DESC;
```

### Churn Prediction Features

```sql
-- Generate features for churn prediction
WITH customer_features AS (
    SELECT
        c.customer_id,
        -- Recency features
        DATEDIFF('day', MAX(o.order_date), CURRENT_DATE) as days_since_last_order,
        -- Frequency features
        COUNT(DISTINCT o.order_id) as total_orders,
        COUNT(DISTINCT DATE_TRUNC('month', o.order_date)) as active_months,
        -- Monetary features
        AVG(o.order_total) as avg_order_value,
        SUM(o.order_total) as total_spent,
        -- Engagement features
        COUNT(DISTINCT e.event_type) as event_types_used,
        SUM(CASE WHEN e.event_type = 'support_ticket' THEN 1 ELSE 0 END) as support_tickets,
        -- Trend features
        SUM(CASE WHEN o.order_date >= CURRENT_DATE - 30 THEN o.order_total ELSE 0 END) /
        NULLIF(SUM(CASE WHEN o.order_date >= CURRENT_DATE - 90
                   AND o.order_date < CURRENT_DATE - 30 THEN o.order_total ELSE 0 END), 0) as spend_trend,
        -- Label
        CASE WHEN MAX(o.order_date) < CURRENT_DATE - 90 THEN 1 ELSE 0 END as is_churned
    FROM dim_customers c
    LEFT JOIN fact_orders o ON c.customer_id = o.customer_id
    LEFT JOIN fact_events e ON c.customer_id = e.customer_id
    WHERE c.first_order_date <= CURRENT_DATE - 180 -- Only customers with history
    GROUP BY c.customer_id
)
SELECT * FROM customer_features;
```

## 🚀 Implementation Notes

### Best Practices

1. **Segment Stability**: Don't change segment definitions frequently
2. **Cohort Consistency**: Always use the same cohort period (monthly)
3. **Privacy Compliance**: Anonymize PII in analytics
4. **Statistical Significance**: Ensure segment sizes are meaningful

### Common Pitfalls

- Using current segment for historical analysis
- Not accounting for seasonality in retention
- Ignoring customer acquisition channel in LTV
- Over-segmenting into tiny groups

### Performance Tips

- Pre-calculate RFM scores daily
- Materialize cohort tables
- Index on customer_id, order_date
- Partition events by date

## 📚 Related Resources

- [Marketing Analytics Playbook](marketing-playbook.md)
- [Segmentation Best Practices](guides/segmentation-guide.md)
- [CLV Calculation Methods](guides/clv-methods.md)

## 🔄 Change Log

- 2024-02: Initial version
- 2024-03: Added churn prediction features
