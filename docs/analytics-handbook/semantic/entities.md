# Entities

Core business entities — each entity maps to the grain of a mart table.

> **Canonical source:** this file
> **Implementation:** `transformation/models/marts/`

---

## Order

> **Type:** Entity | **Mart:** `fact_orders` | **Grain:** 1 row = 1 order | **Status:** `active`
> **Key:** `order_id` (surrogate: `order_key`) | **Source:** Sapo | **Since:** 2021

**Definition:** An order placed through any sales channel via Sapo — covers retail, B2B, POS, and marketplace (Shopee, TikTok).

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `order_id` | bigint | Sapo internal ID |
| `order_code` | varchar | Natural key (e.g. `260316A6VJXGMT`) |
| `order_key` | varchar | MD5 surrogate key |
| `ordered_at` | timestamptz | Order creation time (UTC-stored, ICT display) |
| `date_key` | date | ICT calendar date (use for daily aggregations) |
| `channel_key` | varchar | FK → dim_channels |
| `customer_key` | varchar | FK → dim_customers |
| `seller_staff_key` | varchar | Staff who fulfilled/closed the order |
| `scope_sales` | boolean | In-scope for sales reporting |
| `is_completed` | boolean | Pre-computed status flag |

**Intent:** Count orders, aggregate GMV, filter by channel/date/staff, compute conversion and fulfillment KPIs.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Order Line Item (`fact_order_items`) | 1:many | `order_id` |
| Order Economics (`fact_order_economics`) | 1:1 | `order_code` |
| Order Returns (`fact_order_returns`) | 1:many | `order_code` |
| Order Costs (`fact_order_costs`) | 1:many | `order_id` |
| Fulfillment (`fact_fulfillments`) | 1:many | `order_id` |
| Staff (`dim_staff`) | many:1 | `seller_staff_key` |
| Channel (`dim_channels`) | many:1 | `channel_key` |

#### Conflicts
*None.*

#### Anti-patterns
- JOIN with `fact_order_items` then `COUNT(*)` → overcounts orders; always `COUNT(DISTINCT order_id)`.
- JOIN directly with `fact_targets` in native SQL — different grain (target=cycle, order=event); use `mart_sales_actual_vs_target` instead.
- Filtering `fulfillment_status = 'RETURNED'` to measure returns — undercounts partial returns; use `fact_order_returns`.

#### Data Quality
| Dimension | Status | Note |
|---|---|---|
| Freshness | Near-realtime | Webhook-driven, lag ~5 min |
| Completeness | High | All Sapo channels in scope |
| `customer_type` | Partial | Only ~3 WHOLESALE live; B2B historical unreliable pre-2026 |

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `fact_orders` SLA row.

---

## Order Line Item

> **Type:** Entity | **Mart:** `fact_order_items` (alias: `fact_sales`) | **Grain:** 1 row = 1 SKU line in 1 order | **Status:** `active`
> **Key:** `order_id + product_id` | **Source:** Sapo | **Since:** 2021

**Definition:** Each distinct SKU on an order. Used for product-level revenue, quantity, and margin analysis. `fact_sales` is a view alias over this table.

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `order_id` | bigint | FK → fact_orders |
| `product_id` | bigint | Sapo product ID |
| `product_key` | varchar | FK → dim_products |
| `sku` | varchar | SKU code |
| `quantity` | int | Units sold |
| `unit_price` | numeric | Price per unit (VAT-inclusive) |
| `line_revenue` | numeric | quantity × unit_price |
| `discount_amount` | numeric | Line-level discount |
| `channel_key` | varchar | Inherited from parent order |

**Intent:** Product-level revenue breakdown, SKU ranking, channel mix by SKU, quantity analysis.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Order (`fact_orders`) | many:1 | `order_id` |
| Product (`dim_products`) | many:1 | `product_key` |

#### Conflicts
*None.*

#### Anti-patterns
- `COUNT(*)` after joining with fact_orders to count orders → overcounts; fan-out from line items inflates order count.
- Summing `line_revenue` across all rows without scope filter → includes cancelled/test orders.

#### Data Quality
*No known gaps beyond parent order completeness.*

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `fact_order_items` SLA row.

---

## Customer

