# Playbook: Orders Executive [All]

## Overview

- **Metrics View:** `orders_core_metrics`
- **Layer:** 1 - Executive
- **Scope Filter:** `scope_sales = true`
- **Audience:** CEO, Founders, Directors
- **Goal:** Business health overview — revenue trends, channel mix, operational efficiency

## Default Configuration

### Time Range
- Default: Last 7 days (weekly pulse) or Last 30 days (monthly review)

### Pre-applied Filters
- `scope_sales = true` — excludes internal orders, cancelled

### Recommended Dimensions

| Priority | Dimension | Use Case |
|----------|-----------|----------|
| Primary | `channel_category` | Online vs Offline split |
| Primary | `customer_type` | Retail vs B2B revenue mix |
| Secondary | `platform` | Shopee/Lazada/TikTok/Web/POS breakdown |
| Secondary | `value_group` | VIP/Gold/Silver/Bronze customer contribution |

### Key Measures

| Measure | Domain Reference | Notes |
|---------|------------------|-------|
| `sales_revenue` | [Net Revenue](../../domains/sales.md#2-net-revenue) | Pre-filtered to scope_sales |
| `sales_orders` | [Total Orders](../../domains/sales.md#4-total-orders) | Pre-filtered to scope_sales |
| `avg_order_value` | [AOV](../../domains/sales.md#5-aov-average-order-value) | Use with scope filter |
| `fulfillment_rate` | - | Operational health indicator |

## Use Cases

### Weekly Business Pulse
1. Set time range: Last 7 days
2. Compare to previous period
3. Check: `sales_revenue`, `sales_orders`, `avg_order_value`
4. Group by `channel_category` for mix shifts

### Monthly Revenue Review
1. Set time range: Last 30 days
2. Group by `customer_type` to see Retail vs B2B contribution
3. Drill into `platform` for channel-specific performance
4. Check `value_group` for VIP customer trends

### Channel Health Check
1. Group by `platform`
2. Add `channel_format` for deeper breakdown
3. Compare `fulfillment_rate` across channels
4. Identify underperforming channels

## Warning: Scope Discipline

**DO NOT** analyze discount metrics at this layer. Discounts mix Retail promotions with B2B wholesale pricing → meaningless aggregate.

For discount analysis → use `orders_retail_ops.md` with `scope_retail = true`.

## Related

- **Domain:** [Sales Domain](../../domains/sales.md)
- **Metabase Playbooks:** 
  - [CEO Weekly Pulse](../ceo_weekly_pulse.md)
  - [CEO Monthly Scorecard](../ceo_monthly_scorecard.md)
- **Blueprint:** [orders_executive.yaml](../../blueprints/rill/orders_executive.yaml)

