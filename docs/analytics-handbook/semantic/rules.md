# Business Rules

Cross-cutting business rules — apply consistently across every blueprint and Rill metric.

> **Canonical source:** this file
> **Domain context:** [Sales](../domains/sales.md), [Finance](../domains/finance.md)

---

## VAT Treatment

> **Type:** Rule | **Domain:** [Sales](../domains/sales.md) | **Status:** `active`
> **Applies To:** net_revenue, vat_amount, total_collected, gross_revenue | **Since:** 2024-01-01

**Rule:** Sapo prices are VAT-inclusive — never divide by a blanket rate; use pre-computed mart columns.

**SQL:**
```sql
-- ✅ Correct pattern — use pre-computed columns
SUM(net_revenue)          -- VAT already stripped
SUM(vat_amount)           -- VAT isolated
SUM(total_collected)      -- gross_revenue minus discount, VAT still included

-- ❌ Wrong pattern — blanket rate assumes all orders are 8% VAT, misses 10% items and 0% exports
SUM(total_price / 1.08)   -- wrong direction AND wrong rate for ~40% of items
SUM(total_price * 8/108)  -- wrong: blanket rate ignores 10% tier and VAT-exempt exports
```

**Intent:** Sapo embeds VAT in `total_price`. Two rates exist (8/108, 10/110) and ~60% of orders (US export + no-VAT items) have `vat_amount = 0`. Any blanket `/1.08` formula is wrong for the majority of the dataset and inflates P&L by 8–10%.