> **Type:** Entity | **Mart:** `dim_customers` | **Grain:** 1 row = 1 unique customer | **Status:** `active`
> **Key:** `customer_id` (surrogate: `customer_key`) | **Source:** Sapo | **Since:** 2021

**Definition:** A customer registered in Sapo. Includes behavioral metrics (RFM, last purchase date, lifetime value) computed at refresh time.

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `customer_id` | bigint | Sapo natural key |
| `customer_key` | varchar | MD5 surrogate key |
| `customer_name` | varchar | Display name |
| `customer_type` | varchar | `RETAIL` / `WHOLESALE` (migration incomplete) |
| `phone` | varchar | Primary contact (PII) |
| `total_orders` | int | Lifetime order count |
| `total_revenue` | numeric | Lifetime revenue |
| `last_order_date` | date | Most recent purchase date (ICT) |
| `rfm_segment` | varchar | Pre-computed RFM segment |

**Intent:** Customer segmentation, RFM analysis, repeat purchase tracking, CRM action triggers.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Order (`fact_orders`) | 1:many | `customer_key` |
| Customer Action Queue (`mart_customer_action_queue`) | 1:1 | `customer_key` |

#### Conflicts
*None.*

#### Anti-patterns
- Trusting `customer_type = 'WHOLESALE'` for historical B2B analysis — migration only ~3 WHOLESALE live; pre-2026 data defaults to RETAIL.

#### Data Quality
| Dimension | Status | Note |
|---|---|---|
| `customer_type` | Incomplete | Historical B2B unreliable; TYPE_* group-code re-tag unfinished |
| PII fields | Sensitive | `phone`, `email` — access-controlled |

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `dim_customers` SLA row.

---

## Channel

> **Type:** Entity | **Mart:** `dim_channels` | **Grain:** 1 row = 1 sales channel | **Status:** `active`
> **Key:** `channel_id` (surrogate: `channel_key`) | **Source:** Sapo | **Since:** 2021

**Definition:** A sales channel through which orders are placed (e.g., retail POS, Shopee, TikTok Shop, B2B direct).

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `channel_id` | bigint | Sapo natural key |
| `channel_key` | varchar | MD5 surrogate key |
| `channel_name` | varchar | Display name |
| `channel_category` | varchar | Grouping (e.g. Marketplace, Direct, POS) |
| `channel_format` | varchar | Format classification |
| `platform` | varchar | Underlying platform (Shopee, Sapo POS, etc.) |
| `is_sales_channel` | boolean | In-scope for sales reporting |
| `market` | varchar | Geographic market |

**Intent:** Channel-level revenue breakdowns, channel mix analysis, per-channel KPI tracking.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Order (`fact_orders`) | 1:many | `channel_key` |
| Order Returns (`fact_order_returns`) | 1:many | `channel_key` |
| Channel Targets (`dim_channel_targets`) | 1:many | `channel_key` |

#### Conflicts
*None.*

#### Anti-patterns
*None.*

#### Data Quality
*No known gaps.*

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `dim_channels` SLA row.

---

## Product

> **Type:** Entity | **Mart:** `dim_products` | **Grain:** 1 row = 1 SKU (variant) | **Status:** `active`
> **Key:** `product_id` (surrogate: `product_key`) | **Source:** Sapo | **Since:** 2021

**Definition:** A product variant (SKU) sold through Sapo. Includes product hierarchy (brand, category, sub-category) and pricing attributes.

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `product_id` | bigint | Sapo natural key |
| `product_key` | varchar | MD5 surrogate key |
| `sku` | varchar | SKU code |
| `product_name` | varchar | Product display name |
| `variant_name` | varchar | Variant (size/color) |
| `category` | varchar | Product category |
| `brand` | varchar | Brand name |
| `unit_cost` | numeric | Latest MAC from Sapo |
| `retail_price` | numeric | Standard retail price (VAT-inclusive) |

**Intent:** Product catalog lookups, category/brand analysis, price and margin reference.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Order Line Item (`fact_order_items`) | 1:many | `product_key` |
| Inventory Snapshot (`fact_inventory_snapshot`) | 1:many | `sku` / `variant_id` |
| SKU Economics Monthly (`mart_sku_economics_monthly`) | 1:many | `product_key` |

#### Conflicts
*None.*

