# Schema Scan: Orders / Sales / Products Domain
**Report:** schema-scan-260613-1133-orders-sales-products-domain-report  
**Date:** 2026-06-13  
**Scope:** CRM reverse-ETL readiness — per-customer/order/SKU insights catalog

---

## 1. Canonical Keys

| Concept | Column | Type | Notes |
|---|---|---|---|
| Order PK (Sapo) | `order_id` | INT/BIGINT | unique per order |
| Order code (human) | `order_code` | VARCHAR | e.g. `D12345678`; join key to MISA, Shopee |
| Product PK | `product_key` | VARCHAR(surrogate) | MD5 of `product_id-variant_id` |
| SKU | `sku` | VARCHAR | Sapo SKU; MISA join uses `misa_join_key` (may differ for packs) |
| Variant ID | `variant_id` | INT | Sapo sellable unit |
| Customer PK | `customer_key` | VARCHAR(surrogate) | MD5 of `customer_id` |
| Customer ID | `customer_id` | VARCHAR | Sapo native ID |
| Customer code | `customer_code` | VARCHAR | Sapo display code |
| Date key | `date_key` | INT YYYYMMDD | **ICT timezone** (Asia/Ho_Chi_Minh) — do NOT use UTC |

---

## 2. Entity / Model Catalog

### 2.1 Fact Tables

| Model | Layer | Grain | PK | Key FKs | Core Metrics |
|---|---|---|---|---|---|
| `fact_orders` | mart/fact | 1 row/order | `order_id` | `customer_key`, `channel_key`, `seller_staff_key`, `team_key`, `branch_location_key`, `date_key` | `gross_revenue`, `discount_amount`, `net_revenue` (VAT-excl), `vat_amount`, `total_collected`, `max_discount_rate`, `primary_discount_type`, `time_to_complete_hours`, `first_shipped_at`; scope flags: `scope_sales`, `scope_retail`, `scope_b2b`, `is_active_order` |
| `fact_sales` | mart/fact | 1 row/order-line | `order_line_id` | `product_key`, `customer_key`, `channel_key`, `order_id` | `quantity`, `net_revenue` (VAT-excl via per-order ratio), `discount_amount`, `distributed_discount_amount`, `weight_grams` |
| `fact_order_economics` | mart/fact | 1 row/order | `order_id` | `order_code`, `channel_key` | Full P&L waterfall: `gross_profit`, `gross_margin_pct`, `channel_net_profit`, `channel_net_margin_pct`, `fully_loaded_net_profit`, `cogs_amount`, `cogs_source`, `has_cogs`, `shopee_platform_fees`, `shopee_net_settlement`, `return_amount`, `has_returns`, `promo_goods_cost`, `allocated_overhead` |
| `fact_order_costs` | mart/fact | 1 row/order×cost_type | `order_id`+`cost_type` | `order_code`, `channel_key` | Long-format cost ledger: `cost_type` (cogs, platform_*, discount_*, promo_goods, overhead_*), `cost_category`, `amount`, `cogs_source` |
| `fact_order_returns` | mart/fact | 1 row/return-event | `return_id` | `order_id`, `order_code`, `channel_key`, `date_key` | `refund_amount`, `return_quantity`, `return_status`, `refund_status`, `return_reason`, `returned_at` |
| `fact_payments` | mart/fact | 1 row/payment | (see model) | `order_id` | **WARNING: 1 all-null placeholder row — effectively empty. Do not use for cash flow.** |
| `fact_fulfillments` | mart/fact | 1 row/fulfillment | see model | `order_id` | `cod_amount`, `carrier_id`, `shipped_at`; primary used via `fact_order_economics.cod_amount` |

### 2.2 Dimension Tables

| Model | Grain | PK | Key Columns for CRM |
|---|---|---|---|
| `dim_customers` | 1 row/customer | `customer_key` | Full RFM + behavioral profile (see §4). Incremental. |
| `dim_products` | 1 row/variant | `product_key` | `sku`, `variant_name`, `category`, `brand_name`, `is_packsize`, `misa_join_key`, `misa_qty_multiplier`, `last_sold_price` |
| `dim_sku_alias` | 1 row/pack variant | `sku_alias_key` | `sapo_pack_sku` → `misa_join_key` + `misa_qty_multiplier` |
| `dim_order_status` | dim | `status_key` | status label mapping |
| `dim_promotions` | dim | `promotion_key` | discount code metadata |
| `dim_payment_methods` | dim | `payment_method_key` | `payment_method_type` (cod / prepaid) |
| `dim_channels` | dim | `channel_key` | `channel_name`, `channel_format`, `is_sales_channel` |

