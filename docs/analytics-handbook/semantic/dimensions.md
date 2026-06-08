# Dimensions

Attributes used to slice/group metrics. All are columns in mart tables — never recompute them.

> **Canonical source:** this file
> **Implementation:** `fact_orders`, `fact_order_items`, `dim_channels`, `dim_customers`, `dim_products`, `dim_staff`, `fact_marketing_spend`

---

## Channel Dimensions

### channel_name

> **Type:** Dimension | **Column:** `fact_orders.channel_name` | **Status:** `active`
> **Values:** free text | **Source:** `dim_channels`

**Definition:** The specific sales channel name (e.g., "Shopee VN", "Website", "Cửa hàng Q1").

**Use in SQL:** `GROUP BY channel_name` or `WHERE channel_name = 'Shopee VN'`

#### 🎯 When to Use
Use for channel-level revenue breakdown or when you need the exact named channel. Use `channel_format` for grouped channel type analysis.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| channel_format | Groups channels by type | Comparing Marketplace vs Direct |
| channel_brand | Groups by brand (e.g., "Shopee") | Aggregating across multiple Shopee channels |
| platform | Technical platform label | Filtering by integration platform |

#### ❌ Anti-patterns
*None.*

---

### channel_category

> **Type:** Dimension | **Column:** `fact_orders.channel_category` | **Status:** `active`
> **Values:** `E-commerce`, `Social`, `Offline`, `B2B` | **Source:** `dim_channels`

**Definition:** High-level channel grouping — coarser than `channel_format`.

**Use in SQL:** `GROUP BY channel_category` or `WHERE channel_category = 'Offline'`

#### 🎯 When to Use
Top-level channel cut for executive reporting. Use `channel_format` when you need finer segmentation within a category.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| channel_format | More granular (Marketplace vs Direct) | Segment analysis within a category |

#### ❌ Anti-patterns
*None.*

---

### channel_format

> **Type:** Dimension | **Column:** `fact_orders.channel_format` | **Status:** `active`
> **Values:** `Marketplace`, `Direct`, `Wholesale`, `Retail`, `Social`, `B2B`, `System` | **Source:** `dim_channels`

**Definition:** The channel's commercial format — how orders reach the business.

**Use in SQL:** `GROUP BY channel_format` or `WHERE channel_format = 'Marketplace'`

#### 🎯 When to Use
Use for channel-mix analysis. Do NOT use `channel_format = 'Social'` as a customer segment proxy — Social channels carry both RETAIL and B2B orders.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| customer_type | Segment of the buyer, not the channel | Retail vs B2B segment analysis |
| channel_category | Coarser grouping | Top-level executive cut |

#### ❌ Anti-patterns
```sql
-- WRONG: Social channel ≠ retail segment
WHERE channel_format = 'Social'
-- CORRECT: use customer_type for segment
WHERE customer_type = 'RETAIL'
```

---

### platform

> **Type:** Dimension | **Column:** `fact_orders.platform` | **Status:** `active`
> **Values:** `Shopee`, `TikTok`, `Zalo`, `POS`, free text | **Source:** `dim_channels`

**Definition:** The technical platform or integration (e.g., "Shopee", "TikTok", "POS").

**Use in SQL:** `GROUP BY platform` or `WHERE platform = 'Shopee'`

#### 🎯 When to Use
Use when comparing technical integrations. Use `channel_brand` when grouping multiple instances of the same brand.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| channel_brand | Rolls up multiple platform instances | Aggregating all Shopee channels |

#### ❌ Anti-patterns
*None.*

---

### is_sales_channel

> **Type:** Dimension | **Column:** `fact_orders.is_sales_channel` | **Status:** `active`
> **Values:** `true`, `false` | **Source:** `dim_channels`

**Definition:** Whether the channel is a real sales channel (excludes internal/test channels). Core component of `scope_sales`.

**Use in SQL:** `WHERE is_sales_channel = true`

#### 🎯 When to Use
Apply in every sales KPI query. Omitting this filter includes internal/test orders and inflates revenue.

#### ⚠️ Conflicts
| Source | Column | Definition difference | Note |
|---|---|---|---|
| dim_customers | customer_type = 'CROSSBORDER' | CROSSBORDER orders excluded at channel level | Appears in dim_customers but not in scope_sales/retail/b2b |

#### 🔗 Similar (not synonym)
*None.*

#### ❌ Anti-patterns
```sql
-- WRONG: omitting channel filter inflates revenue
SELECT SUM(net_revenue) FROM fact_orders

-- CORRECT
SELECT SUM(net_revenue) FROM fact_orders WHERE is_sales_channel = true
```

---

### channel_brand

> **Type:** Dimension | **Column:** `fact_orders.channel_brand` | **Status:** `active`
> **Values:** `Shopee`, `TikTok`, `Zalo`, free text | **Source:** `dim_channels`

**Definition:** Brand of the channel (e.g., "Shopee", "TikTok"). Higher-level than `platform` — aggregates multiple instances of the same brand.

**Use in SQL:** `GROUP BY channel_brand` or `WHERE channel_brand = 'Shopee'`

#### 🎯 When to Use
Use when consolidating multiple Shopee/TikTok channel configurations into a single brand row.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| platform | Single integration instance | Distinguishing two Shopee stores |

#### ❌ Anti-patterns
*None.*

---

### market