#### Anti-patterns
- Using `unit_cost` from dim_products for P&L — this is the current Sapo MAC, not the order-time cost; use `fact_order_economics` or `fact_order_costs` for per-order COGS.

#### Data Quality
*No known structural gaps.*

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `dim_products` SLA row.

---

## Order Economics

> **Type:** Entity | **Mart:** `fact_order_economics` | **Grain:** 1 row = 1 order (extended P&L) | **Status:** `active`
> **Key:** `order_id` / `order_code` | **Source:** Sapo + MISA (Derived) | **Since:** 2024

**Definition:** Per-order P&L enrichment — COGS, overhead allocation, gross profit, and net profit. Joins Sapo order data with MISA cost accounting.

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `order_code` | varchar | Natural join key to fact_orders |
| `net_revenue` | numeric | Revenue after discounts and VAT |
| `cogs_amount` | numeric | COGS from MISA (actual) or Sapo MAC (estimated) |
| `has_cogs` | boolean | True when MISA-matched COGS is available |
| `gross_profit` | numeric | net_revenue − cogs_amount |
| `gross_margin_pct` | numeric | gross_profit / net_revenue |
| `overhead_allocated` | numeric | Allocated fixed cost for this order |
| `fully_loaded_net_profit` | numeric | Tier-3 metric — gross profit minus all allocated costs |

**Intent:** Per-order profitability analysis, COGS coverage reporting, Tier-2/Tier-3 margin reporting.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Order (`fact_orders`) | 1:1 | `order_code` |
| Order Costs (`fact_order_costs`) | partial overlap | `order_id` (different granularity) |

#### Conflicts
*None.*

#### Anti-patterns
- Filtering `cogs_source = 'misa'` to get accurate P&L — this column is deprecated; use `has_cogs = true`.
- Using `fully_loaded_net_profit` for per-order accept/reject decisions — this is a Tier-3 aggregate report metric, not an operational signal.
- Treating 35% of orders with `has_cogs = false` as zero-margin — they have estimated COGS from Sapo MAC, not zero.

#### Data Quality
| Dimension | Status | Note |
|---|---|---|
| COGS coverage | ~65% | MISA date-range match; remaining 35% use Sapo MAC estimate |
| `cogs_source` | Deprecated | Column still exists but use `has_cogs` instead |

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `fact_order_economics` SLA row.

---

## Order Returns

> **Type:** Entity | **Mart:** `fact_order_returns` | **Grain:** 1 row = 1 return event | **Status:** `active`
> **Key:** `return_id` | **Source:** Sapo | **Since:** 2022

**Definition:** Each distinct return event from Sapo. Tracks refund amount, reason, and status independently from the original order.

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `return_id` | bigint | Sapo return ID |
| `order_code` | varchar | Link to original order |
| `return_date` | date | Date return was recognized (ICT) |
| `refund_amount` | numeric | Amount refunded to customer |
| `return_reason` | varchar | Reason code |
| `return_status` | varchar | Current return status |
| `channel_key` | varchar | FK → dim_channels |

**Intent:** Return rate analysis, refund impact on revenue, channel-level return patterns.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Order (`fact_orders`) | many:1 | `order_code` |
| Channel (`dim_channels`) | many:1 | `channel_key` |
| Fulfillment (`fact_fulfillments`) | correlated | `order_id` + 30-day window |

#### Conflicts
*None.*

#### Anti-patterns
- Using `fulfillment_status = 'RETURNED'` on `fact_orders` instead — this undercounts partial returns; a single order can have multiple return events.
- Restating returns into the original order's P&L period — returns are recognized at `return_date`, not the original order date.

#### Data Quality
*No known structural gaps.*

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `fact_order_returns` SLA row.

---

## Order Costs (Cost Ledger)

> **Type:** Entity | **Mart:** `fact_order_costs` | **Grain:** 1 row = 1 (order_id, cost_type) | **Status:** `active`
> **Key:** `order_id + cost_type` | **Source:** Sapo + Derived | **Since:** 2024

