# Order-Side OLAP Schema Inventory
**Report:** researcher-01-260529-2223-order-schema-inventory.md  
**Date:** 2026-05-29 | **Scope:** READ-ONLY — no code changes

---

## 1. Order Grain & Keys

| Field | Type | Source | Notes |
|---|---|---|---|
| `order_id` | INTEGER | Sapo | Primary internal PK. Unique in `fact_orders`, `fact_order_economics`, `fact_order_costs` (per cost_type), `fact_order_returns` (per return). |
| `order_code` | VARCHAR | Sapo | Human-readable code (e.g. `HD00123`). What users search by. Used as join key to MISA (`voucher_no = order_code`) and Shopee fees. |
| `item_id` | INTEGER | Sapo | Line-item PK in `fact_sales` (grain = order × item). |
| `return_id` | INTEGER | Sapo | PK in `fact_order_returns` (grain = 1 per return event). |
| `payment_key` | VARCHAR (surrogate) | computed | PK in `fact_payments`. |

**Search strategy:** User will search by `order_code` (human-readable). Look up `order_id` via `fact_orders.order_code` then join all other facts on either `order_id` or `order_code`.

---

## 2. Per-Table Column Inventory

### 2a. `fact_orders` — Order header (grain: 1 row per order)

| Column | Type | Computed? | Meaning |
|---|---|---|---|
| `order_id` | INT | raw | Sapo PK |
| `order_code` | VARCHAR | raw | Human-readable order code |
| `customer_key` | VARCHAR | dim FK | → dim_customers_base |
| `shipping_geography_key` | VARCHAR | computed | Surrogate of shipping province/district/ward/country |
| `billing_geography_key` | VARCHAR | computed | Surrogate of billing province/district/ward/country |
| `shipping_address` | VARCHAR | computed | Concatenated shipping address string |
| `billing_address` | VARCHAR | computed | Concatenated billing address string |
| `promotion_key` | VARCHAR | computed | FK → dim_promotions (first promo code only) |
| `branch_location_key` | VARCHAR | dim FK | → dim_branch_location (warehouse/store) |
| `channel_key` | VARCHAR | computed | FK → dim_channels (source_id + location_id logic) |
| `seller_staff_key` | VARCHAR | dim FK | → dim_staff; Sapo assignee — primary for attribution |
| `creator_staff_key` | VARCHAR | dim FK | → dim_staff; Sapo account/creator — fallback only |
| `team_key` | VARCHAR | computed | SCD2 lookup via seller email → stg_team_members |
| `status_key` | VARCHAR | dim FK | → dim_order_status |
| `date_key` | INT | computed | YYYYMMDD from `created_at` (ICT timezone) |
| `time_key` | INT | computed | HHMM integer from `created_at` |
| `status` | VARCHAR | raw | OPEN / COMPLETED / CANCELLED / ARCHIVED / DRAFT |
| `payment_status` | VARCHAR | raw | PAID / PARTIALLY_PAID / REFUNDED / VOIDED / PENDING / UNPAID |
| `fulfillment_status` | VARCHAR | computed | COMPLETED / SHIPPED_PAID / SHIPPED_COD / PAID_PROCESSING / RETURNED / IN_PROGRESS / CANCELLED |
| `gross_revenue` | DECIMAL | **COMPUTED** | net_revenue + discount_amount (price × qty before discount) |
| `discount_amount` | DECIMAL | raw | Total discount off the order |
| `net_revenue` | DECIMAL | raw | Sapo `$.total` — after discount, before VAT |
| `tax_amount` | DECIMAL | raw | VAT (8% or 10%) |
| `total_collected` | DECIMAL | **COMPUTED** | net_revenue + tax_amount |
| `first_shipped_at` | TIMESTAMPTZ | raw | MIN(shipped_at) from std_fulfillments |
| `time_to_complete_hours` | INT | **COMPUTED** | DIFF hours: created_at → completed_at |
| `client_details` | JSON | raw | IP, User Agent from Sapo |
| `discount_codes` | JSON | raw | Array of promo code objects |
| `max_discount_rate` | DECIMAL | **COMPUTED** | Max discount_rate (0-100) across discount_items |
| `primary_discount_nature` | VARCHAR | **COMPUTED** | Semantic class of biggest-amount discount (see below) |
| `order_timestamp` | TIMESTAMPTZ | raw | created_at alias |
| `updated_at` | TIMESTAMPTZ | raw | Last update from Sapo |

