# Model Catalog

> Complete catalog of dbt models and their dependencies

## Model Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                           STAGING LAYER                               │
├──────────────────────────────────────────────────────────────────────┤
│ src_sapo_orders ──► stg_sapo_orders                                  │
│ src_sapo_customers ──► stg_sapo_customers                            │
│ src_sapo_accounts ──► stg_sapo_accounts                              │
│ src_sapo_targets ──► stg_sapo_targets                                │
└─────────────────────────────┬────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        INTERMEDIATE LAYER                             │
├──────────────────────────────────────────────────────────────────────┤
│ int_orders_enriched (orders + customers + geography)                 │
│ int_order_items (order line items flattened)                         │
└─────────────────────────────┬────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                           MARTS LAYER                                 │
├────────────────────────────────┬─────────────────────────────────────┤
│         DIMENSIONS             │              FACTS                   │
├────────────────────────────────┼─────────────────────────────────────┤
│ dim_date (seed)                │ fact_orders                         │
│ dim_customers                  │ fact_sales                          │
│ dim_products                   │ fact_targets                        │
│ dim_geography (seed)           │                                     │
│ dim_staff                      │                                     │
│ dim_locations                  │                                     │
└────────────────────────────────┴─────────────────────────────────────┘
```

---

## Staging Models

### src_sapo_orders

**Type:** Source Extraction
**Materialization:** Incremental (delete+insert)
**Path:** `models/staging/src_sapo_orders.sql`
**Tags:** source, sapo
**unique_key:** `order_id`

**Purpose:** Extract all JSON fields from raw parquet, tech dedup (entity_id) + biz dedup (order_id). Output is flat — no payload. Serves as single source of truth for all order-related models.

**Key Logic:**
1. Tech dedup: `ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY event_timestamp DESC, ingest_method_priority DESC) = 1`
2. JSON extraction: 50+ scalar fields + 3 nested arrays as text
3. Biz dedup: `QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY event_timestamp DESC, modified_on DESC) = 1`

**Output Columns:**
- entity_id, entity_type, event_timestamp, ingest_method
- order_id, order_code, modified_on
- order_status, financial_status, fulfillment_status, packed_status, received_status
- total_amount, total_discount, tax_amount
- customer_id, source_id, location_id
- assignee_*, account_*, customer_name/phone/email
- shipping_*/billing_* address fields
- note, tags, discount_codes, client_details
- created_on, issued_on, finalized_on, cancelled_on, completed_on
- channel_name, payment_method_id
- **order_line_items_json, payments_json, fulfillments_json** (nested arrays as text for unnest models)

**Consumers:**
- `stg_sapo_orders` (enrichment joins)
- `stg_sapo_order_items` (unnest order_line_items_json)
- `stg_sapo_payments` (unnest payments_json)
- `stg_sapo_fulfillments` (unnest fulfillments_json)

---

### stg_sapo_orders

**Type:** Staging
**Materialization:** View
**Path:** `models/staging/stg_sapo_orders.sql`
**Tags:** staging, orders

**Purpose:** Enrichment joins only. All dedup already done in src_sapo_orders.

**Key Logic:**
- Reads from `ref('src_sapo_orders')` (flat, 1 row per order_id)
- LEFT JOIN ref_order_sources (tag-based mapping)
- LEFT JOIN ref_payment_methods, ref_order_sources, ref_branch_locations

**Output Columns:**
All columns from src_sapo_orders plus:
| Column | Type | Description |
|--------|------|-------------|
| final_source_id | VARCHAR | Resolved source (tag mapping or original) |
| payment_method_name | VARCHAR | From ref_payment_methods |
| source_name | VARCHAR | From ref_order_sources |
| location_name | VARCHAR | From ref_branch_locations |

**Tests:**
- unique: order_id
- not_null: order_id

---

### stg_sapo_customers

**Type:** Staging
**Materialization:** View
**Path:** `models/staging/stg_sapo_customers.sql`
**Tags:** staging, customers, otp

**Output Columns:**
| Column | Type | Description |
|--------|------|-------------|
| customer_id | VARCHAR | Primary key |
| customer_code | VARCHAR | Business reference |
| customer_name | VARCHAR | Full name |
| email | VARCHAR | Email address |
| phone | VARCHAR | Phone number |
| customer_group | VARCHAR | Segment |
| total_spent | DECIMAL | Lifetime value |
| orders_count | INTEGER | Total orders |

---

### stg_sapo_accounts

**Type:** Staging
**Materialization:** View
**Path:** `models/staging/stg_sapo_accounts.sql`
**Tags:** staging, accounts

**Output Columns:**
| Column | Type | Description |
|--------|------|-------------|
| account_id | VARCHAR | Primary key |
| full_name | VARCHAR | Staff name |
| email | VARCHAR | Email |
| role | VARCHAR | Job role |
| status | VARCHAR | active/inactive |

---

## Intermediate Models

### int_orders_enriched

**Type:** Intermediate
**Materialization:** Ephemeral
**Path:** `models/intermediate/int_orders_enriched.sql`

**Purpose:** Enrich orders with customer and geography data.

**Dependencies:**
- stg_sapo_orders
- stg_sapo_customers
- dim_geography

**Output Columns:**
| Column | Type | Source |
|--------|------|--------|
| order_id | VARCHAR | stg_orders |
| order_code | VARCHAR | stg_orders |
| customer_name | VARCHAR | stg_customers |
| customer_group | VARCHAR | stg_customers |
| province | VARCHAR | dim_geography |
| district | VARCHAR | dim_geography |

---

### int_order_items

**Type:** Intermediate
**Materialization:** Ephemeral
**Path:** `models/intermediate/int_order_items.sql`

**Purpose:** Flatten order line items from JSON array.

```sql
SELECT
    o.order_id,
    item.id as line_item_id,
    item.product_id,
    item.variant_id,
    item.quantity,
    item.price,
    item.line_amount