**Definition:** Long-format cost ledger — one row per cost type per order. All `amount` values are positive (ABS); direction is derived from `cost_category`. Covers COGS, platform fees, taxes, shipping, and discounts.

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `order_id` | bigint | FK → fact_orders |
| `cost_type` | varchar | Specific cost type (e.g. `cogs`, `tax_vat`, `discount_seller`) |
| `cost_category` | varchar | Grouping: `COGS`, `PLATFORM_FEE`, `TAX`, `SHIPPING`, `DISCOUNT` |
| `amount` | numeric | Cost amount (always positive) |
| `currency` | varchar | Currency code |

**Intent:** Detailed cost decomposition per order, platform fee analysis, discount attribution, tax reporting.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Order (`fact_orders`) | many:1 | `order_id` |
| Order Economics (`fact_order_economics`) | partial overlap | `order_id` (different granularity) |

#### Conflicts
| Name | Location | Difference | Note |
|---|---|---|---|
| COGS | `fact_order_economics` | Economics has MISA-matched COGS; costs table has same data in long format | Use economics for per-order P&L; use costs for cost-type drill-down |

#### Anti-patterns
- `SUM(amount)` without filtering `cost_category` — mixes COGS + platform fees + discounts into a meaningless total.
- Using Shopee fee rows for non-Shopee orders — platform fees are channel-specific; always filter by channel.

#### Data Quality
| Dimension | Status | Note |
|---|---|---|
| COGS coverage | ~65% | MISA matched orders only |
| Shopee fees | Shopee-only | Not applicable to other channels |

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `fact_order_costs` SLA row.

---

## Marketing Spend

> **Type:** Entity | **Mart:** `fact_marketing_spend` | **Grain:** 1 row = 1 campaign/day | **Status:** `active`
> **Key:** `spend_date + campaign_id` | **Source:** Manual (Google Sheets) | **Since:** 2023

**Definition:** Marketing cost per campaign per day. Manually imported from Sheets — not automated. Covers paid ads across channels.

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `spend_date` | date | Campaign date (ICT) |
| `channel_name` | varchar | Marketing channel name |
| `campaign_id` | varchar | Campaign identifier |
| `spend_amount` | numeric | Cost in VND |
| `clicks` | int | Click count (where available) |
| `impressions` | int | Impression count (where available) |

**Intent:** Marketing cost tracking, channel spend analysis, ROAS numerator (spend side).

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Order (`fact_orders`) | indirect | Needs attribution model — no direct FK |

#### Conflicts
*None.*

#### Anti-patterns
- Joining `fact_marketing_spend` directly with `fact_orders` for ROAS — no attribution model exists; marketing channel ≠ order channel without last-click or multi-touch logic.
- Assuming daily data is complete — SLA is 48h (manual import); recent days may have gaps.

#### Data Quality
| Dimension | Status | Note |
|---|---|---|
| Freshness SLA | 48h | Manual import; gaps possible |
| Attribution | Not modeled | ROAS requires attribution layer that does not yet exist |

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `fact_marketing_spend` SLA row.

---

## Inventory Snapshot

> **Type:** Entity | **Mart:** `fact_inventory_snapshot` | **Grain:** 1 row = (variant_id, location_id, snapshot_date) | **Status:** `active`
> **Key:** `variant_id + location_id + snapshot_date` | **Source:** Sapo | **Since:** 2023

**Definition:** Daily end-of-day inventory snapshot from Sapo nightly batch (3am ICT). Incremental parquet, retained indefinitely.

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `variant_id` | bigint | Sapo variant ID |
| `sku` | varchar | SKU code |
| `location_id` | bigint | Warehouse/location ID |
| `location_name` | varchar | Human-readable location name |
| `snapshot_date` | date | Snapshot date (ICT) |
| `on_hand` | int | Units on hand at snapshot time |
| `stock_value_at_mac` | numeric | on_hand × MAC at snapshot time |

**Intent:** Stock level tracking, inventory valuation, days-of-supply inputs, OOS detection.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Product (`dim_products`) | many:1 | `sku` / `variant_id` |
| Inventory Health (`mart_inventory_health`) | 1:1 | `sku + location_id + snapshot_date` |

#### Conflicts
| Name | Location | Difference | Note |
|---|---|---|---|
| Stock value | MISA | Sapo MAC may lag GRN pricing 1-2 days; not accounting-grade | Use MISA for official stock valuation |

