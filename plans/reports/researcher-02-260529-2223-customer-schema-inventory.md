# Customer OLAP Schema Inventory
**Purpose:** Catalog all customer-side data the warehouse holds, to support a single-customer insight web app.
**Scope:** Read-only. dbt SQL + schema.yml — no live DuckDB query.
**Date:** 2026-05-29

---

## 1. Customer Grain & Keys

| Key | Column | Type | Note |
|-----|--------|------|------|
| Surrogate (DW) | `customer_key` | VARCHAR (md5) | `md5(customer_id)` — join key across all facts |
| Natural (Sapo) | `customer_id` | VARCHAR | Sapo numeric ID (cast to varchar) |
| Code | `customer_code` | VARCHAR | Available in staging (`stg_sapo_customers`) only; **not surfaced to mart** |
| Phone | `phone` | VARCHAR | Search-friendly; cleaned in staging |
| Email | `email` | VARCHAR | Present; quality variable |

**Searchable by UI:** phone (most reliable), full_name fuzzy, email. `customer_id` usable if known.
`customer_code` exists in raw staging but is dropped before `std_customers` → not in serving layer.

---

## 2. Per-Table Column Inventory

### 2a. `dim_customers_base` — Profile Spine (internal; not in serving layer)

Grain: 1 row per customer. SCD Type 1 (last-write-wins).
Materialized incremental; **not exported** to Metabase/olap.duckdb.

| Column | Dtype | RAW / COMPUTED | Meaning |
|--------|-------|----------------|---------|
| `customer_key` | VARCHAR | RAW (derived) | Surrogate key (md5 of customer_id) |
| `customer_id` | VARCHAR | RAW | Sapo numeric customer ID |
| `full_name` | VARCHAR | RAW | Display name |
| `email` | VARCHAR | RAW | Email address |
| `phone` | VARCHAR | RAW | Phone number |
| `dob` | DATE | RAW | Date of birth |
| `sex` | VARCHAR | RAW | Gender |
| `customer_group` | VARCHAR | RAW | Raw Sapo group tag (e.g. TYPE_WHOLESALE) |
| `loyalty_point` | INTEGER | RAW | Loyalty points balance from Sapo |
| `city` | VARCHAR | RAW | City (may duplicate province) |
| `province` | VARCHAR | RAW | Province/city |
| `district` | VARCHAR | RAW | District |
| `ward` | VARCHAR | RAW | Ward |
| `address1` | VARCHAR | RAW | Street address |
| `country` | VARCHAR | RAW | Country |
| `created_at` | TIMESTAMPTZ | RAW | Customer created in Sapo |
| `updated_at` | TIMESTAMPTZ | RAW | Last modified in Sapo |

Also includes an "Unknown" sentinel row (`customer_id='Unknown'`) for orders with no customer match.

---

### 2b. `dim_customers` — Final Serving Dimension (in olap.duckdb)

Grain: 1 row per customer. Incremental on `last_modified`.
= dim_customers_base + int_customer_metrics + 8 computed segmentation dimensions.

**Profile Fields (RAW)**

| Column | Dtype | Meaning |
|--------|-------|---------|
| `customer_key` | VARCHAR | Surrogate key |
| `customer_id` | VARCHAR | Natural key |
| `full_name` | VARCHAR | Display name |
| `email` | VARCHAR | Email |
| `phone` | VARCHAR | Phone |
| `dob` | DATE | Date of birth |
| `sex` | VARCHAR | Gender |
| `customer_group` | VARCHAR | Raw Sapo group tag (kept for reference) |
| `loyalty_point` | INTEGER | Loyalty points |
| `city/province/district/ward/address1/country` | VARCHAR | Address fields |
| `created_at` | TIMESTAMPTZ | Sapo account creation |
| `updated_at` | TIMESTAMPTZ | Last Sapo update |
| `last_modified` | TIMESTAMPTZ | MAX(updated_at, metric_calculated_at) — incremental watermark |

**Computed Segmentation Dimensions**

