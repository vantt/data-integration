# Metabase Dashboard Purpose Verification
**Date:** 2026-06-13 | **Scope:** Dashboards 106, 104, 51, 78, 34, 74 | **Mode:** Read-only

---

## 1. Dashboard 106 — Monthly · Customer Intelligence [Cross]

**Verdict: MATCH**

- 54 dashcards covering segmentation, lifecycle, LTV, health, and affinity.
- Cards confirmed: `Customer Segment Distribution`, `Customer Health Scorecard`, `Total Customer LTV` (snapshot-driven `lifetime_value_to_date`), `Avg LTV per Customer`, `Loyalty Point Distribution by Segment`, `Channel Revenue by Segment`, `Top 10 Products — VIP/First-Time Buyers`.
- SQL uses `mart_customers` snapshot pattern; `value_group`, `customer_status` columns map exactly to value/lifecycle segmentation.

---

## 2. Dashboard 104 — Monthly · Customer Profitability [Retail]

**Verdict: MATCH**

- 18 dashcards; scoped to `customer_type = 'RETAIL'`.
- Cards confirmed: `Channel × Repeat Rate × Contribution Margin` (SQL: `contribution_margin` from `fact_order_economics`, scoped `scope_retail`), `Margin-Negative Retail Customers` (SQL: `is_margin_negative = true`), `PROMO_DEPENDENT Retail Customers` (`discount_sensitivity`), `Avg Contribution Margin by Discount Sensitivity`.
- Contribution margin is the primary metric; LTV is not present (per-customer LTV lives on D-106); this is per-cohort/channel profitability, not per-customer LTV — still within stated purpose.
- Minor gap: no explicit per-customer LTV column visible. `dim_customers` fields used for segmentation counts; actual per-customer margin detail is in `Discount Sensitivity × Value Tier × Margin Detail` table card.

---

## 3. Dashboard 51 — Us CrossBorder [US]

**Verdict: PARTIAL**

- 17 dashcards; filters consistently on `ch.channel_name = 'US'` (not "CrossBorder" string), using dedicated mart `fact_us_shipment_economics`.
- Channel isolation: **confirmed** — every card (Net Revenue, Unique Customers, Orders List, Trend) uses `JOIN dim_channels WHERE channel_name = 'US'`.
- Purpose gap: stated purpose is "US gift-recipient segment (CrossBorder channel, người nhận quà)." Dashboard shows channel-level revenue/orders/fulfillment metrics and data quality cards (`Don thieu gia US`, `SKU chua co gia`). No cards explicitly segmenting gift-recipients or recipient demographic profiling. "Người nhận quà" framing is not reflected as a distinct dimension.
- Dashboard scope is operationally correct for US channel performance monitoring, but does not surface recipient-segment intelligence as the purpose description implies.

---

## 4. Dashboard 78 — Accounting Reconciliation Cockpit [Internal]

**Verdict: MATCH**

- 26 dashcards; all cards focused on MISA/Shopee reconciliation status.
- Cards confirmed: `MISA Coverage %`, `Unmatched Rate %`, `Shopee Fee Coverage %`, `Revenue at Risk by Recon Status`, `Unmatched Orders — Missing MISA Invoice`, `Reconciliation Funnel`, `Recon Coverage Trend by Month`.
- SQL in `Revenue at Risk` uses `has_cogs`, `has_platform_fees` flags from `fact_order_economics` to classify reconciliation states. `Unmatched Orders` card shows individual unmatched order codes.

**Cashflow/AR check:** No cards compute accounts receivable, outstanding debt, or COD collection. Focus is MISA invoice matching and Shopee fee coverage — order-level reconciliation, not cash/AR aging. `fact_payments` (empty) is not referenced. Cashflow/AR purpose is **NOT served** by this dashboard.

---

## 5. Dashboard 34 — Finance P&L [All]

**Verdict: PARTIAL**

- 37 dashcards: revenue, COGS, gross profit, Shopee settlement, 3-tier profit trend, cost breakdown.
- Cards confirmed: `Revenue Waterfall` (SQL: gross_revenue → net via `fact_orders`), `3-Tier Profit Trend` (`gross_profit`, `channel_net_profit`, `fully_loaded_net_profit` from `fact_order_economics`), `Cost Breakdown by Category`, `Overhead Estimated Flag Summary`.
- P&L coverage: **strong** — revenue, COGS, gross margin, channel-level margin, Shopee settlement, 3-tier net profit all present.

**Cashflow/AR check:** No cards reference receivables, outstanding debt, payment aging, or COD collection. `fact_payments` not referenced. Cashflow/AR dimension is **absent** — dashboard is P&L only, not cash flow statement. If the plan intended an AR/cashflow section within D-34, it is not implemented.

---

## 6. Dashboard 74 — Cost Ledger Analyzer [All]

**Verdict: MATCH**

- 11 dashcards; exclusively cost-focused using `fact_order_costs`.
- Cards confirmed: `Total Costs MTD`, `COGS Ratio MTD`, `Platform Fees Ratio MTD`, `Voucher Subsidy Ratio MTD`, `Cost Composition by Month`, `Top 20 Channels by Total Cost`, `Cost Breakdown Donut MTD`.
- SQL: all cards join `fact_order_costs` + `fact_orders` + `dim_channels`. No AR/payment content.

**Cashflow/AR check:** No AR/debt content. Cost ledger purpose is correctly served; cashflow is **not present** (not expected here by name, but noted for completeness).

---

## Cashflow / AR Overall Verdict

**None of the three financial dashboards (78, 34, 74) measure accounts receivable, outstanding debt, or COD collection.**

- Root cause: `fact_payments` is empty (single all-null placeholder row); true cash/AR data is not available in the mart layer.
- D-78 measures order-level MISA/Shopee reconciliation (coverage + unmatched rate) — closest to "recon" but not AR aging.
- D-34 measures P&L (accrual revenue and cost), not cash received or owed.
- D-74 measures cost composition, not cash flows.
- If the plan's "cashflow / công nợ AR" branch requires COD collection tracking or receivables aging, this is **not implementable** with current `fact_payments` data and is therefore **NOT served**.

---

## Summary Table

| DID | Name | Purpose | Verdict |
|-----|------|---------|---------|
| 106 | Monthly · Customer Intelligence | Customer profile/segmentation/LTV | **MATCH** |
| 104 | Monthly · Customer Profitability | Per-customer contribution margin | **MATCH** |
| 51 | Us CrossBorder | US CrossBorder segment (gift-recipient) | **PARTIAL** — channel isolated, recipient segmentation absent |
| 78 | Accounting Reconciliation Cockpit | Reconciliation | **MATCH** (recon only; AR not served) |
| 34 | Finance P&L | P&L | **PARTIAL** — P&L complete; cashflow/AR absent |
| 74 | Cost Ledger Analyzer | Cost ledger | **MATCH** (cost only; AR not applicable) |

---

## Unresolved Questions

1. **D-51 "người nhận quà" intent:** Is the dashboard purpose description aspirational (future recipient-segment analytics) or a current requirement? If current, recipient-level segmentation cards are missing.
2. **D-34 cashflow scope:** Did the plan explicitly include an AR/cashflow section for D-34, or was "cashflow" aspirational pending `fact_payments` population? Needs plan document review.
3. **D-104 per-customer LTV:** Is cohort/channel-level margin (current) sufficient, or was per-customer LTV row-level detail required? LTV lives on D-106 only.
4. **`ch.channel_name = 'US'` vs "CrossBorder":** Are these the same channel in `dim_channels`? If "CrossBorder" is a distinct channel name, D-51 may be filtering the wrong set.