#### Anti-patterns
- Using `stock_value_at_mac` for official inventory valuation — Sapo MAC lags GRN pricing 1-2 days; MISA is the accounting source.
- Querying intra-day stock changes — snapshot is once daily at 3am ICT; no intra-day granularity.

#### Data Quality
| Dimension | Status | Note |
|---|---|---|
| Locations | 3 active | 452566 Trương Định (main), 494912 Hậu Giang, 624127 MM Market An Phú (consignment) |
| MAC accuracy | Lags 1-2d | Not accounting-grade; use MISA for official valuation |

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `fact_inventory_snapshot` SLA row.

---

## Inventory Health

> **Type:** Entity | **Mart:** `mart_inventory_health` | **Grain:** 1 row = (sku, location_id, snapshot_date) | **Status:** `active`
> **Key:** `sku + location_id + snapshot_date` | **Source:** Derived | **Since:** 2024

**Definition:** Derived health classification per SKU per location per day. Combines `fact_inventory_snapshot` stock levels with `mart_sku_economics_monthly` velocity data.

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `sku` | varchar | SKU code |
| `location_id` | bigint | Warehouse location |
| `snapshot_date` | date | Reference date |
| `is_oos` | boolean | Out-of-stock flag |
| `is_slow_mover` | boolean | Low velocity flag (proxy via sales recency) |
| `is_dead_stock` | boolean | No sales for extended period |
| `days_of_supply` | numeric | Estimated days remaining at current velocity |
| `slow_mover_value_at_risk` | numeric | VND at risk from slow-moving stock |
| `dead_stock_value_at_risk` | numeric | VND at risk from dead stock |

**Intent:** Inventory risk flagging, replenishment triggers, dead stock liquidation planning.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Inventory Snapshot (`fact_inventory_snapshot`) | derived from | `sku + location_id + snapshot_date` |
| SKU Economics Monthly (`mart_sku_economics_monthly`) | derived from | `product_key` / `sku` |

#### Conflicts
*None.*

#### Anti-patterns
- Using `is_slow_mover` without filtering to exclude MM Market (location 624127 consignment) — consignment shows high OOS by design; inflates slow-mover counts.
- Trusting `is_slow_mover` for SKUs newer than 30 days — proxy based on sales recency; new SKUs may be incorrectly flagged.

#### Data Quality
| Dimension | Status | Note |
|---|---|---|
| `is_slow_mover` | Proxy only | Based on sales recency, not true velocity model |
| New SKUs (<30d) | Potentially wrong | May be false-positive slow-mover |

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `mart_inventory_health` SLA row.

---

## SKU Economics Monthly

> **Type:** Entity | **Mart:** `mart_sku_economics_monthly` | **Grain:** 1 row = (product_key, snapshot_month) | **Status:** `active`
> **Key:** `product_key + snapshot_month` | **Source:** Derived | **Since:** 2024

**Definition:** Single source of truth for SKU-level monthly economics. Replaces ad-hoc joins of `int_misa_sales_lines` + `fact_sales` + `int_return_sku_lines`. COGS coverage ~65% (MISA-matched orders only).

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `product_key` | varchar | FK → dim_products |
| `snapshot_month` | date | Month start date |
| `units_sold` | int | Net units sold (returns deducted) |
| `net_revenue` | numeric | Revenue after returns and discounts |
| `cogs_amount` | numeric | COGS for the month (65% coverage) |
| `gross_profit` | numeric | net_revenue − cogs_amount |
| `gross_margin_pct` | numeric | gross_profit / net_revenue |
| `return_rate` | numeric | Units returned / units sold |
| `return_adjusted_margin_pct` | numeric | Worst-case margin (full refund, zero COGS recovery) |
| `days_since_last_sale` | int | Staleness indicator |
| `is_slow_mover` | boolean | Velocity flag |
| `top_channel_name` | varchar | Channel with highest revenue for this SKU |

**Intent:** SKU profitability ranking, slow-mover identification, channel mix by SKU, monthly COGS trend.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Product (`dim_products`) | many:1 | `product_key` |
| Inventory Health (`mart_inventory_health`) | feeds into | `product_key` / `sku` |

#### Conflicts
*None.*