| Column | Dtype | COMPUTED | Logic |
|--------|-------|----------|-------|
| `customer_type` | VARCHAR | COMPUTED (manual-sourced) | RETAIL / WHOLESALE / PARTNER / STAFF / KOL — derived from customer_group tag |
| `value_group` | VARCHAR | COMPUTED | VALUE_VIP (≥50M or ≥20 orders) / VALUE_GOLD (≥20M) / VALUE_SILVER (≥5M) / VALUE_BRONZE |
| `lifecycle_stage` | VARCHAR | COMPUTED | LIFECYCLE_NEW / ACTIVE / AT_RISK / CHURNED — recency + tenure |
| `channel_preference` | VARCHAR | COMPUTED | CHANNEL_SOCIAL / MARKETPLACE / DIRECT / OFFLINE / OTHER — mode of channel_format across orders |
| `product_affinity` | VARCHAR | COMPUTED | PRODUCT_FINE_JAPAN / FG_CARE / FINE_CARE / MULTI — brand with >60% revenue share |
| `payment_behavior` | VARCHAR | COMPUTED | PAYMENT_COD (>70% COD) / PAYMENT_PREPAID |
| `geo_region` | VARCHAR | COMPUTED | GEO_HCMC / HANOI / MEKONG / CENTRAL / OTHER — derived from province |
| `acquisition_source` | VARCHAR | COMPUTED | Always NULL (pending Sapo implementation) |
| `customer_status` | VARCHAR | COMPUTED | **DEPRECATED** — use lifecycle_stage. Legacy: Active/At Risk/Churned |

**RFM & Value Metrics (COMPUTED)**

| Column | Dtype | Meaning |
|--------|-------|---------|
| `lifetime_value` | DECIMAL | SUM(fact_orders.total_collected) — after discount, incl. tax |
| `total_orders_count` | INTEGER | COUNT(DISTINCT order_id) |
| `first_order_date` | TIMESTAMPTZ | MIN(order_timestamp) |
| `last_order_date` | TIMESTAMPTZ | MAX(order_timestamp) |
| `recency_days` | INTEGER | current_date - last_order_date |
| `lifespan_days` | INTEGER | first_order_date to last_order_date |

---

### 2c. `int_customer_metrics` — Intermediate Metrics Model (internal)

Grain: 1 row per customer. Input to dim_customers. Not in serving layer.

| Column | Dtype | COMPUTED | Formula |
|--------|-------|----------|---------|
| `customer_key` | VARCHAR | RAW (join) | FK |
| `first_order_date` | TIMESTAMPTZ | COMPUTED | MIN(order_timestamp) |
| `last_order_date` | TIMESTAMPTZ | COMPUTED | MAX(order_timestamp) |
| `recency_days` | INTEGER | COMPUTED | date_diff('day', last_order_date, current_date) |
| `frequency` | INTEGER | COMPUTED | COUNT(DISTINCT order_id) |
| `monetary_value` | DECIMAL | COMPUTED | SUM(total_collected) |
| `lifespan_days` | INTEGER | COMPUTED | date_diff first→last order |
| `channel_preference` | VARCHAR | COMPUTED | Mode of channel_format (sales channels only) |
| `product_affinity` | VARCHAR | COMPUTED | Brand with >60% revenue share |
| `payment_behavior` | VARCHAR | COMPUTED | COD ratio > 70% → PAYMENT_COD |
| `metric_calculated_at` | TIMESTAMPTZ | COMPUTED | current_timestamp of dbt run |

---

### 2d. `mart_customer_status_snapshot_monthly` — Status Timeline (in olap.duckdb)

Grain: 1 row per (customer_key × snapshot_month). Rolling 24-month window (closed months only).
Filters: `customer_type = 'RETAIL'`, has orders, first_order_date IS NOT NULL.

