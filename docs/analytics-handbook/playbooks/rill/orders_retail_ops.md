# Playbook: Orders Retail Operations [Retail]

## Overview

- **Metrics View:** `orders_core_metrics`
- **Layer:** 2 - Operational (Retail)
- **Scope Filter:** `scope_retail = true`
- **Audience:** Sales Ops, Store Managers, Marketing
- **Goal:** Daily operations, promotion analysis, customer insights for retail business

## Default Configuration

### Time Range
- Default: Today (real-time) or Yesterday (finalized)

### Pre-applied Filters
- `scope_retail = true` — Retail customers only, excludes B2B/Internal

### Recommended Dimensions

| Priority | Dimension | Use Case |
|----------|-----------|----------|
| Primary | `channel_name` | Specific channel performance |
| Primary | `seller_name` | Staff performance tracking |
| Secondary | `value_group` | Customer tier analysis |
| Secondary | `customer_status` | Active/At Risk/Churned breakdown |
| Secondary | `order_size_band` | Small/Medium/Large order distribution |

### Key Measures

| Measure | Domain Reference | Notes |
|---------|------------------|-------|
| `retail_revenue` | [Net Revenue](../../domains/sales.md#2-net-revenue) | Pre-filtered to scope_retail |
| `retail_orders` | [Total Orders](../../domains/sales.md#4-total-orders) | Pre-filtered to scope_retail |
| `discount_rate` | [Discount Impact](../../domains/sales.md#13-discount-impact) | **VALID only with scope_retail** |
| `discount_amount` | [Discount Impact](../../domains/sales.md#13-discount-impact) | **VALID only with scope_retail** |
| `avg_order_value` | [AOV](../../domains/sales.md#5-aov-average-order-value) | Retail-specific AOV |

## Use Cases

### Daily Sales Monitoring
1. Set time range: Today
2. Check `retail_revenue`, `retail_orders` vs yesterday
3. Group by `order_hour` for hourly trend
4. Identify slow hours for action

### Promotion Effectiveness
1. Filter by promotion period dates
2. Compare `discount_rate` to baseline
3. Check if `retail_revenue` increased proportionally
4. Group by `channel_name` to see promotion reach

### Staff Performance Review
1. Set time range: Last 7 days
2. Group by `seller_name`
3. Measures: `retail_orders`, `retail_revenue`, `avg_order_value`
4. Identify top performers and coaching needs

### Customer Health Check
1. Group by `customer_status`
2. Track Active vs At Risk vs Churned distribution
3. Drill into `value_group` for VIP customer status
4. Alert if VIP customers moving to At Risk

### Order Size Analysis
1. Group by `order_size_band`
2. Compare Small/Medium/Large distribution
3. Cross with `channel_name` to identify upsell opportunities

## Scope Validation

This playbook is **ONLY VALID** with `scope_retail = true` because:

| Metric | Without Scope | With scope_retail |
|--------|---------------|-------------------|
| Discount Rate | 35% (meaningless) | 15% (retail promo actual) |
| AOV | 650K (mixed) | 450K (retail benchmark) |
| Customer Metrics | Polluted | Clean retail segment |

## Related

- **Domain:** [Sales Domain](../../domains/sales.md)
- **Metabase Playbooks:**
  - [Daily Sales Operation](../sales_daily_operation.md)
  - [Daily Sales](../sales_daily_retail.md)
  - [Promotion Analysis](../sales_promotion_analysis.md)
- **Blueprint:** [orders_retail_ops.yaml](../../blueprints/rill/orders_retail_ops.yaml)