#### Anti-patterns
- Joining `int_misa_sales_lines` + `fact_sales` ad-hoc for SKU economics — this table is the single source of truth; ad-hoc joins produce inconsistent results.
- Treating `return_adjusted_margin_pct` as expected margin — it is the worst-case lower bound (full refund deducted, zero COGS recovery assumed).

#### Data Quality
| Dimension | Status | Note |
|---|---|---|
| COGS coverage | ~65% | MISA matched only; 35% use Sapo MAC or missing |
| `return_adjusted_margin_pct` | Worst-case | Conservative estimate; actual may be better |

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `mart_sku_economics_monthly` SLA row.

---

## Fulfillment

> **Type:** Entity | **Mart:** `fact_fulfillments` (source: `std_fulfillments`) | **Grain:** 1 row = 1 fulfillment event | **Status:** `active`
> **Key:** `fulfillment_id` | **Source:** Sapo | **Since:** 2022

**Definition:** A shipment event against an order. One order may have multiple fulfillments (partial shipments). Grain is shipment, not order.

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `fulfillment_id` | bigint | Sapo fulfillment ID |
| `order_id` | bigint | FK → fact_orders |
| `shipped_at` | timestamptz | Shipment timestamp (UTC-stored) |
| `status` | varchar | Fulfillment status |
| `carrier_id` | bigint | Carrier/3PL identifier |
| `cod_amount` | numeric | Cash-on-delivery amount |
| `created_at` | timestamptz | Record creation time |

**Intent:** Shipment tracking, carrier performance, COD reconciliation, delivery SLA analysis.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Order (`fact_orders`) | many:1 | `order_id` |
| Order Returns (`fact_order_returns`) | correlated | `order_id` + 30-day window |

#### Conflicts
| Name | Location | Difference | Note |
|---|---|---|---|
| `std_fulfillments` | Source layer | Raw source view; `fact_fulfillments` is the mart | Currently using `std_fulfillments` directly; `mart_shipments` planned replacement |

#### Anti-patterns
- Counting fulfillments to count orders — 1 order can have N fulfillments; always join back to `fact_orders` and count distinct order IDs.

#### Data Quality
*No known gaps.*

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `fact_fulfillments` SLA row.

---

## Staff

> **Type:** Entity | **Mart:** `dim_staff` | **Grain:** 1 row = 1 staff member | **Status:** `active`
> **Key:** `staff_key` | **Source:** Sapo | **Since:** 2021

**Definition:** Sales and operations staff registered in Sapo. Used for commission attribution and order audit trail.

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `staff_key` | varchar | MD5 surrogate key |
| `staff_id` | bigint | Sapo natural key |
| `staff_name` | varchar | Display name |
| `email` | varchar | Staff email (PII) |
| `role` | varchar | Role classification |

**Intent:** Commission reporting, order attribution by staff, sales performance by rep.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Order (`fact_orders`) | 1:many | `seller_staff_key` (primary) or `creator_staff_key` |

#### Conflicts
*None.*

#### Anti-patterns
- Using `creator_staff_key` for commission reporting — this is an audit trail field (who created the order in the system); use `seller_staff_key` for sales/commission attribution.

#### Data Quality
*No known gaps.*

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `dim_staff` SLA row.

---

## Channel Targets

> **Type:** Entity | **Mart:** `dim_channel_targets` | **Grain:** 1 row = (channel_key, period_month, metric_type, target_source) | **Status:** `active`
> **Key:** composite | **Source:** Manual (CSV seed) | **Since:** 2024

**Definition:** Budget targets per channel per month. Manually maintained as a dbt seed CSV. Supports multiple metric types per channel per period.

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `channel_key` | varchar | FK → dim_channels |
| `period_month` | date | Target month (month start) |
| `metric_type` | varchar | `NET_REVENUE`, `NET_MARGIN_PCT`, `ORDER_COUNT` |
| `target_value` | numeric | Target value for the metric |
| `target_source` | varchar | Source/version of the target |

**Intent:** Actual vs. target reporting, channel performance tracking against plan.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Channel (`dim_channels`) | many:1 | `channel_key` |
| Targets (`fact_targets`) | sibling | Different scope — channel targets vs. aggregate sales targets |

#### Conflicts
*None.*