| Column | Dtype | COMPUTED | Meaning |
|--------|-------|----------|---------|
| `customer_key` | VARCHAR | RAW | FK to dim_customers |
| `snapshot_month` | DATE | COMPUTED | Last day of month (month-end) |
| `status` | VARCHAR | COMPUTED | ACTIVE / AT_RISK / CHURNED as-of month-end |
| `is_new` | BOOLEAN | COMPUTED | TRUE if first_order_date falls within this month |
| `value_group` | VARCHAR | COMPUTED (approx) | Current value_group (not point-in-time) |
| `orders_to_date` | INTEGER | COMPUTED (approx) | Current total_orders_count (not historical) |
| `lifetime_value_to_date` | DECIMAL | COMPUTED (approx) | Current lifetime_value (not historical) |
| `days_since_last_order` | INTEGER | COMPUTED | date_diff(last_order_date, snapshot_month) |
| `customer_type` | VARCHAR | RAW | Always 'RETAIL' (filter applied) |
| `channel_preference` | VARCHAR | COMPUTED | From dim_customers |
| `product_affinity` | VARCHAR | COMPUTED | From dim_customers |

**Status logic as-of month-end:**
- ACTIVE: last_order_date > snapshot_month OR days_since ≤ 30
- AT_RISK: days_since 31–90
- CHURNED: days_since > 90

---

## 3. Customer → Orders Linkage

**Join key:** `customer_key` (surrogate, VARCHAR md5)

```
dim_customers.customer_key
  ←→ fact_orders.customer_key         (order-grain; 1 row per order)
  ←→ fact_order_economics.order_id    (via fact_orders.order_id)
  ←→ fact_payments.order_id           (via fact_orders.order_id)
  ←→ fact_sales.customer_key          (line-item grain; N rows per order)
```

**To list a customer's orders:**
```sql
SELECT o.*, e.gross_profit, e.channel_net_profit, e.gross_margin_pct
FROM fact_orders o
LEFT JOIN fact_order_economics e ON o.order_id = e.order_id
WHERE o.customer_key = <target_customer_key>
ORDER BY o.order_timestamp DESC
```

**To aggregate customer spend/margin:**
```sql
SELECT
  customer_key,
  COUNT(DISTINCT o.order_id)          AS order_count,
  SUM(o.total_collected)              AS total_spent,
  SUM(o.net_revenue)                  AS total_net_revenue,
  SUM(e.gross_profit)                 AS total_gross_profit,
  AVG(o.total_collected)              AS aov,
  SUM(e.cogs_amount)                  AS total_cogs,
  AVG(e.gross_margin_pct)             AS avg_gross_margin_pct
FROM fact_orders o
LEFT JOIN fact_order_economics e ON o.order_id = e.order_id
WHERE o.customer_key = <target>
  AND o.status = 'COMPLETED'  -- or exclude CANCELLED
GROUP BY 1
```

**Useful joins for enriched order list:**

| Fact/Dim | Join | Adds |
|----------|------|------|
| `dim_channels` | `fact_orders.channel_key = dim_channels.channel_key` | channel_name, channel_format, platform |
| `dim_staff` | `fact_orders.seller_staff_key = dim_staff.staff_key` | seller name, email |
| `dim_geography` | `fact_orders.shipping_geography_key = dim_geography.geography_key` | shipping province/district |
| `fact_payments` | `fact_orders.order_id = fact_payments.order_id` | payment method, amount, paid_on |
| `fact_order_returns` | `fact_orders.order_code = fact_order_returns.order_code` | return events, refund_amount |

---

## 4. Status Snapshot — What `mart_customer_status_snapshot_monthly` Tracks

- **Purpose:** Month-over-month retention/churn trends without point-in-time order re-aggregation
- **Window:** Rolling 24 months of closed periods (excludes current incomplete month)
- **Population:** RETAIL customers only with ≥1 order and known first_order_date
- **Status transitions:** ACTIVE → AT_RISK → CHURNED (one-way in practice; re-activation shows ACTIVE again at a later month)
- **New customer flag:** `is_new = TRUE` in the month of first order — enables cohort acquisition tracking
- **Cohort analysis:** Filter `is_new = TRUE` per month, then track `status` over subsequent months for that cohort