**discount_nature values:** `voucher_promotional`, `bundle`, `sampling_gift`, `wholesale_explicit`, `overseas`, `campaign`, `employee_internal`, `negotiated_micro`, `negotiated_standard`, `negotiated_deep`

---

### 2b. `fact_order_economics` — Per-order P&L (grain: 1 row per order)

Inherits keys from `fact_orders` (joined on `order_id`/`order_code`).

| Column | Type | Computed? | Meaning |
|---|---|---|---|
| `order_id` | INT | raw | FK to fact_orders |
| `order_code` | VARCHAR | raw | Join key to MISA + Shopee |
| `channel_key` | VARCHAR | raw | Inherited |
| `date_key` | INT | raw | Inherited |
| `status` | VARCHAR | raw | Inherited |
| `gross_revenue` | DECIMAL | COMPUTED | Inherited |
| `discount_amount` | DECIMAL | raw | Inherited |
| `net_revenue` | DECIMAL | raw | Inherited |
| `tax_amount` | DECIMAL | raw | Inherited |
| `total_collected` | DECIMAL | COMPUTED | Inherited |
| `cogs_amount` | DECIMAL | **COMPUTED** | MISA invoice COGS (NULL if no MISA match, ~35% orders) |
| `misa_line_count` | INT | raw | Count of MISA invoice lines matched |
| `has_cogs` | BOOLEAN | **COMPUTED** | TRUE if MISA data exists |
| `gross_profit` | DECIMAL | **COMPUTED** | net_revenue − cogs_amount (0 COGS if NULL) |
| `gross_margin_pct` | DOUBLE | **COMPUTED** | gross_profit / net_revenue |
| `shopee_platform_fees` | DECIMAL | raw | Total Shopee fees (NULL non-Shopee) |
| `shopee_infra_fee` | DECIMAL | raw | Shopee infrastructure fee |
| `shopee_voucher_xtra_fee` | DECIMAL | raw | Shopee Voucher Xtra fee |
| `shopee_taxes` | DECIMAL | raw | Shopee VAT + personal income tax |
| `shopee_net_settlement` | DECIMAL | raw | Actual Shopee payout |
| `has_platform_fees` | BOOLEAN | **COMPUTED** | TRUE if Shopee fee data exists |
| `channel_net_profit` | DECIMAL | **COMPUTED** | net_revenue − COGS − all Shopee fees |
| `channel_net_margin_pct` | DOUBLE | **COMPUTED** | channel_net_profit / net_revenue |
| `cod_amount` | DECIMAL | raw | COD value from primary shipment |
| `carrier_id` | VARCHAR | raw | Carrier (GHTK/J&T/GHN/VTP…) from primary shipment |
| `return_amount` | DECIMAL | **COMPUTED** | SUM(refund_amount) from fact_order_returns (reference only — not subtracted from profit) |
| `return_count` | INT | **COMPUTED** | Count of return events |
| `has_returns` | BOOLEAN | **COMPUTED** | return_count > 0 |

**Critical note:** `channel_net_profit` does NOT subtract `return_amount`. Returns are P&L-recognized at return date in `fact_order_returns`. `return_amount` here is for reference/display only.

---

### 2c. `fact_order_costs` — Cost ledger (grain: 1 row per order × cost_type)

One order → multiple rows (one per cost line).

| Column | Type | Computed? | Meaning |
|---|---|---|---|
| `order_id` | INT | raw | FK to fact_orders |
| `order_code` | VARCHAR | raw | — |
| `cost_type` | VARCHAR | **COMPUTED** | Granular label (see below) |
| `cost_category` | VARCHAR | **COMPUTED** | COGS / PLATFORM_FEE / TAX / SHIPPING / DISCOUNT |
| `amount` | DECIMAL(18,2) | **COMPUTED** | Always positive; sign from category |
| `discount_rate` | DECIMAL | raw | Only for DISCOUNT rows |
| `discount_nature` | VARCHAR | **COMPUTED** | Only for DISCOUNT rows |
| `source_system` | VARCHAR | raw | misa / shopee / sapo |
| `source_record` | VARCHAR | raw | Traceability: voucher_no / order_code / discount reason |
| `fee_source` | VARCHAR | raw | actual / estimated |
| `date_key` | INT | raw | Inherited from fact_orders |
| `channel_key` | VARCHAR | raw | Inherited from fact_orders |