FROM stg_sapo_orders o,
UNNEST(o.order_line_items) as item
```

---

## Dimension Models

### dim_date

**Type:** Dimension
**Materialization:** Seed / Table
**Path:** `seeds/dim_date.csv` or generated

**Columns:**
- date_key (YYYYMMDD)
- date_actual
- year, quarter, month, week_of_year
- day_of_month, day_of_week, day_name
- is_weekend, is_holiday
- fiscal_year, fiscal_quarter

---

### dim_customers

**Type:** Dimension
**Materialization:** External (Parquet)
**Path:** `models/marts/core/dim_customers.sql`
**Tags:** mart, core, olap

**Dependencies:**
- stg_sapo_customers

**Output Columns:**
| Column | Type | Description |
|--------|------|-------------|
| customer_key | VARCHAR | Surrogate key |
| customer_id | VARCHAR | Natural key |
| customer_name | VARCHAR | Full name |
| customer_group | VARCHAR | Segment |
| customer_tier | VARCHAR | Derived tier |
| total_orders | INTEGER | Order count |
| total_spent | DECIMAL | Lifetime value |
| is_active | BOOLEAN | Recently ordered |

---

### dim_products

**Type:** Dimension
**Materialization:** External (Parquet)
**Path:** `models/marts/core/dim_products.sql`
**Tags:** mart, core, olap

---

### dim_geography

**Type:** Dimension
**Materialization:** Seed
**Path:** `seeds/dim_geography.csv`

**Columns:**
- geography_key
- ward_id, ward_name
- district_id, district_name
- province_id, province_name
- region

---

### dim_staff

**Type:** Dimension
**Materialization:** External (Parquet)
**Path:** `models/marts/core/dim_staff.sql`

**Dependencies:**
- stg_sapo_accounts

---

### dim_locations

**Type:** Dimension
**Materialization:** External (Parquet)
**Path:** `models/marts/core/dim_locations.sql`

---

## Fact Models

### fact_orders

**Type:** Fact
**Materialization:** External (Parquet)
**Path:** `models/marts/sales/fact_orders.sql`
**Tags:** mart, sales, olap

**Grain:** One row per order

**Dependencies:**
- int_orders_enriched
- dim_date
- dim_customers
- dim_locations
- dim_staff

**Measures:**
- gross_amount
- discount_amount
- tax_amount
- net_amount
- line_item_count

---

### fact_sales

**Type:** Fact
**Materialization:** External (Parquet)
**Path:** `models/marts/sales/fact_sales.sql`
**Tags:** mart, sales, olap

**Grain:** One row per order line item

**Dependencies:**
- int_order_items
- fact_orders
- dim_products

**Measures:**
- quantity
- unit_price
- line_amount
- discount_amount
- net_amount
- cost_amount
- margin_amount

---

### fact_targets

**Type:** Fact
**Materialization:** External (Parquet)
**Path:** `models/marts/sales/fact_targets.sql`
**Tags:** mart, sales, olap

**Grain:** One row per staff/location/month

**Dependencies:**
- stg_sapo_targets
- dim_staff
- dim_locations
- dim_date

**Measures:**
- target_amount

---

## DAG Visualization

```
source('sapo_raw', 'order')
    │
    ▼
src_sapo_orders (INCREMENTAL — extract + dedup)
    ├──► stg_sapo_order_items ──► std_order_items ──► fact_sales, dim_products
    ├──► stg_sapo_payments ──► std_payments ──► fact_payments
    ├──► stg_sapo_fulfillments ──► std_fulfillments
    │
    ▼
stg_sapo_orders (VIEW — enrichment) ──► std_orders ──► fact_orders, fact_sales

src_sapo_customers ──► stg_sapo_customers ──► std_customers ──► dim_customers

stg_sapo_accounts ──► dim_staff ──┐
                                  ├──► fact_targets
stg_targets ──────────────────────┘
```

---

## Related

- [Deduplication Strategy](./DEDUPLICATION.md)
- [Testing](./TESTING.md)
- [Materialization](./MATERIALIZATION.md)