**Key caveat (documented in SQL):** `orders_to_date` and `lifetime_value_to_date` use current dim_customers values, not historical. For exact point-in-time these would require re-aggregating fact_orders per month-end — acceptable at monthly trend grain but NOT suitable for "what was this customer's LTV in March 2025."

---

## 5. Insight Catalog for ONE Customer

Grouped by proposed UI tab:

### Tab: Profile
| Insight | Source Column(s) | Type |
|---------|-----------------|------|
| Full name | `dim_customers.full_name` | RAW |
| Phone | `dim_customers.phone` | RAW |
| Email | `dim_customers.email` | RAW |
| Date of birth | `dim_customers.dob` | RAW |
| Gender | `dim_customers.sex` | RAW |
| Address | `dim_customers.address1, ward, district, province, country` | RAW |
| Geographic region | `dim_customers.geo_region` | COMPUTED |
| Loyalty points | `dim_customers.loyalty_point` | RAW |
| Customer type | `dim_customers.customer_type` | COMPUTED (manual-sourced) |
| Sapo group tag | `dim_customers.customer_group` | RAW |
| Acquisition source | `dim_customers.acquisition_source` | COMPUTED (always NULL) |
| Account created | `dim_customers.created_at` | RAW |
| Last Sapo update | `dim_customers.updated_at` | RAW |

### Tab: Value Metrics
| Insight | Source Column(s) | Type |
|---------|-----------------|------|
| Lifetime value (total collected) | `dim_customers.lifetime_value` | COMPUTED |
| Total orders count | `dim_customers.total_orders_count` | COMPUTED |
| AOV (derived) | `lifetime_value / total_orders_count` | COMPUTED |
| Value tier | `dim_customers.value_group` | COMPUTED |
| Total gross profit contributed | `SUM(fact_order_economics.gross_profit)` | COMPUTED (query) |
| Total COGS | `SUM(fact_order_economics.cogs_amount)` | COMPUTED (query) |
| Avg gross margin % | `AVG(fact_order_economics.gross_margin_pct)` | COMPUTED (query) |
| Return history | `SUM(fact_order_economics.return_amount)`, `return_count` | COMPUTED (query) |

### Tab: Behavior
| Insight | Source Column(s) | Type |
|---------|-----------------|------|
| First order date | `dim_customers.first_order_date` | COMPUTED |
| Last order date | `dim_customers.last_order_date` | COMPUTED |
| Customer tenure (days) | `dim_customers.lifespan_days` | COMPUTED |
| Recency (days since last order) | `dim_customers.recency_days` | COMPUTED |
| Frequency | `dim_customers.total_orders_count` | COMPUTED |
| Monetary (lifetime_value) | `dim_customers.lifetime_value` | COMPUTED |
| Lifecycle stage | `dim_customers.lifecycle_stage` | COMPUTED |
| Preferred channel | `dim_customers.channel_preference` | COMPUTED |
| Brand affinity | `dim_customers.product_affinity` | COMPUTED |
| Payment behavior | `dim_customers.payment_behavior` | COMPUTED |
| Cohort month (acquisition) | `DATE_TRUNC('month', first_order_date)` | COMPUTED |

### Tab: Status Timeline
| Insight | Source Column(s) | Type |
|---------|-----------------|------|
| Monthly status (ACTIVE/AT_RISK/CHURNED) for last 24 months | `mart_customer_status_snapshot_monthly.status` | COMPUTED |
| Was "new customer" flag per month | `mart_customer_status_snapshot_monthly.is_new` | COMPUTED |
| Days since last order as-of each month | `mart_customer_status_snapshot_monthly.days_since_last_order` | COMPUTED |
| Value group trend (approx) | `mart_customer_status_snapshot_monthly.value_group` | COMPUTED (approx) |