**cost_type values by category:**
- COGS: `cogs`
- PLATFORM_FEE: `platform_service`, `platform_payment`, `platform_fixed`, `platform_affiliate`, `platform_piship`, `platform_infra`, `platform_voucher_xtra`
- TAX: `tax_vat`, `tax_pit`
- SHIPPING: `shipping_platform`
- DISCOUNT: `discount_seller_voucher`, `discount_bundle`, `discount_seller`, `discount_manual`

---

### 2d. `fact_order_returns` — Return events (grain: 1 row per return event)

| Column | Type | Computed? | Meaning |
|---|---|---|---|
| `return_id` | INT | raw | Sapo return PK |
| `order_id` | INT | raw | Link back to original order |
| `order_code` | VARCHAR | raw | — |
| `return_timestamp` | TIMESTAMPTZ | raw | issued_at COALESCE created_at |
| `return_date` | DATE | **COMPUTED** | DATE(return_timestamp) in ICT |
| `refund_amount` | DECIMAL | raw | Refund value from Sapo |
| `return_quantity` | INT | raw | Units returned |
| `return_status` | VARCHAR | raw | Sapo return status |
| `refund_status` | VARCHAR | raw | Sapo refund status |
| `return_reason` | VARCHAR | raw | reason / note from Sapo |
| `channel_key` | VARCHAR | raw | Inherited from fact_orders (NULL for legacy orders) |
| `date_key` | INT | **COMPUTED** | YYYYMMDD from return_timestamp (ICT) |

---

### 2e. `fact_payments` — Payment transactions (grain: 1 row per payment attempt)

| Column | Type | Computed? | Meaning |
|---|---|---|---|
| `payment_key` | VARCHAR (surrogate) | COMPUTED | PK |
| `order_id` | INT | raw | FK to fact_orders |
| `payment_method_key` | VARCHAR (surrogate) | COMPUTED | FK → dim_payment_methods |
| `amount` | DECIMAL | raw | Transaction amount |
| `status` | VARCHAR | raw | paid / pending / etc. |
| `payment_timestamp` | TIMESTAMPTZ | raw | Payment created_at |
| `paid_on` | TIMESTAMPTZ | raw | Payment paid_at (completion time) |

---

### 2f. `fact_sales` — Line items (grain: 1 row per order × item)

| Column | Type | Computed? | Meaning |
|---|---|---|---|
| `product_key` | VARCHAR (surrogate) | COMPUTED | FK → dim_products |
| `product_type_key` | VARCHAR (surrogate) | COMPUTED | FK → dim_product_types |
| `customer_key` | VARCHAR (surrogate) | COMPUTED | FK → dim_customers_base |
| `branch_location_key` | VARCHAR (surrogate) | COMPUTED | FK → dim_branch_location |
| `channel_key` | VARCHAR (surrogate) | COMPUTED | FK → dim_channels |
| `seller_staff_key` | VARCHAR (surrogate) | COMPUTED | FK → dim_staff (assignee) |
| `creator_staff_key` | VARCHAR (surrogate) | COMPUTED | FK → dim_staff (creator) |
| `team_key` | VARCHAR (surrogate) | COMPUTED | FK → dim_teams |
| `status_key` | VARCHAR (surrogate) | COMPUTED | FK → dim_order_status |
| `date_key` | INT | COMPUTED | YYYYMMDD from order created_at (ICT) |
| `time_key` | INT | COMPUTED | HHMM from order created_at |
| `shipping_geography_key` | VARCHAR (surrogate) | COMPUTED | FK → dim_geography |
| `billing_geography_key` | VARCHAR (surrogate) | COMPUTED | FK → dim_geography |
| `order_id` | INT | raw | Degenerate key — links to fact_orders |
| `item_id` | INT | raw | Line-item Sapo ID |
| `quantity` | INT | raw | Units sold |
| `revenue` | DECIMAL | raw | line_amount = quantity × unit_price |
| `discount_amount` | DECIMAL | raw | Direct per-line discount |
| `distributed_discount_amount` | DECIMAL | raw | Order-level discount pro-rated to line |
| `weight_grams` | DECIMAL | raw | Item weight |
| `sol_timestamp` | TIMESTAMPTZ | raw | Order created_at |
| `updated_at` | TIMESTAMPTZ | raw | — |

**Note:** Per-line COGS/margin is NOT in `fact_sales`. Margin is only order-level in `fact_order_economics`. Per-line economics exist only in `mart_sku_economics_monthly` (monthly grain).

---

### 2g. `fact_us_shipment_economics` — US CrossBorder revenue (grain: 1 row per US order)

