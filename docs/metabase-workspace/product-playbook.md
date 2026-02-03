# Product Analytics Playbook

## 🎯 Overview

This playbook covers product performance, inventory health, and merchandising analytics:

- **Product Performance** → [product-blueprint-performance.md] _(coming soon)_
- **Inventory Management** → [product-blueprint-inventory.md] _(coming soon)_

## 📊 Business Context

### Target Users

- **Merchandising Team**: Assortment planning and pricing
- **Inventory Managers**: Stock levels and replenishment
- **Marketing Team**: Product promotion strategies
- **Management**: Top-line product performance

### Update Frequency

- **Real-time**: Inventory status (Stock level)
- **Daily**: Sales performance by product/category
- **Weekly**: Merchandising review, slow-moving stock
- **Monthly**: Category performance, lifecycle analysis

## 🎯 Key Product Metrics

### Performance Metrics

| Metric              | Formula                    | Business Rule            | Target      |
| ------------------- | -------------------------- | ------------------------ | ----------- |
| **Units Sold**      | SUM(quantity)              | Confirmed orders         | Growth >10% |
| **Product Revenue** | SUM(line_amount)           | Gross revenue            | Growth >15% |
| **Attach Rate**     | Prod Orders / Total Orders | For accessories/warranty | >15%        |
| **Return Rate**     | Returns / Units Sold       | Quality control          | <2%         |

### Inventory Metrics

| Metric                 | Formula                               | Business Rule       | Target     |
| ---------------------- | ------------------------------------- | ------------------- | ---------- |
| **Inventory Turnover** | COGS / Avg Inventory                  | Efficiency          | >4x/year   |
| **Days of Supply**     | Stock / Daily Sales Rate              | Stock health        | 30-60 days |
| **Out of Stock Rate**  | OOS SKUs / Total SKUs                 | Availability        | <5%        |
| **Sell-through Rate**  | Units Sold / (Start Stock + Received) | Seasonal efficiency | >80%       |

## 📈 Dashboard Designs

### 1. Product Performance Dashboard

**Purpose**: Monitor sales velocity and revenue contribution by product

**Layout**:

```
┌─────────────────────────┬─────────────────────────┐
┌─────────────────────────┬─────────────────────────┐
│ Revenue Contribution    │ Top Movers (Volume)     │
│ (Treemap)              │ (Bar Chart)             │
└─────────────────────────┴─────────────────────────┘
┌─────────────────────────┬─────────────────────────┐
│ Category Mix Trend      │ Return Rate by Cat      │
│ (Stacked Area)         │ (Bar Chart)             │
└─────────────────────────┴─────────────────────────┘
```

### 2. Inventory Health Dashboard

**Purpose**: Optimizing stock levels and identifying dead stock

**Layout**:

```
┌─────────────────────────┬─────────────────────────┐
│ Stock Status (Gauge)    │ Inventory Value (KPI)   │
│ In/Low/OOS              │ Total $$ held           │
└─────────────────────────┴─────────────────────────┘
┌─────────────────────────┬─────────────────────────┐
│ Slow Moving Stock       │ Stock Cover by Cat      │
│ (Table: >90 days)       │ (Bar Chart: Days)       │
└─────────────────────────┴─────────────────────────┘
```

## 💾 Data Requirements

### Source Tables

| Table              | Update Frequency | Key Fields                     | Data Quality Checks |
| ------------------ | ---------------- | ------------------------------ | ------------------- |
| `dim_products`     | Daily            | product_id, sku, cost_price    | Valid SKUs          |
| `fact_inventory`   | Real-time        | product_id, quantity, location | No negative stock   |
| `fact_order_items` | Real-time        | product_id, quantity, price    | Links to orders     |
| `dim_categories`   | Monthly          | category_id, name, hierarchy   | No orphans          |

## 🔧 SQL Library

### Top Selling Products

```sql
SELECT
    p.product_name,
    p.sku,
    SUM(oli.quantity) as units_sold,
    SUM(oli.line_amount) as revenue,
    COUNT(DISTINCT oli.order_id) as orders,
    AVG(oli.price) as avg_price,
    SUM(oli.discount_amount) as total_discount
FROM order_line_items oli
JOIN products p ON oli.product_id = p.product_id
WHERE oli.created_on >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY p.product_id, p.product_name, p.sku
ORDER BY revenue DESC
LIMIT 50
```

### Product Velocity

```sql
SELECT
    p.product_name,
    SUM(oli.quantity) as total_sold,
    AVG(oli.quantity) as avg_per_order,
    COUNT(DISTINCT DATE(o.created_on)) as days_sold,
    SUM(oli.quantity) * 1.0 /
        NULLIF(COUNT(DISTINCT DATE(o.created_on)), 0) as daily_velocity
FROM orders o
JOIN order_line_items oli ON o.order_id = oli.order_id
JOIN products p ON oli.product_id = p.product_id
WHERE o.created_on >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY p.product_id, p.product_name
ORDER BY daily_velocity DESC
```

### Stock Status Summary

```sql
SELECT
    inventory_status,
    COUNT(*) as product_count,
    SUM(quantity * cost_price) as inventory_value
FROM products
GROUP BY inventory_status
```

### Slow-Moving Inventory (Dead Stock)

```sql
SELECT
    p.product_name,
    p.sku,
    pv.quantity as current_stock,
    MAX(o.created_on) as last_sold_date,
    DATEDIFF(day, MAX(o.created_on), CURRENT_DATE) as days_since_last_sale,
    pv.quantity * p.cost_price as inventory_value
FROM products p
JOIN product_variants pv ON p.product_id = pv.product_id
LEFT JOIN order_line_items oli ON pv.variant_id = oli.variant_id
LEFT JOIN orders o ON oli.order_id = o.order_id
GROUP BY p.product_id, p.product_name, p.sku, pv.quantity, p.cost_price
HAVING days_since_last_sale > 90 OR MAX(o.created_on) IS NULL
ORDER BY inventory_value DESC
```

## 🚀 Implementation Notes

### Best Practices

1. **ABC Analysis**: Classify products (A=Top 20%, B=Next 30%, C=Bottom 50%)
2. **Seasonality**: Compare velocity against same period last year
3. **Bundling**: Analyze "frequently bought together" for upsell
4. **Historical Stock**: Snapshot inventory levels daily for trend analysis

### Common Pitfalls

1. Ignoring returns in net revenue calculations
2. Calculating supply days based on average instead of peak demand
3. Not separating new launches from slow movers
