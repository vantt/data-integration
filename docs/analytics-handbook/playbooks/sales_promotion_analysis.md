# Playbook: Sales Promotion & Discount Analysis

## Overview

- **Audience:** Marketing Manager, Sales Ops, Finance
- **Goal:** Evaluate the effectiveness of promotions, manage discount spending, and analyze payment costs.
- **Collection:** `Sales Analytics` > `Promotions`
- **Data Source:** `fact_orders`, `promotion_redemptions`, `payment_methods`

## Metrics & KPIs

### 1. Promotion Performance

| Metric                 | Business Definition                                         | Logic Reference                                                       |
| :--------------------- | :---------------------------------------------------------- | :-------------------------------------------------------------------- |
| **Usage Count**        | Number of unique orders using a specific promo code.        | [Promotion Performance](../domains/sales.md#14-promotion-performance) |
| **Promo Revenue**      | Total GMV generated from orders with a promotion.           | [Promotion Performance](../domains/sales.md#14-promotion-performance) |
| **Uplift (Estimated)** | Comparison of AOV (Promo Orders) vs AOV (Non-Promo Orders). | _Calculated in Pivot Table_                                           |

### 2. Discount Efficiency

| Metric                   | Business Definition                         | Logic Reference                                           |
| :----------------------- | :------------------------------------------ | :-------------------------------------------------------- |
| **Total Discount Value** | Total money "given away" in discounts.      | [Discount Impact](../domains/sales.md#13-discount-impact) |
| **Discount Rate %**      | `Total Discount / GMV`.                     | [Discount Impact](../domains/sales.md#13-discount-impact) |
| **Discount Frequency**   | `% of Orders` that have a discount applied. | [Discount Impact](../domains/sales.md#13-discount-impact) |

## Analysis Workflows

### Scenario A: Campaign ROI Analysis

**Goal:** Determine if "Summer Sale 2024" was profitable.

1. Filter `Promotion Performance` by Campaign Name.
2. Compare `Promo Revenue` vs `Marketing Spend` (Offline data).
3. Check `Discount Rate %`. If Discount > Margin, the campaign destroyed value.

### Scenario B: Discount Abuse Monitoring

**Goal:** Identify stores or channels giving excessive discretionary discounts.

1. Create a "Discount by Store" table.
2. Sort by `Discount Rate %` DESC.
3. Drill down into specific orders for outliers (e.g., > 50% discount).

### Scenario C: Payment Cost Optimization

**Goal:** Reduce transaction fees.

1. Analyze [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution).
2. Calculate cost per method (e.g., Credit Card 2% vs COD 0%).
3. Identify opportunities to steer customers to lower-cost methods.

## Action Triggers

| Metric | Threshold | Owner | Action |
| :----- | :-------- | :---- | :----- |
| **Discount Rate %** | > 15% of GMV | Marketing Manager | Review top discount channels, check for abuse patterns |
| **Discount Rate %** | > 25% of GMV | Finance | Escalate — margin erosion alert, freeze discretionary discounts |
| **AOV Uplift** | Promo AOV < Non-Promo AOV | Marketing Manager | Re-evaluate promo targeting — attracting low-value orders |
| **Top Promo Concentration** | Top 1 promo > 50% of promo revenue | Sales Ops | Diversify promo portfolio, reduce single-promo dependency |
| **High-Discount Orders** | > 5 orders/week with CK > 30% from same branch | Sales Ops | Audit branch, check for discount abuse or system error |
| **Promo Usage Count** | MoM drop > 30% | Marketing Manager | Check if promo expired, communicate with channels |
| **Channel Discount Rate** | Any channel > 20% avg discount | Sales Ops | Review channel-specific discount policies |

## Reading Flow

1. **Start at View 1 — Discount Overview:** Check Total Discount Amount and Discount Rate % to assess overall discount health. If Discount Rate > 15%, investigate further.
2. **Promo vs Non-Promo comparison:** Confirm promo orders generate higher AOV (positive uplift). Negative uplift = promo attracting low-value buyers.
3. **Discount Depth Histogram:** Scan for concentration in high-discount buckets (> 30%). Heavy tail = potential abuse or overly generous campaigns.
4. **Move to View 2 — Promotion Performance:** Identify top-performing promotions by revenue and usage. Cross-check efficiency in the Performance Table (high discount rate + low usage = inefficient).
5. **Move to View 3 — Channel Impact:** Compare promo dependency by channel. High promo revenue share = channel too reliant on discounts.
6. **High-Discount Orders List:** Drill into specific suspicious orders for audit. Filter by branch/staff if abuse pattern detected.

## Design Spec

See [Design Spec: Sales Promotion & Discount Analysis](../designs/sales_promotion_analysis.md).

## Visualization Configs

### Discount Depth Histogram

_Distribution of orders by discount percentage._

```sql
SELECT
  FLOOR((total_discount_amount / NULLIF(gmv,0)) * 10) * 10 as discount_bucket,
  COUNT(*) as order_count
FROM fact_orders
WHERE total_discount_amount > 0
GROUP BY 1
ORDER BY 1
```

- **Viz settings:** Bar chart. X-axis: `discount_bucket` (0%, 10%, 20%...), Y-axis: `order_count`.

### Promotion Leaderboard

_Top 10 Promotions by Revenue._

```json
{
  "display": "table",
  "visualization_settings": {
    "table.columns": [
      { "name": "promotion_name", "enabled": true },
      { "name": "usage_count", "enabled": true },
      { "name": "revenue_with_promo", "enabled": true }
    ]
  }
}
```