| Column | Type | Computed? | Meaning |
|---|---|---|---|
| `order_id` | INT | raw | FK to fact_orders |
| `order_code` | VARCHAR | raw | — |
| `channel_key` | VARCHAR | raw | — |
| `date_key` | INT | raw | — |
| `total_us_revenue_excl_vat` | DECIMAL | **COMPUTED** | SUM(qty × us_price_excl_vat) — actual US deal revenue |
| `total_us_revenue_incl_vat` | DECIMAL | **COMPUTED** | SUM(qty × us_price_incl_vat) |
| `line_item_count` | INT | COMPUTED | Count of line items |
| `has_unpriced_sku` | BOOLEAN | COMPUTED | TRUE if any SKU missing from US price list |
| `unpriced_sku_count` | INT | COMPUTED | Count of unpriced lines |

**Critical:** For US orders, `fact_orders.net_revenue = 0` (Sapo records US as 0). Use `fact_us_shipment_economics` for all US revenue reporting.

---

### 2h. Key Dimensions (summary)

| Dim Table | Grain | PK | Key Fields |
|---|---|---|---|
| `dim_customers` | 1 per customer | `customer_key` | `customer_id`, `full_name`, `email`, `phone`, `province/district/ward`, `customer_type`, `value_group`, `lifecycle_stage`, `channel_preference`, `product_affinity`, `payment_behavior`, `geo_region`, `lifetime_value`, `total_orders_count`, `first_order_date`, `last_order_date`, `recency_days`, `loyalty_point`, `dob`, `sex` |
| `dim_products` | 1 per variant | `product_key` | `product_id`, `variant_id`, `sku`, `barcode`, `product_name`, `variant_name`, `brand_name`, `brand_code`, `category`, `unit`, `weight_grams`, `is_packsize`, `packsize_root_sku`, `is_active_status`, `misa_join_key` |
| `dim_channels` | 1 per source+location | `channel_key` | `channel_name`, `channel_code`, `channel_category`, `channel_format`, `platform`, `channel_brand`, `market`, `is_sales_channel` |
| `dim_staff` | 1 per account | `staff_key` | `staff_id`, `full_name`, `email`, `phone_number` |
| `dim_order_status` | static 5 rows | `status_key` | `status_code`: OPEN/COMPLETED/CANCELLED/ARCHIVED/DRAFT |
| `dim_payment_methods` | 1 per method | `payment_method_key` | `payment_method_id`, `payment_method_name`, `payment_method_type` |
| `dim_promotions` | 1 per promo code | `promotion_key` | `promotion_code`, `discount_amount`, `promotion_type` |
| `dim_geography` | 1 per province/district/ward/country | `geography_key` | `province`, `district`, `ward`, `country` |
| `dim_branch_location` | 1 per warehouse/store | `branch_location_key` | `branch_location_id`, `branch_location_name`, `branch_location_code` |
| `dim_date` | 1 per day 2010–2030 | `date_key` (YYYYMMDD INT) | `date_actual`, `year`, `month`, `quarter`, `day_of_week`, `is_weekend` |
| `dim_time` | 1 per minute | `time_key` (HHMM INT) | `hour_24`, `is_business_hour`, `is_peak_hour`, `day_period` |

---

## 3. Join Map — Single Order Full View

```
fact_orders (anchor, join on order_id)
├── → fact_order_economics ON order_id           (1:1 — P&L summary)
├── → fact_order_costs ON order_id               (1:N — cost ledger rows)
├── → fact_order_returns ON order_code           (1:N — return events)
├── → fact_payments ON order_id                  (1:N — payment transactions)
├── → fact_sales ON order_id                     (1:N — line items)
│       └── → dim_products ON product_key        (1:1 — SKU detail)
├── → fact_us_shipment_economics ON order_id     (1:1, US orders only)
│
├── → dim_channels ON channel_key
├── → dim_customers ON customer_key
├── → dim_staff ON seller_staff_key              (seller)
├── → dim_staff ON creator_staff_key             (creator)
├── → dim_order_status ON status_key
├── → dim_branch_location ON branch_location_key
├── → dim_promotions ON promotion_key
├── → dim_geography ON shipping_geography_key
├── → dim_geography ON billing_geography_key
├── → dim_date ON date_key
└── → dim_time ON time_key

fact_payments → dim_payment_methods ON payment_method_key
```