### 2.3 Monthly Mart Tables

| Model | Grain | Key Insights |
|---|---|---|
| `mart_sku_economics_monthly` | product_key × snapshot_month | Full per-SKU P&L per month (24-month rolling) |
| `mart_inventory_health` | variant_id × location_id × snapshot_date | Inventory signals per SKU-location |
| `mart_product_health` | product_key (current) | Synthesized product health scores |
| `mart_product_action_queue` | product_key (action required) | Actionable product ops queue |
| `mart_cohort_retention` | cohort_dim × value × window × period_n | Multi-axis cohort retention |
| `mart_customer_status_snapshot_monthly` | customer_key × snapshot_month | Monthly customer status snapshots |
| `mart_customer_action_queue` | customer_key (action required) | Actionable CS/sales queue |
| `mart_retention_waterfall_monthly` | snapshot_month × status × segment | Point-in-time retention (survivorship-bias-free) |

---

## 3. Important Business Rules (Critical for CRM)

| Rule | Detail |
|---|---|
| **VAT-inclusive pricing** | Sapo prices embed VAT. `total_collected` = what customer paid (VAT inside). `net_revenue` = `total_collected − vat_amount` (VAT-exclusive, use for P&L). Do NOT divide by 1.08/1.10 — use pre-computed columns. |
| **ICT date_key** | `date_key` (YYYYMMDD) is Asia/Ho_Chi_Minh timezone. Revenue window queries must use ICT — using UTC causes ~15% drift for 0h–7h orders. |
| **realized_margin_pct vs gross_margin_pct** | Use `realized_margin_pct` for pricing/CRM displays — it uses actual Sapo `net_revenue` as denominator. `gross_margin_pct` uses MISA book revenue and has uncorrected H010 SKU errors (~2× too low for 5 SKUs). |
| **COGS coverage ~65%** | `has_cogs=TRUE` covers ~65% of orders. Always gate margin metrics with `has_cogs=TRUE`. |
| **fact_payments is empty** | 1 placeholder row. AR/cash cannot be measured from this table. |
| **is_active_order filter** | `status NOT IN ('CANCELLED', 'DRAFT')`. Use this flag everywhere for revenue metrics. |
| **scope flags** | `scope_sales` = sales channel; `scope_retail` = sales + RETAIL customer type; `scope_b2b` = sales + WHOLESALE/PARTNER. Never mix for per-order rates. |
| **0đ gift lines** | 43.9% of order lines are gifts/swag with `net_revenue=0`. All per-SKU affinity computations filter these out with `net_revenue > 0`. |

---

## 4. Per-Customer Insights Catalog (CRM Surface)

All sourced from `dim_customers` (with intermediate models listed). RETAIL scope unless noted.

