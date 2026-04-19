# Playbook: Orders B2B Operations [B2B]

## Overview

- **Metrics View:** `orders_core_metrics`
- **Layer:** 2 - Operational (B2B)
- **Scope Filter:** `scope_b2b = true`
- **Audience:** B2B Sales, Partner Managers
- **Goal:** Wholesale/Partner order tracking, credit monitoring, B2B customer management

## Default Configuration

### Time Range
- Default: Last 7 days or Last 30 days (B2B cycles are longer)

### Pre-applied Filters
- `scope_b2b = true` — WHOLESALE + PARTNER customers only

### Recommended Dimensions

| Priority | Dimension | Use Case |
|----------|-----------|----------|
| Primary | `customer_type` | Wholesale vs Partner split |
| Primary | `customer_name` | Individual partner tracking |
| Secondary | `channel_name` | B2B channel breakdown |
| Secondary | `payment_status` | Credit/Payment tracking |
| Secondary | `fulfillment_status` | Delivery tracking |

### Key Measures

| Measure | Domain Reference | Notes |
|---------|------------------|-------|
| `b2b_revenue` | [Net Revenue](../../domains/sales.md#2-net-revenue) | Pre-filtered to scope_b2b |
| `b2b_orders` | [Total Orders](../../domains/sales.md#4-total-orders) | Pre-filtered to scope_b2b |
| `avg_order_value` | [AOV](../../domains/sales.md#5-aov-average-order-value) | B2B AOV (~2.5M typical) |
| `avg_hours_to_complete` | - | B2B fulfillment SLA tracking |

## Use Cases

### Partner Performance Review
1. Set time range: Last 30 days
2. Group by `customer_name`
3. Measures: `b2b_orders`, `b2b_revenue`
4. Rank partners by contribution

### Wholesale vs Partner Mix
1. Group by `customer_type`
2. Compare WHOLESALE vs PARTNER contribution
3. Track trend over time

### Credit Risk Monitoring
1. Filter: `payment_status = 'pending'`
2. Group by `customer_name`
3. Identify customers with outstanding payments
4. Cross with order age for risk assessment

### Fulfillment SLA Tracking
1. Group by `fulfillment_status`
2. Check `pending_gt_24h_orders`, `pending_gt_48h_orders`
3. B2B orders often have longer fulfillment windows

## Scope Notes

**DO NOT analyze these at B2B layer:**
- `discount_rate` — B2B discounts are wholesale pricing, not promotions
- Promotion ROI — B2B doesn't participate in retail promotions
- Customer acquisition — B2B customers are acquired through sales, not marketing

**B2B-specific insights:**
- Higher AOV (2-5x retail)
- Longer order cycles
- Payment terms / credit considerations
- Relationship-based (repeat partners)

## Related

- **Domain:** [Sales Domain](../../domains/sales.md)
- **Metabase Playbooks:**
  - [B2B Orders Tracking](../b2b_orders_tracking.md) (if exists)
- **Blueprint:** [orders_b2b_ops.yaml](../../blueprints/rill/orders_b2b_ops.yaml)