**Applies To:**
- [net_revenue](metrics.md#net_revenue) — primary revenue metric after VAT strip
- [vat_amount](metrics.md#vat_amount) — pre-computed field; never recalculate
- [total_collected](metrics.md#total_collected) — post-discount, pre-VAT-strip; used for top-line only
- [gross_revenue](metrics.md#gross_revenue) — pre-discount baseline; still VAT-inclusive

#### ⚠️ Conflicts
*None.*

#### 🔗 Related Rules
| Rule | Relationship |
|---|---|
| [Cancellation Convention](#cancellation-convention) | Both are revenue filter prerequisites — apply before VAT strip |
| [Scope Required for Promotion/Discount](#scope-required-for-promotiondiscount) | Scope filter + VAT treatment must both be applied for correct net_revenue |

#### ❌ Common Violations
- `SUM(total_price) / 1.08` — author assumes uniform 8% VAT; fails for 10% products and exports
- `SUM(total_price * 8/108)` — same blanket rate error, different form
- Using `total_collected` as a margin numerator (it still contains VAT, so margin % is understated)
- Forgetting to strip VAT before comparing against MISA P&L figures (MISA uses net revenue)

#### 📊 Impact if Violated
P&L inflated by 8–10% when using `total_collected` instead of `net_revenue` for margin comparison. Blanket `/1.08` formula is wrong for ~60% of orders (VAT-exempt or 10% tier).

---

## Cancellation Convention

> **Type:** Rule | **Domain:** [Sales](../domains/sales.md) | **Status:** `active`
> **Applies To:** scope_sales, scope_retail, scope_b2b, status | **Since:** 2024-01-01

**Rule:** Exclude `CANCELLED` orders for revenue metrics — use `is_active_order` (pre-computed gate). Do NOT embed status exclusion in scope_* definitions; scope_* is pure channel/segment classification.

**SQL:**
```sql
-- ✅ Correct — revenue metric: scope + status gate
WHERE scope_retail AND is_active_order

-- ✅ Correct — count all orders including cancelled
WHERE scope_retail

-- ✅ Correct — count cancelled orders only
WHERE scope_retail AND NOT is_active_order

-- ❌ Wrong — embedding status in scope derivation (scope_* no longer includes this)
WHERE is_sales_channel = true AND status != 'CANCELLED'

-- ❌ Wrong — scope_* alone for revenue (scope_sales includes cancelled after refactor)
WHERE scope_sales   -- missing AND is_active_order for revenue
```

**Intent:** Sapo's `status` field uses `CANCELLED` for cancelled orders. `is_active_order` is a pre-computed boolean column in `fact_orders` and `fact_order_economics`. Scope flags classify channel/segment; `is_active_order` gates on execution status — two orthogonal concerns.

**Applies To:**
- [is_active_order](segments.md#is_active_order) — pre-computed gate implementing this rule
- [scope_sales](segments.md#scope_sales) — pure channel classification, no status filter
- [scope_retail](segments.md#scope_retail) — pure channel + retail segment, no status filter
- [scope_b2b](segments.md#scope_b2b) — pure channel + B2B segment, no status filter
- [status](dimensions.md#status) — raw dimension; use `is_active_order` not raw comparisons

#### ⚠️ Conflicts
*None.*

#### 🔗 Related Rules
| Rule | Relationship |
|---|---|
| [VAT Treatment](#vat-treatment) | Cancellation filter must be applied before VAT metrics are summed |
| [Scope Required for Promotion/Discount](#scope-required-for-promotiondiscount) | scope_retail implements both cancellation and B2B exclusion |

#### ❌ Common Violations
- Using raw `status` filter in a new query instead of reusing scope flags
- `WHERE status = 'COMPLETED'` for revenue — misses all non-cancelled, non-completed active orders

#### 📊 Impact if Violated
Not excluding `CANCELLED` orders includes cancelled order volume in revenue and count metrics.

---

## is_completed Definition

> **Type:** Rule | **Domain:** [Sales](../domains/sales.md) | **Status:** `active`
> **Applies To:** is_completed, Order entity | **Since:** 2024-01-01

**Rule:** An order is "completed" only when BOTH fulfilled AND paid — use the pre-computed `is_completed` boolean, never re-derive the two-condition check.

**SQL:**
```sql
-- ✅ Correct pattern — pre-computed boolean
WHERE is_completed

-- ❌ Wrong pattern — misclassifies delivered-but-unpaid orders as completed
WHERE status = 'COMPLETED'

-- ❌ Wrong pattern — partial check: fulfilled but not necessarily paid
WHERE fulfillment_status = 'fulfilled'

-- ❌ Wrong pattern — re-deriving what the mart already computes
WHERE fulfillment_status = 'fulfilled' AND payment_status = 'paid'
```

**Intent:** The Sapo `status` field reflects fulfillment state, not payment state. An order can show `COMPLETED` fulfillment while still having an outstanding payment. `is_completed` is the only field that enforces both conditions simultaneously.

**Applies To:**
- [is_completed](dimensions.md#is_completed) — the pre-computed boolean to use
- [Order entity](entities.md#order) — defines the completion lifecycle

#### ⚠️ Conflicts
*None.*

#### 🔗 Related Rules
| Rule | Relationship |
|---|---|
| [Cancellation Convention](#cancellation-convention) | is_completed implicitly excludes cancelled orders; scope_sales adds explicit CANCELLED exclusion |
| [Returns Not Restated in P&L](#returns-not-restated-in-pl) | Completed orders can still generate returns; completion ≠ final financial state |

#### ❌ Common Violations
- `WHERE status = 'COMPLETED'` — common shortcut that misclassifies ~3–8% of orders where payment collection lags delivery
- Filtering on `fulfillment_status` alone in COD (cash-on-delivery) scenarios where payment is collected at door
- Using `is_completed` to claim an order's P&L is final (returns can still happen after completion)

#### 📊 Impact if Violated
`status = 'COMPLETED'` overclassifies orders by the proportion with payment collection lag. In COD-heavy channels (offline POS), this can be 5–15% of order volume during any given day.

---

## Order Count Convention

> **Type:** Rule | **Domain:** [Sales](../domains/sales.md) | **Status:** `active`
> **Applies To:** orders_count, any metric using COUNT | **Since:** 2024-01-01

**Rule:** Always use `COUNT(DISTINCT order_id)` — never `COUNT(*)` — whenever the query touches item-level or line-level tables.

**SQL:**
```sql
-- ✅ Correct pattern — safe regardless of join type
COUNT(DISTINCT order_id) AS orders_count

-- ✅ Correct pattern — on fact_orders alone (no item join), COUNT(*) is technically safe
-- but COUNT(DISTINCT order_id) is preferred for consistency
COUNT(DISTINCT fo.order_id) AS orders_count

-- ❌ Wrong pattern — overcounts when joined to fact_order_items or fact_sales
COUNT(*) AS orders_count

-- ❌ Wrong pattern — COUNT(order_id) without DISTINCT still duplicates on item joins
COUNT(fo.order_id) AS orders_count
```

**Intent:** `fact_order_items` and `fact_sales` have one row per line item. A 3-SKU order = 3 rows. Any join without `DISTINCT` inflates order count by avg items per order (~1.5×).

**Applies To:**
- [orders_count](metrics.md#orders_count) — the primary affected metric
- Any metric built on `COUNT` when query joins to item-level tables

#### ⚠️ Conflicts
*None.*

#### 🔗 Related Rules
| Rule | Relationship |
|---|---|
| [Shopee Service Fee — No Double-Count](#shopee-service-fee--no-double-count) | Both rules address overcounting from multi-row joins |
| [Scope Required for Promotion/Discount](#scope-required-for-promotiondiscount) | Scope filter should be applied before COUNT to avoid counting excluded orders |

#### ❌ Common Violations
- `COUNT(*)` in a query that JOINs `fact_orders` to `fact_order_items` — inflates by avg items per order
- `COUNT(order_id)` without DISTINCT — same overcount, different syntax
- Computing AOV as `SUM(net_revenue) / COUNT(*)` after an item join — both numerator (if not aggregated) and denominator are wrong

#### 📊 Impact if Violated
~1.5× overcount when joining items without DISTINCT (based on average 1.5 line items per order). For orders with 3+ SKUs (bundle orders), overcount can reach 3×.

---

## Scope Required for Promotion/Discount

> **Type:** Rule | **Domain:** [Sales](../domains/sales.md) | **Status:** `active`
> **Applies To:** discount_rate, discount_amount, aov, scope_retail | **Since:** 2024-01-01

**Rule:** All discount, promotion, and AOV metrics MUST filter `scope_retail` — never `scope_sales` alone.

**SQL:**
```sql
-- ✅ Correct pattern — retail scope isolates consumer promotions
SELECT
    AVG(net_revenue)                              AS aov,
    SUM(discount_amount) / SUM(gross_revenue)     AS discount_rate
FROM fact_orders
WHERE scope_retail

-- ❌ Wrong pattern — mixes retail promotions with B2B wholesale pricing
SELECT
    AVG(net_revenue)                              AS aov,
    SUM(discount_amount) / SUM(gross_revenue)     AS discount_rate
FROM fact_orders
WHERE scope_sales   -- includes B2B orders with 40-50% structural discounts
```

**Intent:** B2B orders carry a structural 40–50% "discount" that is actually wholesale pricing — not a promotion. Mixing B2B and retail makes discount rate and AOV metrics meaningless. Retail AOV ~450K, B2B AOV ~2.5M; the blended number (~650K) represents neither segment.

**Applies To:**
- [discount_rate](metrics.md#discount_rate) — retail-only meaningful metric
- [discount_amount](metrics.md#discount_amount) — retail scope for promo analysis
- [aov](metrics.md#aov) — retail AOV vs B2B AOV are separate KPIs
- [scope_retail](segments.md#scope_retail) — the required filter

#### ⚠️ Conflicts
*None.*

#### 🔗 Related Rules
| Rule | Relationship |
|---|---|
| [Cancellation Convention](#cancellation-convention) | scope_retail already implements cancellation exclusion |
| [Discount Classification Taxonomy](#discount-classification-taxonomy) | Taxonomy applies within scope_retail; wholesale_explicit type appears when B2B leaks through |

#### ❌ Common Violations
- Using `WHERE scope_sales` for discount analysis — includes B2B wholesale discounts in promotion metrics
- Building a "discount rate" dashboard without any scope filter — produces ~35% blended rate (neither retail ~10-20% nor B2B ~40-50%)
- Comparing AOV across periods where B2B order mix varied — not a like-for-like comparison without scope_retail

#### 📊 Impact if Violated
Blended discount rate ~35% is meaningless — retail is ~10–20%, B2B is ~40–50%. AOV: retail ~450K, B2B ~2.5M, blended ~650K understates retail and overstates typical single-consumer spend.

---

## Date Key Timezone

> **Type:** Rule | **Domain:** [Sales](../domains/sales.md), [Finance](../domains/finance.md) | **Status:** `active`
> **Applies To:** date_key, ordered_at, KPI window functions | **Since:** 2024-01-01

**Rule:** `date_key` is ICT (Asia/Ho_Chi_Minh) — filter on `date_key` directly or use `ordered_at` (TIMESTAMPTZ, auto-converts); never apply manual UTC offset.

**SQL:**
```sql
-- ✅ Correct pattern — date_key is ICT, direct comparison is correct
WHERE date_key = current_date - 1

-- ✅ Correct pattern — TIMESTAMPTZ: Metabase/DuckDB auto-converts to ICT session TZ
WHERE ordered_at >= '2026-06-01'::date

-- ✅ Correct pattern — KPI window using ICT helper
WHERE date_key BETWEEN _yesterday_window_ict()

-- ❌ Wrong pattern — manual UTC offset double-converts; DuckDB session is already ICT
WHERE ordered_at >= (current_date - 1)::timestamp AT TIME ZONE 'UTC'

-- ❌ Wrong pattern — treating ordered_at as naive timestamp truncates at UTC midnight
WHERE DATE_TRUNC('day', ordered_at) = current_date - 1
```

**Intent:** `fact_orders.date_key` is derived in ICT at pipeline time (`profiles.yml TimeZone=Asia/Ho_Chi_Minh`). Orders placed 23:00–06:59 ICT belong to that ICT calendar day but fall on a different UTC day. Filtering by UTC boundaries assigns those orders to the wrong reporting period.

**Applies To:**
- [date_key](dimensions.md#date_key) — ICT-derived date; use for all period filters
- [ordered_at](dimensions.md#ordered_at) — TIMESTAMPTZ; let session TZ handle conversion
- KPI window functions — must use `_yesterday_window_ict()` or equivalent ICT-aware helper

#### ⚠️ Conflicts
*None.*

#### 🔗 Related Rules
| Rule | Relationship |
|---|---|
| [MISA COGS Sourcing](#misa-cogs-sourcing) | Both rules prevent silent wrong numbers from infrastructure misuse |
| [Returns Not Restated in P&L](#returns-not-restated-in-pl) | fact_order_returns uses return_date (also ICT) — same timezone rule applies |

#### ❌ Common Violations
- `DATE_TRUNC('day', ordered_at)` without timezone awareness — UTC midnight boundary misclassifies ICT late-night orders
- Manual `AT TIME ZONE 'UTC'` in WHERE clause — DuckDB session is already ICT; double-conversion shifts window by +7 hours
- Using `ordered_at::date` directly — strips timezone, truncates at UTC midnight

#### 📊 Impact if Violated
~15% daily KPI drift — orders placed 23:00–06:59 ICT (~15% of daily volume assuming even distribution) get assigned to the wrong reporting day, shifting revenue to the wrong period.

---

## MISA COGS Sourcing

> **Type:** Rule | **Domain:** [Finance](../domains/finance.md) | **Status:** `active`
> **Applies To:** cogs_amount, gross_profit, has_cogs filter, Order Economics entity | **Since:** 2026-01-01

**Rule:** Use `has_cogs = true` to filter orders with COGS data — never filter by `cogs_source = 'misa'`, which excludes the primary Sapo-MAC source.

**SQL:**
```sql
-- ✅ Correct pattern — boolean flag covers all COGS sources
WHERE has_cogs = true   -- includes sapo_mac, misa, and both sources

-- ✅ Correct pattern — inspect source distribution
SELECT cogs_source, COUNT(*), SUM(cogs_amount)
FROM fact_order_economics
GROUP BY cogs_source
-- cogs_source values: 'sapo_mac' (primary), 'misa' (fallback), 'both', 'none'

-- ❌ Wrong pattern — deprecated; silently drops all sapo_mac primary COGS
WHERE cogs_source = 'misa'

-- ❌ Wrong pattern — wrong null check; has_cogs is the canonical flag
WHERE cogs_amount IS NOT NULL
```

**Intent:** The MISA-632 repoint (2026) made Sapo Moving Average Cost (sapo_mac) the primary COGS source, replacing MISA TK632 which was undercounting. Filtering `cogs_source = 'misa'` excludes the primary source and shows only fallback data — a pre-repoint pattern that is now incorrect.

**Applies To:**
- [cogs_amount](metrics.md#cogs_amount) — sourced from reconciled pipeline; use has_cogs filter
- [gross_profit](metrics.md#gross_profit) — only valid where has_cogs = true
- [has_cogs filter](segments.md#filter_has_cogs) — the canonical filter for COGS-available orders
- [Order Economics entity](entities.md#order-economics) — cogs_source column documents provenance

#### ⚠️ Conflicts
*None.*

#### 🔗 Related Rules
| Rule | Relationship |
|---|---|
| [Overhead Allocation (Tier-3 Only)](#overhead-allocation-tier-3-only) | Both are P&L correctness rules; overhead sits above gross_profit in the waterfall |
| [Promo Goods Cost (Not COGS)](#promo-goods-cost-not-cogs) | promo_goods_cost is excluded from cogs_amount by design |
| [Date Key Timezone](#date-key-timezone) | Both prevent silent wrong numbers from infrastructure-level data misuse |

#### ❌ Common Violations
- `WHERE cogs_source = 'misa'` — pre-2026 pattern; now excludes ~65% of COGS data (sapo_mac primary)
- `WHERE cogs_amount IS NOT NULL` — less reliable than `has_cogs`; misses edge cases
- Comparing gross_profit trend across 2025 (MISA-only) vs 2026 (sapo_mac primary) without normalizing — the ~56% GP drop is by design (undercounting fixed), not a business decline

#### 📊 Impact if Violated
`WHERE cogs_source = 'misa'` loses ~35% of COGS data (all sapo_mac primary orders). Gross profit trend analysis crossing the 2026 repoint date shows artificial ~56% GP decline if not normalized.

---

## Overhead Allocation (Tier-3 Only)

> **Type:** Rule | **Domain:** [Finance](../domains/finance.md) | **Status:** `active`
> **Applies To:** fully_loaded_net_profit, Order Economics entity | **Since:** 2024-01-01

**Rule:** `allocated_overhead` is for aggregate reporting only — never use `fully_loaded_net_profit` to accept or reject individual orders.

**SQL:**
```sql
-- ✅ Correct pattern — aggregate report (Tier-3 P&L waterfall)
SELECT
    SUM(channel_net_profit)          AS contribution_profit,
    SUM(allocated_overhead)          AS overhead,
    SUM(fully_loaded_net_profit)     AS fully_loaded_net_profit
FROM fact_order_economics
WHERE allocated_overhead IS NOT NULL

-- ❌ Wrong pattern — overhead is estimated, not traceable per-order
WHERE fully_loaded_net_profit > 0   -- do NOT use to accept/reject individual orders

-- ❌ Wrong pattern — is_overhead_estimated=true means the number is modeled, not actual
SELECT order_id FROM fact_order_economics
WHERE is_overhead_estimated = true AND fully_loaded_net_profit < 0
```

**Intent:** Overhead (warehouse, headcount, utilities) cannot be precisely traced to individual orders — it is allocated using an estimation model. `is_overhead_estimated = true` signals this. Per-order decisions based on estimated overhead introduce model error that compounds at scale.

**Applies To:**
- [fully_loaded_net_profit](metrics.md#fully_loaded_net_profit) — Tier-3 report metric only
- [Order Economics entity](entities.md#order-economics) — defines the three-tier P&L structure

#### ⚠️ Conflicts
*None.*

#### 🔗 Related Rules
| Rule | Relationship |
|---|---|
| [MISA COGS Sourcing](#misa-cogs-sourcing) | Both are P&L correctness rules in the order economics waterfall |
| [Promo Goods Cost (Not COGS)](#promo-goods-cost-not-cogs) | promo_goods_cost sits below gross_profit, above overhead — same Tier-3 layer |

#### ❌ Common Violations
- Filtering `WHERE fully_loaded_net_profit > 0` to identify "profitable orders" — overhead is estimated, this is not reliable for individual routing decisions
- Treating `allocated_overhead` as a precise cost (it is modeled from aggregate overhead pools)
- Using Tier-3 P&L for real-time order processing decisions (it is batch-computed, not real-time)

#### 📊 Impact if Violated
Using overhead-estimated per-order profit to make accept/reject decisions introduces estimation error that is unquantifiable without knowing the overhead allocation model's accuracy. Reported in CFO reports only.

---

## Promo Goods Cost (Not COGS)

> **Type:** Rule | **Domain:** [Finance](../domains/finance.md) | **Status:** `active`
> **Applies To:** cogs_amount, gross_profit | **Since:** 2024-01-01

**Rule:** `promo_goods_cost` is marketing cost (gifted items at Sapo-MAC), not COGS — keep it out of `cogs_amount` and gross_profit calculations.

**SQL:**
```sql
-- ✅ Correct pattern — gross_profit excludes promo goods cost by design
SELECT SUM(gross_profit) FROM fact_order_economics WHERE has_cogs

-- ✅ Correct pattern — contribution after promos (marketing view)
SELECT
    SUM(gross_profit) - SUM(COALESCE(promo_goods_cost, 0)) AS contribution_after_promos
FROM fact_order_economics
WHERE has_cogs

-- ❌ Wrong pattern — promo_goods_cost is not COGS; adding it double-counts gifted item cost
SELECT SUM(cogs_amount) + SUM(COALESCE(promo_goods_cost, 0)) AS total_cogs
FROM fact_order_economics   -- inflates COGS by the marketing gift line
```

**Intent:** Accounting principle: COGS = cost of goods SOLD. Gifted items have revenue = 0; including their cost in COGS inflates cost base and deflates gross margin without a corresponding revenue entry. They belong in marketing spend, not product cost.

**Applies To:**
- [cogs_amount](metrics.md#cogs_amount) — excludes promo goods cost by design
- [gross_profit](metrics.md#gross_profit) — correctly excludes promo goods cost

#### ⚠️ Conflicts
*None.*

#### 🔗 Related Rules
| Rule | Relationship |
|---|---|
| [MISA COGS Sourcing](#misa-cogs-sourcing) — both govern what enters cogs_amount |
| [Overhead Allocation (Tier-3 Only)](#overhead-allocation-tier-3-only) — promo_goods_cost is a Tier-2 deduction below gross_profit |

#### ❌ Common Violations
- Adding `promo_goods_cost` to `cogs_amount` in ad-hoc queries to get "total cost per order"
- Including `promo_goods_cost` in gross margin denominator — inflates apparent cost, deflates margin
- Forgetting `COALESCE(promo_goods_cost, 0)` when building contribution_after_promos — NULL propagates and zeroes the row

#### 📊 Impact if Violated
Including promo_goods_cost in COGS inflates cost by the full marketing cost of gifted items. During heavy promo campaigns, gifted item cost can reach 5–15% of net_revenue, materially deflating gross margin.

---

## Shopee Service Fee — No Double-Count

> **Type:** Rule | **Domain:** [Sales](../domains/sales.md) | **Status:** `active`
> **Applies To:** shopee_platform_fee_rate, channel_net_profit | **Since:** 2025-01-01

**Rule:** Use the pre-computed `shopee_platform_fees` column — never re-aggregate from `int_shopee_order_fees` without understanding D-row vs F-row structure.

**SQL:**
```sql
-- ✅ Correct pattern — pre-computed, double-count already resolved (Phase-07)
SELECT SUM(shopee_platform_fees) FROM fact_order_economics

-- ✅ Correct pattern — rate calculation
SELECT
    SUM(shopee_platform_fees) / NULLIF(SUM(gross_revenue), 0) AS shopee_fee_rate
FROM fact_order_economics
WHERE channel = 'shopee'

-- ❌ Wrong pattern — D-rows are aggregates of F-rows; summing both = 2× fee
SELECT SUM(amount) FROM int_shopee_order_fees
-- D (aggregate) = infra_fee + voucher_xtra_fee (F-rows) → total doubles when both included
```

**Intent:** Shopee income statements contain two row types for service fees: D-rows (aggregate totals) and F-rows (line-item detail: infrastructure_fee + voucher_xtra_fee). D = sum of F. Summing both row types double-counts Shopee fees. Phase-07 resolved this by keeping only F-rows in the pipeline; `shopee_platform_fees` reflects this fix.

**Applies To:**
- [shopee_platform_fee_rate](metrics.md#shopee_platform_fee_rate) — use pre-computed column
- [channel_net_profit](metrics.md#channel_net_profit) — shopee_platform_fees is a deduction in this waterfall

#### ⚠️ Conflicts
*None.*

#### 🔗 Related Rules
| Rule | Relationship |
|---|---|
| [Order Count Convention](#order-count-convention) | Both rules guard against overcounting from multi-row join patterns |
| [MISA Channel Classification](#misa-channel-classification) | Both relate to channel-level cost accuracy |

#### ❌ Common Violations
- Querying `int_shopee_order_fees` directly and summing all rows — D + F rows double the fee
- Building a custom Shopee fee calculation from raw tables without filtering by row_type
- Not filtering `WHERE channel = 'shopee'` when using `shopee_platform_fees` in cross-channel queries

#### 📊 Impact if Violated
Double-counting Shopee fees inflates platform cost by ~100% for Shopee orders, making Shopee appear unprofitable in channel P&L comparisons.

---

## MISA Channel Classification

> **Type:** Rule | **Domain:** [Finance](../domains/finance.md) | **Status:** `active`
> **Applies To:** gross_margin_pct, analyses from int_misa_sales_lines | **Since:** 2024-01-01

**Rule:** MISA `channel_code` (DAILY/ECOM/CS/KHAC) is not the same as Sapo channel taxonomy — do not cross-compare without explicit mapping.

**SQL:**
```sql
-- ✅ Correct pattern — use within MISA source only
SELECT channel_code, SUM(gross_profit), SUM(revenue_net_of_discount)
FROM int_misa_sales_lines
WHERE NOT is_promo_line
GROUP BY channel_code

-- ✅ Correct pattern — cross-source analysis needs explicit mapping
SELECT
    CASE m.channel_code
        WHEN 'DAILY' THEN 'POS'
        WHEN 'ECOM'  THEN 'E-Commerce'
        WHEN 'CS'    THEN 'B2B'
        WHEN 'KHAC'  THEN 'Other'
    END AS mapped_channel,
    SUM(m.gross_profit)
FROM int_misa_sales_lines m
WHERE NOT m.is_promo_line

-- ❌ Wrong pattern — treats MISA channel_code as equivalent to dim_channels.channel_name
SELECT * FROM int_misa_sales_lines WHERE channel_code = 'shopee'  -- 'shopee' does not exist in MISA
```

**Intent:** MISA uses a 4-code internal classification (DAILY/ECOM/CS/KHAC) built for accounting, not channel analytics. It does not map 1:1 to Sapo's channel taxonomy (Shopee, TikTok, Web, POS, etc.). Cross-comparing without a mapping layer produces category mismatches.

**MISA channel_code reference:**

| channel_code | Meaning | Sapo equivalent |
|---|---|---|
| DAILY | Retail at counter | POS channels |
| ECOM | E-commerce | Shopee, TikTok, Web |
| CS | Corporate / B2B | B2B channels |
| KHAC | Other | Misc |

**Applies To:**
- [gross_margin_pct](metrics.md#gross_margin_pct) — from MISA source; channel_code scope required
- Analyses from `int_misa_sales_lines` — always scope by channel_code with awareness of the taxonomy gap

#### ⚠️ Conflicts
*None.*

#### 🔗 Related Rules
| Rule | Relationship |
|---|---|
| [is_promo_line Filter (MISA)](#is_promo_line-filter-misa-margin) | Always pair MISA channel analysis with is_promo_line exclusion |
| [Shopee Service Fee — No Double-Count](#shopee-service-fee--no-double-count) | Both relate to channel-level cost accuracy across different source systems |

#### ❌ Common Violations
- Filtering MISA data by Sapo channel names (e.g., `channel_code = 'shopee'`) — no match, returns empty
- Displaying MISA `channel_code` values directly in dashboards without mapping labels
- Comparing MISA channel mix % vs Sapo channel mix % without harmonizing taxonomies

#### 📊 Impact if Violated
Cross-source channel comparisons produce category mismatches. MISA ECOM includes all online channels (Shopee + TikTok + Web) while Sapo tracks each separately — aggregation levels are incomparable without mapping.

---

## is_promo_line Filter (MISA Margin)

> **Type:** Rule | **Domain:** [Finance](../domains/finance.md) | **Status:** `active`
> **Applies To:** gross_margin_pct, cogs_amount from MISA source | **Since:** 2024-01-01

**Rule:** Always filter `WHERE NOT is_promo_line` when analyzing margin from `int_misa_sales_lines`.

**SQL:**
```sql
-- ✅ Correct pattern — promo lines excluded from margin analysis
SELECT
    SUM(gross_profit)                                              AS gross_profit,
    SUM(gross_profit) / NULLIF(SUM(revenue_net_of_discount), 0)   AS gross_margin_pct
FROM int_misa_sales_lines
WHERE NOT is_promo_line

-- ❌ Wrong pattern — promo lines have revenue=0 but positive COGS → margin collapses artificially
SELECT
    SUM(gross_profit) / NULLIF(SUM(revenue_net_of_discount), 0)   AS gross_margin_pct
FROM int_misa_sales_lines
-- Promo lines: revenue=0, cogs>0 → each line contributes negative gross_profit
```

**Intent:** MISA records promotional/gifting lines as separate rows with `revenue = 0` but actual COGS. Including these in margin calculations creates artificially negative gross_profit contributions that drag down the margin percentage without reflecting real sales economics.

**Applies To:**
- [gross_margin_pct](metrics.md#gross_margin_pct) — from MISA source; promo filter mandatory
- [cogs_amount](metrics.md#cogs_amount) — from MISA source; promo lines inflate apparent cost

#### ⚠️ Conflicts
*None.*

#### 🔗 Related Rules
| Rule | Relationship |
|---|---|
| [MISA Channel Classification](#misa-channel-classification) | Both apply to int_misa_sales_lines; always apply together |
| [Promo Goods Cost (Not COGS)](#promo-goods-cost-not-cogs) | Conceptually parallel: both rules prevent promo gifting cost from inflating COGS |

#### ❌ Common Violations
- Querying `int_misa_sales_lines` without `WHERE NOT is_promo_line` — drags gross_margin_pct down by including revenue=0 rows with COGS
- Aggregating ALL rows to check total revenue (promo lines must still be excluded even for revenue totals, as they contribute 0 revenue but distort averages)
- Not applying the filter in CTEs upstream — filter must appear at the base table scan, not added later in the chain

#### 📊 Impact if Violated
Promo lines with revenue=0 and positive COGS create artificial negative gross_profit entries. During heavy campaign periods, 5–10% of MISA lines are promo lines, which can drag gross_margin_pct down by 3–8 percentage points depending on campaign scale.

---

## Returns Not Restated in P&L

> **Type:** Rule | **Domain:** [Finance](../domains/finance.md) | **Status:** `active`
> **Applies To:** return_rate, post_ship_return_rate, return_count, refund_amount, Order Returns entity | **Since:** 2024-01-01

**Rule:** Returns are recognized at `return_date` in `fact_order_returns` — they do NOT restate `fact_order_economics` for the original order.

**SQL:**
```sql
-- ✅ Correct pattern — returns in their own table at return_date
SELECT SUM(refund_amount), COUNT(DISTINCT order_id) AS return_count
FROM fact_order_returns
WHERE return_date >= '2026-06-01'   -- use return_date, not ordered_at

-- ✅ Correct pattern — return_rate: use fact_order_returns as numerator
SELECT
    COUNT(DISTINCT r.order_id)::float / COUNT(DISTINCT o.order_id) AS return_rate
FROM fact_orders o
LEFT JOIN fact_order_returns r USING (order_id)
WHERE o.scope_sales AND o.date_key >= '2026-06-01'

-- ❌ Wrong pattern — channel_net_profit in fact_order_economics does NOT decrease on return
SELECT order_id, channel_net_profit FROM fact_order_economics
WHERE order_id IN (SELECT order_id FROM fact_order_returns)
-- channel_net_profit here is the ORIGINAL economics; returns are not subtracted

-- ❌ Wrong pattern — filtering fact_order_returns by ordered_at loses periodization accuracy
WHERE ordered_at >= '2026-06-01'   -- use return_date instead
```

**Intent:** Accounting principle: a return is a separate financial event recognized at the time of return, not a retroactive amendment to the original order's P&L. `fact_order_economics` columns (`return_amount`, `return_count`) are reference-only; they do not reduce `channel_net_profit`.

**Applies To:**
- [return_rate](metrics.md#return_rate) — Finance P&L rate; numerator from fact_order_returns using return_date
- [post_ship_return_rate](metrics.md#post_ship_return_rate) — Logistics rate; return_date within 30 days of ship_date
- [return_count](metrics.md#return_count) — Ops count; uses fulfillment_status, no financial join needed
- [refund_amount](metrics.md#refund_amount) — from fact_order_returns, not from fact_order_economics
- [Order Returns entity](entities.md#order-returns) — the correct table for return financial flows

#### ⚠️ Conflicts
*None.*

#### 🔗 Related Rules
| Rule | Relationship |
|---|---|
| [Date Key Timezone](#date-key-timezone) — return_date is also ICT; same timezone rule applies |
| [Discount Classification Taxonomy](#discount-classification-taxonomy) — both affect channel_net_profit interpretation |

#### ❌ Common Violations
- Expecting `fact_order_economics.channel_net_profit` to decrease when a return is processed — it does not
- Filtering `fact_order_returns` by `ordered_at` for period returns analysis — use `return_date` for when the financial event occurred
- Treating `return_amount` in `fact_order_economics` as a deduction already made — it is reference-only

#### 📊 Impact if Violated
Filtering returns by `ordered_at` instead of `return_date` misperiodizes return events — a return in June for a January order appears in January's P&L instead of June's. For high-return SKUs, this can shift 10–20% of return volume to the wrong period.

---

## Discount Classification Taxonomy

> **Type:** Rule | **Domain:** [Sales](../domains/sales.md) | **Status:** `active`
> **Applies To:** primary_discount_type, discount_amount | **Since:** 2024-01-01

**Rule:** Use `primary_discount_type` from `fact_orders` for discount structure analysis — never re-parse raw discount reason text.

**SQL:**
```sql
-- ✅ Correct pattern — use pre-classified column within retail scope
SELECT
    primary_discount_type,
    COUNT(DISTINCT order_id)                          AS order_count,
    SUM(discount_amount)                              AS total_discount,
    SUM(discount_amount) / SUM(gross_revenue)         AS discount_rate
FROM fact_orders
WHERE scope_retail AND discount_amount > 0
GROUP BY primary_discount_type
ORDER BY total_discount DESC

-- ❌ Wrong pattern — re-parsing raw text is fragile and non-standard
SELECT
    CASE WHEN discount_item_reason LIKE '%voucher%' THEN 'voucher' ELSE 'other' END AS type
FROM fact_orders
-- Use primary_discount_type instead — it handles all classification logic consistently

-- ❌ Wrong pattern — analyzing without scope_retail includes B2B structural discounts
SELECT primary_discount_type, SUM(discount_amount)
FROM fact_orders WHERE scope_sales   -- wholesale_explicit dominates, obscures retail promo mix
```

**Intent:** `primary_discount_type` is a pre-classified enum derived from discount item reason text at pipeline time. It provides consistent, parseable categories for promotion analysis without requiring analysts to write fragile LIKE-pattern SQL on raw text fields.

**Discount type reference (10 granular types):**

| primary_discount_type | 4-Bucket Group | Meaning |
|---|---|---|
| voucher_promotional | `voucher` | Seller voucher — customer proactively redeems a code |
| bundle | `campaign` | Bundle deal discount |
| sampling_gift | `campaign` | Sample / gift item |
| campaign | `campaign` | Named campaign (CTKM, Father's Day, etc.) |
| wholesale_explicit | `negotiated` | Explicit wholesale/agency pricing in reason |
| overseas | `negotiated` | US/overseas order pricing |
| employee_internal | `negotiated` | Employee / CTV / commission benefit |
| negotiated_micro | `negotiated` | Negotiated discount < 20% |
| negotiated_standard | `negotiated` | Negotiated discount 20–40% |
| negotiated_deep | `negotiated` | Negotiated discount > 40% |

**4-Bucket grouping for customer-level analytics:**

| Bucket | Source | Business Signal |
|---|---|---|
| `line_discount` | `order_items.discount_amount / (unit_price × quantity)` — NOT from `discount_items` | Line-level reduction; tracked independently |
| `voucher` | `discount_type = 'voucher_promotional'` | Customer engagement (proactive redemption) |
| `campaign` | `bundle`, `campaign`, `sampling_gift` | Merchant-initiated promotion (dependency signal) |
| `negotiated` | `negotiated_*`, `wholesale_explicit`, `employee_internal`, `overseas` | Contract/relationship pricing |

**Double-count note:** 31,890 orders have BOTH a `line_discount` (from `order_items`) AND an order-level discount (from `discount_items`). They are tracked independently — do NOT sum across buckets to get total discount.

**Customer-level fields in `dim_customers` and `wh_customer_insight`:** 8 fields — per bucket, `last_*` (most-recent order with that bucket) and `max_*` (highest rate ever). All 0.0–1.0. NULL = customer never had an order of that type.

**Applies To:**
- [primary_discount_type](dimensions.md#primary_discount_type) — the pre-classified dimension
- [discount_amount](metrics.md#discount_amount) — the metric analyzed by this dimension

#### ⚠️ Conflicts
*None.*

#### 🔗 Related Rules
| Rule | Relationship |
|---|---|
| [Scope Required for Promotion/Discount](#scope-required-for-promotiondiscount) — always apply scope_retail before analyzing primary_discount_type |
| [Returns Not Restated in P&L](#returns-not-restated-in-pl) — both affect channel_net_profit interpretation |

#### ❌ Common Violations
- Re-parsing `discount_item_reason` with custom LIKE patterns — inconsistent classification, misses edge cases handled by the pipeline classifier
- Not applying `scope_retail` — `wholesale_explicit` type dominates when B2B orders are included, obscuring the retail promo mix
- Filtering `discount_amount > 0` without `scope_retail` — includes orders where "discount" is B2B pricing, not consumer promotion

#### 📊 Impact if Violated
Without `scope_retail`, `wholesale_explicit` and `negotiated_*` types from B2B orders dominate the distribution, making retail promotion analysis impossible. Re-parsing raw reason text misclassifies ~15–20% of discount rows that the pipeline classifier handles with multi-pattern logic.