> **Type:** Dimension | **Column:** `fact_orders.market` | **Status:** `active`
> **Values:** `VN`, `US`, free text | **Source:** `dim_channels`

**Definition:** Geographic market of the channel (e.g., "VN", "US"). Use to filter US export orders out of domestic revenue analysis.

**Use in SQL:** `WHERE market = 'VN'` or `GROUP BY market`

#### 🎯 When to Use
Add `WHERE market = 'VN'` to exclude cross-border/export orders from domestic KPIs.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
*None.*

#### ❌ Anti-patterns
*None.*

---

### source_type

> **Type:** Dimension | **Column:** `fact_orders.source_type` | **Status:** `active`
> **Values:** `ecom`, `social`, `pos`, free text | **Source:** `dim_channels`

**Definition:** The order's source type — more granular than `channel_format`.

**Use in SQL:** `GROUP BY source_type` or `WHERE source_type = 'pos'`

#### 🎯 When to Use
Use when `channel_format` is too coarse and you need exact source-level cuts.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| channel_format | Coarser grouping | Standard reporting |

#### ❌ Anti-patterns
*None.*

---

## Customer Dimensions

### customer_type

> **Type:** Dimension | **Column:** `fact_orders.customer_type` | **Status:** `ambiguous`
> **Values:** `RETAIL`, `WHOLESALE`, `PARTNER`, `STAFF`, `KOL`, `CROSSBORDER` | **Source:** `dim_customers`

**Definition:** Commercial type of the buyer — drives the entire scope architecture (scope_retail, scope_b2b, scope_sales).

**Use in SQL:** `WHERE customer_type = 'RETAIL'` or `GROUP BY customer_type`

#### 🎯 When to Use
Primary filter for any segment analysis. Use `scope_retail` or `scope_b2b` segments (defined in `segments.md`) rather than filtering `customer_type` directly.

#### ⚠️ Conflicts
| Source | Column | Definition difference | Note |
|---|---|---|---|
| dim_channels | is_sales_channel | CROSSBORDER customer_type excluded at channel level | Appears in dim_customers but not in scope_sales/retail/b2b |

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| channel_format | Channel type, not buyer type | Channel-mix analysis |
| value_group | RFM tier within a segment | Identifying high-value customers |

#### ❌ Anti-patterns
```sql
-- WRONG: channel_format is not a segment proxy
WHERE channel_format = 'Wholesale'
-- CORRECT
WHERE customer_type = 'WHOLESALE'
```

#### 📊 Data Quality
Migration incomplete — only ~3 WHOLESALE records are live in production. Historical B2B data pre-2026 is not reliable. Do not use `customer_type = 'WHOLESALE'` for historical trend analysis before 2026.

---

### value_group

> **Type:** Dimension | **Column:** `fact_orders.value_group` | **Status:** `active`
> **Values:** `VALUE_VIP`, `VALUE_GOLD`, `VALUE_SILVER`, `VALUE_BRONZE` | **Source:** `dim_customers`

**Definition:** Customer value tier based on RFM/spending at the time of order.

**Use in SQL:** `WHERE value_group = 'VALUE_VIP'` or `GROUP BY value_group`

#### 🎯 When to Use
Use for retention and upsell analysis. Always combine with `customer_type` to avoid mixing B2B and retail tiers.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| customer_status | Recency-based (Active/Churned) | Analyzing engagement/churn risk |

#### ❌ Anti-patterns
*None.*

---

### customer_status

> **Type:** Dimension | **Column:** `fact_orders.customer_status` | **Status:** `active`
> **Values:** `Active`, `At Risk`, `Churned`, `New/Unknown` | **Source:** `dim_customers`

**Definition:** RFM-based customer status at the time of order placement.

**Use in SQL:** `WHERE customer_status = 'At Risk'` or `GROUP BY customer_status`

#### 🎯 When to Use
Use for churn analysis and lifecycle campaigns. `New/Unknown` = first order or no purchase history.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| value_group | Spending tier, not recency | Revenue contribution analysis |
| next_purchase_signal | Forward-looking purchase prediction | Proactive engagement |

#### ❌ Anti-patterns
*None.*

---

### discount_sensitivity

> **Type:** Dimension | **Column:** `dim_customers.discount_sensitivity` | **Status:** `active`
> **Values:** `PROMO_DEPENDENT`, `PROMO_MIXED`, `FULL_PRICE`, `NULL` | **Source:** `dim_customers`

**Definition:** Customer's dependence on discounts — computed from `dim_customers.discount_order_rate`.

**Use in SQL:** `WHERE discount_sensitivity = 'PROMO_DEPENDENT'` or `GROUP BY discount_sensitivity`

#### 🎯 When to Use
Use for email campaign segmentation (promo vs full-price offers). Join `fact_orders` → `dim_customers` on `customer_key`.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| primary_discount_type | Per-order discount type | Analyzing discount structure on individual orders |
| max_discount_rate | Depth of discount on a single order | Identifying deep-discount orders |

#### ❌ Anti-patterns
```sql
-- WRONG: NULL ≠ never discounted
WHERE discount_sensitivity IS NULL  -- this means no qualifying orders, not zero-discount
-- CORRECT: zero-discount customers
WHERE discount_sensitivity = 'FULL_PRICE'
```

---

### next_purchase_signal

> **Type:** Dimension | **Column:** `dim_customers.next_purchase_signal` | **Status:** `active`
> **Values:** `OVERDUE`, `DUE_SOON`, `ON_TRACK`, `NULL` | **Source:** `dim_customers`