**Assembly SQL sketch:**
```sql
SELECT
    fo.*,                           -- header + revenue
    foe.cogs_amount,
    foe.gross_profit,
    foe.gross_margin_pct,
    foe.channel_net_profit,
    foe.channel_net_margin_pct,
    foe.carrier_id,
    foe.cod_amount,
    foe.return_amount,
    foe.has_returns
FROM fact_orders fo
LEFT JOIN fact_order_economics foe ON fo.order_id = foe.order_id
-- then left join dims, payments, returns, sales as needed per UI tab
WHERE fo.order_code = '<user_input>'
```

---

## 4. Line-Item / SKU Detail

**Table:** `fact_sales` (grain: order × item)  
**Join key:** `fact_sales.order_id = fact_orders.order_id`  
**Product detail:** `fact_sales.product_key → dim_products.product_key`

Per-line fields available:

| Field | Source | Notes |
|---|---|---|
| `item_id` | fact_sales | Sapo line item ID |
| `sku` | dim_products | via product_key join |
| `barcode` | dim_products | — |
| `product_name` | dim_products | — |
| `variant_name` | dim_products | e.g. size/color variant |
| `brand_name` | dim_products | normalized brand |
| `category` | dim_products | product category |
| `unit` | dim_products | selling unit |
| `quantity` | fact_sales | units sold |
| `revenue` | fact_sales | line_amount = qty × unit_price |
| `discount_amount` | fact_sales | per-line discount |
| `distributed_discount_amount` | fact_sales | order-level discount allocated to line |
| `weight_grams` | fact_sales | item weight |

**What is NOT available at line level:** COGS per line, margin per line. These exist only at order level (fact_order_economics) or monthly SKU level (mart_sku_economics_monthly).

**US CrossBorder line-level:** `int_us_shipment_line_prices` has per-line `us_price_excl_vat`, `us_price_incl_vat`, `line_revenue_excl_vat`, `line_revenue_incl_vat` — but this is an intermediate model, not surfaced as a mart. Accessible via `fact_us_shipment_economics` aggregated to order level only.

---

## 5. Insight Catalog for ONE Order

### Tab: Financial Summary
- Gross revenue (before discount)
- Discount amount + discount nature classification
- Net revenue (after discount, before VAT)
- VAT amount
- Total collected from customer
- COGS (from MISA, NULL if no match)
- Gross profit + gross margin %
- Platform fees breakdown (Shopee only: service/payment/fixed/affiliate/piship/infra/voucher_xtra)
- Platform taxes (VAT + PIT on Shopee)
- Shopee net settlement amount
- Channel net profit + channel net margin %
- COD amount (if COD order)
- Return amount (reference; not restated in P&L)
- has_cogs / has_platform_fees / has_returns flags

### Tab: Line Items / SKUs
- Per-SKU: item_id, sku, barcode, product_name, variant_name, brand, category, unit
- Quantity, unit price (revenue / qty), line revenue
- Per-line discount + distributed discount
- Weight
- US price (excl/incl VAT) if US CrossBorder order
- Subtotal check: SUM(line revenue) should equal net_revenue

### Tab: Cost Ledger (detail)
- All rows from `fact_order_costs` for this order
- Grouped by cost_category: COGS / PLATFORM_FEE / TAX / SHIPPING / DISCOUNT
- Source traceability: source_system + source_record
- Discount nature per discount row

### Tab: Payments
- All rows from `fact_payments`
- Payment method name/type (via dim_payment_methods)
- Amount, status, payment_timestamp, paid_on
- Summary: total paid, payment method mix, COD vs prepaid

### Tab: Fulfillment & Shipping
- Order status + payment_status + fulfillment_status
- first_shipped_at (from fact_orders)
- Carrier ID, COD amount (from fact_order_economics)
- Shipping address (province/district/ward/country)
- Shipping geography region
- time_to_complete_hours
- Fulfillment events (requires std_fulfillments — not a mart; intermediate only)

### Tab: Returns
- Return events from `fact_order_returns`
- Return date (ICT), refund amount, quantity returned
- Return status, refund status, return reason
- Total return count + total refund amount