### Tab: Order History
| Insight | Source Column(s) | Type |
|---------|-----------------|------|
| List of orders (code, date, status, amount) | `fact_orders.*` | RAW |
| Channel per order | `dim_channels.channel_name, channel_format` | RAW |
| Seller per order | `dim_staff.full_name` (seller_staff_key) | RAW |
| Shipping address per order | `fact_orders.shipping_address` | RAW |
| Gross/net revenue per order | `fact_orders.gross_revenue, net_revenue, total_collected` | RAW |
| Gross profit per order | `fact_order_economics.gross_profit, gross_margin_pct` | COMPUTED |
| Discount info | `fact_orders.discount_amount, max_discount_rate, primary_discount_nature` | COMPUTED |
| Payment method(s) | `fact_payments.payment_method_key → dim_payment_methods` | RAW |
| Return events | `fact_order_returns.refund_amount, return_reason, return_timestamp` | RAW |
| Fulfillment carrier | `fact_order_economics.carrier_id` | RAW |
| COD amount | `fact_order_economics.cod_amount` | RAW |

---

## 6. Gaps & Caveats

| # | Issue | Detail |
|---|-------|--------|
| 1 | `customer_code` not in serving | Available in `stg_sapo_customers` but dropped at `std_customers` → mart. Not searchable from DW. |
| 2 | `acquisition_source` always NULL | Manual field pending Sapo tagging implementation. Cannot show "how customer was acquired." |
| 3 | `payment_behavior` simplified | Full spec: PREPAID / COD / CREDIT / DELINQUENT. Warehouse only implements PREPAID vs COD. CREDIT and DELINQUENT require debt/credit_term fields not yet ingested. |
| 4 | Status snapshot uses current, not historical, LTV | `orders_to_date` / `lifetime_value_to_date` in `mart_customer_status_snapshot_monthly` = current dim_customers values, not point-in-time. Trend line is directionally correct but month-level LTV is inaccurate. |
| 5 | Customer profile update lag | Sapo customer batch sync is nightly. Profile changes (name, phone, address) reflect next day. NOT real-time. |
| 6 | Timezone: `recency_days` uses server date | `int_customer_metrics` computes `recency_days` via `current_date` at dbt run time (UTC). dbt runs at ~3am ICT = prior-day UTC. Off by ≤1 day; acceptable for RFM segment but worth noting. |
| 7 | `dim_customers_base` not in serving | Internal model only. UI must query `dim_customers` (the full mart) for profile + metrics. |
| 8 | COGS coverage ~65% | `fact_order_economics.cogs_amount` is NULL for orders without a MISA invoice match (~35%). Gross profit and margin calculations for these orders default to net_revenue (no COGS subtracted), overstating margin. `has_cogs` flag available. |
| 9 | Snapshot RETAIL-only | `mart_customer_status_snapshot_monthly` excludes WHOLESALE/PARTNER/STAFF/KOL customers. Status timeline tab only works for RETAIL customers. |
| 10 | No customer-level debt or credit field | Sapo `debt` field exists in `std_customers` source (from stg_sapo_customers) but is not surfaced in `dim_customers`. Cannot show outstanding balance in UI without adding it. |

---

**Status:** DONE
**Summary:** dim_customers is the single serving table for customer profile + all 8 segmentation dimensions + RFM metrics. Fact tables join via customer_key. The monthly snapshot mart enables status timeline. COGS (~35% gap), acquisition_source (always NULL), and point-in-time LTV in snapshot are the main data quality caveats.

**Unresolved questions:**
- Is `customer_code` (Sapo code) needed for UI search? If yes, must add it to std_customers → dim_customers pipeline.
- Should WHOLESALE/PARTNER/STAFF/KOL customers have a status timeline? Currently excluded from mart_customer_status_snapshot_monthly.
- Is the `debt` field from Sapo reliable enough to surface as "outstanding balance"? Currently dropped before mart layer.
- What constitutes a "completed" order for spend aggregation — should CANCELLED orders be excluded? (No filter applied in dim_customers.lifetime_value currently.)