**Definition:** Forward-looking lifecycle signal based on recency vs average purchase cycle. OVERDUE ≥ 1.5× avg cycle; DUE_SOON ≥ 0.8× avg; ON_TRACK < 0.8×.

**Use in SQL:** `WHERE next_purchase_signal = 'OVERDUE'` or `GROUP BY next_purchase_signal`

#### 🎯 When to Use
Use to trigger proactive re-engagement (CRM, push). NULL = one-time buyer with no cycle to measure — use `lifecycle_stage` instead.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| customer_status | Backward-looking (Active/Churned) | Reporting current state |
| predicted_next_purchase_date | Exact date estimate | Scheduling campaign timing |

#### ❌ Anti-patterns
```sql
-- WRONG: NULL signal does not mean ON_TRACK
WHERE next_purchase_signal IS NULL OR next_purchase_signal = 'ON_TRACK'
-- CORRECT: exclude 1-time buyers explicitly
WHERE next_purchase_signal = 'ON_TRACK'
  AND avg_days_between_orders IS NOT NULL
```

---

### predicted_next_purchase_date

> **Type:** Dimension | **Column:** `dim_customers.predicted_next_purchase_date` | **Status:** `active`
> **Values:** DATE (ICT) or `NULL` | **Source:** `dim_customers`

**Definition:** Estimated next purchase date = `last_order_date + avg_days_between_orders`. NULL for one-time buyers.

**Use in SQL:** `WHERE predicted_next_purchase_date BETWEEN :start AND :end`

#### 🎯 When to Use
Use to schedule CRM outreach windows. Treat as a probabilistic estimate, not a guarantee.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| next_purchase_signal | Categorical urgency label | Filtering by urgency tier |

#### ❌ Anti-patterns
*None.*

---

### avg_days_between_orders

> **Type:** Dimension | **Column:** `dim_customers.avg_days_between_orders` | **Status:** `active`
> **Values:** INTEGER (days) or `NULL` | **Source:** `dim_customers`

**Definition:** Average days between purchases. Excludes same-day repeats (0-day gaps). NULL for single-order customers.

**Use in SQL:** `WHERE avg_days_between_orders < 30` or `GROUP BY avg_days_between_orders`

#### 🎯 When to Use
Use for repurchase-cycle segmentation. NULL means the customer has only one order — do not treat as 0.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
*None.*

#### ❌ Anti-patterns
*None.*

---

### cancel_rate

> **Type:** Dimension | **Column:** `dim_customers.cancel_rate` | **Status:** `active`
> **Values:** DOUBLE (0.0–1.0) | **Source:** `dim_customers`

**Definition:** Fraction of the customer's orders that were cancelled. DRAFT orders excluded from denominator.

**Use in SQL:** `WHERE cancel_rate > 0.3` or `GROUP BY CASE WHEN cancel_rate > 0.3 THEN 'high' END`

#### 🎯 When to Use
Use to flag high-risk customers (payment issues, order regret) or exclude them from fulfillment priority.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| is_cancelled | Per-order flag | Filtering individual cancelled orders |

#### ❌ Anti-patterns
*None.*

---

### avg_order_spend

> **Type:** Dimension | **Column:** `dim_customers.avg_order_spend` | **Status:** `active`
> **Values:** BIGINT (VND) or `NULL` | **Source:** `int_customer_metrics.sql` → `dim_customers`

**Definition:** Average amount a customer actually pays per order, computed over their entire history. **Customer/CRM lens** — uses `total_collected` (VAT-inclusive), the real cash the customer hands over. NULL for customers with no completed orders.

**Formula (computed in int_customer_metrics.sql):**
```sql
ROUND(SUM(o.total_collected) / NULLIF(COUNT(DISTINCT o.order_id), 0))::BIGINT
-- CANCELLED/DRAFT excluded — those have total_collected=0
```

**Intent:** Customer scoring and CRM action prioritization. Drives `value_at_stake` in `mart_customer_action_queue` (CALL_NOW × 2, REORDER_NUDGE × 1, WIN_BACK × 3, SECOND_ORDER × 1). Uses `total_collected` — not `net_revenue` — because value_at_stake estimates actual cash flow, not accounting revenue.

**Use in SQL:** `dim_customers.avg_order_spend` (pre-computed — join `fact_orders → dim_customers` on `customer_key`)

