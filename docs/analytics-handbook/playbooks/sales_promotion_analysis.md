# Playbook: Sales Promotion & Discount Analysis

## Overview

- **Audience:** Marketing Manager, Sales Ops, Finance
- **Goal:** Evaluate the effectiveness of promotions, manage discount spending, and analyze payment costs.
- **Collection:** `Marketing & Customers`
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

## Discount ROI

### Overview

The Discount ROI tab answers whether promotion spending generates incremental revenue above the cost of the discount.

**Methodology:**
- **Baseline:** Average net revenue per non-discounted order in the same 30-day window and channel.
- **Incremental revenue:** `actual_promo_revenue - (baseline_AOV × promo_order_count)`
- **ROI %:** `(incremental_revenue - discount_cost) / discount_cost × 100`
- **Limitation:** No holdout group. Treat as directional signal, not causal proof.

### Metrics

| Metric | Definition |
| :----- | :--------- |
| **Discount Amount** | Total VND given away as discount for this campaign |
| **Incremental Revenue** | Actual promo revenue minus estimated baseline (non-promo AOV × order count) |
| **ROI %** | `(incremental_revenue - discount_amount) / discount_amount × 100` |
| **ROI Trend** | Monthly aggregate ROI % over last 6 months |

### Action Triggers

| Signal | Threshold | Action |
| :----- | :-------- | :----- |
| **ROI %** | < -50% | Eliminate campaign — losing >50 VND per 100 VND spent on discounts |
| **ROI %** | > 200% | Scale campaign — every 100 VND discount drives 200 VND net incremental return |
| **ROI Trend** | 3 consecutive months negative | Audit entire promo strategy — systemic discount dependency without uplift |
| **Discount Amount high, ROI low** | High spend + ROI < 0 | Pause campaign, redirect budget to positive-ROI codes |

### Reading Flow

1. **Discount ROI by Promotion Code (table):** Sort by ROI % ASC to find worst performers (red rows). Sort DESC to find candidates for scale-up (green rows).
2. **Discount ROI Trend (line):** Check if overall portfolio ROI is improving or deteriorating month-over-month. A negative trend with rising discount spend = structural problem.
3. **Cross-reference with Tab 2 (Promotion Performance):** High-usage promos with negative ROI are the highest-priority to cut — they scale the loss.

---

## Analysis Workflows

### Scenario A: Campaign ROI Analysis

**Goal:** Determine if "Summer Sale 2024" was profitable.

1. Filter `Promotion Performance` by Campaign Name.
2. Compare `Promo Revenue` vs `Marketing Spend` (Offline data).
3. Check `Discount Rate %`. If Discount > Margin, the campaign destroyed value.

### Scenario B: Discount Abuse Monitoring

**Goal:** Identify customers, codes, or staff abusing discretionary discounts.

1. Go to **Tab: Phát hiện lạm dụng & Bất thường**.
2. Check **Abuse Risk Scorecard** — any count > 0 triggers action.
3. **Top 20 Customers** table: sort by "Tong CK 30d" — flag rows with "Nghi van" status.
4. **Suspicious Codes** table: unique_ratio < 0.2 = code is widely shared/leaked → kill immediately.
5. **Staff Leaderboard**: "Rui ro cao" = escalate to Sales Manager same day.
6. **Staff × Customer**: any row appearing = investigate within 1 week.

### Scenario D: Discount Cannibalization Check

**Goal:** Verify that promo-period sales gains are incremental, not cannibalized from non-promoted categories.

1. Go to **Tab: Discount ROI** → **Discount Cannibalization by Product Type** table.
2. Filter by "Co KM = Y" (promoted types) — check Delta units: are they up?
3. Filter by "Co KM = N" (non-promoted types) — check Delta units: are they down by similar amount?
4. If non-promo drop ≈ promo gain → demand shifted, no incremental lift → review promo strategy.
5. If non-promo stable or up → promotion is generating additive demand → good signal.

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
| **AOV by Band** | AOV monotonic increase across all discount bands | Marketing Manager | Likely threshold effect not lift — re-evaluate min-spend promo design |
| **AOV by Band** | AOV inverted-U with peak at low band (1-10%) | Marketing Manager | Optimal band exists — tighten max discount, concentrate promos at that band |
| **Top Promo Concentration** | Top 1 promo > 50% of promo revenue | Sales Ops | Diversify promo portfolio, reduce single-promo dependency |
| **High-Discount Orders** | > 5 orders/week with CK > 30% from same branch | Sales Ops | Audit branch, check for discount abuse or system error |

### Abuse Detection Triggers (Tab: Phát hiện lạm dụng & Bất thường)

| Signal | Threshold | Owner | Action | SLA |
| :----- | :-------- | :---- | :----- | :-- |
| **Suspicious customers count** | > 5 in 30d | Finance + Sales Ops | Weekly review of flagged customer list — cross-check order patterns | 7 days |
| **Promo code unique_ratio** | < 0.3 AND total_uses > 10 | Marketing | Kill or restrict code immediately — stop discount bleeding | 48 hours |
| **Staff high-discount orders** | > 10 orders with CK > 30% | Sales Manager | Review staff, check if discretionary discounts authorized | 3 days |
| **Staff-customer concentration** | Same staff + same customer >= 3 orders AND avg_ck > 20% | Sales Manager + Finance | Investigate for collusion — compare against peer staff patterns | 7 days |
| **Cannibalization signal** | Non-promo category units drop ≈ promo category units gain (same period) | Marketing | Review promo strategy — shift to additive demand generation, avoid best-sellers | 14 days |
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
