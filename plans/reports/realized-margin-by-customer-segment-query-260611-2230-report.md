# Realized Margin by Customer Segment — Query Report
**Date:** 2026-06-11 | **Scope:** Retail, is_active_order=true, has_cogs=true (649/652 = 99.5% COGS coverage)

---

## LEAD FINDING
**PROMO_DEPENDENT customers (639 orders, 98.5% of cohort) generate −20% avg fully-loaded margin; FULL_PRICE customers (8 orders) generate +0% discount drag and +138K VND profit/order vs +74K VND for promo customers. Overhead allocation, not discounts alone, is destroying margin.**

---

## 1. Margin by Value Group

| value_group | orders | net_rev (M VND) | avg gross_margin% | avg FL_margin% | total FL_profit (M VND) |
|---|---|---|---|---|---|
| VALUE_SILVER | 117 | 402.6 | 48.7% | **+10.8%** | **+25.4** |
| VALUE_GOLD | 46 | 333.9 | 54.3% | **−5.9%** | +22.6 |
| VALUE_VIP | 24 | 304.8 | 56.4% | **+3.6%** | +7.7 |
| VALUE_BRONZE | 462 | 494.7 | 33.4% | **−29.8%** | **−6.8** |

**Finding:** VALUE_BRONZE (71% of orders, 32% of revenue) is net-negative: −6.8M VND total FL loss. VALUE_GOLD has 54% gross margin but sinks to −5.9% FL — overhead allocation hits large-order customers harder. VALUE_SILVER is the sweet spot: best FL margin AND positive total profit.

**Counterintuitive:** VIP/GOLD are higher gross margin but lower fully-loaded margin than SILVER — likely due to larger orders absorbing more overhead per order unit.

SQL: `GROUP BY dc.value_group` joined via `fact_orders.customer_key = dim_customers.customer_key`

---

## 2. Discount Leak — Margin by Discount Sensitivity

| discount_sensitivity | orders | avg gross_margin% | avg FL_margin% | discount% of gross_rev | FL_profit/order (K VND) | total FL_profit (M VND) |
|---|---|---|---|---|---|---|
| FULL_PRICE | 8 | 35.6% | 0.0% | 0.0% | **138.8** | 1.1 |
| PROMO_DEPENDENT | 639 | 38.7% | **−20.1%** | **55.4%** | 74.2 | 47.4 |
| NULL | 2 | 24.0% | −47.0% | 37.9% | 189.7 | 0.4 |

**Finding:** Discounts absorb 55.4% of gross revenue for PROMO_DEPENDENT customers — yet FL margin is −20% (not −55%), meaning the gross margin cushion partially absorbs it but overhead pushes it negative. FULL_PRICE cohort is tiny (8 orders, 11 customers). The +74K FL_profit/order for PROMO_DEPENDENT is **nominal not margin-based** — total 47.4M profit despite −20% margin suggests these orders have higher absolute revenue. FULL_PRICE earns 87% more per order (138K vs 74K) with zero discount cost.

**Concern:** Only 11 FULL_PRICE customers exist — this is not a large protecting segment, but signals pricing power where it exists.

---

## 3. Channel Profitability

| channel | orders | net_rev (M) | avg gross_margin% | avg channel_net_margin% | avg FL_margin% | total FL_profit (M) |
|---|---|---|---|---|---|---|
| Zalo | 37 | 220.5 | 46.2% | 46.2% | **+6.9%** | **+15.9** |
| Shopee - Fine Japan Vietnam | 215 | 345.9 | 42.6% | 27.1% | **−18.8%** | +15.9 |
| Đại Lý (Agency/Wholesale) | 94 | 474.5 | 39.0% | 39.0% | **−9.2%** | +8.4 |
| Facebook | 36 | 91.0 | 58.3% | 58.3% | **+23.2%** | +4.0 |
| Web | 32 | 79.6 | 54.2% | 54.2% | **+24.9%** | +3.4 |
| Shopee - thehealthyus | 22 | 11.5 | 23.4% | 15.5% | **−44.7%** | +1.8 |
| Shopee - JPC SHOP | 132 | 154.1 | 20.6% | 12.7% | **−32.7%** | **−0.2** |