#### Anti-patterns
- Editing the CSV seed without running `dbt seed --select dim_channel_targets && dbt build --select dim_channel_targets` — table will not reflect changes until rebuilt.

#### Data Quality
| Dimension | Status | Note |
|---|---|---|
| Update frequency | Manual | Requires explicit dbt seed run after CSV edits |

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `dim_channel_targets` SLA row.

---

## Targets (Sales)

> **Type:** Entity | **Mart:** `fact_targets` | **Grain:** 1 row = 1 target rule (cycle + scope) | **Status:** `active`
> **Key:** composite (cycle + scope flags) | **Source:** Manual | **Since:** 2024

**Definition:** Sales targets with flexible cycle types (daily, weekly, monthly, quarterly, yearly) and scope filters. Grain is a target rule, not an order — different from `fact_orders`.

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `cycle_type` | varchar | `daily`, `weekly`, `monthly`, `quarterly`, `yearly` |
| `cycle_start_date` | date | Cycle start |
| `cycle_end_date` | date | Cycle end |
| `target_val` | numeric | Target value |
| `actual_revenue` | numeric | Pre-computed actual for the cycle |
| `scope_filter` | varchar | Scope this target applies to |

**Intent:** Sales target tracking, actual vs. target gap analysis, cycle performance reporting.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Channel Targets (`dim_channel_targets`) | sibling | Different scope — aggregate vs. per-channel |

#### Conflicts
*None.*

#### Anti-patterns
- Joining `fact_targets` directly with `fact_orders` in native SQL — different grain (target=cycle rule, order=event); use `mart_sales_actual_vs_target` or pre-aggregate orders to cycle level first.

#### Data Quality
*No known gaps.*

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `fact_targets` SLA row.

---

## Payments

> **Type:** Entity | **Mart:** `fact_payments` | **Grain:** 1 row = 1 payment transaction | **Status:** `active`
> **Key:** `payment_id` | **Source:** Sapo | **Since:** 2022

**Definition:** Cash flow tracking — individual inflow and outflow payment movements recorded in Sapo.

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `payment_id` | bigint | Sapo payment ID |
| `payment_date` | date | Transaction date (ICT) |
| `type` | varchar | `inflow` / `outflow` |
| `amount` | numeric | Transaction amount (VND) |
| `payment_method` | varchar | Method (COD, bank transfer, e-wallet, etc.) |

**Intent:** Cash flow reporting, payment method mix, receivables tracking.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Order (`fact_orders`) | correlated | No direct FK; link via order context in payment notes |

#### Conflicts
*None.*

#### Anti-patterns
*None.*

#### Data Quality
*No known gaps.*

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `fact_payments` SLA row.

---

## Customer Action Queue

> **Type:** Entity | **Mart:** `mart_customer_action_queue` | **Grain:** 1 row = 1 customer who needs action now | **Status:** `active`
> **Key:** `customer_key` | **Source:** Derived | **Since:** 2024

**Definition:** Derived queue of customers requiring CS or sales action. Built from `dim_customers` behavioral metrics. Surfaces only customers with an actionable signal at refresh time.

**Key Fields:**
| Field | Type | Description |
|---|---|---|
| `customer_key` | varchar | FK → dim_customers |
| `customer_name` | varchar | Display name |
| `action_type` | varchar | `OVERDUE`, `NEW_HIGH_VALUE`, `AT_RISK`, etc. |
| `action_priority` | int | Priority rank within action type |
| `last_order_date` | date | Most recent purchase date |
| `total_revenue` | numeric | Lifetime revenue |

**Intent:** CRM action triggers, CS outreach prioritization, high-value customer retention.

#### Related Entities
| Entity | Relationship | Join Key |
|---|---|---|
| Customer (`dim_customers`) | derived from | `customer_key` |
| Order (`fact_orders`) | indirect | Via dim_customers behavioral metrics |

#### Conflicts
*None.*

#### Anti-patterns
- Treating the queue as a complete customer list — it only contains customers with an active actionable signal; customers with no signal are absent.

#### Data Quality
| Dimension | Status | Note |
|---|---|---|
| `customer_type` accuracy | Incomplete | Inherits dim_customers limitation for pre-2026 B2B |

#### Freshness
See [freshness.md](freshness.md#mart-sla) — `mart_customer_action_queue` SLA row.