### Tab: Channel & Source
- Channel name, code, category, format, platform
- Channel brand (which brand's channel)
- Market: Domestic / Export
- is_sales_channel flag
- Promotion code (dim_promotions: code, discount_amount, type)
- discount_codes JSON (all promo codes on order)
- max_discount_rate + primary_discount_nature

### Tab: Staff & Team
- Seller (assignee): full_name, email — primary for attribution
- Creator: full_name, email — who placed the Sapo order
- Team: team attribution via SCD2 lookup (team as-of order date)
- Branch/warehouse: branch_location_name, code

### Tab: Customer
- Full name, email, phone
- Address (province/district/ward)
- customer_type: RETAIL / WHOLESALE / PARTNER / STAFF / KOL
- value_group: VALUE_VIP / VALUE_GOLD / VALUE_SILVER / VALUE_BRONZE
- lifecycle_stage: LIFECYCLE_NEW / LIFECYCLE_ACTIVE / LIFECYCLE_AT_RISK / LIFECYCLE_CHURNED
- channel_preference, product_affinity, payment_behavior, geo_region
- lifetime_value, total_orders_count, first_order_date, last_order_date, recency_days
- loyalty_point, dob, sex, customer_group (raw Sapo)

### Tab: Timeline / Dates
- order_timestamp (created_at ICT)
- date_key → dim_date: year, month, quarter, day_of_week, is_weekend
- time_key → dim_time: hour_24, day_period, is_business_hour, is_peak_hour
- first_shipped_at
- time_to_complete_hours
- Return timestamps (if any)
- Payment paid_on timestamps

---

## 6. Gaps & Caveats

| Issue | Detail |
|---|---|
| **US orders: net_revenue = 0** | Sapo records US CrossBorder revenue as 0. Must use `fact_us_shipment_economics` for US revenue. A UI showing "revenue" from `fact_orders` will show $0 for all US orders. |
| **COGS missing ~35% of orders** | `has_cogs = FALSE` for orders with no MISA invoice match. `gross_profit` defaults to `net_revenue` when COGS NULL. UI must clearly signal when margin is unverified. |
| **date_key is ICT, not UTC** | `fact_orders.date_key` = `strftime(created_at, '%Y%m%d')` where `created_at` is TIMESTAMPTZ stored UTC but displayed/truncated in pipeline as ICT (Asia/Ho_Chi_Minh, UTC+7). Orders placed 0:00–7:00 UTC may appear on the previous calendar day if truncated in UTC. Per memory: `TimeZone=Asia/Ho_Chi_Minh` in profiles.yml. |
| **Returns not restated in order P&L** | `fact_order_economics.return_amount` is display-only. The actual P&L impact of a return is recognized on the return date in `fact_order_returns`, not on the original order. |
| **No per-line COGS** | MISA COGS available at order level only (aggregated from invoice lines by voucher_no). Cannot show per-SKU margin within an order from warehouse data alone. |
| **promotion_key = first promo code only** | Orders with multiple promo codes: `fact_orders.promotion_key` maps to first code in JSON array. Full list in `discount_codes` JSON field. |
| **Shopee fees: only Shopee** | `has_platform_fees` is Shopee-only today. Lazada/TikTok fee data not yet integrated. Non-Shopee orders have NULL Shopee columns. |
| **Fulfillment detail not a mart** | `std_fulfillments` is a staging view (not materialized mart). Full shipment history (all shipment legs, tracking codes) requires joining `std_fulfillments` directly — not part of the OLAP serving layer. |
| **US line-level prices not a mart** | `int_us_shipment_line_prices` is intermediate only. Line-level US revenue only accessible by querying intermediate models, not the serving DuckDB mart layer. |
| **team_key SCD2 complexity** | Team attribution uses SCD2 by effective_from/effective_to date. Re-querying current team membership may differ from team at order date. Use `fact_orders.team_key` (locked at order time) not a live team lookup. |
| **dim_customers has circular dep** | `dim_customers` uses `dim_geography` which references `dim_customers`. Materialized incrementally. `dim_customers_base` (no circular dep) is the FK used in facts. |
| **acquisition_source always NULL** | `dim_customers.acquisition_source` is CAST(NULL AS VARCHAR) — pending Sapo implementation. |

---

**Status:** DONE  
**Summary:** Full schema catalogued from dbt SQL + schema.yml. All 7 order-related facts + 11 dims documented with grain, keys, column list, and computed/raw flag. Join map + insight catalog assembled for web app UI design.

**Unresolved questions:**
1. Does the serving `olap.duckdb` expose `std_fulfillments` and `int_us_shipment_line_prices` as views, or are they staging-only? If not exposed, full shipment history and US line-level detail are unavailable in read-only serving layer.
2. Is there a `fact_sales`-level COGS join in any intermediate that wasn't surfaced here (e.g., via `int_misa_sales_lines` × `dim_products.misa_join_key`)? `mart_sku_economics_monthly` does this at monthly grain — unclear if a per-order per-line COGS is feasible.
3. For Shopee orders: what is the relationship between `fact_orders.order_id` and Shopee's own order ID? Is there a native Shopee order ID stored anywhere for cross-referencing Shopee seller center?