**Shopee findings:**
- Shopee - Fine Japan Vietnam: 215 orders, 345.9M revenue, nominally profitable (+15.9M) but FL margin = **−18.8%** — platform fees dragging −48.7M VND.
- Shopee - JPC SHOP: fully-loaded **loss** (−0.2M), FL margin −32.7%.
- Shopee - thehealthyus: FL margin −44.7% (worst Shopee channel).
- **Web & Facebook are the most profitable on FL margin basis** (+24.9% and +23.2%) with zero platform fees.
- Zalo: 37 orders but +15.9M profit, FL margin +6.9% — highly efficient.

**VALIDATES the hypothesis:** Shopee acquisition is low-ROI after platform fees. Web/Facebook/Zalo channels are significantly more profitable per order.

---

## 4. Returns Drag

- **Total returns:** 1 order with returns out of 652 (0.15% return rate) — returns are NOT a material drag.
- Return amount: 2.3M VND, FL profit on that order: +0.5M VND (still profitable despite return).
- Returns concentrated in Shopee - JPC SHOP (1 return, 2.3M VND return amount).

**Finding:** Returns are negligible. Margin problems are structural (overhead + platform fees + discounts), not return-driven.

---

## 5. Negative-Margin Orders

| Summary | Value |
|---|---|
| Orders with FL_profit < 0 | **199 / 649 (30.7%)** |
| Total FL loss on negative orders | **−113.9M VND** |
| Avg gross_margin on neg orders | 4.1% |
| Avg discount on neg orders | 1,645K VND |

**By channel (top culprits):**
- Shopee - Fine Japan Vietnam: 83 neg-FL orders (cogs_source=both) → −37.5M VND loss
- Shopee - JPC SHOP: 33 neg-FL orders → −20.6M VND loss
- Shopee - Fine Japan Vietnam (sapo_mac only): 29 orders → −6.2M VND
- Shopee - thehealthyus: 12 orders → −1.9M VND

**Drivers:** avg gross_margin of only 4.1% on neg orders — these orders have near-zero gross profit before overhead. Overhead allocation (allocated_overhead column) then tips them negative. Discounts (avg 1,645K VND per neg order) are secondary driver.

**cogs_source='both'** (MISA+Sapo reconciled) has the most negative orders — suggests the reconciled COGS is capturing true cost, not underreporting.

---

## COGS Coverage Caveat
99.5% of active retail orders have COGS (649/652). Margins are reliable. 3 orders without COGS excluded from margin queries — immaterial.

---

## Key Actions (Ranked by Impact)

1. **Stop/re-evaluate Shopee JPC SHOP** — losing money in aggregate (−0.2M FL, 30.7% of all orders are neg-margin, −20.6M on neg orders alone).
2. **VALUE_BRONZE is a loss segment** — 462 orders, −6.8M FL profit. Overhead per small order is killing economics. Either raise AOV or segment out.
3. **Protect Web + Facebook channels** — +24.9% / +23.2% FL margin with no platform fee drag; scale these before Shopee.
4. **FULL_PRICE cohort (11 customers)** deserves white-glove retention — 87% more profit per order, zero discount cost.
5. **Overhead model review** — VIP/GOLD customers (54% gross margin) end up FL-negative or near-zero because overhead allocation makes large-order customers disproportionately expensive; may need revised allocation key.

---

**Status:** DONE
**Summary:** 30.7% of retail orders are fully-loaded loss orders, concentrated in Shopee channels. Web/Facebook/Zalo profitable; Shopee channels structurally underwater after platform fees + overhead. VALUE_BRONZE segment is net-negative. PROMO_DEPENDENT customers are nominally profitable in absolute VND but −20% FL margin.
**Concerns:**
- `discount_sensitivity=NULL` covers 5,458 customers (unclassified) — only 2 orders in this dataset, but bulk of customer base has no sensitivity tag; analysis may shift when classification is complete.
- Overhead allocation method not verified — if allocated_overhead uses a flat per-order rate vs revenue-weighted, VIP/GOLD distortion may be an artifact.
- `PROMO_MIXED` has only 1 customer in dim_customers — segment too thin to draw conclusions.