#### 🎯 When to Use
Customer scoring, segmentation, and CRM action prioritization. For period-level trend analysis on a dashboard, use [`aov`](metrics.md#aov) instead.

#### ⚠️ Conflicts
| Source | Lens | Difference |
|---|---|---|
| `aov` | Business/P&L | `net_revenue` (VAT-excl), period-scoped — same order, ~8-10% lower number |

#### 🔗 Similar (not synonym)
| Concept | Key difference | Use instead when |
|---|---|---|
| `aov` | [metrics.md](metrics.md#aov) — business lens, net_revenue, period filter | dashboard trends, P&L analysis |
| `lifetime_value` | cumulative total, not per-order average | ranking by total revenue contribution |

#### ❌ Anti-patterns
```sql
-- ❌ Using avg_order_spend as a period AOV on a dashboard
--    It's a lifetime customer attribute — not date-range filtered, won't reflect recent changes

-- ❌ Using aov (net_revenue) for value_at_stake estimation
--    Underestimates actual cash by ~8-10% VAT — use avg_order_spend instead
```

---

## Time Dimensions

### date_key

> **Type:** Dimension | **Column:** `fact_orders.date_key` | **Status:** `active`
> **Values:** DATE (ICT, Asia/Ho_Chi_Minh) | **Source:** `fact_orders`

**Definition:** Order date in ICT (Asia/Ho_Chi_Minh). The primary date field for KPI windows and day-level grouping.

**Use in SQL:** `WHERE date_key = '2026-06-06'` or `GROUP BY date_key`

#### 🎯 When to Use
Use `date_key` for all day-level date filters. Use `ordered_at` only when exact timestamps are needed. Never apply manual UTC↔ICT offset — `date_key` is already ICT.

#### ⚠️ Conflicts
| Source | Column | Definition difference | Note |
|---|---|---|---|
| fact_orders | ordered_at | TIMESTAMPTZ stored UTC, displayed ICT by Metabase | Metabase auto-converts via session TZ — do not add +7 manually |

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| ordered_at | Exact TIMESTAMPTZ, stored UTC | Sub-day analysis, event sequencing |

#### ❌ Anti-patterns
```sql
-- WRONG: manual UTC→ICT conversion shifts date boundaries
WHERE ordered_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Ho_Chi_Minh' = '2026-06-06'

-- CORRECT: date_key is pre-computed in ICT
WHERE date_key = '2026-06-06'
```

#### 📊 Data Quality
Critical: KPI windows using UTC instead of ICT get ~15% drift on orders placed between 23:00–07:00 ICT. Always use `date_key` or `_yesterday_window_ict()` for business date filters.

---

### ordered_at

> **Type:** Dimension | **Column:** `fact_orders.ordered_at` | **Status:** `active`
> **Values:** TIMESTAMPTZ (stored UTC) | **Source:** `fact_orders`

**Definition:** Exact order timestamp stored as UTC. Metabase displays ICT automatically via session timezone (Asia/Ho_Chi_Minh).

**Use in SQL:** `WHERE ordered_at >= '2026-06-01 00:00:00+07'` or `ORDER BY ordered_at`

#### 🎯 When to Use
Use for sub-day analysis (hourly trends, event sequencing, SLA calculations). For day-level grouping, use `date_key` instead.

#### ⚠️ Conflicts
| Source | Column | Definition difference | Note |
|---|---|---|---|
| fact_orders | date_key | DATE in ICT (pre-computed) | Do not derive date_key from ordered_at — use the pre-computed column |

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| date_key | DATE in ICT, no time component | Day-level grouping and KPI windows |

#### ❌ Anti-patterns
```sql
-- WRONG: casting TIMESTAMPTZ to DATE uses session default, may be wrong in DuckDB
WHERE ordered_at::DATE = '2026-06-06'

-- CORRECT
WHERE date_key = '2026-06-06'
```

---

### order_hour

> **Type:** Dimension | **Column:** `fact_orders.order_hour` | **Status:** `active`
> **Values:** INTEGER (0–23, ICT) | **Source:** `fact_orders`

**Definition:** Hour of day the order was placed (ICT), pre-computed from `ordered_at`.

**Use in SQL:** `GROUP BY order_hour` or `WHERE order_hour BETWEEN 9 AND 17`

#### 🎯 When to Use
Use for intraday traffic analysis and staffing models. Prefer over extracting hour from `ordered_at` directly.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| day_of_week | Day of week (1–7) | Weekly pattern analysis |

#### ❌ Anti-patterns
*None.*

---

### day_of_week

> **Type:** Dimension | **Column:** `fact_orders.day_of_week` | **Status:** `active`
> **Values:** INTEGER (1=Monday … 7=Sunday, ICT) | **Source:** `fact_orders`

**Definition:** Day of week (ICT), pre-computed from `ordered_at`.

**Use in SQL:** `GROUP BY day_of_week` or `WHERE day_of_week IN (6, 7)`

#### 🎯 When to Use
Use for weekly seasonality analysis. Prefer over extracting from `ordered_at`.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| order_hour | Hour of day | Intraday analysis |

#### ❌ Anti-patterns
*None.*

---

## Location Dimensions

### province

> **Type:** Dimension | **Column:** `fact_orders.province` | **Status:** `active`
> **Values:** free text (Vietnamese province names) | **Source:** `fact_orders`

**Definition:** Delivery province of the order.

**Use in SQL:** `GROUP BY province` or `WHERE province = 'Hồ Chí Minh'`

#### 🎯 When to Use
Use for regional demand analysis and logistics cost modeling.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| district | Sub-province granularity | Last-mile routing analysis |

#### ❌ Anti-patterns
*None.*

---

### district

> **Type:** Dimension | **Column:** `fact_orders.district` | **Status:** `active`
> **Values:** free text | **Source:** `fact_orders`

**Definition:** Delivery district — sub-province granularity.

**Use in SQL:** `GROUP BY district`

#### 🎯 When to Use
Use when province-level is too coarse (e.g., last-mile delivery zone analysis).

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| province | Higher-level geography | Regional reporting |

#### ❌ Anti-patterns
*None.*

---

### branch_location_name

> **Type:** Dimension | **Column:** `fact_orders.branch_location_name` | **Status:** `active`
> **Values:** free text | **Source:** `fact_orders`

**Definition:** The branch or warehouse that processed the order.

**Use in SQL:** `GROUP BY branch_location_name` or `WHERE branch_location_name = 'HCM Kho chính'`

#### 🎯 When to Use
Use for branch-level performance reporting and inventory attribution.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
*None.*

#### ❌ Anti-patterns
*None.*

---

## Status Dimensions

### status

> **Type:** Dimension | **Column:** `fact_orders.status` | **Status:** `active`
> **Values:** `OPEN`, `COMPLETED`, `CANCELLED`, `ARCHIVED`, `DRAFT` | **Source:** `fact_orders`

**Definition:** Order lifecycle status mapped from Sapo. Only `CANCELLED` exists for cancelled orders — Sapo has no 'Voided' order status (voided is a payment-level concept that always co-occurs with cancellation).

**Use in SQL:** `WHERE status != 'CANCELLED'` or `GROUP BY status`

#### 🎯 When to Use
Use only when you need the raw status value. Prefer `scope_sales` / `scope_retail` / `scope_b2b` pre-computed flags for KPI queries — they already apply the correct cancellation filter.

#### ⚠️ Conflicts
| Source | Column | Definition difference | Note |
|---|---|---|---|
| fact_orders | is_completed | `status = 'COMPLETED'` is NOT the same as `is_completed` | is_completed requires BOTH fulfillment + payment; status tracks lifecycle only |

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| is_completed | Boolean: fulfillment AND payment both done | Identifying financially complete orders |
| is_cancelled | Boolean: status = 'CANCELLED' | Filtering out cancelled orders |
| payment_status | Payment leg only | Collection/reconciliation analysis |
| fulfillment_status | Fulfillment leg only | Logistics/delivery analysis |

#### ❌ Anti-patterns
```sql
-- WRONG: 'Voided' does not exist in Sapo order status
WHERE status NOT IN ('CANCELLED', 'Voided')

-- CORRECT
WHERE status != 'CANCELLED'

-- WRONG: status = 'COMPLETED' ≠ financially complete
WHERE status = 'COMPLETED'

-- CORRECT: financially complete orders
WHERE is_completed = true
```

---

### payment_status

> **Type:** Dimension | **Column:** `fact_orders.payment_status` | **Status:** `active`
> **Values:** `PAID`, `UNPAID`, `PARTIALLY_PAID`, `REFUNDED`, `PENDING` | **Source:** `fact_orders`

**Definition:** Payment leg status of the order, mapped from Sapo's `payment_status` field. `UNPAID` is the default when no payment has been collected (including COD orders in transit).

**Source mapping (Sapo → std_orders):**
| Sapo value | Mapped value |
|---|---|
| `paid` | `PAID` |
| `partial` | `PARTIALLY_PAID` |
| `refunded` | `REFUNDED` |
| `pending` | `PENDING` |
| *(anything else)* | `UNPAID` |

**Use in SQL:** `WHERE payment_status = 'PAID'` or `GROUP BY payment_status`

#### 🎯 When to Use
Use for cash collection analysis and reconciliation. For financial completeness, use `is_completed` which requires both payment + fulfillment.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| is_completed | Requires fulfilled + paid | Identifying revenue-recognized orders |
| fulfillment_status | Logistics leg, not payment | Shipping/delivery analysis |

#### ❌ Anti-patterns
```sql
-- WRONG: lowercase Sapo raw values — always use the mapped uppercase constants
WHERE payment_status = 'paid'

-- CORRECT
WHERE payment_status = 'PAID'
```

---

### fulfillment_status

> **Type:** Dimension | **Column:** `fact_orders.fulfillment_status` | **Status:** `active`
> **Values:** `fulfilled`, `unfulfilled`, `partial`, `RETURNED` | **Source:** `fact_orders`

**Definition:** Consolidated fulfillment status of the order. 'RETURNED' = delivered but customer returned it.

**Use in SQL:** `WHERE fulfillment_status = 'fulfilled'` or `GROUP BY fulfillment_status`

#### 🎯 When to Use
Use for logistics/delivery analysis. For return analysis, use `fact_order_returns` which has full return event detail.

#### ⚠️ Conflicts
| Source | Column | Definition difference | Note |
|---|---|---|---|
| fact_order_returns | (return events) | `fulfillment_status = 'RETURNED'` is a flag on the original order; `fact_order_returns` tracks the return event with refund_amount, return_reason, return_date | Flag undercounts partial returns |

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| is_fulfilled | Boolean shorthand | Simple filter for fulfilled orders |
| is_completed | Requires paid + fulfilled | Revenue recognition |

#### ❌ Anti-patterns
```sql
-- WRONG: underestimates returns (misses partial returns)
WHERE fulfillment_status = 'RETURNED'
-- CORRECT for return analysis: use fact_order_returns
SELECT * FROM fact_order_returns
```

---

### is_completed

> **Type:** Dimension | **Column:** `fact_orders.is_completed` | **Status:** `active`
> **Values:** `true`, `false` | **Source:** `fact_orders`

**Definition:** True ONLY when BOTH `fulfillment_status = 'fulfilled'` AND `payment_status = 'paid'`. Represents a financially complete order.

**Use in SQL:** `WHERE is_completed = true`

#### 🎯 When to Use
Use as the default filter for revenue and COGS analysis. This is the correct definition of a "completed" order.

#### ⚠️ Conflicts
| Source | Column | Definition difference | Note |
|---|---|---|---|
| fact_orders | status | `status = 'COMPLETED'` is NOT equivalent | status tracks Sapo lifecycle; is_completed tracks financial completion |

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| status | Raw Sapo lifecycle status | You need the exact Sapo status string |

#### ❌ Anti-patterns
```sql
-- WRONG: status = 'COMPLETED' misses orders that are fulfilled + paid but lifecycle is still 'PROCESSING'
WHERE status = 'COMPLETED'

-- CORRECT
WHERE is_completed = true
```

---

### is_cancelled

> **Type:** Dimension | **Column:** `fact_orders.is_cancelled` | **Status:** `active`
> **Values:** `true`, `false` | **Source:** `fact_orders`

**Definition:** True when `status = 'CANCELLED'`. Sapo has no 'Voided' order status — `CANCELLED` is the only cancellation value.

**Use in SQL:** `WHERE is_cancelled = false` or `WHERE NOT is_cancelled`

#### 🎯 When to Use
Cleaner alternative to `status != 'CANCELLED'` — prefer this for readability and to future-proof against any status enum changes.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| status | Raw status string | You need the exact Sapo status value |

#### ❌ Anti-patterns
*None.*

---

### is_fulfilled

> **Type:** Dimension | **Column:** `fact_orders.is_fulfilled` | **Status:** `active`
> **Values:** `true`, `false` | **Source:** `fact_orders`

**Definition:** True when `fulfillment_status = 'fulfilled'`.

**Use in SQL:** `WHERE is_fulfilled = true`

#### 🎯 When to Use
Shorthand for fully fulfilled orders. Use `fulfillment_status` directly when you need partial or returned status.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| fulfillment_status | Includes partial/returned states | Detailed logistics breakdown |

#### ❌ Anti-patterns
*None.*

---

### is_open

> **Type:** Dimension | **Column:** `fact_orders.is_open` | **Status:** `active`
> **Values:** `true`, `false` | **Source:** `fact_orders`

**Definition:** True when order is in an active, unresolved state (not completed or cancelled).

**Use in SQL:** `WHERE is_open = true`

#### 🎯 When to Use
Use for WIP/in-progress order monitoring and ops dashboards.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
*None.*

#### ❌ Anti-patterns
*None.*

---

## Staff Dimensions

### seller_name

> **Type:** Dimension | **Column:** `fact_orders.seller_name` | **Status:** `active`
> **Values:** free text | **Source:** `dim_staff` via `seller_staff_key`

**Definition:** Display name of the staff member who closed/was assigned the order. Primary attribution for commission and team KPIs.

**Use in SQL:** `GROUP BY seller_name` or `WHERE seller_name = 'Nguyen Van A'`

#### 🎯 When to Use
Use for team performance and commission reports. For joins and aggregations, use `seller_staff_key` (surrogate key) instead of the name string.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| creator_name | Person who created the order in Sapo | Audit/operational attribution |

#### ❌ Anti-patterns
```sql
-- WRONG: joining on name string is fragile (name changes)
JOIN dim_staff ON dim_staff.name = fact_orders.seller_name
-- CORRECT
JOIN dim_staff ON dim_staff.staff_key = fact_orders.seller_staff_key
```

---

### creator_name

> **Type:** Dimension | **Column:** `fact_orders.creator_name` | **Status:** `active`
> **Values:** free text | **Source:** `dim_staff` via `creator_staff_key`

**Definition:** Display name of the staff member who created the order in Sapo. Operational attribution — differs from `seller_name` for CS-created orders.

**Use in SQL:** `GROUP BY creator_name`

#### 🎯 When to Use
Use for audit trails and CS ticket attribution. Usually the same as `seller_name`; differs when CS creates orders on behalf of customers.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| seller_name | Commission/team attribution | Sales performance analysis |

#### ❌ Anti-patterns
*None.*

---

### seller_staff_key

> **Type:** Dimension | **Column:** `fact_orders.seller_staff_key` | **Status:** `active`
> **Values:** surrogate key | **Source:** `dim_staff`

**Definition:** Surrogate key for the staff member who closed/was assigned the order. Use for all joins and aggregations.

**Use in SQL:** `GROUP BY seller_staff_key` or `JOIN dim_staff ON staff_key = seller_staff_key`

#### 🎯 When to Use
Primary key for commission/team KPI attribution. Use `seller_staff_key` → `team_members` (SCD2) → `dim_teams` for team-level rollup.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| creator_staff_key | Created the order, not necessarily assigned | Audit/CS operational tracking |

#### ❌ Anti-patterns
*None.*

---

### creator_staff_key

> **Type:** Dimension | **Column:** `fact_orders.creator_staff_key` | **Status:** `active`
> **Values:** surrogate key | **Source:** `dim_staff`

**Definition:** Surrogate key for the staff member who created the order in Sapo. Operational fallback — usually equals `seller_staff_key`.

**Use in SQL:** `GROUP BY creator_staff_key` or `JOIN dim_staff ON staff_key = creator_staff_key`

#### 🎯 When to Use
Use for operational audit (who entered the order). For commission attribution, always use `seller_staff_key`.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| seller_staff_key | Assigned/commission holder | Sales KPIs, team performance |

#### ❌ Anti-patterns
*None.*

---

### team_key

> **Type:** Dimension | **Column:** `fact_orders.team_key` | **Status:** `active`
> **Values:** surrogate key | **Source:** `dim_teams` via SCD2 `team_members`

**Definition:** Team attribution derived via `seller_staff_key` → `team_members` (SCD2) → `dim_teams`. Used for team-level KPI rollup.

**Use in SQL:** `GROUP BY team_key` or `JOIN dim_teams ON dim_teams.team_key = fact_orders.team_key`

#### 🎯 When to Use
Use when reporting at team level. The SCD2 `team_members` table ensures historical team assignments are respected.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| seller_staff_key | Individual-level | Per-rep analysis |

#### ❌ Anti-patterns
*None.*

---

## Product Dimensions

### product_name

> **Type:** Dimension | **Column:** `fact_order_items.product_name` | **Status:** `active`
> **Values:** free text | **Source:** `dim_products`

**Definition:** Product name. Grain: one row per product in `dim_products`.

**Use in SQL:** `GROUP BY product_name` or `WHERE product_name ILIKE '%collagen%'`

#### 🎯 When to Use
Use for product-level revenue and margin analysis. For variant-level detail, use `variant_name` or `sku`.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| variant_name | SKU/variant granularity | Analyzing size or flavor breakdown |
| brand_name | Brand level | Brand portfolio analysis |

#### ❌ Anti-patterns
*None.*

---

### variant_name

> **Type:** Dimension | **Column:** `fact_order_items.variant_name` | **Status:** `active`
> **Values:** free text | **Source:** `dim_products`

**Definition:** Specific variant name (size, flavor, etc.). Finer grain than `product_name`.

**Use in SQL:** `GROUP BY variant_name`

#### 🎯 When to Use
Use when product-level aggregation is too coarse — e.g., comparing "500g" vs "1kg" SKUs of the same product.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| sku | Natural key (stable code) | Inventory joins |
| product_name | Product-level rollup | Simpler product analysis |

#### ❌ Anti-patterns
*None.*

---

### sku

> **Type:** Dimension | **Column:** `fact_order_items.sku` | **Status:** `active`
> **Values:** free text (natural key) | **Source:** `dim_products`

**Definition:** SKU code of the variant — the natural key for inventory. Joins to `fact_inventory_snapshot` and `mart_sku_economics_monthly`.

**Use in SQL:** `GROUP BY sku` or `JOIN fact_inventory_snapshot ON fact_inventory_snapshot.sku = fact_order_items.sku`

#### 🎯 When to Use
Use whenever inventory or economics data is needed. SKU is the stable natural key — prefer over `variant_name` for joins.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| variant_name | Display name, not stable key | Human-readable reporting |

#### ❌ Anti-patterns
*None.*

---

### brand_name

> **Type:** Dimension | **Column:** `fact_order_items.brand_name` | **Status:** `active`
> **Values:** free text | **Source:** `dim_products`

**Definition:** Product brand. Used for revenue and margin analysis by brand.

**Use in SQL:** `GROUP BY brand_name` or `WHERE brand_name = 'BrandX'`

#### 🎯 When to Use
Use for brand portfolio analysis. Note: one order can have items from multiple brands.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| product_type | Category grouping | Category-level analysis |

#### ❌ Anti-patterns
*None.*

---

### product_type

> **Type:** Dimension | **Column:** `fact_order_items.product_type` | **Status:** `active`
> **Values:** free text (category) | **Source:** `dim_products`

**Definition:** Product category/type. Used for category-level grouping in product performance.

**Use in SQL:** `GROUP BY product_type` or `WHERE product_type = 'Supplement'`

#### 🎯 When to Use
Use for category-level revenue and margin analysis. More stable than `product_name` for trend comparisons.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| brand_name | Brand owner | Brand portfolio breakdown |

#### ❌ Anti-patterns
*None.*

---

## Fulfillment Dimensions

### first_shipped_at

> **Type:** Dimension | **Column:** `fact_orders.first_shipped_at` | **Status:** `active`
> **Values:** TIMESTAMPTZ or `NULL` | **Source:** `fact_orders`

**Definition:** Timestamp of first shipment dispatch. NULL if not yet shipped. Used to compute `avg_hours_to_first_ship` and `same_day_ship_rate`.

**Use in SQL:** `WHERE first_shipped_at IS NOT NULL` or `SELECT first_shipped_at - ordered_at AS fulfillment_lag`

#### 🎯 When to Use
Use for SLA and fulfillment speed analysis. NULL means the order has not shipped yet — exclude from cycle time calculations.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| first_ship_bucket | Pre-bucketed time band | Histogram/distribution analysis |

#### ❌ Anti-patterns
```sql
-- WRONG: including NULL (unshipped) in avg SLA
AVG(first_shipped_at - ordered_at)
-- CORRECT
AVG(first_shipped_at - ordered_at) FILTER (WHERE first_shipped_at IS NOT NULL)
```

---

### first_ship_bucket

> **Type:** Dimension | **Column:** `fact_orders.first_ship_bucket` | **Status:** `active`
> **Values:** `0-4h`, `4-8h`, `8-24h`, `>24h` (pre-computed) | **Source:** `fact_orders`

**Definition:** Pre-computed time bucket for first shipment speed.

**Use in SQL:** `GROUP BY first_ship_bucket` or `WHERE first_ship_bucket = '0-4h'`

#### 🎯 When to Use
Use for distribution histograms of fulfillment speed. Prefer over computing `CASE WHEN` on `first_shipped_at` each time.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| complete_time_bucket | Full order lifecycle | End-to-end cycle time analysis |

#### ❌ Anti-patterns
*None.*

---

### complete_time_bucket

> **Type:** Dimension | **Column:** `fact_orders.complete_time_bucket` | **Status:** `active`
> **Values:** pre-computed bucket string | **Source:** `fact_orders`

**Definition:** Pre-computed time bucket for `time_to_complete_hours` — full order lifecycle from placement to completion.

**Use in SQL:** `GROUP BY complete_time_bucket`

#### 🎯 When to Use
Use for order lifecycle distribution analysis. Captures end-to-end cycle time, not just first ship.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| first_ship_bucket | First ship only | Fulfillment speed (not collection) |

#### ❌ Anti-patterns
*None.*

---

### order_size_band

> **Type:** Dimension | **Column:** `fact_orders.order_size_band` | **Status:** `active`
> **Values:** `<100K`, `100K-500K`, `500K-2M`, `>2M` (pre-computed) | **Source:** `fact_orders`

**Definition:** Pre-computed order value band. Used for order value distribution analysis.

**Use in SQL:** `GROUP BY order_size_band`

#### 🎯 When to Use
Use for distribution analysis of order values. Prefer over computing `CASE WHEN` on order value.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
*None.*

#### ❌ Anti-patterns
*None.*

---

## Discount & Pricing Dimensions

### primary_discount_type

> **Type:** Dimension | **Column:** `fact_orders.primary_discount_type` | **Status:** `active`
> **Values:** `voucher_promotional`, `bundle`, `sampling_gift`, `wholesale_explicit`, `overseas`, `campaign`, `employee_internal`, `negotiated_micro`, `negotiated_standard`, `negotiated_deep` | **Source:** `fact_orders`

**Definition:** The dominant discount type by amount when an order has multiple discounts. Classified from `std_order_discount_items.reason` text.

**Use in SQL:** `GROUP BY primary_discount_type` or `WHERE primary_discount_type = 'voucher_promotional'`

#### 🎯 When to Use
Use for discount structure analysis without re-parsing raw reason text. Threshold for negotiated tiers: micro < 20%, standard 20–40%, deep > 40%.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| max_discount_rate | Depth of deepest discount on the order | Identifying deep-discount outliers |
| discount_sensitivity | Customer-level pattern over all orders | Campaign segmentation |

#### ❌ Anti-patterns
```sql
-- WRONG: parsing raw text instead of using classified field
WHERE reason ILIKE '%voucher%'
-- CORRECT
WHERE primary_discount_type = 'voucher_promotional'
```

---

### max_discount_rate

> **Type:** Dimension | **Column:** `fact_orders.max_discount_rate` | **Status:** `active`
> **Values:** NUMERIC (0.0–1.0, percentage) | **Source:** `fact_orders`

**Definition:** Highest discount rate among all discount items on the order. Used to identify deep-discount orders.

**Use in SQL:** `WHERE max_discount_rate > 0.4` or `GROUP BY CASE WHEN max_discount_rate > 0.4 THEN 'deep' ELSE 'standard' END`

#### 🎯 When to Use
Use to flag orders with aggressive discounting. Combine with `primary_discount_type` to understand both depth and type.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| primary_discount_type | Type classification | Discount category analysis |

#### ❌ Anti-patterns
*None.*

---

## Marketing Dimensions

### campaign_id

> **Type:** Dimension | **Column:** `fact_marketing_spend.campaign_id` | **Status:** `active`
> **Values:** free text | **Source:** `fact_marketing_spend`

**Definition:** Marketing campaign identifier. Join to performance metrics for ROI analysis.

**Use in SQL:** `JOIN fact_marketing_spend ON campaign_id = ...` or `GROUP BY campaign_id`

#### 🎯 When to Use
Use when linking spend data to order/revenue outcomes. The grain of `fact_marketing_spend` is campaign + date.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| spend_code | Cost classification code | Cost structure breakdown |

#### ❌ Anti-patterns
*None.*

---

### spend_code

> **Type:** Dimension | **Column:** `fact_marketing_spend.spend_code` | **Status:** `active`
> **Values:** free text | **Source:** `fact_marketing_spend`

**Definition:** Classification code for marketing spend line items. Used for cost structure analysis.

**Use in SQL:** `GROUP BY spend_code`

#### 🎯 When to Use
Use to break down marketing spend by cost category. More granular than `campaign_id`.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| marketing_spend_bucket | Pre-bucketed spend level | Distribution analysis |

#### ❌ Anti-patterns
*None.*

---

### marketing_spend_bucket

> **Type:** Dimension | **Column:** `fact_marketing_spend.marketing_spend_bucket` | **Status:** `active`
> **Values:** pre-computed bucket string | **Source:** `fact_marketing_spend`

**Definition:** Pre-computed bucket grouping marketing spend levels. Used for segment analysis of spend distribution.

**Use in SQL:** `GROUP BY marketing_spend_bucket`

#### 🎯 When to Use
Use for spend distribution analysis without computing `CASE WHEN` on raw spend amounts.

#### ⚠️ Conflicts
*None.*

#### 🔗 Similar (not synonym)
| Dimension | Key difference | Use instead when |
|---|---|---|
| spend_code | Categorical cost type | Cost structure breakdown |

#### ❌ Anti-patterns
*None.*