| Insight Name | Column(s) | Grain | Meaning | Source Model | CRM Use |
|---|---|---|---|---|---|
| **Value tier (RFM-M)** | `value_group` | customer | VALUE_VIP (LTV≥50M or orders≥20) / GOLD / SILVER / BRONZE | `dim_customers` | Priority queue, outreach level |
| **Customer status (RFM-R)** | `customer_status` | customer | Active (≤30d) / At Risk (31-90d) / Churned (>90d) since last order | `dim_customers` | Reactivation trigger |
| **Lifecycle stage** | `lifecycle_stage` | customer | LIFECYCLE_NEW / ACTIVE / AT_RISK / CHURNED | `dim_customers` | Onboarding vs retention vs win-back |
| **RFM raw signals** | `recency_days`, `frequency`, `monetary_value` | customer | Days since last order, order count, lifetime spend | `dim_customers` | Scoring, tiering |
| **Lifetime Value (LTV)** | `lifetime_value` | customer | `SUM(total_collected)` on active orders | `dim_customers` | CLV ranking |
| **Lifetime contribution margin** | `lifetime_contribution_margin`, `is_margin_negative` | customer | `SUM(channel_net_profit)` where `has_cogs=TRUE` — profitability by customer | `int_customer_economics` | Avoid negative-margin upsells; gate high-touch outreach |
| **Predicted next purchase date** | `predicted_next_purchase_date` | customer | `last_order_date + avg_days_between_orders`; NULL for 1-time buyers | `dim_customers` | Schedule outreach timing |
| **Next purchase signal** | `next_purchase_signal` | customer | OVERDUE (≥1.5× avg cycle) / DUE_SOON (≥0.8×) / ON_TRACK / NULL | `dim_customers` | Pre-emptive reorder nudge |
| **Purchase cycle** | `avg_days_between_orders` | customer | Average days between consecutive orders (gaps >0 only) | `int_customer_metrics` | Reorder scheduling |
| **Average order spend** | `avg_order_spend` | customer | Avg `total_collected` per active order (customer cash lens) | `dim_customers` | Value_at_stake in action queue |
| **Discount sensitivity** | `discount_sensitivity` | customer | PROMO_DEPENDENT (>70% discounted orders) / PROMO_MIXED / FULL_PRICE | `dim_customers` | Tailor offer type — don't give promos to FULL_PRICE |
| **Cancel rate** | `cancel_rate` | customer | Share of non-draft orders that were cancelled | `dim_customers` | Flag high-cancel customers (HIGH_CANCEL_RISK action) |
| **Channel preference** | `channel_preference` | customer | CHANNEL_SOCIAL / MARKETPLACE / DIRECT / OFFLINE — mode of channels ordered from | `dim_customers` | Route reactivation to preferred channel |
| **Product affinity (brand)** | `product_affinity` | customer | Brand with >60% revenue share: PRODUCT_FINE_JAPAN / FG_CARE / FINE_CARE / MULTI | `dim_customers` | Brand-aligned campaign targeting |
| **Last purchased product/SKU** | `last_purchased_product`, `last_purchased_sku` | customer | SKU from most-recent paid order (highest-qty line) | `dim_customers` | Reorder script: "Lần trước anh/chị mua X…" |
| **Top affinity product/SKU** | `top_affinity_product`, `top_affinity_sku` | customer | Most-frequently reordered SKU (order frequency rank #1) | `dim_customers` | Habitual reorder reminder |
| **Second affinity product** | `second_affinity_product` | customer | Frequency rank #2 SKU; NULL if only 1 distinct paid SKU ever | `dim_customers` | Cross-sell script |
| **Payment behavior** | `payment_behavior` | customer | PAYMENT_COD (>70% COD) / PAYMENT_PREPAID | `dim_customers` | Confirmation call priority for COD customers |
| **Acquisition source** | `acquisition_source` | customer | Channel name of first order (proxy for acquisition channel) | `dim_customers` | Attribution for campaigns |
| **Entry product / category** | (from `int_customer_entry_attributes`) | customer | First-order SKU + category — immutable entry attributes | `int_customer_entry_attributes` | Cohort segmentation |
| **Entry value band** | `entry_value_band` | customer | LOW (<300K) / MID / HIGH / PREMIUM — first order AOV | `int_customer_entry_attributes` | LTV prediction |
| **Is contactable** | `is_contactable` | customer | Phone IS NOT NULL AND != '' | `dim_customers` | CS reachability gate |
| **Geo region** | `geo_region` | customer | GEO_HCMC / HANOI / MEKONG / CENTRAL / OTHER | `dim_customers` | Regional sales routing |
| **Action type** | `action_type` | customer | CALL_NOW / REORDER_NUDGE / REORDER_PREEMPT / WIN_BACK / SECOND_ORDER / HIGH_CANCEL_RISK | `mart_customer_action_queue` | Daily CS/sales worklist |
| **Action rationale** | `action_rationale` | customer | Human-readable Vietnamese text for each action | `mart_customer_action_queue` | Script context |
| **Value at stake** | `value_at_stake` | customer | Estimated VND opportunity per action (e.g. 2× avg_order_spend for CALL_NOW) | `mart_customer_action_queue` | Prioritize by revenue impact |
| **Cohort retention** | `retention_pct`, `revenue_retention`, `repeat_rate` | cohort×period | Multi-axis (first_order_month, entry_product, channel, basket, value_band) | `mart_cohort_retention` | Retention analytics, not per-customer |

---

## 5. Per-Order Insights Catalog

| Insight | Column(s) | Model | Meaning |
|---|---|---|---|
| Revenue waterfall | `gross_revenue`, `discount_amount`, `net_revenue`, `vat_amount`, `total_collected` | `fact_orders` | Full P&L from list price to VAT-excl net |
| Discount type | `primary_discount_type`, `max_discount_rate` | `fact_orders` | Discount classification: voucher_promotional / bundle / campaign / negotiated_deep / etc. |
| Profitability | `gross_profit`, `gross_margin_pct`, `channel_net_profit`, `fully_loaded_net_profit` | `fact_order_economics` | 3-tier P&L per order |
| Realized margin | derived from `fact_order_economics` | `fact_order_economics` | `channel_net_profit / net_revenue` — use for per-order margin display |
| COGS source | `cogs_source` | `fact_order_economics` | sapo_mac / misa / both / none — data quality signal |
| Return flag | `has_returns`, `return_amount`, `return_count` | `fact_order_economics` | Whether order generated returns |
| Time to fulfill | `time_to_complete_hours`, `first_shipped_at` | `fact_orders` | Order cycle time |
| Shopee economics | `shopee_platform_fees`, `shopee_net_settlement` | `fact_order_economics` | Platform fee burden (Shopee only) |
| Overhead | `allocated_overhead`, `is_overhead_estimated` | `fact_order_economics` | Fully-loaded cost (Tier-3 reporting only) |

---

## 6. Per-SKU Insights Catalog (Monthly Grain)

All from `mart_sku_economics_monthly` (rolling 24 months) and `mart_product_health` (current snapshot).

| Insight | Column(s) | Model | Meaning | CRM Use |
|---|---|---|---|---|
| **Volume & velocity** | `units_sold`, `daily_velocity`, `order_count` | `mart_sku_economics_monthly` | Units/orders per month; avg daily units | Understand product demand |
| **Realized margin** | `realized_margin_pct`, `realized_gross_profit` | `mart_sku_economics_monthly` | `(net_revenue − cogs) / net_revenue` on actual Sapo price — **preferred for pricing** | Which SKUs are high-margin to upsell |
| **COGS per unit** | `cogs_per_unit`, `cogs_per_unit_3m_avg` | `mart_sku_economics_monthly` | Unit cost; trailing 3-month average | Price floor guidance |
| **COGS variance** | `cogs_variance_pct` | `mart_sku_economics_monthly` | % drift vs 3M trailing avg — signals supply cost change | Alert merchandising |
| **Return metrics** | `return_rate`, `return_quantity`, `return_adjusted_margin_pct` | `mart_sku_economics_monthly` | Return rate per SKU-month; worst-case margin after returns | Avoid pushing high-return SKUs |
| **Revenue share** | `revenue_share_pct` | `mart_sku_economics_monthly` | SKU's % of total portfolio revenue that month | Portfolio concentration |
| **Top channel** | `top_channel_name`, `top_channel_revenue_pct` | `mart_sku_economics_monthly` | Primary revenue channel per SKU | Match SKU-channel for upsell |
| **Slow mover flag** | `is_slow_mover`, `days_since_last_sale` | `mart_sku_economics_monthly` | No sale in 14+ final days AND not top-200 | Avoid pushing dead inventory |
| **Margin outlier** | `margin_outlier` | `mart_sku_economics_monthly` | Margin < 10% threshold — flag for review | Don't promote low-margin outliers without approval |
| **ABC class** | `abc_class` | `mart_product_health` | A (top 80% revenue) / B (80-95%) / C (tail) | Priority routing for stock alerts |
| **Health class** | `health_class` | `mart_product_health` | STAR (high vel + high margin) / WORKHORSE / QUESTION / DOG / BALANCED | Product mix strategy |
| **Lifecycle stage** | `lifecycle_stage` | `mart_product_health` | NEW / GROWING / MATURE / DECLINING / DORMANT | Campaign timing |
| **Velocity momentum** | `velocity_momentum` | `mart_product_health` | ACCELERATING / STABLE / DECELERATING (30d vs 90d) | Trend-aware upsell |
| **OOS risk** | `oos_risk`, `is_oos`, `is_low_stock`, `days_of_supply` | `mart_product_health` | Stockout risk for high-velocity/A-class SKUs | Don't pitch OOS products |
| **Dead stock** | `is_dead_stock`, `dead_stock_value_at_risk` | `mart_product_health` | No sale in 90 days; capital at risk | Clearance campaigns |
| **Discount dependency** | `discount_dependency` | `mart_product_health` | PROMO_HEAVY / PROMO_LIGHT / FULL_PRICE — SKU-level | Avoid excessive discounting on FULL_PRICE SKUs |
| **Product action** | `action_type`, `action_rationale`, `value_at_stake` | `mart_product_action_queue` | RESTOCK_NOW / CLEAR_DEADSTOCK / REVIEW_MARGIN / PROMOTE / DELIST | Merchandising ops queue |

---

## 7. Reverse-ETL Table Recommendations for CRM

The CRM should pull these marts for the described surfaces:

| CRM Surface | Source Mart | Update Frequency |
|---|---|---|
| Customer profile card | `dim_customers` | Daily |
| Daily CS/sales worklist | `mart_customer_action_queue` | Daily |
| Product "what to pitch" | `mart_product_health` + `mart_product_action_queue` | Daily |
| Order history per customer | `fact_orders` + `fact_order_economics` | Daily |
| SKU-level purchase history | `fact_sales` | Daily |
| Product economics drill-down | `mart_sku_economics_monthly` | Monthly |
| Cohort analytics | `mart_cohort_retention` | Monthly |
| Retention trend | `mart_retention_waterfall_monthly` | Monthly |

---

## 8. Insight Gaps for Re-selling (CRM Not Yet Available)

| Gap | Description | Impact |
|---|---|---|
| **No projected CLV** | Only historical `lifetime_value`. Projected CLV (AOV × frequency × lifespan) is planned but not implemented. | Cannot rank by future value for investment decisions |
| **No cross-sell affinity matrix** | No basket-analysis / co-occurrence model between SKUs across customers. `second_affinity_product` is per-customer history, not population-level "customers who buy X also buy Y". | Cross-sell recommendations are habit-based not population-based |
| **No CAC data** | `fact_marketing_spend` exists but CAC calculation not implemented. Cannot compute LTV/CAC ratio. | Cannot measure acquisition efficiency by channel |
| **fact_payments empty** | Cannot track actual payment collection status or AR aging. | Cannot identify customers with outstanding payments |
| **No real-time inventory-to-customer routing** | OOS risk is in `mart_product_health` but no automated "don't pitch OOS to customer" pipeline in CRM. | Staff may pitch unavailable products |
| **customer_type migration incomplete** | Only ~3 WHOLESALE customers tagged; historical data defaults to RETAIL. TYPE_* re-tag unfinished. | B2B segmentation unreliable for pre-2026-04 data |
| **COGS coverage ~65%** | ~35% of orders lack margin data. Lifetime contribution margin missing for ~35% of customer economics. | `is_margin_negative` unreliable for low-purchase customers |
| **No seasonal purchase pattern** | `avg_days_between_orders` assumes uniform cycle. Seasonal customers (e.g. Tết gifts) will show OVERDUE incorrectly in off-season. | Next purchase signal misfires seasonally |
| **No channel-specific product affinity** | Top/second affinity SKUs are across all channels. Marketplace vs social buying habits are not distinguished. | Outreach via Zalo may pitch wrong SKU |

---

## Open Questions

1. **CRM write-back:** Will the CRM push contact outcomes (called, converted, no-response) back into the warehouse? If so, what is the feedback loop model? This affects action queue completeness.
2. **Affinity model scope:** Is `second_affinity_product` (frequency rank #2) sufficient for cross-sell, or does the CRM require a population-level basket affinity model (customers who buy X also buy Y)?
3. **Real-time vs batch:** Are the `mart_customer_action_queue` snapshots sufficient (daily refresh), or does re-selling require intra-day event triggers (e.g., order placed → immediate upsell window)?
4. **Staff attribution:** `seller_staff_key` and `creator_staff_key` in `fact_orders` — will the CRM route action queue rows to the specific seller who owns the customer, or to a general CS pool?
5. **B2B/WHOLESALE segment:** Given `customer_type` migration is ~95% incomplete (only ~3 WHOLESALE tagged), is B2B CRM in scope for this phase? If yes, all WHOLESALE-specific insights are unreliable for historical data.
