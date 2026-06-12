# Metrics

Standard aggregate formulas — computed from mart columns, not redefined in blueprints.

> **Canonical source:** this file
> **WHY reference:** [Revenue Terminology](../guides/revenue_terminology.md), [Sales Domain](../domains/sales.md)
> **Implementation:** `fact_orders` columns + Rill `rill/metrics/orders_core_metrics.yaml`

---

## Sales Metrics

---

## orders_count

> **Type:** Metric | **Domain:** [Sales](../domains/sales.md) | **Unit:** count
> **Status:** `active` | **Scope:** scope_retail or scope_b2b | **Grain:** per order | **Since:** 2021-01-01

**Definition:** Count of unique orders.

**Real question:** "Có bao nhiêu đơn hàng được tạo trong kỳ?"

**Formula:**
```sql
COUNT(DISTINCT order_id)
```

**Column:** `fact_orders.order_id` (no pre-computed column; compute at query time)

**Intent:** Baseline volume metric — used to normalize all per-order ratios (AOV, discount_rate, return_rate).

**Use in SQL:** `COUNT(DISTINCT order_id)` — never `COUNT(*)` when joining items.

#### 🎯 When to Use
Use as denominator for any per-order rate. Always specify scope (retail vs B2B) — totals mix two very different populations.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `units_sold` | [metrics.md](#units_sold) | items per order vs orders | measuring product volume |

#### ❌ Anti-patterns
```sql
-- ❌ COUNT(*) when joining fact_order_items → overcounts (one row per item)
SELECT COUNT(*) FROM fact_orders JOIN fact_order_items USING (order_id)

-- ❌ No scope filter → retail + B2B mixed, totals meaningless for behavioral analysis
SELECT COUNT(DISTINCT order_id) FROM fact_orders  -- missing WHERE scope_retail
```

#### 🏷️ Used In
*Not tracked yet.*

---

## gross_revenue

> **Type:** Metric | **Domain:** [Sales](../domains/sales.md) | **Unit:** VND
> **Status:** `active` | **Scope:** any | **Grain:** per order | **Since:** 2021-01-01

**Definition:** Total revenue before discounts, VAT-inclusive (Sapo embeds VAT in list price).

**Real question:** "Tổng doanh thu niêm yết (trước chiết khấu, gộp VAT) là bao nhiêu?"

**Formula:**
```sql
SUM(gross_revenue)
```

**Column:** `fact_orders.gross_revenue`

**Intent:** Represents what was offered at list price — before promotions. Used as denominator for discount_rate. Do NOT use for P&L (includes VAT and pre-discount value).

**Use in SQL:** `SUM(gross_revenue)`

#### 📖 Walkthrough
**Revenue Waterfall** — Order: list price 1,000,000đ, coupon 200,000đ, VAT 10%:

| Step | Calculation | Value |
|---|---|---|
| gross_revenue | 1,000,000 + 200,000 | 1,200,000đ |
| discount_amount | — | 200,000đ |
| total_collected | 1,200,000 − 200,000 | 1,000,000đ ← on invoice |
| vat_amount | 1,000,000 × 10/110 | 90,909đ |
| **net_revenue** | 1,000,000 − 90,909 | **909,091đ ← P&L** |

~60% orders: vat_amount=0 (US export + no-VAT retail) → net_revenue = total_collected for those.

#### 🎯 When to Use
Use as denominator for `discount_rate`. Do not use for revenue reporting — use `net_revenue` (P&L) or `total_collected` (cash).

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `total_collected` | [metrics.md](#total_collected) | after discount, still VAT-inclusive | reconciling cash receipts |
| `net_revenue` | [metrics.md](#net_revenue) | after discount AND VAT stripped | P&L reporting |
| `realized_revenue` | [metrics.md](#realized_revenue) | after refunds | cash flow analysis |

#### ❌ Anti-patterns
```sql
-- ❌ Using gross_revenue for P&L — includes VAT and pre-discount value
SELECT SUM(gross_revenue) AS revenue FROM fact_orders  -- ❌ misleads P&L
```

#### 🏷️ Used In
*Not tracked yet.*

---

## total_collected

> **Type:** Metric | **Domain:** [Sales](../domains/sales.md) | **Unit:** VND
> **Status:** `active` | **Scope:** any | **Grain:** per order | **Since:** 2021-01-01

**Definition:** Amount actually collected from customer — invoice amount, after discount, VAT-inclusive.

**Real question:** "Khách thực trả bao nhiêu sau chiết khấu (trước trừ VAT)?"

**Formula:**
```sql
SUM(total_collected)
```

**Column:** `fact_orders.total_collected`

**Intent:** Matches what appears on the customer invoice. Use for cash reconciliation, not P&L.

**Use in SQL:** `SUM(total_collected)`

#### 📖 Walkthrough
See `gross_revenue` waterfall above — total_collected is the middle step (post-discount, pre-VAT-strip).

#### 🎯 When to Use
Use for cash flow analysis and payment reconciliation. For P&L use `net_revenue`. For revenue-after-returns use `realized_revenue`.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `net_revenue` | [metrics.md](#net_revenue) | VAT stripped out | P&L, margin calculations |
| `realized_revenue` | [metrics.md](#realized_revenue) | further minus refunds | actual cash net of returns |
| `shopee_net_settlement` | [metrics.md](#shopee_net_settlement) | Shopee payout after platform fees | reconciling Shopee transfers |

#### ❌ Anti-patterns
```sql
-- ❌ Using total_collected for gross margin → VAT still embedded
SELECT SUM(total_collected) - SUM(cogs_amount) AS margin FROM fact_order_economics
-- ✅ Use SUM(net_revenue) - SUM(cogs_amount)
```

#### 🏷️ Used In
*Not tracked yet.*

---

## net_revenue

> **Type:** Metric | **Domain:** [Sales](../domains/sales.md) | **Unit:** VND
> **Status:** `active` | **Scope:** any | **Grain:** per order | **Since:** 2021-01-01

**Definition:** Net revenue after discount and VAT stripped — the accounting P&L number.

**Real question:** "Doanh thu P&L sau chiết khấu và sau trừ VAT là bao nhiêu?"

**Formula:**
```sql
SUM(net_revenue)
```

**Column:** `fact_orders.net_revenue`

**Intent:** The single revenue number for P&L, margins, and profitability. Sapo VAT is embedded (8/108 or 10/110 rate per item); `net_revenue` has it stripped.

**Use in SQL:** `SUM(net_revenue)`

#### 📖 Walkthrough
See `gross_revenue` waterfall above. net_revenue is the final step.

Sapo VAT extraction: `net_revenue = total_collected - vat_amount` where `vat_amount = total_collected × rate/(100+rate)`. Rate is 8% or 10% per item type. ~60% of orders have vat_amount=0 (US export + non-VAT items) — for those orders net_revenue = total_collected exactly.

#### 🎯 When to Use
Default revenue metric for all P&L, margin, and profitability reports. Use `total_collected` only when matching customer invoices or cash flow. Use `gross_revenue` only as discount_rate denominator.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `total_collected` | [metrics.md](#total_collected) | VAT still included | invoice reconciliation |
| `gross_revenue` | [metrics.md](#gross_revenue) | pre-discount, VAT-inclusive | computing discount_rate |
| `realized_revenue` | [metrics.md](#realized_revenue) | net_revenue scope, minus refunds | cash flow net of returns |

#### ❌ Anti-patterns
```sql
-- ❌ total_price / 1.08 — wrong direction AND wrong rate
SELECT total_price / 1.08 AS net_rev FROM fact_orders

-- ❌ total_collected as P&L revenue — VAT embedded
SELECT SUM(total_collected) AS revenue FROM fact_orders
```

#### 🏷️ Used In
*Not tracked yet.*

---

## discount_amount

> **Type:** Metric | **Domain:** [Sales](../domains/sales.md) | **Unit:** VND
> **Status:** `active` | **Scope:** scope_retail (required) | **Grain:** per order | **Since:** 2021-01-01

**Definition:** Total discounts applied (coupons, promotions, combos, staff discounts).

**Real question:** "Tổng tiền khuyến mãi đã giảm cho khách trong kỳ là bao nhiêu?"

**Formula:**
```sql
SUM(discount_amount)
```

**Column:** `fact_orders.discount_amount`

**Intent:** Measures promotion cost in absolute VND. Drives discount_rate computation.

**Use in SQL:** `SUM(discount_amount) WHERE scope_retail`

#### 🎯 When to Use
Always filter `scope_retail`. B2B discount = fixed wholesale price, not a promotion — mixing produces a meaningless number that blends two completely different pricing mechanisms.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `discount_rate` | [metrics.md](#discount_rate) | percentage form | comparing discount intensity across periods/channels |

#### ❌ Anti-patterns
```sql
-- ❌ No scope filter — B2B "discount" is wholesale pricing, not promotion
SELECT SUM(discount_amount) FROM fact_orders  -- missing WHERE scope_retail
```

#### 🏷️ Used In
*Not tracked yet.*

---

## discount_rate

> **Type:** Metric | **Domain:** [Sales](../domains/sales.md) | **Unit:** %
> **Status:** `active` | **Scope:** scope_retail (required) | **Grain:** per period | **Since:** 2021-01-01

**Definition:** Discount as % of gross revenue — promotion intensity ratio.

**Real question:** "Mức độ khuyến mãi chiếm bao nhiêu % doanh thu niêm yết?"
**Denominator:** scope_retail gross_revenue in the period

**Formula:**
```sql
SUM(discount_amount) / NULLIF(SUM(gross_revenue), 0)
```

**Intent:** Tracks how aggressively promotions are being applied. Useful for trend and channel comparison.

**Use in SQL:** `SUM(discount_amount) / NULLIF(SUM(gross_revenue), 0) WHERE scope_retail`

#### 🎯 When to Use
Prefer `discount_rate` over `discount_amount` when comparing across periods or channels with different volumes. Use `discount_amount` when you need absolute VND impact.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `discount_amount` | [metrics.md](#discount_amount) | absolute VND | totals, financial impact |

#### ❌ Anti-patterns
```sql
-- ❌ scope_sales (mixed retail+B2B) — B2B "discounts" are wholesale prices
SELECT SUM(discount_amount) / NULLIF(SUM(gross_revenue), 0) FROM fact_orders
-- missing WHERE scope_retail
```

#### 🏷️ Used In
*Not tracked yet.*

---

## aov

> **Type:** Metric | **Domain:** [Sales](../domains/sales.md) | **Unit:** VND
> **Status:** `active` | **Scope:** scope_retail OR scope_b2b (never mixed) | **Grain:** per period | **Since:** 2021-01-01

**Definition:** Average revenue per order in a period. **Business/P&L lens** — uses `net_revenue` (VAT-excluded), the amount the business books as earned revenue.

**Real question:** "Trung bình mỗi đơn hàng tạo ra bao nhiêu doanh thu P&L?"
**Denominator:** scope_retail (or scope_b2b) orders in the period

**Formula:**
```sql
SUM(net_revenue) / NULLIF(COUNT(DISTINCT order_id), 0)
```

**Intent:** P&L and dashboard trend analysis. Scope is critical — retail and B2B AOV differ by ~5x. Not the same as what the customer paid (see `avg_order_spend`).

**Use in SQL:** `SUM(net_revenue) / NULLIF(COUNT(DISTINCT order_id), 0) WHERE scope_retail`

#### 📖 Walkthrough
**AOV Scope Comparison:**

| Scope | Typical Value | Note |
|---|---|---|
| scope_retail | ~450,000 VND | Correct retail AOV |
| scope_b2b | ~2,500,000 VND | Correct B2B AOV |
| scope_sales (mixed) | ~650,000 VND | Not actionable — population is undefined |

#### 🎯 When to Use
Dashboard trend, channel comparison, P&L context. Always pick one scope. Do NOT use for customer scoring or CRM action estimation — use `avg_order_spend` instead.

#### ⚠️ Conflicts
*None — Rill YAML fixed to `count(distinct order_id)`, consistent with this definition.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `avg_order_spend` | [dimensions.md](dimensions.md#avg_order_spend) | **Customer lens** — `total_collected` (VAT-inclusive), what the customer actually paid, lifetime per-customer attribute | customer scoring, action queue, value_at_stake |
| `arpu` | [metrics.md](#arpu) | revenue per customer not per order | measuring customer-level contribution |

#### ❌ Anti-patterns
```sql
-- ❌ Mixed scope — retail + B2B blended AOV is not actionable
SELECT SUM(net_revenue) / NULLIF(COUNT(DISTINCT order_id), 0)
FROM fact_orders  -- missing scope filter

-- ❌ Using aov (net_revenue) for CRM value_at_stake — underestimates cash by ~8-10% VAT
-- Use dim_customers.avg_order_spend instead
```

#### 🏷️ Used In
*Not tracked yet.*

---

## vat_amount

> **Type:** Metric | **Domain:** [Sales](../domains/sales.md) | **Unit:** VND
> **Status:** `active` | **Scope:** any | **Grain:** per order | **Since:** 2021-01-01

**Definition:** VAT embedded in list price, extracted from total_collected.

**Real question:** "Tổng thuế VAT đã thu trong kỳ là bao nhiêu?"

**Formula:**
```sql
SUM(vat_amount)
```

**Column:** `fact_orders.vat_amount`

**Intent:** Tax reporting and reconciliation. Intermediate step in revenue waterfall.

**Use in SQL:** `SUM(vat_amount)`

#### 🎯 When to Use
Use for VAT reporting or to verify net_revenue derivation. For most analytics, use net_revenue directly.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
*None.*

#### ❌ Anti-patterns
```sql
-- ❌ Flat rate extraction — rate varies by item (8% or 10%)
SELECT total_collected * 0.1 AS vat  -- wrong for 8% items
-- ✅ Use fact_orders.vat_amount (pre-computed per item)
```

#### 🔍 Null & Zero
0 is valid — US export orders and non-VAT items have vat_amount=0. Not a data error. ~60% of orders have vat_amount=0.

#### 🏷️ Used In
*Not tracked yet.*

---

## Finance Metrics

---

## cogs_amount

> **Type:** Metric | **Domain:** [Finance](../domains/finance.md) | **Unit:** VND
> **Status:** `active` | **Scope:** has_cogs = true | **Grain:** per order | **Since:** 2022-01-01

**Definition:** Cost of goods sold per order — Sapo-MAC moving-average cost (primary), MISA TK632 fallback.

**Real question:** "Giá vốn hàng bán (COGS) trong kỳ là bao nhiêu?"

**Formula:**
```sql
SUM(cogs_amount) WHERE has_cogs = true
```

**Column:** `fact_order_economics.cogs_amount`

**Intent:** Determines gross profit per order. Foundation of all profitability metrics.

**Use in SQL:** `SUM(cogs_amount) FILTER (WHERE has_cogs = true)`

#### 🎯 When to Use
Always gate with `has_cogs = true`. Coverage is ~65% — aggregate results represent covered orders only, not full business.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
*None.*

#### ❌ Anti-patterns
```sql
-- ❌ source_system='misa' filter — deprecated, breaks since Sapo-MAC repoint
SELECT SUM(cogs_amount) FROM fact_order_economics WHERE cogs_source = 'misa'
-- ✅ Use: WHERE has_cogs = true

-- ❌ NULLIF(cogs_amount, 0) omitted when 0 means "not matched"
SELECT AVG(cogs_amount) FROM fact_order_economics  -- includes 0-value unmatched rows
-- ✅ WHERE has_cogs = true
```

#### 🔍 Null & Zero
NULL = no COGS data (order not matched to MISA/Sapo-MAC). 0 = has_cogs=false. Use `NULLIF(cogs_amount, 0)` to expose unmatched rows as NULL in averages.

#### 📊 Data Quality
| Dimension | Status | Note |
|---|---|---|
| Coverage | ~65% | Only orders with MISA/Sapo-MAC match |
| Historical | ⚠️ Pre-2026 changed | MISA-632 repoint — baseline not comparable across migration boundary |

#### 🏷️ Used In
*Not tracked yet.*

---

## gross_profit

> **Type:** Metric | **Domain:** [Finance](../domains/finance.md) | **Unit:** VND
> **Status:** `active` | **Scope:** has_cogs = true | **Grain:** per order | **Since:** 2022-01-01

**Definition:** Gross profit = net_revenue − COGS per order.

**Real question:** "Lợi nhuận gộp sau khi trừ giá vốn là bao nhiêu?"

**Formula:**
```sql
SUM(gross_profit) WHERE has_cogs = true
```

**Column:** `fact_order_economics.gross_profit`

**Intent:** Measures basic profitability after cost of goods. First step in P&L ladder.

**Use in SQL:** `SUM(gross_profit) FILTER (WHERE has_cogs = true)`

#### 📖 Walkthrough
**P&L Ladder** — Shopee order, net_revenue 1,000,000đ, COGS 600,000đ, Shopee fees 80,000đ, overhead 50,000đ:

| Metric | Value | Formula |
|---|---|---|
| gross_profit | 400,000đ | net_revenue − COGS |
| channel_net_profit | 320,000đ | gross_profit − platform_fees |
| fully_loaded_net_profit | 270,000đ | channel_net_profit − overhead (Tier-3 only) |

#### 🎯 When to Use
Use as the starting profitability metric. Step down to `channel_net_profit` when Shopee fees matter; to `fully_loaded_net_profit` only for Tier-3 fully-allocated reporting.

#### ⚠️ Conflicts
| Source | Formula/Definition | When it appears | Note |
|---|---|---|---|
| `int_misa_sales_lines` | requires `WHERE NOT is_promo_line` | intermediate dbt model | promo lines must be excluded explicitly |
| `fact_order_economics` | already excludes promo lines; use `WHERE has_cogs = true` | mart (use this) | pre-filtered — preferred source |

Both produce consistent results when filters applied correctly.

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `channel_net_profit` | [metrics.md](#channel_net_profit) | further minus platform fees | Shopee P&L analysis |
| `fully_loaded_net_profit` | [metrics.md](#fully_loaded_net_profit) | further minus overhead | Tier-3 fully-loaded reports |

#### ❌ Anti-patterns
```sql
-- ❌ No has_cogs filter — averages include unmatched 0-COGS orders
SELECT SUM(gross_profit) FROM fact_order_economics

-- ❌ int_misa_sales_lines without promo filter — double-counts promo cost
SELECT SUM(gross_profit) FROM int_misa_sales_lines  -- missing WHERE NOT is_promo_line
```

#### 📊 Data Quality
| Dimension | Status | Note |
|---|---|---|
| Coverage | ~65% | Inherits from cogs_amount coverage |
| Historical | ⚠️ Pre-2026 changed | MISA-632 repoint — do not compare trends across boundary |

#### 🏷️ Used In
*Not tracked yet.*

---

## gross_margin_pct

> **Type:** Metric | **Domain:** [Finance](../domains/finance.md) | **Unit:** %
> **Status:** `active` | **Scope:** has_cogs = true | **Grain:** per period | **Since:** 2022-01-01

**Definition:** Gross margin = gross_profit / net_revenue.

**Real question:** "Tỉ lệ lợi nhuận gộp trên doanh thu P&L là bao nhiêu %?"
**Denominator:** has_cogs = true net_revenue in the period

**Formula:**
```sql
SUM(gross_profit) / NULLIF(SUM(net_revenue), 0)
```

**Column:** `fact_order_economics.gross_margin_pct` (per-order pre-computed), or compute from aggregates.

**Intent:** Measures COGS efficiency relative to revenue. Thresholds: Healthy >40% | Watch 25-40% | Alert <25%.

**Use in SQL:** `SUM(gross_profit) / NULLIF(SUM(net_revenue), 0) WHERE has_cogs = true`

#### 🎯 When to Use
Use for channel or SKU profitability comparison. Always filter `has_cogs = true` — unmatched orders have gross_profit=0 which deflates the ratio.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `channel_net_margin_pct` | [metrics.md](#channel_net_margin_pct) | further minus platform fees | Shopee channel comparison |
| `shopee_platform_fee_rate` | [metrics.md](#shopee_platform_fee_rate) | fee burden specifically | auditing Shopee cost structure |

#### ❌ Anti-patterns
```sql
-- ❌ No has_cogs filter — unmatched rows drag down margin artificially
SELECT SUM(gross_profit) / NULLIF(SUM(net_revenue), 0) AS gm
FROM fact_order_economics  -- missing WHERE has_cogs = true
```

#### 🏷️ Used In
*Not tracked yet.*

---

## channel_net_profit

> **Type:** Metric | **Domain:** [Finance](../domains/finance.md) | **Unit:** VND
> **Status:** `active` | **Scope:** has_cogs = true | **Grain:** per order | **Since:** 2022-01-01

**Definition:** Channel net profit = gross_profit − Shopee platform fees. Non-Shopee orders: channel_net_profit = gross_profit (no platform fee).

**Real question:** "Lợi nhuận sau khi trừ phí sàn là bao nhiêu?"

**Formula:**
```sql
SUM(channel_net_profit)
```

**Column:** `fact_order_economics.channel_net_profit`

**Intent:** Measures profit after paying the sales platform. Second step in P&L ladder.

**Use in SQL:** `SUM(channel_net_profit) FILTER (WHERE has_cogs = true)`

#### 🎯 When to Use
Use when comparing Shopee vs direct channel profitability. Shopee fees are already embedded as negative values in mart — no manual subtraction needed.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `gross_profit` | [metrics.md](#gross_profit) | before platform fees | non-channel P&L or when fees not relevant |
| `fully_loaded_net_profit` | [metrics.md](#fully_loaded_net_profit) | further minus overhead | Tier-3 full allocation reports |

#### ❌ Anti-patterns
```sql
-- ❌ Manually subtracting fees that are already embedded in mart
SELECT SUM(channel_net_profit) - SUM(shopee_fees) FROM fact_order_economics
-- Shopee fees already deducted in channel_net_profit
```

#### 📊 Data Quality
| Dimension | Status | Note |
|---|---|---|
| Coverage | ~65% | Inherits from cogs_amount |
| Historical | ⚠️ Pre-2026 changed | Same migration boundary as gross_profit |

#### 🏷️ Used In
*Not tracked yet.*

---

## channel_net_margin_pct

> **Type:** Metric | **Domain:** [Finance](../domains/finance.md) | **Unit:** %
> **Status:** `active` | **Scope:** has_cogs = true | **Grain:** per period | **Since:** 2022-01-01

**Definition:** Channel net margin = channel_net_profit / net_revenue.

**Real question:** "Tỉ lệ lợi nhuận sau phí sàn trên doanh thu là bao nhiêu %?"
**Denominator:** has_cogs = true net_revenue in the period

**Formula:**
```sql
SUM(channel_net_profit) / NULLIF(SUM(net_revenue), 0)
```

**Column:** `fact_order_economics.channel_net_margin_pct`

**Intent:** Compares net margin across sales channels. Thresholds: Healthy >20% | Watch 0-20% | Alert (Loss Leader) <0%.

**Use in SQL:** `SUM(channel_net_profit) / NULLIF(SUM(net_revenue), 0) WHERE has_cogs = true`

#### 🎯 When to Use
Use for channel profitability benchmarking. Pair with `shopee_platform_fee_rate` to understand fee drag on Shopee margin.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `gross_margin_pct` | [metrics.md](#gross_margin_pct) | before platform fees | comparing raw COGS efficiency |
| `shopee_platform_fee_rate` | [metrics.md](#shopee_platform_fee_rate) | fee % only | auditing Shopee fee burden |

#### ❌ Anti-patterns
```sql
-- ❌ No has_cogs filter → unmatched 0-profit orders deflate margin
SELECT SUM(channel_net_profit) / NULLIF(SUM(net_revenue), 0)
FROM fact_order_economics  -- missing WHERE has_cogs = true
```

#### 🏷️ Used In
*Not tracked yet.*

---

## fully_loaded_net_profit

> **Type:** Metric | **Domain:** [Finance](../domains/finance.md) | **Unit:** VND
> **Status:** `active` | **Scope:** allocated_overhead IS NOT NULL | **Grain:** per order | **Since:** 2022-01-01

**Definition:** Fully-loaded net profit = channel_net_profit − overhead allocation. Tier-3 reporting only.

**Real question:** "Lợi nhuận thực sau khi phân bổ đầy đủ chi phí overhead là bao nhiêu?"

**Formula:**
```sql
SUM(fully_loaded_net_profit) WHERE allocated_overhead IS NOT NULL
```

**Column:** `fact_order_economics.fully_loaded_net_profit`

**Intent:** Measures profitability after all indirect costs allocated. Third step in P&L ladder. NOT for per-order operational decisions — overhead is an estimate.

**Use in SQL:** `SUM(fully_loaded_net_profit) FILTER (WHERE allocated_overhead IS NOT NULL)`

#### 🎯 When to Use
Use only in Tier-3 fully-allocated P&L reports. For operational decisions (fulfillment accept/reject), use `channel_net_profit` — overhead allocation is estimated, not exact.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `channel_net_profit` | [metrics.md](#channel_net_profit) | before overhead | operational decisions |
| `gross_profit` | [metrics.md](#gross_profit) | before fees AND overhead | comparing pure COGS efficiency |

#### ❌ Anti-patterns
```sql
-- ❌ Using for per-order accept/reject decisions — overhead is estimated allocation
SELECT order_id, fully_loaded_net_profit FROM fact_order_economics
WHERE fully_loaded_net_profit < 0  -- don't cancel orders based on this
```

#### 📊 Data Quality
| Dimension | Status | Note |
|---|---|---|
| Coverage | <65% | Subset of has_cogs=true; requires overhead allocation data |
| Historical | ⚠️ Pre-2026 | Overhead allocation data availability varies |

#### 🏷️ Used In
*Not tracked yet.*

---

## return_rate

> **Type:** Metric | **Domain:** [Finance](../domains/finance.md) | **Unit:** %
> **Status:** `active` | **Scope:** scope_sales | **Grain:** per period | **Since:** 2021-01-01

**Definition:** % of scope_sales orders that generated a return event (Finance/P&L lens).

**Real question:** "Bao nhiêu % đơn revenue tạo ra return event?"
**Denominator:** scope_sales orders in the period (ordered_at window)
**Time anchor:** `return_date` (numerator) / `ordered_at` period (denominator)

**Formula:**
```sql
COUNT(DISTINCT r.order_code) / NULLIF(COUNT(DISTINCT o.order_id), 0) * 100
FROM fact_orders o LEFT JOIN fact_order_returns r USING (order_code)
WHERE o.scope_sales AND o.date_key BETWEEN :start AND :end
```

**Intent:** Measures return risk and order quality (Finance/P&L lens). Thresholds: Healthy <2% | Watch 2-5% | Alert >5%. Returns recognized at `return_date`, not restated into original order P&L.

**Use in SQL:** Join `fact_order_returns` as numerator; filter denominator on `scope_sales` orders. Do NOT use `fulfillment_status='RETURNED'` — misses partial returns.

#### 🎯 When to Use
Use for Finance/P&L return analysis. For logistics SLA (post-ship 30-day window), use `post_ship_return_rate`. For daily ops count, use `return_count`.

#### ⚠️ Conflicts
| Source | Formula/Definition | When it appears | Note |
|---|---|---|---|
| Sales ops | `COUNT(CASE WHEN fulfillment_status='RETURNED') / COUNT(DISTINCT order_id)` | order-status-based reports | Undercounts partial returns — this is `return_count` territory |
| Logistics | 30-day post-ship rolling window, shipped denominator | logistics SLA reports | Different denominator + window — use `post_ship_return_rate` |

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `post_ship_return_rate` | [metrics.md](#post_ship_return_rate) | shipped denominator, 30-day post-ship window | logistics SLA analysis |
| `return_count` | [metrics.md](#return_count) | absolute count, not rate | ops daily signal |
| `refund_amount` | [metrics.md](#refund_amount) | VND value of refunds not rate | measuring financial exposure |

#### ❌ Anti-patterns
```sql
-- ❌ fulfillment_status='RETURNED' — misses partial returns (use fact_order_returns join instead)
SELECT COUNT(CASE WHEN fulfillment_status='RETURNED' THEN 1 END) / COUNT(DISTINCT order_id)
FROM fact_orders

-- ❌ Missing scope_sales filter — includes CANCELLED/DRAFT orders in denominator
SELECT COUNT(DISTINCT r.order_id) / COUNT(DISTINCT o.order_id) FROM fact_orders o ...
-- missing: WHERE o.scope_sales
```

#### 🏷️ Used In
*Not tracked yet.*

---

## post_ship_return_rate

> **Type:** Metric | **Domain:** [Logistics](../domains/logistics.md) | **Unit:** %
> **Status:** `active` | **Scope:** shipped orders only | **Grain:** per period | **Since:** 2021-01-01

**Definition:** % of shipped orders that were returned within 30 days of ship date (Logistics / supply chain quality lens).

**Real question:** "Trong hàng đã ship, bao nhiêu % quay về trong 30 ngày?"
**Denominator:** fact_fulfillments with status = shipped
**Time anchor:** `return_date`, 30-day window after `ship_date`

**Formula:**
```sql
COUNT(DISTINCT r.order_id)::float
  / NULLIF(COUNT(DISTINCT f.order_id), 0) * 100
FROM fact_fulfillments f
LEFT JOIN fact_order_returns r
  ON r.order_id = f.order_id
  AND r.return_date BETWEEN f.ship_date AND f.ship_date + INTERVAL '30 days'
WHERE f.status = 'SHIPPED'
```

**Intent:** Measures logistics quality — returns that occur AFTER shipping, within a 30-day SLA window. Distinct from `return_rate` which uses all scope_sales orders as denominator and has no post-ship window.

**Use in SQL:** Denominator is `fact_fulfillments` (shipped), not `fact_orders`. Window is always 30 days from `ship_date`.

#### 🎯 When to Use
Use for logistics SLA reporting, carrier quality analysis, and supply chain post-ship quality monitoring.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `return_rate` | [metrics.md](#return_rate) | scope_sales denominator, no post-ship window | Finance/P&L return analysis |
| `return_count` | [metrics.md](#return_count) | absolute count only | ops daily signal |

#### ❌ Anti-patterns
```sql
-- ❌ Confusing with return_rate — different denominator (shipped vs scope_sales)
-- return_rate uses fact_orders denominator; post_ship_return_rate uses fact_fulfillments shipped

-- ❌ Using ordered_at window instead of 30-day post-ship window
WHERE r.return_date BETWEEN :period_start AND :period_end  -- wrong
-- ✅ Window must be anchored to ship_date + 30 days
```

#### 🏷️ Used In
*Not tracked yet.*

---

## return_count

> **Type:** Metric | **Domain:** [Sales](../domains/sales.md) | **Unit:** count
> **Status:** `active` | **Scope:** any | **Grain:** per period | **Since:** 2021-01-01

**Definition:** Absolute count of orders with `fulfillment_status = 'RETURNED'` today/in period. Ops signal only — not a rate.

**Real question:** "Hôm nay bao nhiêu đơn chuyển sang RETURNED status?"

**Formula:**
```sql
COUNT(DISTINCT order_id) FILTER (WHERE fulfillment_status = 'RETURNED')
FROM fact_orders
WHERE date_key = :today
```

**Column:** `fact_orders.fulfillment_status`

**Intent:** Daily ops monitoring signal. Measures how many orders flipped to RETURNED status in the period. Does NOT measure financial impact or partial returns.

**Use in SQL:** Simple filter on `fact_orders.fulfillment_status = 'RETURNED'`. For P&L analysis use `return_rate` instead.

#### 🎯 When to Use
Use for ops team daily status monitoring. Not for P&L or logistics SLA analysis. Undercounts partial returns (only fully-returned orders are flagged).

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `return_rate` | [metrics.md](#return_rate) | rate with fact_order_returns join, captures partial | Finance/P&L return analysis |
| `post_ship_return_rate` | [metrics.md](#post_ship_return_rate) | rate with shipped denominator + 30-day window | logistics SLA |

#### ❌ Anti-patterns
```sql
-- ❌ Using return_count as P&L measure — undercounts partial returns, no financial context
-- ✅ For P&L: use return_rate (fact_order_returns join)

-- ❌ Treating as a rate — return_count is absolute; don't divide without explicit denominator
```

#### 🏷️ Used In
*Not tracked yet.*

---

## refund_amount

> **Type:** Metric | **Domain:** [Finance](../domains/finance.md) | **Unit:** VND
> **Status:** `active` | **Scope:** any | **Grain:** per return event | **Since:** 2021-01-01

**Definition:** Total refunds paid out in period — financial risk from returned orders. (alias: refund_liability)

**Real question:** "Tổng tiền đã hoàn lại cho khách trong kỳ là bao nhiêu?"
**Time anchor:** `return_date` (refund date, not original ordered_at)

**Formula:**
```sql
SUM(refund_amount)
```

**Column:** `fact_order_returns.refund_amount`

**Intent:** Quantifies VND financial exposure from returns. Use for cash flow risk and reserve sizing.

**Use in SQL:** `SUM(refund_amount)` from `fact_order_returns`

#### 🎯 When to Use
Use when you need the VND impact of returns (not just the rate). Pair with `return_rate` for context.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `return_rate` | [metrics.md](#return_rate) | percentage of orders | measuring operational return risk |
| `realized_revenue` | [metrics.md](#realized_revenue) | net_revenue minus refunds | full cash flow view |

#### ❌ Anti-patterns
*None.*

#### 🏷️ Used In
*Not tracked yet.*

---

## shopee_net_settlement

> **Type:** Metric | **Domain:** [Finance](../domains/finance.md) | **Unit:** VND
> **Status:** `active` | **Scope:** Shopee channel only | **Grain:** per payout | **Since:** 2022-01-01

**Definition:** Actual Shopee transfer to seller after fees and taxes. Matches "Tổng phát hành" column in Shopee Seller Center.

**Real question:** "Shopee thực chuyển bao nhiêu tiền về sau khi trừ phí và thuế?"
**Time anchor:** `payout_released_at` (when Shopee released the payout, not ordered_at)

**Formula:**
```sql
SUM(net_settlement)  -- or SUM(shopee_net_settlement) from fact_order_economics
```

**Column:** `fact_order_economics.shopee_net_settlement` (sourced from `int_shopee_order_fees`)

**Intent:** Reconcile Shopee bank transfers against Seller Center report. Only released payouts included.

**Use in SQL:** `SUM(net_settlement) FILTER (WHERE payout_released_at IS NOT NULL)`

#### 🎯 When to Use
Use specifically for Shopee cash reconciliation. Not for P&L — use `channel_net_profit` instead.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `channel_net_profit` | [metrics.md](#channel_net_profit) | profit concept, not payout | P&L analysis |
| `total_collected` | [metrics.md](#total_collected) | gross cash from customer | customer invoice reconciliation |

#### ❌ Anti-patterns
```sql
-- ❌ Including unreleased payouts — settlement not yet confirmed by Shopee
SELECT SUM(net_settlement) FROM fact_order_economics
WHERE channel = 'shopee'  -- missing: AND payout_released_at IS NOT NULL
```

#### 📊 Data Quality
| Dimension | Status | Note |
|---|---|---|
| Coverage | Shopee orders only | Other channels not applicable |
| Reliability | reliable | Only released payouts (payout_released_at IS NOT NULL) |

#### 🏷️ Used In
*Not tracked yet.*

---

## shopee_platform_fee_rate

> **Type:** Metric | **Domain:** [Finance](../domains/finance.md) | **Unit:** %
> **Status:** `active` | **Scope:** Shopee channel only | **Grain:** per period | **Since:** 2022-01-01

**Definition:** Total Shopee platform fees (service + payment + fixed + infra + voucher_xtra) as % of gross_revenue.

**Real question:** "Phí sàn Shopee chiếm bao nhiêu % doanh thu niêm yết?"
**Denominator:** Shopee channel gross_revenue in the period

**Formula:**
```sql
SUM(shopee_platform_fees + shopee_infra_fee + shopee_voucher_xtra_fee)
  / NULLIF(SUM(gross_revenue), 0)
```

**Intent:** Measures Shopee fee burden on revenue. Thresholds: Healthy <8% | Watch 8-12% | Alert >12%.

**Use in SQL:** Compute from `fact_order_economics` WHERE channel='shopee'.

#### 🎯 When to Use
Use to audit Shopee fee structure changes or compare fee rates across Shopee campaign types.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `channel_net_margin_pct` | [metrics.md](#channel_net_margin_pct) | margin after fees, not fee rate | channel profitability |
| `gross_margin_pct` | [metrics.md](#gross_margin_pct) | COGS efficiency, not fee burden | product-level analysis |

#### ❌ Anti-patterns
```sql
-- ❌ Single fee component only — misses infra + voucher_xtra
SELECT shopee_platform_fees / NULLIF(gross_revenue, 0)
-- Use full sum: shopee_platform_fees + shopee_infra_fee + shopee_voucher_xtra_fee
```

#### 🏷️ Used In
*Not tracked yet.*

---

## realized_revenue

> **Type:** Metric | **Domain:** [Finance](../domains/finance.md) | **Unit:** VND
> **Status:** `active` | **Scope:** any | **Grain:** per period | **Since:** 2021-01-01

**Definition:** Net cash in = total_collected − refund_amount. Cash flow perspective (VAT still included).

**Real question:** "Sau khi trừ hoàn hàng, dòng tiền thực thu là bao nhiêu?"
**Time anchor:** `ordered_at` for revenue component / `return_date` for refund deduction — two different anchors mixed

**Formula:**
```sql
SUM(total_collected) - COALESCE(SUM(refund_amount), 0)
```

**Column:** No pre-computed column in mart — must compute at query time from `fact_orders` + `fact_order_returns`.

**Intent:** Measures actual cash flow after returns. Not an accounting revenue — for cash management only.

**Use in SQL:** Must join `fact_orders` and `fact_order_returns`, aggregate separately, then subtract.

#### 🎯 When to Use
Use for cash flow analysis and working capital estimation. Do NOT use in P&L or compare against net_revenue — VAT is still embedded.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `net_revenue` | [metrics.md](#net_revenue) | VAT stripped, no refund deduction | P&L reporting |
| `total_collected` | [metrics.md](#total_collected) | before refunds | pre-return cash position |

#### ❌ Anti-patterns
```sql
-- ❌ Treating as accounting revenue — VAT embedded
SELECT SUM(total_collected) - COALESCE(SUM(refund_amount), 0) AS p_and_l_revenue
-- ❌ No COALESCE on refund_amount — NULL - anything = NULL
SELECT SUM(total_collected) - SUM(refund_amount)  -- NULL when no returns in period
```

#### 🏷️ Used In
*Not tracked yet.*

---

## target_achievement_rate

> **Type:** Metric | **Domain:** [Finance](../domains/finance.md) | **Unit:** %
> **Status:** `active` | **Scope:** any | **Grain:** per cycle | **Since:** 2021-01-01

**Definition:** % target achieved = actual_revenue / target_val in cycle.

**Real question:** "Doanh thu đạt bao nhiêu % so với mục tiêu kỳ này?"
**Denominator:** target_val set for the cycle
**Time anchor:** `fact_targets` cycle period (not ordered_at — cycle-defined boundaries)

**Formula:**
```sql
SUM(actual_revenue) / NULLIF(SUM(target_val), 0)
```

**Column:** `fact_targets` (source table)

**Intent:** Tracks revenue target attainment by period and segment.

**Use in SQL:** `SUM(actual_revenue) / NULLIF(SUM(target_val), 0) FROM fact_targets`

#### 🎯 When to Use
Use in management dashboards and cycle reviews. Pair with `variance_to_target` for absolute gap context.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `variance_to_target` | [metrics.md](#variance_to_target) | absolute VND gap | understanding magnitude not % |

#### ❌ Anti-patterns
```sql
-- ❌ Missing NULLIF on target — divide-by-zero when target not set
SELECT SUM(actual_revenue) / SUM(target_val) FROM fact_targets
```

#### 🏷️ Used In
*Not tracked yet.*

---

## variance_to_target

> **Type:** Metric | **Domain:** [Finance](../domains/finance.md) | **Unit:** VND
> **Status:** `active` | **Scope:** any | **Grain:** per cycle | **Since:** 2021-01-01

**Definition:** Absolute gap between actual and target in cycle. Positive = over-target, negative = under.

**Real question:** "Còn bao nhiêu VND chênh lệch so với mục tiêu kỳ này?"
**Time anchor:** `fact_targets` cycle period (cycle-defined boundaries, not ordered_at)

**Formula:**
```sql
SUM(actual_revenue) - SUM(target_val)
```

**Column:** `fact_targets` (source table)

**Intent:** Shows VND distance from target. Complements `target_achievement_rate` percentage view.

**Use in SQL:** `SUM(actual_revenue) - SUM(target_val) FROM fact_targets`

#### 🎯 When to Use
Pair with `target_achievement_rate`. Use when you need to size the gap in money terms (e.g., "we need 500M more this month").

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `target_achievement_rate` | [metrics.md](#target_achievement_rate) | % form | comparing achievement across cycles of different scale |

#### ❌ Anti-patterns
*None.*

#### 🏷️ Used In
*Not tracked yet.*

---

## Logistics Metrics

---

## fulfillment_rate

> **Type:** Metric | **Domain:** [Logistics](../domains/logistics.md) | **Unit:** %
> **Status:** `active` | **Scope:** non-DRAFT orders | **Grain:** per period | **Since:** 2021-01-01

**Definition:** % eligible orders fulfilled (fulfillment_status = 'fulfilled').

**Real question:** "Bao nhiêu % đơn đã được xử lý hoàn chỉnh?"
**Denominator:** non-DRAFT orders in the period

**Formula:**
```sql
COUNT(CASE WHEN is_fulfilled THEN 1 END)
  / NULLIF(COUNT(CASE WHEN status != 'DRAFT' THEN 1 END), 0) * 100
```

**Column:** `fact_orders.is_fulfilled` (pre-computed flag); `orders_core_metrics.yaml` fulfillment_rate measure.

**Intent:** Measures warehouse order execution capacity. Threshold: Drop <85% → investigate bottleneck.

**Use in SQL:** `COUNT(is_fulfilled=true) / NULLIF(COUNT(status != 'DRAFT'), 0) * 100`

#### 🎯 When to Use
Use for warehouse operations monitoring. Drop below 85% signals capacity or process issue.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `same_day_ship_rate` | [metrics.md](#same_day_ship_rate) | speed (same day) not rate | measuring platform SLA compliance |

#### ❌ Anti-patterns
```sql
-- ❌ Re-derives status manually instead of using is_active_order
WHERE status NOT IN ('CANCELLED', 'DRAFT')
-- ✅ AND is_active_order  (pre-computed gate: status != 'CANCELLED')
```

#### 🏷️ Used In
*Not tracked yet.*

---

## same_day_ship_rate

> **Type:** Metric | **Domain:** [Logistics](../domains/logistics.md) | **Unit:** %
> **Status:** `active` | **Scope:** non-DRAFT orders | **Grain:** per period | **Since:** 2021-01-01

**Definition:** % orders shipped on the same calendar date (ICT) as order creation — e-commerce platform KPI.

**Real question:** "Bao nhiêu % đơn được giao tay carrier ngay ngày đặt hàng?"
**Denominator:** non-DRAFT orders in the period
**Time anchor:** `ordered_at` calendar date (ICT) compared to `first_shipped_at` calendar date — calendar day comparison, not 24h window

**Formula:**
```sql
COUNT(ship_same_day_flag = true)
  / NULLIF(COUNT(CASE WHEN status != 'DRAFT' THEN 1 END), 0)
```

**Column:** `fact_orders.ship_same_day_flag` (pre-computed boolean); `orders_core_metrics.yaml` same_day_ship_rate.

**Intent:** Measures fulfillment speed against e-commerce platform SLA requirements.

**Use in SQL:** `COUNT(ship_same_day_flag=true) / NULLIF(COUNT(status!='DRAFT'), 0)`

#### 🎯 When to Use
Use for platform SLA compliance monitoring. "Same-day" = calendar date ICT, NOT within 24 hours — orders created after warehouse cutoff (18h) cannot achieve same-day ship.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `avg_hours_to_first_ship` | [metrics.md](#avg_hours_to_first_ship) | continuous hours, not binary flag | measuring warehouse processing speed |
| `fulfillment_rate` | [metrics.md](#fulfillment_rate) | fulfilled (any day) not same-day | overall execution capacity |

#### ❌ Anti-patterns
```sql
-- ❌ "Same-day" interpreted as within 24 hours — wrong for platform SLA
-- Platform SLA is calendar date ICT, not 24h window
-- ship_same_day_flag is pre-computed using ICT date comparison, do not recompute
```

#### 🏷️ Used In
*Not tracked yet.*

---

## avg_hours_to_first_ship

> **Type:** Metric | **Domain:** [Logistics](../domains/logistics.md) | **Unit:** hours
> **Status:** `active` | **Scope:** shipped orders only | **Grain:** per period | **Since:** 2021-01-01

**Definition:** Average hours from order creation to first shipment — measures warehouse processing speed. (alias: order_cycle_time)

**Real question:** "Trung bình mất bao nhiêu giờ từ khi đặt đơn đến khi ship?"

**Formula:**
```sql
AVG(hours_to_first_ship) WHERE first_shipped_at IS NOT NULL
```

**Column:** `fact_orders.first_shipped_at`; `orders_core_metrics.yaml` avg_hours_to_first_ship.

**Intent:** Benchmarks warehouse speed from order receipt to handoff to carrier.

**Use in SQL:** `AVG(hours_to_first_ship) FILTER (WHERE first_shipped_at IS NOT NULL)`

#### 🎯 When to Use
Use for warehouse operations benchmarking. Measures warehouse speed only (not delivery). Negative hours = timezone bug — add `WHERE hours_to_first_ship > 0` filter.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `time_to_complete_hours` | [metrics.md](#time_to_complete_hours) | order→COMPLETED (includes delivery+collection) | end-to-end customer experience |
| `same_day_ship_rate` | [metrics.md](#same_day_ship_rate) | binary same-day flag | platform SLA compliance |

#### ❌ Anti-patterns
```sql
-- ❌ Including negative hours — indicates timezone data issue
SELECT AVG(hours_to_first_ship) FROM fact_orders
WHERE first_shipped_at IS NOT NULL  -- missing: AND hours_to_first_ship > 0
```

#### 🏷️ Used In
*Not tracked yet.*

---

## time_to_complete_hours

> **Type:** Metric | **Domain:** [Logistics](../domains/logistics.md) | **Unit:** hours
> **Status:** `active` | **Scope:** COMPLETED orders only | **Grain:** per period | **Since:** 2021-01-01

**Definition:** Average hours from order creation to status COMPLETED — end-to-end order lifecycle.

**Real question:** "Trung bình mất bao nhiêu giờ để hoàn tất toàn bộ vòng đời đơn hàng?"

**Formula:**
```sql
AVG(time_to_complete_hours) WHERE status = 'COMPLETED'
```

**Column:** `fact_orders.time_to_complete_hours` (pre-computed).

**Intent:** Measures total customer experience cycle including delivery and payment collection.

**Use in SQL:** `AVG(time_to_complete_hours) FILTER (WHERE status = 'COMPLETED')`

#### 🎯 When to Use
Use for customer experience measurement. Distinct from `avg_hours_to_first_ship` — this includes delivery + collection, not just warehouse processing.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `avg_hours_to_first_ship` | [metrics.md](#avg_hours_to_first_ship) | order→ship only (warehouse speed) | warehouse operations |

#### ❌ Anti-patterns
```sql
-- ❌ Not filtering to COMPLETED — includes in-transit orders with no end time
SELECT AVG(time_to_complete_hours) FROM fact_orders
-- missing: WHERE status = 'COMPLETED'
```

#### 🏷️ Used In
*Not tracked yet.*

---

## Customer Metrics

---

## mau

> **Type:** Metric | **Domain:** [Customer](../domains/customer.md) | **Unit:** count
> **Status:** `active` | **Scope:** scope_retail (recommended) | **Grain:** per rolling 30-day window | **Since:** 2021-01-01

**Definition:** Unique customers with an order in the past 30 days. (Monthly Active Users)

**Real question:** "Có bao nhiêu khách hàng đã mua trong 30 ngày qua?"
**Time anchor:** `ordered_at` — 30-day rolling window back from current_date

**Formula:**
```sql
COUNT(DISTINCT customer_key)
WHERE ordered_at >= CURRENT_DATE - INTERVAL '30 days'
  AND scope_retail
```

**Intent:** Tracks monthly active customer base size. Inputs to `health_score` Customer Loyalty component.

**Use in SQL:** `COUNT(DISTINCT customer_key) WHERE ordered_at >= CURRENT_DATE - 30 AND scope_retail`

#### 🎯 When to Use
Use as denominator for per-customer rates (arpu, retention). Apply `scope_retail` — B2B "active" is contract-based not frequency-based.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `retention_rate` | [metrics.md](#retention_rate) | % retained across periods | cohort health analysis |
| `churn_rate` | [metrics.md](#churn_rate) | % lost | identifying loss risk |
| `repeat_buyer_rate` | [metrics.md](#repeat_buyer_rate) | repeat buyer % of orders | loyalty signal within a period |
| `mau_repeat` | [metrics.md](#mau_repeat) | MAU filtered to ≥2 lifetime orders | measuring engaged core vs total active |

#### ❌ Anti-patterns
```sql
-- ❌ No scope filter — B2B high-value accounts distort active count
SELECT COUNT(DISTINCT customer_key) FROM fact_orders
WHERE ordered_at >= CURRENT_DATE - 30  -- missing AND scope_retail
```

#### 🏷️ Used In
*Not tracked yet.*

---

## mau_repeat

> **Type:** Metric | **Domain:** [Customer](../domains/customer.md) | **Unit:** count
> **Status:** `active` | **Scope:** scope_retail (required) | **Grain:** per rolling 30-day window | **Since:** 2021-01-01

**Definition:** Unique customers with ≥ 2 lifetime orders who placed at least one order in the past 30 days. (Repeat-buyer MAU)

**Real question:** "Trong MAU, có bao nhiêu khách đã mua nhiều hơn 1 lần (đã chứng minh quay lại)?"
**Time anchor:** `ordered_at` — 30-day rolling window back from current_date
**Order count source:** `dim_customers.order_count` (= lifetime order frequency, active orders only)

**Formula:**
```sql
COUNT(DISTINCT o.customer_key)
FROM fact_orders o
JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.ordered_at >= CURRENT_DATE - INTERVAL '30 days'
  AND o.scope_retail
  AND c.order_count >= 2
```

**Intent:** Filters out one-time buyers from MAU to expose the "engaged core" — customers who have proven they return. Used as a quality signal alongside `mau`: if `mau` grows but `mau_repeat` stays flat, growth is driven by first-time buyers, not retention.

**Use in SQL:** Join `fact_orders` + `dim_customers`, filter `order_count >= 2` and 30-day window.

#### 🎯 When to Use
Use when MAU alone is insufficient — e.g., when one-time buyers inflate active count and mask real engagement health. Plot alongside `mau` on a trend to see the gap widen or narrow over time.

#### ⚠️ Conflicts
`order_count` in `dim_customers` is a **lifetime** count, not period-scoped — a customer with 2 total orders counts even if the 2nd was 2 years ago. This is intentional: the signal is "has demonstrated willingness to return", not "bought twice recently".

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `mau` | [metrics.md](#mau) | includes one-time buyers | sizing total active base |
| `repeat_buyer_rate` | [metrics.md](#repeat_buyer_rate) | ratio within a period, not count | comparing loyalty % across periods |
| `retention_rate` | [metrics.md](#retention_rate) | cohort-based, cross-period | measuring period-over-period return |

#### ❌ Anti-patterns
```sql
-- ❌ Counting repeat orders in last 30 days instead of repeat customers
WHERE order_count_in_period >= 2  -- wrong grain — mau_repeat uses lifetime order_count, not period count

-- ❌ Using frequency from fact_orders aggregate instead of dim_customers.order_count
-- dim_customers.order_count is pre-computed and consistent with other customer metrics
```

#### 🏷️ Used In
*Not tracked yet.*

---

## retention_rate

> **Type:** Metric | **Domain:** [Customer](../domains/customer.md) | **Unit:** %
> **Status:** `active` | **Scope:** scope_retail (required) | **Grain:** per cohort period | **Since:** 2021-01-01

**Definition:** % customers who return to purchase in the next period (retail cohort).

**Real question:** "Bao nhiêu % khách kỳ trước tiếp tục mua trong kỳ này?"
**Denominator:** customers who ordered in cohort period N
**Time anchor:** cohort period boundary (period N vs period N+1 — not a single column, requires explicit window parameters)

**Formula:**
```sql
-- Cohort-based:
Customers_with_purchase_in_period_N+1 / Customers_in_period_N * 100
```

**Intent:** Measures customer loyalty and retention effectiveness. B2B retention has different contract-based logic.

**Use in SQL:** Requires cohort windowing on `dim_customers` + `fact_orders`. Not a simple column aggregate.

#### 🎯 When to Use
Use for cohort health analysis across months or quarters. Requires explicit scope_retail — B2B retention logic is contract-based, not frequency-based.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `churn_rate` | [metrics.md](#churn_rate) | 100% − retention (lost customers) | focusing on loss side |
| `repeat_buyer_rate` | [metrics.md](#repeat_buyer_rate) | repeat buyers within a single period | within-period loyalty signal |
| `mau` | [metrics.md](#mau) | absolute active count not rate | sizing the active base |

#### ❌ Anti-patterns
```sql
-- ❌ scope_b2b included — B2B retention is contract-driven, not order-frequency
SELECT ... FROM dim_customers  -- missing WHERE scope_retail
```

#### 📊 Data Quality
| Dimension | Status | Note |
|---|---|---|
| Coverage | scope_retail only | B2B retention not tracked in this metric |
| Historical | reliable | Reliable from ingestion start date |

#### 🏷️ Used In
*Not tracked yet.*

---

## churn_rate

> **Type:** Metric | **Domain:** [Customer](../domains/customer.md) | **Unit:** %
> **Status:** `active` | **Scope:** scope_retail (required) | **Grain:** per snapshot | **Since:** 2021-01-01

**Definition:** % customers with customer_status = 'Churned' (last purchase > 90 days ago).

**Real question:** "Bao nhiêu % khách đã ngừng mua (quá 90 ngày chưa mua lại)?"
**Denominator:** all scope_retail customers in the dim_customers snapshot
**Time anchor:** `last_order_date` — 90-day threshold from current_date (point-in-time snapshot)

**Formula:**
```sql
COUNT(*) FILTER (WHERE customer_status = 'Churned')
  / NULLIF(COUNT(*), 0) * 100
```

**Column:** `dim_customers.customer_status`

**Intent:** Identifies pace of customer loss to prioritize retention interventions.

**Use in SQL:** `COUNT(customer_status='Churned') / NULLIF(COUNT(*), 0) * 100 FROM dim_customers WHERE scope_retail`

#### 🎯 When to Use
Use for retention risk alerting. 90-day churn threshold is hardcoded in `dim_customers.customer_status` logic — do not redefine.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `retention_rate` | [metrics.md](#retention_rate) | inverse — those who stayed | cohort loyalty analysis |
| `mau` | [metrics.md](#mau) | active count, not churn rate | sizing active base |

#### ❌ Anti-patterns
```sql
-- ❌ Redefining churn threshold — inconsistent with dim_customers.customer_status
SELECT COUNT(*) FILTER (WHERE last_order_date < CURRENT_DATE - 60)  -- wrong threshold
-- ✅ Use customer_status = 'Churned' (90-day logic pre-applied)
```

#### 🏷️ Used In
*Not tracked yet.*

---

## returning_rate

> **Type:** Metric | **Domain:** [Customer](../domains/customer.md) | **Unit:** %
> **Status:** `deprecated` | **Scope:** scope_retail (recommended) | **Grain:** per period | **Since:** 2021-01-01

**⚠️ DEPRECATED** — Use [`repeat_buyer_rate`](#repeat_buyer_rate) instead. "returning" is ambiguous in English (returning goods vs returning customer). `repeat_buyer_rate` is the unambiguous replacement.

**Definition:** % of orders/customers who have purchased before — repeat buyer signal. (Renamed to `repeat_buyer_rate`.)

**Use in SQL:** Migrate all references to `repeat_buyer_rate`.

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `repeat_buyer_rate` | [metrics.md](#repeat_buyer_rate) | **replacement** — same metric, unambiguous name | always — this entry is deprecated |

---

## repeat_buyer_rate

> **Type:** Metric | **Domain:** [Sales](../domains/sales.md) | **Unit:** %
> **Status:** `active` | **Scope:** scope_retail (required) | **Grain:** per period (7-day rolling) | **Since:** 2021-01-01

**Definition:** % of customers who ordered in the period that had purchased before the window start. Component of Health Score (Customer Loyalty, max 25 points). Replaces `returning_rate`.

**Real question:** "Trong khách mua tuần này, bao nhiêu % là khách cũ?"
**Denominator:** all customers who placed an order in the 7-day rolling window
**Time anchor:** `ordered_at` (7-day rolling window)

**Formula:**
```sql
COUNT(DISTINCT CASE WHEN c.first_order_date < :window_start THEN o.customer_key END)::float
  / NULLIF(COUNT(DISTINCT o.customer_key), 0) * 100
FROM fact_orders o
JOIN dim_customers c USING (customer_key)
WHERE o.scope_retail
  AND o.date_key BETWEEN :window_start AND :window_end  -- 7-day rolling
```

**Intent:** Within-period loyalty signal. Measures what fraction of this week's buyers are repeat customers. Used in `health_score` Customer Loyalty component.

**Use in SQL:** Join `fact_orders` with `dim_customers.first_order_date`; compare `first_order_date` to `window_start` (not current date). Apply `scope_retail`.

#### 🎯 When to Use
Use for within-period loyalty snapshots or health_score calculation. Distinct from `retention_rate` (cohort-based across periods). NOT related to returns — this is a loyalty metric.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `retention_rate` | [metrics.md](#retention_rate) | cohort-based across periods | multi-period retention analysis |
| `churn_rate` | [metrics.md](#churn_rate) | inverse — those who left | loss risk identification |
| `return_rate` | [metrics.md](#return_rate) | hoàn hàng (refunds), completely unrelated | Finance/P&L return analysis |

#### ❌ Anti-patterns
```sql
-- ❌ Confusing with return_rate — repeat_buyer_rate is loyalty (mua lại), NOT hoàn hàng
-- ❌ Missing scope_retail — B2B "repeat" has different contract-based logic
-- ❌ Using current_date as window boundary instead of window_start
WHERE c.first_order_date < CURRENT_DATE  -- wrong: should be < window_start
```

#### 🏷️ Used In
- `health_score` — Customer Loyalty component (see sales_today_operation.md, sales_daily_retail.md)

---

## clv

> **Type:** Metric | **Domain:** [Customer](../domains/customer.md) | **Unit:** VND
> **Status:** `active` | **Scope:** non-CANCELLED/non-DRAFT orders | **Grain:** per customer | **Since:** 2021-01-01

**Definition:** Total revenue generated by a customer from first purchase to date (Phase 1: historical). Phase 2 projected CLV is planned. (Customer Lifetime Value)

**Real question:** "Tổng doanh thu khách này đã tạo ra từ lần mua đầu tiên đến nay là bao nhiêu?"

**Formula:**
```sql
SUM(total_collected) WHERE is_active_order
```

**Column:** `dim_customers.lifetime_value`

**Intent:** Ranks customers by total value for segmentation and prioritization.

**Use in SQL:** `dim_customers.lifetime_value` (pre-computed)

#### 🎯 When to Use
Use for customer segmentation and VIP identification. Phase 1 is historical accumulation only — does not predict future value.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `arpu` | [metrics.md](#arpu) | average revenue per user per period | period-level revenue contribution |

#### ❌ Anti-patterns
```sql
-- ❌ Including cancelled orders — overstates lifetime value
SELECT SUM(total_collected) FROM fact_orders
WHERE customer_key = :id  -- missing: AND is_active_order
```

#### 📊 Data Quality
| Dimension | Status | Note |
|---|---|---|
| Historical | reliable | Phase 1 historical accumulation |
| Projected | planned | Phase 2 projected CLV model not yet built |

#### 🏷️ Used In
*Not tracked yet.*

---

## arpu

> **Type:** Metric | **Domain:** [Customer](../domains/customer.md) | **Unit:** VND
> **Status:** `active` | **Scope:** any | **Grain:** per period | **Since:** 2021-01-01

**Definition:** Average revenue per active user in period. (Average Revenue Per User)

**Real question:** "Trung bình mỗi khách hàng đóng góp bao nhiêu doanh thu trong kỳ?"
**Denominator:** unique customers who placed an order in the period

**Formula:**
```sql
SUM(net_revenue) / NULLIF(COUNT(DISTINCT customer_key), 0)
```

**Intent:** Measures per-customer revenue contribution in a period. Complement to AOV (per-order) and CLV (lifetime).

**Use in SQL:** `SUM(net_revenue) / NULLIF(COUNT(DISTINCT customer_key), 0) FROM fact_orders`

#### 🎯 When to Use
Use when the unit of analysis is customers (not orders). If a customer places 3 orders, ARPU captures total spend; AOV captures single-order average.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `aov` | [metrics.md](#aov) | per-order not per-customer | order-level basket analysis |
| `clv` | [metrics.md](#clv) | total lifetime not per-period | customer ranking and segmentation |

#### ❌ Anti-patterns
```sql
-- ❌ COUNT(*) instead of COUNT(DISTINCT customer_key) — counts orders not customers
SELECT SUM(net_revenue) / NULLIF(COUNT(*), 0) AS arpu FROM fact_orders
```

#### 🏷️ Used In
*Not tracked yet.*

---

## cac

> **Type:** Metric | **Domain:** [Customer](../domains/customer.md) | **Unit:** VND
> **Status:** `planned` | **Scope:** new customers | **Grain:** per period | **Since:** —

**Definition:** Average cost to acquire one new customer. (Customer Acquisition Cost)

**Real question:** "Trung bình tốn bao nhiêu chi phí marketing để có 1 khách hàng mới?"
**Denominator:** new customers acquired in the period (first_order_date falls within period)

**Formula:**
```sql
SUM(marketing_spend) / NULLIF(COUNT(DISTINCT new_customers), 0)
-- Planned: requires fact_marketing_spend fully populated
```

**Intent:** Measures acquisition efficiency. Pairs with CLV for LTV:CAC ratio.

**Use in SQL:** Not yet computable — requires marketing attribution model.

#### 🎯 When to Use
Planned for use after `fact_marketing_spend` is complete with channel attribution. Currently not computable automatically.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `roas` | [metrics.md](#roas) | revenue per ad spend | measuring campaign return, not acquisition cost |

#### ❌ Anti-patterns
*None.*

#### 📊 Data Quality
| Dimension | Status | Note |
|---|---|---|
| Coverage | planned | Needs full fact_marketing_spend with channel attribution |

#### 🏷️ Used In
*Not tracked yet.*

---

## Product & Inventory Metrics

---

## units_sold

> **Type:** Metric | **Domain:** [Sales/Product](../domains/product.md) | **Unit:** count
> **Status:** `active` | **Scope:** confirmed orders | **Grain:** per item | **Since:** 2021-01-01

**Definition:** Total product units sold in confirmed orders.

**Real question:** "Bao nhiêu đơn vị sản phẩm đã được bán ra?"

**Formula:**
```sql
SUM(quantity)
```

**Column:** `fact_order_items.quantity` (or `fact_sales.quantity`)

**Intent:** Measures product volume output. Denominator for `avg_selling_price`.

**Use in SQL:** `SUM(quantity) FROM fact_sales WHERE is_active_order`

#### 🎯 When to Use
Use for inventory planning, velocity calculations, and product ranking.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `orders_count` | [metrics.md](#orders_count) | orders not units | order volume analysis |
| `basket_size` | [metrics.md](#basket_size) | units per order average | cross-sell optimization |

#### ❌ Anti-patterns
```sql
-- ❌ Including cancelled orders — inflates inventory depletion estimates
SELECT SUM(quantity) FROM fact_order_items  -- missing status filter
```

#### 🏷️ Used In
*Not tracked yet.*

---

## basket_size

> **Type:** Metric | **Domain:** [Sales/Product](../domains/product.md) | **Unit:** count
> **Status:** `active` | **Scope:** any | **Grain:** per order (averaged) | **Since:** 2021-01-01

**Definition:** Average number of product units per order. (alias: avg_items_per_order)

**Real question:** "Trung bình mỗi đơn hàng có bao nhiêu sản phẩm?"
**Denominator:** orders in the period (COUNT DISTINCT order_id)

**Formula:**
```sql
SUM(quantity) / NULLIF(COUNT(DISTINCT order_id), 0)
```

**Intent:** Measures basket depth for cross-sell and upsell optimization.

**Use in SQL:** `SUM(quantity) / NULLIF(COUNT(DISTINCT order_id), 0) FROM fact_order_items`

#### 🎯 When to Use
Use to track whether promotions or merchandising changes are driving multi-item purchase behavior.

**Note:** For operational monitoring of fulfilled orders (e.g., Today Sales dashboard), add `AND o.is_active_order` to exclude cancelled order lines. Use without the filter only when measuring customer intent across all order attempts.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `aov` | [metrics.md](#aov) | revenue per order (VND) | revenue basket value |
| `units_sold` | [metrics.md](#units_sold) | total volume not per-order average | volume analysis |

#### ❌ Anti-patterns
```sql
-- ❌ COUNT(*) at order level — doesn't count items
SELECT COUNT(*) / NULLIF(COUNT(DISTINCT order_id), 0) FROM fact_order_items  -- always ~1
```

#### 🏷️ Used In
*Not tracked yet.*

---

## avg_selling_price

> **Type:** Metric | **Domain:** [Sales/Product](../domains/product.md) | **Unit:** VND/unit
> **Status:** `active` | **Scope:** any | **Grain:** per SKU (averaged) | **Since:** 2021-01-01

**Definition:** Average realized selling price per unit.

**Real question:** "Giá bán thực tế trung bình mỗi đơn vị sản phẩm là bao nhiêu?"
**Denominator:** units sold (SUM quantity) in the period

**Formula:**
```sql
SUM(net_revenue) / NULLIF(SUM(quantity), 0)
```

**Intent:** Tracks actual selling price evolution over time and across channels. Monitors price erosion or premium capture.

**Use in SQL:** `SUM(net_revenue) / NULLIF(SUM(quantity), 0) FROM fact_sales`

#### 🎯 When to Use
Use for price trend analysis per SKU or category. Compare across channels to identify pricing inconsistencies.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `aov` | [metrics.md](#aov) | revenue per order not per unit | order-level basket analysis |

#### ❌ Anti-patterns
```sql
-- ❌ Using gross_revenue instead of net_revenue — includes pre-discount and VAT
SELECT SUM(gross_revenue) / NULLIF(SUM(quantity), 0)  -- inflated by discount + VAT
```

#### 🏷️ Used In
*Not tracked yet.*

---

## oos_rate

> **Type:** Metric | **Domain:** [Sales/Product](../domains/product.md) | **Unit:** %
> **Status:** `active` | **Scope:** active SKUs, per location | **Grain:** per snapshot date | **Since:** 2022-01-01

**Definition:** % of active SKUs with on_hand ≤ 0 at snapshot date, by location. (Out of Stock Rate)

**Real question:** "Bao nhiêu % SKU đang hết hàng tại thời điểm kiểm tra?"
**Denominator:** active SKUs at the snapshot date, per location
**Time anchor:** snapshot date (point-in-time inventory position, not a sales period)

**Formula:**
```sql
COUNT(DISTINCT CASE WHEN is_oos THEN sku END)
  / NULLIF(COUNT(DISTINCT sku), 0) * 100
```

**Column:** `mart_inventory_health.is_oos`

**Intent:** Identifies stockout risk to prioritize replenishment. Thresholds: Green <5% | Amber 5-10% | Red >10%.

**Use in SQL:** `COUNT(is_oos=true) / NULLIF(COUNT(DISTINCT sku), 0) * 100 FROM mart_inventory_health`

#### 🎯 When to Use
Always filter by location — MM Market (consignment) has structurally high OOS which is expected and should not trigger the same alert as warehouse OOS.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `days_of_supply` | [metrics.md](#days_of_supply) | forward-looking days of cover | planning replenishment timing |

#### ❌ Anti-patterns
```sql
-- ❌ No location filter — MM Market consignment OOS inflates rate misleadingly
SELECT COUNT(is_oos) / COUNT(sku) FROM mart_inventory_health
-- missing: WHERE location_id != 'MM_MARKET'
```

#### 🔍 Null & Zero
NULL `days_of_supply` when SKU has no sales history in rolling 24 months.

#### 🏷️ Used In
*Not tracked yet.*

---

## days_of_supply

> **Type:** Metric | **Domain:** [Sales/Product](../domains/product.md) | **Unit:** days
> **Status:** `active` | **Scope:** active SKUs with sales history | **Grain:** per SKU per snapshot | **Since:** 2022-01-01

**Definition:** Days of current stock at current daily sales velocity.

**Real question:** "Với tốc độ bán hiện tại, hàng tồn còn đủ dùng bao nhiêu ngày?"
**Time anchor:** snapshot date (point-in-time stock position vs rolling 24-month velocity)

**Formula:**
```sql
on_hand / daily_velocity  -- pre-computed in mart
```

**Column:** `mart_inventory_health.days_of_supply`

**Intent:** Prioritizes restocking urgency. Lower = more urgent.

**Use in SQL:** `mart_inventory_health.days_of_supply` (pre-computed)

#### 🎯 When to Use
Use for replenishment planning. Pair with `oos_rate` for current snapshot vs forward-looking view.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `oos_rate` | [metrics.md](#oos_rate) | current stockout % not forward days | current stockout alerting |

#### ❌ Anti-patterns
```sql
-- ❌ Manual recomputation with wrong velocity window — use mart pre-computed value
SELECT on_hand / (SUM(quantity) / 7) AS days_supply  -- 7-day window may not match mart
-- ✅ Use mart_inventory_health.days_of_supply
```

#### 🔍 Null & Zero
NULL when SKU has no sales history in rolling 24 months — cannot compute velocity.

#### 🏷️ Used In
*Not tracked yet.*

---

## Marketing Metrics

---

## marketing_spend

> **Type:** Metric | **Domain:** Marketing | **Unit:** VND
> **Status:** `active` | **Scope:** any | **Grain:** per campaign/channel/period | **Since:** 2022-01-01

**Definition:** Total marketing spend by channel/campaign in period.

**Real question:** "Tổng ngân sách marketing đã chi trong kỳ là bao nhiêu?"

**Formula:**
```sql
SUM(spend_amount)
```

**Column:** `fact_marketing_spend.spend_amount`; `marketing_spend_core_metrics.yaml` spend.

**Intent:** Total marketing investment for ROI and ROAS calculations.

**Use in SQL:** `SUM(spend_amount) FROM fact_marketing_spend`

#### 🎯 When to Use
Baseline denominator for `roas` and `cac`. Segment by channel_type or campaign for granular spend analysis.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
*None.*

#### ❌ Anti-patterns
*None.*

#### 🏷️ Used In
*Not tracked yet.*

---

## clicks

> **Type:** Metric | **Domain:** Marketing | **Unit:** count
> **Status:** `active` | **Scope:** any | **Grain:** per campaign | **Since:** 2022-01-01

**Definition:** Total clicks from marketing campaigns.

**Real question:** "Tổng số lượt nhấp vào quảng cáo trong kỳ là bao nhiêu?"

**Formula:**
```sql
SUM(clicks)
```

**Column:** `fact_marketing_spend.clicks`

**Intent:** Measures ad engagement volume. Numerator for `ctr` and denominator for `cpc`.

**Use in SQL:** `SUM(clicks) FROM fact_marketing_spend`

#### 🎯 When to Use
Use in combination with `impressions` (for CTR) and `marketing_spend` (for CPC). Raw click count alone is not actionable without context.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `impressions` | [metrics.md](#impressions) | exposure not engagement | measuring reach |
| `ctr` | [metrics.md](#ctr) | clicks/impressions rate | comparing ad creative effectiveness |

#### ❌ Anti-patterns
*None.*

#### 🏷️ Used In
*Not tracked yet.*

---

## impressions

> **Type:** Metric | **Domain:** Marketing | **Unit:** count
> **Status:** `active` | **Scope:** any | **Grain:** per campaign | **Since:** 2022-01-01

**Definition:** Total ad impressions served.

**Real question:** "Tổng số lần quảng cáo được hiển thị trong kỳ là bao nhiêu?"

**Formula:**
```sql
SUM(impressions)
```

**Column:** `fact_marketing_spend.impressions`

**Intent:** Measures total reach of campaigns. Denominator for `ctr` and `cpm`.

**Use in SQL:** `SUM(impressions) FROM fact_marketing_spend`

#### 🎯 When to Use
Use for brand awareness and reach analysis. Pair with `clicks` for CTR efficiency.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `clicks` | [metrics.md](#clicks) | engagement not exposure | measuring ad response |

#### ❌ Anti-patterns
*None.*

#### 🏷️ Used In
*Not tracked yet.*

---

## ctr

> **Type:** Metric | **Domain:** Marketing | **Unit:** %
> **Status:** `active` | **Scope:** any | **Grain:** per campaign | **Since:** 2022-01-01

**Definition:** Click-through rate = clicks / impressions.

**Real question:** "Bao nhiêu % lần hiển thị quảng cáo dẫn đến lượt nhấp?"
**Denominator:** total impressions in the period

**Formula:**
```sql
SUM(clicks) / NULLIF(SUM(impressions), 0)
```

**Intent:** Measures ad creative appeal and audience targeting quality.

**Use in SQL:** `SUM(clicks) / NULLIF(SUM(impressions), 0) FROM fact_marketing_spend`

#### 🎯 When to Use
Use for A/B testing ad creatives. Benchmark varies by platform (Search: ~3-5%, Display: ~0.1-0.5%).

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `cpc` | [metrics.md](#cpc) | cost efficiency per click | spend efficiency analysis |

#### ❌ Anti-patterns
```sql
-- ❌ Missing NULLIF — divide-by-zero when new campaigns have 0 impressions
SELECT SUM(clicks) / SUM(impressions) FROM fact_marketing_spend
```

#### 🏷️ Used In
*Not tracked yet.*

---

## cpc

> **Type:** Metric | **Domain:** Marketing | **Unit:** VND
> **Status:** `active` | **Scope:** any | **Grain:** per campaign | **Since:** 2022-01-01

**Definition:** Cost per click. (Cost Per Click)

**Real question:** "Chi bao nhiêu tiền để có 1 lượt nhấp vào quảng cáo?"
**Denominator:** total clicks in the period

**Formula:**
```sql
SUM(spend_amount) / NULLIF(SUM(clicks), 0)
```

**Intent:** Measures traffic acquisition cost efficiency.

**Use in SQL:** `SUM(spend_amount) / NULLIF(SUM(clicks), 0) FROM fact_marketing_spend`

#### 🎯 When to Use
Use for bid optimization and channel cost comparison. High CPC + low CTR = low-quality targeting.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `cpm` | [metrics.md](#cpm) | cost per 1000 impressions | brand/awareness campaigns |
| `ctr` | [metrics.md](#ctr) | click rate not cost | creative effectiveness |

#### ❌ Anti-patterns
```sql
-- ❌ Missing NULLIF — divide-by-zero on zero-click campaigns
SELECT SUM(spend_amount) / SUM(clicks) FROM fact_marketing_spend
```

#### 🏷️ Used In
*Not tracked yet.*

---

## cpm

> **Type:** Metric | **Domain:** Marketing | **Unit:** VND
> **Status:** `active` | **Scope:** any | **Grain:** per campaign | **Since:** 2022-01-01

**Definition:** Cost per 1000 impressions. (Cost Per Mille)

**Real question:** "Chi bao nhiêu tiền để có 1000 lần hiển thị quảng cáo?"
**Denominator:** 1000 impressions in the period

**Formula:**
```sql
1000 * SUM(spend_amount) / NULLIF(SUM(impressions), 0)
```

**Intent:** Standard industry metric for brand awareness campaign cost efficiency.

**Use in SQL:** `1000 * SUM(spend_amount) / NULLIF(SUM(impressions), 0) FROM fact_marketing_spend`

#### 🎯 When to Use
Use for brand/awareness campaigns. Prefer `cpc` for direct-response campaigns where clicks are the goal.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `cpc` | [metrics.md](#cpc) | per click not per 1000 impressions | performance campaigns |

#### ❌ Anti-patterns
```sql
-- ❌ Forgetting the 1000 multiplier — CPM without ×1000 is just spend/impression
SELECT SUM(spend_amount) / SUM(impressions)  -- this is cost-per-single-impression
```

#### 🏷️ Used In
*Not tracked yet.*

---

## roas

> **Type:** Metric | **Domain:** Marketing | **Unit:** ratio
> **Status:** `planned` | **Scope:** attributed orders | **Grain:** per campaign | **Since:** —

**Definition:** Revenue generated per VND of ad spend. (Return on Ad Spend). Planned — requires join between fact_marketing_spend and fact_orders via campaign attribution.

**Real question:** "Mỗi đồng chi marketing tạo ra bao nhiêu đồng doanh thu?"
**Denominator:** marketing spend in the period (via attribution model)

**Formula:**
```sql
SUM(net_revenue) / NULLIF(SUM(spend_amount), 0)
-- Planned: requires marketing attribution model
```

**Intent:** Primary marketing efficiency metric. e.g. 3.5x = 3.5 VND revenue per 1 VND spend.

**Use in SQL:** Not yet computable automatically — requires attribution model to link spend to orders.

#### 🎯 When to Use
Use once attribution model is available. For now, use `marketing_spend` + `net_revenue` in separate panels without joining.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `cac` | [metrics.md](#cac) | cost per new customer not revenue ratio | customer acquisition efficiency |

#### ❌ Anti-patterns
*None.*

#### 📊 Data Quality
| Dimension | Status | Note |
|---|---|---|
| Coverage | planned | Needs marketing attribution model linking spend→orders |

#### 🏷️ Used In
*Not tracked yet.*

---

## Composite Metrics

---

## health_score

> **Type:** Metric | **Domain:** [Sales](../domains/sales.md) | **Unit:** 0-100
> **Status:** `active` | **Scope:** scope_retail | **Grain:** per 7-day rolling window | **Since:** 2021-01-01

**Definition:** Composite 0-100 business health score — sum of 4 components (Revenue Momentum, Order Momentum, Customer Loyalty, AOV Stability), each max 25 points.

**Real question:** "Sức khỏe kinh doanh tổng thể trong tuần này đang ở mức nào?"
**Time anchor:** 7-day rolling window anchored to yesterday (ordered_at based)

**Formula:**
```sql
-- See guides/health_score.md for full scoring table
-- Components: revenue_momentum + order_momentum + customer_loyalty + aov_stability
```

**Intent:** Synthesizes multiple signals into a single indicator for rapid business health assessment. Thresholds: 75-100 Healthy | 50-74 Watch | 0-49 Alert.

**Use in SQL:** Computed in mart or Rill — do not recompute components manually. See [health_score guide](../guides/health_score.md).

#### 🎯 When to Use
Use for executive/daily health monitoring. Drill into individual components when score drops to identify root cause. Designed for retail SMB Vietnam context.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `repeat_buyer_rate` | [metrics.md](#repeat_buyer_rate) | one component only (Customer Loyalty) | deep-dive on loyalty signal |
| `aov` | [metrics.md](#aov) | one component (AOV Stability) | basket value analysis |

#### ❌ Anti-patterns
```sql
-- ❌ Computing health_score outside the defined 7-day rolling window
-- ❌ Applying scope_b2b — scoring weights are calibrated for retail
```

#### 🏷️ Used In
*Not tracked yet.*

---

## Operations Metrics

---

## ingestion_freshness

> **Type:** Metric | **Domain:** [Operations](../domains/operations.md) | **Unit:** hours
> **Status:** `active` | **Scope:** per asset | **Grain:** per asset per check | **Since:** 2022-01-01

**Definition:** Hours since last successful asset ingestion — compared against asset SLA threshold.

**Real question:** "Dữ liệu đã cũ bao nhiêu giờ so với lần chạy pipeline thành công gần nhất?"
**Time anchor:** `run_ended_at` of last successful/partial run vs now()

**Formula:**
```sql
date_diff('hour', MAX(run_ended_at), now())
WHERE status IN ('success', 'partial')
```

**Column:** `ingestion_health.duckdb` → table `ingestion_runs`

**Intent:** Detects data staleness before it impacts dashboards. Status tokens: healthy (<SLA) | warning (≥75% SLA) | stale (≥SLA).

**Use in SQL:** `date_diff('hour', MAX(run_ended_at), now()) FROM ingestion_runs WHERE status IN ('success','partial')`

#### 🎯 When to Use
Monitor in ops dashboards. Stale assets = dashboards may show outdated data — investigate ingestion pipeline.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `recon_drift` | [metrics.md](#recon_drift) | data accuracy (count match) not recency | checking data completeness |
| `run_success_rate` | [metrics.md](#run_success_rate) | reliability over time not current freshness | pipeline health trend |

#### ❌ Anti-patterns
```sql
-- ❌ Including failed/errored runs in MAX — last error time is not last success time
SELECT date_diff('hour', MAX(run_ended_at), now()) FROM ingestion_runs
-- missing: WHERE status IN ('success','partial')
```

#### 🏷️ Used In
*Not tracked yet.*

---

## recon_drift

> **Type:** Metric | **Domain:** [Operations](../domains/operations.md) | **Unit:** %
> **Status:** `active` | **Scope:** reconciliation assets | **Grain:** per asset per run | **Since:** 2022-01-01

**Definition:** % gap between source count and destination count from reconciliation assets.

**Real question:** "Bao nhiêu % bản ghi bị mất hoặc trùng lặp trong quá trình ingestion?"
**Denominator:** source record count per reconciliation asset run

**Formula:**
```sql
CAST(metadata_json->>'drift_pct' AS DOUBLE)  -- per asset
```

**Column:** `ingestion_runs WHERE asset_key LIKE 'recon/%'`

**Intent:** Detects data loss or duplication during ingestion. Thresholds: 0 = healthy | 0-1% = warning | >1% = alert, investigate immediately.

**Use in SQL:** `CAST(metadata_json->>'drift_pct' AS DOUBLE) FROM ingestion_runs WHERE asset_key LIKE 'recon/%'`

#### 🎯 When to Use
Use to validate ingestion completeness after each run. >1% drift = investigate immediately for potential data loss.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `ingestion_freshness` | [metrics.md](#ingestion_freshness) | recency not accuracy | monitoring data staleness |
| `run_success_rate` | [metrics.md](#run_success_rate) | run reliability trend | pipeline health over time |

#### ❌ Anti-patterns
```sql
-- ❌ Comparing drift across assets with different denominators — normalize per asset
SELECT AVG(drift_pct) FROM ingestion_runs WHERE asset_key LIKE 'recon/%'
-- Each asset has own expected drift range; average is meaningless
```

#### 🏷️ Used In
*Not tracked yet.*

---

## run_success_rate

> **Type:** Metric | **Domain:** [Operations](../domains/operations.md) | **Unit:** %
> **Status:** `active` | **Scope:** per asset, rolling 7 days | **Grain:** per asset per week | **Since:** 2022-01-01

**Definition:** % of runs with status success or partial in past 7 days, per asset.

**Real question:** "Bao nhiêu % lần chạy pipeline thành công trong 7 ngày qua?"
**Denominator:** all ingestion runs for the asset in the rolling 7-day window
**Time anchor:** `run_ended_at` — rolling 7-day window back from now()

**Formula:**
```sql
COUNT(CASE WHEN status IN ('success','partial') THEN 1 END)
  / NULLIF(COUNT(*), 0) * 100
-- rolling 7d window
```

**Column:** `ingestion_health.duckdb` → `ingestion_runs`

**Intent:** Measures ingestion pipeline reliability per asset over time. Low rate = systematic issue requiring investigation.

**Use in SQL:** `COUNT(ok_runs) / NULLIF(COUNT(*), 0) * 100 FROM ingestion_runs WHERE run_ended_at >= now() - INTERVAL '7 days'`

#### 🎯 When to Use
Use for pipeline reliability trending. Pair with `ingestion_freshness` for current state and `recon_drift` for data quality.

#### ⚠️ Conflicts
*None identified.*

#### 🔗 Similar (not synonym)
| Concept | File | Key difference | Use instead when |
|---|---|---|---|
| `ingestion_freshness` | [metrics.md](#ingestion_freshness) | current staleness not reliability rate | current data freshness |
| `recon_drift` | [metrics.md](#recon_drift) | data accuracy not run reliability | data completeness |

#### ❌ Anti-patterns
```sql
-- ❌ Single run status instead of rolling rate — one failure is not a reliability trend
SELECT status FROM ingestion_runs WHERE asset_key = :key ORDER BY run_ended_at DESC LIMIT 1
```

#### 🏷️ Used In
*Not tracked yet.*
