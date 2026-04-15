# Data Dictionary

> Schema reference for all entities, models, and business metrics

## Table of Contents

1. [Source Entities](#source-entities)
2. [Staging Models](#staging-models)
3. [Dimension Tables](#dimension-tables)
4. [Fact Tables](#fact-tables)
5. [Business Metrics](#business-metrics)
6. [Naming Conventions](#naming-conventions)

---

## Source Entities

> **Complete reference:** See [`docs/architecture/source-entities/`](./source-entities/index.md) for detailed documentation of all raw entities, envelope schema, and payload structures.

This section provides quick reference tables for the most commonly used entities. For comprehensive payload schemas, see the modular source-entities documentation.

### Orders (`sapo_raw.order`)

The core transactional entity representing customer purchases. Includes line items, fulfillments, payments, and returns.

| Column            | Type      | Description             | Example                     |
| ----------------- | --------- | ----------------------- | --------------------------- |
| `entity_id`       | VARCHAR   | Unique order identifier | `"12345678"`                |
| `entity_type`     | VARCHAR   | Always `"order"`        | `"order"`                   |
| `ingest_method`   | VARCHAR   | Data source             | `"history_log"`, `"text"`, `"webhook"` |
| `event_type`      | VARCHAR   | Event action            | `"create"`, `"update"`      |
| `event_timestamp` | TIMESTAMP | When event occurred     | `2026-01-28T10:30:00Z`      |
| `payload`         | JSON      | Full order snapshot     | See below & reference docs  |

**Payload Structure (Abbreviated Example):**

```json
{
  "id": 12345678,
  "code": "SON000001",
  "tenant_id": 5006,
  "status": "finalized",
  "fulfillment_status": "unshipped",
  "payment_status": "paid",
  "packed_status": "packed",
  "return_status": "none",
  "process_status": "processing",
  "channel": "web",
  "created_on": "2026-01-28T10:00:00Z",
  "modified_on": "2026-01-28T10:30:00Z",
  "finalized_on": "2026-01-28T10:10:00Z",
  "completed_on": null,
  "cancelled_on": null,
  "customer_id": 9876543,
  "location_id": 12345,
  "account_id": 1001,
  "assignee_id": 1002,
  "source_id": 1,
  "source_name": "web",
  "total": 500000,
  "total_discount": 50000,
  "total_tax": 0,
  "delivery_fee": 25000,
  "note": "Fragile item",
  "tags": ["urgent"],
  "order_line_items": [
    {
      "id": 111,
      "product_id": 222,
      "variant_id": 333,
      "quantity": 2,
      "price": 250000,
      "line_amount": 500000,
      "discount_amount": 50000
    }
  ],
  "fulfillments": [{...}],
  "payments": [{...}],
  "promotion_redemptions": [{...}],
  "shipping_address": {
    "address1": "123 Main St",
    "ward_name": "Ward 1",
    "district_name": "District 1",
    "city": "Ho Chi Minh"
  }
}
```

**Complete Payload Field Reference:**

See [`docs/architecture/raw-data-sources.md § Order`](./raw-data-sources.md#order-sapo_raworder) for exhaustive payload schema including all status fields, timestamps, and nested line items, fulfillments, and payments.

**Status Values & Transitions:**

- `status`: `draft` → `finalized` → `completed` OR `cancelled`
- `fulfillment_status`: `unshipped` → `partial` → `fulfilled`
- `payment_status`: `pending` → `partial` → `paid` → (optionally) `refunded`
- `packed_status`, `return_status`, `received_status`: Additional tracking dimensions
- Cancellation: Sets `status=cancelled` and `cancelled_on` timestamp

---

### Customers (`sapo_raw.customer`)

Customer master data. Addresses are nested within customer entity; address changes trigger customer entity updates in history log.

| Column            | Type      | Description                | Example                |
| ----------------- | --------- | -------------------------- | ---------------------- |
| `entity_id`       | VARCHAR   | Unique customer identifier | `"9876543"`            |
| `entity_type`     | VARCHAR   | Always `"customer"`        | `"customer"`           |
| `ingest_method`   | VARCHAR   | Data source                | `"history_log"`, `"text"` |
| `event_timestamp` | TIMESTAMP | When event occurred        | `2026-01-28T09:00:00Z` |
| `payload`         | JSON      | Full customer snapshot     | See below & reference docs |

**Payload Structure:**

```json
{
  "id": 9876543,
  "code": "KH000001",
  "name": "Nguyen Van A",
  "email": "customer@example.com",
  "phone": "0901234567",
  "gender": "male",
  "birthday": "1990-01-15",
  "customer_group_name": "VIP",
  "tags": ["loyal", "premium"],
  "total_spent": 5000000,
  "orders_count": 10,
  "created_on": "2025-01-01T00:00:00Z",
  "modified_on": "2026-01-28T09:00:00Z",
  "addresses": [
    {
      "id": 111,
      "address1": "123 Main St",
      "ward_name": "Ward 1",
      "district_name": "District 1",
      "city": "Ho Chi Minh",
      "is_default": true
    }
  ]
}
```

**Complete Payload Field Reference:**

See [`docs/architecture/raw-data-sources.md § Customer`](./raw-data-sources.md#customer-sapo_rawcustomer) for exhaustive payload schema including address structures and customer group semantics.

---

### Accounts (`sapo_raw.account`)

Staff/employee accounts for sales attribution and order assignment.

| Column        | Type    | Description               | Example     |
| ------------- | ------- | ------------------------- | ----------- |
| `entity_id`   | VARCHAR | Unique account identifier | `"1001"`    |
| `entity_type` | VARCHAR | Always `"account"`        | `"account"` |
| `ingest_method` | VARCHAR | Data source             | `"history_log"`, `"text"` |
| `event_timestamp` | TIMESTAMP | When account changed  | `2026-01-28T10:00:00Z` |
| `payload`     | JSON    | Full account snapshot     | See below & reference docs |

**Payload Structure:**

```json
{
  "id": 1001,
  "email": "staff@company.com",
  "first_name": "Van",
  "last_name": "Nguyen",
  "full_name": "Nguyen Van B",
  "role": "sales",
  "status": "active",
  "locations": [12345, 12346]
}
```

**Role Values:** `admin`, `sales`, `warehouse`, `customer_service`, etc.

**Status Values:** `active`, `inactive`, `suspended`

**Complete Payload Field Reference:**

See [`docs/architecture/raw-data-sources.md § Account`](./raw-data-sources.md#account-sapo_rawaccount) for exhaustive payload schema.

---

### Fulfillments (`sapo_raw.fulfillment`) — NEW

Packing slips (kho đóng gói) from History Log pipeline. Each fulfillment represents goods prepared for a single shipment; one order may spawn multiple fulfillments.

| Column            | Type      | Description             | Example                     |
| ----------------- | --------- | ----------------------- | --------------------------- |
| `entity_id`       | VARCHAR   | Unique fulfillment ID   | `"87654321"`                |
| `entity_type`     | VARCHAR   | Always `"fulfillment"`  | `"fulfillment"`             |
| `ingest_method`   | VARCHAR   | Always `"history_log"`  | `"history_log"`             |
| `event_timestamp` | TIMESTAMP | When fulfillment changed| `2026-01-28T10:30:00Z`      |
| `payload`         | JSON      | Full fulfillment snapshot | See below                 |

**Payload Structure:**

```json
{
  "id": 87654321,
  "code": "KH000001",
  "order_id": 12345678,
  "stock_location_id": 456,
  "status": "shipped",
  "delivery_type": "courier",
  "total": 475000,
  "total_discount": 50000,
  "total_tax": 0,
  "packed_on": "2026-01-28T10:15:00Z",
  "shipped_on": "2026-01-28T10:25:00Z",
  "fulfillment_line_items": [
    {
      "id": 111,
      "product_id": 222,
      "variant_id": 333,
      "quantity": 2,
      "line_amount": 475000
    }
  ],
  "shipment": {
    "id": 555,
    "delivery_service_provider": "GHN",
    "tracking_code": "GHN123456",
    "freight_amount": 30000,
    "estimated_delivery_time": "2026-01-30T23:59:59Z"
  }
}
```

**Status Values:** `fulfilled`, `packed`, `shipped`, `cancelled`

**Relationships:** FK `order_id` → `order`, FK `stock_location_id` → warehouse locations

See [`docs/architecture/raw-data-sources.md § Fulfillments`](./raw-data-sources.md#fulfillment-sapo_rawfulfillment) for complete payload schema and nested structures.

---

### Purchase Orders (`sapo_raw.purchase_order`) — NEW

Supplier purchase orders (nhập hàng) from History Log pipeline. Track goods received from suppliers.

| Column            | Type      | Description             | Example                     |
| ----------------- | --------- | ----------------------- | --------------------------- |
| `entity_id`       | VARCHAR   | Unique PO identifier    | `"11111111"`                |
| `entity_type`     | VARCHAR   | Always `"purchase_order"` | `"purchase_order"`          |
| `ingest_method`   | VARCHAR   | Always `"history_log"`  | `"history_log"`             |
| `event_timestamp` | TIMESTAMP | When PO changed         | `2026-01-28T10:30:00Z`      |
| `payload`         | JSON      | Full PO snapshot        | See reference               |

**Status Values:** Typical: `draft`, `confirmed`, `received`, `cancelled`

**Current State:** 0 rows (awaiting purchase order events in Sapo)

**API Endpoint:** `/admin/purchase_orders/{id}.json`

See [`docs/architecture/raw-data-sources.md § Purchase Orders`](./raw-data-sources.md#purchase_order-sapo_rawpurchase_order) for expected schema.

---

### Order Returns (`sapo_raw.order_return`) — NEW

Return/refund transactions (hoàn/trả hàng) from History Log pipeline. Track customer returns and refunds.

| Column            | Type      | Description             | Example                     |
| ----------------- | --------- | ----------------------- | --------------------------- |
| `entity_id`       | VARCHAR   | Unique return ID        | `"22222222"`                |
| `entity_type`     | VARCHAR   | Always `"order_return"` | `"order_return"`            |
| `ingest_method`   | VARCHAR   | Always `"history_log"`  | `"history_log"`             |
| `event_timestamp` | TIMESTAMP | When return changed     | `2026-01-28T10:30:00Z`      |
| `payload`         | JSON      | Full return snapshot    | See reference               |

**Status Values:** Typical: `pending`, `approved`, `received`, `rejected`, `refunded`

**Current State:** 0 rows (awaiting return events in Sapo)

**API Endpoint:** `/admin/order_returns/{id}.json`

See [`docs/architecture/raw-data-sources.md § Order Returns`](./raw-data-sources.md#order_return-sapo_raworder_return) for expected schema.

---

### Stock Adjustments (`sapo_raw.stock_adjustment`) — NEW

Inventory adjustments (kiểm kho, điều chỉnh tồn kho) from History Log pipeline. Track manual stock corrections, physical inventory counts, and write-offs.

| Column            | Type      | Description             | Example                     |
| ----------------- | --------- | ----------------------- | --------------------------- |
| `entity_id`       | VARCHAR   | Unique adjustment ID    | `"33333333"`                |
| `entity_type`     | VARCHAR   | Always `"stock_adjustment"` | `"stock_adjustment"`    |
| `ingest_method`   | VARCHAR   | Always `"history_log"`  | `"history_log"`             |
| `event_timestamp` | TIMESTAMP | When adjustment occurred| `2026-01-28T10:30:00Z`      |
| `payload`         | JSON      | Full adjustment snapshot| See reference               |

**Reason Types:** `inventory_count` (kiểm kho), `write_off` (xóa tồn), `damage`, `theft`, `correction`

**Current State:** 0 rows (awaiting stock adjustments in Sapo)

**API Endpoint:** `/admin/stock_adjustments/{id}.json`

See [`docs/architecture/raw-data-sources.md § Stock Adjustments`](./raw-data-sources.md#stock_adjustment-sapo_rawstock_adjustment) for expected schema.

---

### Customer Groups (`sapo_raw.customer_group`) — NEW

Customer segmentation groups (nhóm khách hàng) from History Log pipeline. Used for tiering, pricing, and targeting.

| Column            | Type      | Description             | Example                     |
| ----------------- | --------- | ----------------------- | --------------------------- |
| `entity_id`       | VARCHAR   | Unique group ID         | `"44444444"`                |
| `entity_type`     | VARCHAR   | Always `"customer_group"` | `"customer_group"`        |
| `ingest_method`   | VARCHAR   | Always `"history_log"`  | `"history_log"`             |
| `event_timestamp` | TIMESTAMP | When group changed      | `2026-01-28T10:30:00Z`      |
| `payload`         | JSON      | Full group snapshot     | See below                   |

**Payload Structure:**

```json
{
  "id": 44444444,
  "code": "VIP",
  "name": "VIP Customers",
  "description": "Premium customer tier",
  "discount_rate": 10
}
```

**Current State:** 0 rows (awaiting customer group events in Sapo)

**API Endpoint:** `/admin/customer_groups/{id}.json`

See [`docs/architecture/raw-data-sources.md § Customer Groups`](./raw-data-sources.md#customer_group-sapo_rawcustomer_group) for complete schema.

---

### Price Lists (`sapo_raw.price_list`) — NEW

Pricing tiers and rules (bảng giá) from History Log pipeline. Defines product prices per channel, customer group, or time period.

| Column            | Type      | Description             | Example                     |
| ----------------- | --------- | ----------------------- | --------------------------- |
| `entity_id`       | VARCHAR   | Unique price list ID    | `"55555555"`                |
| `entity_type`     | VARCHAR   | Always `"price_list"`   | `"price_list"`              |
| `ingest_method`   | VARCHAR   | Always `"history_log"`  | `"history_log"`             |
| `event_timestamp` | TIMESTAMP | When price list changed | `2026-01-28T10:30:00Z`      |
| `payload`         | JSON      | Full price list snapshot| See below                   |

**Payload Structure:**

```json
{
  "id": 55555555,
  "code": "WHOLESALE_Q1",
  "name": "Wholesale Q1 2026",
  "status": "active",
  "start_date": "2026-01-01",
  "end_date": "2026-03-31",
  "is_default": false,
  "price_list_items": [
    {
      "product_id": 222,
      "price": 180000
    }
  ]
}
```

**Current State:** 0 rows (awaiting price list events in Sapo)

**API Endpoint:** `/admin/price_lists/{id}.json`

See [`docs/architecture/raw-data-sources.md § Price Lists`](./raw-data-sources.md#price_list-sapo_rawprice_list) for complete schema.

---

### Targets (`sapo_raw.targets_raw`)

Sales targets from Google Sheets.

| Column          | Type    | Description             |
| --------------- | ------- | ----------------------- |
| `staff_id`      | VARCHAR | Staff identifier        |
| `staff_name`    | VARCHAR | Staff name              |
| `location_id`   | VARCHAR | Store location          |
| `period`        | VARCHAR | Target period (YYYY-MM) |
| `target_amount` | DECIMAL | Target sales amount     |

---

### Shopee Income (`shopee_raw.order_revenue`) — NEW, planned

Per-order Shopee released-income data (fees, shipping, revenue). Source: Seller Center Excel export.

| Column | Type | Description |
|---|---|---|
| `order_code` | VARCHAR | **Natural key** — Shopee Order SN |
| `payout_released_at` | DATE | Date payout was credited to seller wallet |
| `order_placed_at` | DATE | Date order was placed |
| `total_paid_amount` | BIGINT | VND, total paid by buyer |
| `service_fee` | BIGINT | Platform service fee (negative) |
| `payment_fee` | BIGINT | Payment processing fee (negative) |
| `fixed_fee` | BIGINT | Fixed platform fee (negative) |
| `shipping_fee_actual` | BIGINT | Actual shipping cost (negative) |
| ... | | 53 columns total — see `docs/shopee-integration/data-source-description.md` § 4.3 |

**Related entities:** `shopee_raw.order_revenue_items` (line-item grain), `shopee_raw.order_service_fees` (extra fees: infrastructure + Xtra voucher).

---

### MISA Sales Ledger (`misa_raw.sales_lines`) — NEW, planned

Per-invoice-line sales detail from MISA AMIS accounting system. Contains COGS (giá vốn).

| Column | Type | Description |
|---|---|---|
| `voucher_no` | VARCHAR | MISA voucher ID — **cross-source join key** to Sapo/Shopee |
| `line_no` | INT | Synthesized line number per voucher (original row order) |
| `posting_date` | DATE | Accounting posting date |
| `product_code` | VARCHAR | MISA product code |
| `quantity` | BIGINT | Quantity sold |
| `unit_price` | DECIMAL(18,4) | Unit price (VND) |
| `revenue_gross` | BIGINT | Pre-discount line revenue (VND) |
| `discount_amount` | BIGINT | Discount (VND) |
| `cogs_amount` | BIGINT | **Cost of goods sold** — key column |
| `is_promo_line` | BOOL | `true` = promotional giveaway (revenue=0, cogs>0) |
| `channel_code` | VARCHAR | `DAILY/ECOM/CS/KHAC` — sales channel |
| `customer_code` | VARCHAR | Customer tax code |
| ... | | 25 columns total — see `docs/misa-amis/data-source-description.md` § 4 |

**Business key:** `(voucher_no, line_no)`. Dedup: `ROW_NUMBER() OVER (PARTITION BY voucher_no, line_no ORDER BY ingested_at DESC) = 1`.

---

## Staging Models

### `stg_sapo_orders`

Deduplicated order data - one row per order with latest state.

| Column               | Type          | Source                       | Description            |
| -------------------- | ------------- | ---------------------------- | ---------------------- |
| `order_id`           | VARCHAR       | `payload.id`                 | Primary key            |
| `order_code`         | VARCHAR       | `payload.code`               | Business reference     |
| `status`             | VARCHAR       | `payload.status`             | Order status           |
| `fulfillment_status` | VARCHAR       | `payload.fulfillment_status` | Shipping status        |
| `payment_status`     | VARCHAR       | `payload.payment_status`     | Payment status         |
| `total`              | DECIMAL(15,2) | `payload.total`              | Gross total            |
| `total_discount`     | DECIMAL(15,2) | `payload.total_discount`     | Discount amount        |
| `total_tax`          | DECIMAL(15,2) | `payload.total_tax`          | Tax amount             |
| `net_total`          | DECIMAL(15,2) | Calculated                   | total - discount       |
| `customer_id`        | VARCHAR       | `payload.customer_id`        | FK to customers        |
| `location_id`        | VARCHAR       | `payload.location_id`        | FK to locations        |
| `source_name`        | VARCHAR       | `payload.source_name`        | Order channel          |
| `created_at`         | TIMESTAMP     | `payload.created_on`         | Order creation time    |
| `modified_at`        | TIMESTAMP     | `payload.modified_on`        | Last update time       |
| `event_timestamp`    | TIMESTAMP     | Envelope                     | Event time (for audit) |
| `ingest_method`      | VARCHAR       | Envelope                     | Data source            |

**Deduplication Logic:**

- Partition by `order_id`
- Order by `event_timestamp DESC`, `ingest_method` priority
- Keep `ROW_NUMBER() = 1`

---

### `stg_sapo_customers`

Deduplicated customer data.

| Column           | Type          | Source                        | Description        |
| ---------------- | ------------- | ----------------------------- | ------------------ |
| `customer_id`    | VARCHAR       | `payload.id`                  | Primary key        |
| `customer_code`  | VARCHAR       | `payload.code`                | Business reference |
| `customer_name`  | VARCHAR       | `payload.name`                | Full name          |
| `email`          | VARCHAR       | `payload.email`               | Email address      |
| `phone`          | VARCHAR       | `payload.phone`               | Phone number       |
| `gender`         | VARCHAR       | `payload.gender`              | Gender             |
| `birthday`       | DATE          | `payload.birthday`            | Birth date         |
| `customer_group` | VARCHAR       | `payload.customer_group_name` | Customer segment   |
| `total_spent`    | DECIMAL(15,2) | `payload.total_spent`         | Lifetime value     |
| `orders_count`   | INTEGER       | `payload.orders_count`        | Total orders       |
| `created_at`     | TIMESTAMP     | `payload.created_on`          | Registration time  |

---

### `stg_sapo_accounts`

Deduplicated staff accounts.

| Column       | Type    | Source              | Description     |
| ------------ | ------- | ------------------- | --------------- |
| `account_id` | VARCHAR | `payload.id`        | Primary key     |
| `full_name`  | VARCHAR | `payload.full_name` | Staff name      |
| `email`      | VARCHAR | `payload.email`     | Email           |
| `role`       | VARCHAR | `payload.role`      | Role/position   |
| `status`     | VARCHAR | `payload.status`    | active/inactive |

---

## Intermediate Models (Enrichment Layer)

> Models prefixed `int_` contain enrichment data from external sources (Shopee, MISA). These are NOT primary facts — all orders already exist in Sapo `fact_orders`. `int_` models add fee breakdowns and cost data. They have rolling location for P0 Metabase access; P1 will join them into `fact_order_economics`.

### `int_shopee_order_fees` — NEW, planned

Shopee per-order fee breakdown. Joins `stg_shopee_order_revenue` LEFT JOIN `stg_shopee_order_service_fees`.

| Column | Type | Description |
|---|---|---|
| `shopee_order_sk` | VARCHAR | Surrogate key (MD5 of order_code) |
| `order_code` | VARCHAR | **Natural key** — joins to Sapo `fact_orders.order_code` |
| `payout_released_at` | DATE | Date payout was released |
| `total_paid_amount` | BIGINT | Total paid by buyer (VND) |
| `gross_revenue` | BIGINT | Derived: total_paid + refund |
| `total_shipping_net` | BIGINT | Net shipping (6 components) |
| `total_discounts` | BIGINT | Seller vouchers + coin cashback + subsidies |
| `total_platform_fees` | BIGINT | fixed + service + payment + affiliate + PiShip |
| `infrastructure_fee` | BIGINT | From Service Fee Details sheet (COALESCE 0) |
| `voucher_xtra_fee` | BIGINT | From Service Fee Details sheet (COALESCE 0) |
| `total_taxes` | BIGINT | VAT + personal income tax |
| `net_settlement` | BIGINT | Derived: all components summed = Shopee "Tổng phát hành" |

**Grain:** One row per Shopee order. **Plan:** `plans/260409-1710-shopee-pipeline/design-spec.md` § 3.4

---

### `int_shopee_order_items` — NEW, planned

Shopee per-order × product line items.

| Column | Type | Description |
|---|---|---|
| `shopee_order_item_sk` | VARCHAR | Surrogate key |
| `order_code` | VARCHAR | FK to `int_shopee_order_fees` |
| `product_code` | VARCHAR | Shopee product code |
| `product_name` | VARCHAR | Product name |

**Grain:** One row per order × product.

---

### `int_misa_sales_lines` — NEW, planned

MISA AMIS per-invoice-line with COGS, margin, and channel enrichment.

| Column | Type | Description |
|---|---|---|
| `misa_sales_line_sk` | VARCHAR | Surrogate key (MD5 of voucher_no + line_no) |
| `voucher_no` | VARCHAR | **Cross-source join key** to Sapo/Shopee |
| `line_no` | INT | Line number within voucher |
| `posting_date` | DATE | Accounting posting date |
| `product_code` | VARCHAR | MISA product code |
| `quantity` | BIGINT | Quantity sold |
| `unit_price` | DECIMAL(18,4) | Unit price (VND) |
| `revenue_gross` | BIGINT | Pre-discount revenue (VND) |
| `cogs_amount` | BIGINT | Cost of goods sold (VND) |
| `revenue_net_of_discount` | BIGINT | Derived: revenue - discount |
| `gross_profit` | BIGINT | Derived: net_revenue - COGS |
| `gross_margin_pct` | DECIMAL | Derived: gross_profit / net_revenue |
| `is_promo_line` | BOOL | Promotional giveaway (revenue=0, cogs>0) |
| `channel_code` | VARCHAR | `DAILY/ECOM/CS/KHAC` |
| `channel_name` | VARCHAR | From `ref_misa_channel_codes` seed |
| `voucher_source_hint` | VARCHAR | Heuristic: `SAPO_DEALER/SHOPEE/AEON/OTHER` |

**Grain:** One row per invoice-line. **Plan:** `plans/260409-1742-misa-amis-pipeline/design-spec.md` § 3.5

---

### P1 Vision: `fact_order_economics` — planned

Unified per-order P&L combining all three sources:

```sql
fact_order_economics =
  fact_orders (Sapo — base grain)
  LEFT JOIN int_shopee_order_fees ON order_code   -- platform fees
  LEFT JOIN int_misa_sales_lines  ON voucher_no   -- COGS (aggregated to order level)
→ net_revenue, total_fees, total_cogs, gross_profit, gross_margin_pct
```

---

## Dimension Tables

### `dim_date`

Calendar dimension for time-based analysis.

| Column           | Type    | Description            | Example      |
| ---------------- | ------- | ---------------------- | ------------ |
| `date_key`       | INTEGER | Primary key (YYYYMMDD) | `20260128`   |
| `date_actual`    | DATE    | Actual date            | `2026-01-28` |
| `year`           | INTEGER | Year                   | `2026`       |
| `quarter`        | INTEGER | Quarter (1-4)          | `1`          |
| `month`          | INTEGER | Month (1-12)           | `1`          |
| `month_name`     | VARCHAR | Month name             | `"January"`  |
| `week_of_year`   | INTEGER | ISO week number        | `5`          |
| `day_of_month`   | INTEGER | Day (1-31)             | `28`         |
| `day_of_week`    | INTEGER | Day (1-7, Mon=1)       | `2`          |
| `day_name`       | VARCHAR | Day name               | `"Tuesday"`  |
| `is_weekend`     | BOOLEAN | Weekend flag           | `false`      |
| `is_holiday`     | BOOLEAN | Holiday flag           | `false`      |
| `fiscal_year`    | INTEGER | Fiscal year            | `2026`       |
| `fiscal_quarter` | INTEGER | Fiscal quarter         | `1`          |

---

### `dim_customers`

Customer dimension with current state.

| Column             | Type    | Description                          |
| ------------------ | ------- | ------------------------------------ |
| `customer_key`     | VARCHAR | Surrogate key (MD5 hash)             |
| `customer_id`      | VARCHAR | Natural key from Sapo                |
| `customer_code`    | VARCHAR | Business reference                   |
| `customer_name`    | VARCHAR | Full name                            |
| `email`            | VARCHAR | Email (masked for privacy)           |
| `phone`            | VARCHAR | Phone (masked)                       |
| `gender`           | VARCHAR | male/female/other                    |
| `age_group`        | VARCHAR | Derived: <25, 25-35, 35-45, 45+      |
| `customer_group`   | VARCHAR | Segment from Sapo                    |
| `customer_tier`    | VARCHAR | Derived: Bronze/Silver/Gold/Platinum |
| `first_order_date` | DATE    | First purchase date                  |
| `last_order_date`  | DATE    | Most recent purchase                 |
| `total_orders`     | INTEGER | Lifetime order count                 |
| `total_spent`      | DECIMAL | Lifetime value                       |
| `is_active`        | BOOLEAN | Has ordered in last 90 days          |

**Tier Logic:**

- Platinum: total_spent >= 10,000,000
- Gold: total_spent >= 5,000,000
- Silver: total_spent >= 1,000,000
- Bronze: below 1,000,000

---

### `dim_products`

Product dimension.

| Column         | Type    | Description                           |
| -------------- | ------- | ------------------------------------- |
| `product_key`  | VARCHAR | Surrogate key                         |
| `product_id`   | VARCHAR | Natural key                           |
| `product_code` | VARCHAR | SKU                                   |
| `product_name` | VARCHAR | Product name                          |
| `product_name` | VARCHAR | Product name                          |
| `product_type` | VARCHAR | Type of product (flat classification) |
| `brand`        | VARCHAR | Brand name                            |
| `unit`         | VARCHAR | Unit of measure                       |
| `cost`         | DECIMAL | Cost price                            |
| `price`        | DECIMAL | Selling price                         |
| `is_active`    | BOOLEAN | Currently available                   |

---

### `dim_geography`

Location hierarchy for geographic analysis.

| Column          | Type    | Description                  |
| --------------- | ------- | ---------------------------- |
| `geography_key` | VARCHAR | Surrogate key                |
| `ward_id`       | VARCHAR | Ward identifier              |
| `ward_name`     | VARCHAR | Ward name                    |
| `district_id`   | VARCHAR | District identifier          |
| `district_name` | VARCHAR | District name                |
| `province_id`   | VARCHAR | Province identifier          |
| `province_name` | VARCHAR | Province name                |
| `region`        | VARCHAR | Region (North/Central/South) |

---

### `dim_channels`

Standardized sales and marketing channels (3-Level Hierarchy).

| Column           | Type    | Description                                      |
| ---------------- | ------- | ------------------------------------------------ |
| `channel_key`    | VARCHAR | Surrogate key                                    |
| `channel_name`   | VARCHAR | **Level 3**: Instance (Page Name, Store, Shop A) |
| `platform`       | VARCHAR | **Level 2**: Platform (Facebook, Shopee, Retail) |
| `platform_group` | VARCHAR | **Level 1**: Group (Social, E-com, Retail)       |
| `source_id`      | VARCHAR | Original Source ID or Suffix ID                  |
| `is_active`      | BOOLEAN | Channel status                                   |

---

### `dim_staff`

Staff dimension for sales attribution.

| Column        | Type    | Description        |
| ------------- | ------- | ------------------ |
| `staff_key`   | VARCHAR | Surrogate key      |
| `staff_id`    | VARCHAR | Natural key        |
| `staff_name`  | VARCHAR | Full name          |
| `email`       | VARCHAR | Email address      |
| `role`        | VARCHAR | Job role           |
| `location_id` | VARCHAR | Primary location   |
| `is_active`   | BOOLEAN | Currently employed |

---

### `dim_locations`

Store/warehouse locations.

| Column          | Type    | Description         |
| --------------- | ------- | ------------------- |
| `location_key`  | VARCHAR | Surrogate key       |
| `location_id`   | VARCHAR | Natural key         |
| `location_name` | VARCHAR | Store name          |
| `location_type` | VARCHAR | store/warehouse     |
| `address`       | VARCHAR | Full address        |
| `province`      | VARCHAR | Province            |
| `is_active`     | BOOLEAN | Currently operating |

---

---

### `dim_product_types`

Product Type dimension (formerly confused with Category).

| Column              | Type    | Description                                       |
| ------------------- | ------- | ------------------------------------------------- |
| `product_type_key`  | VARCHAR | Surrogate key                                     |
| `product_type_name` | VARCHAR | Name of the product type (e.g., "Shirt", "Pants") |

> [!NOTE] Insight: Product Type vs Category
> Sapo/Shopify data often conflates "Product Type" (single value, flat) with "Collection/Category" (hierarchical).
> We have explicitly renamed this to `dim_product_types` to reflect that it captures the `product_type` field, which is a flat classification, avoiding the implication of a hierarchical Category tree.

---

## Fact Tables

### `fact_orders`

Order-level fact table.

| Column               | Type          | Description           |
| -------------------- | ------------- | --------------------- |
| `order_key`          | VARCHAR       | Surrogate key         |
| `order_id`           | VARCHAR       | Natural key           |
| `order_code`         | VARCHAR       | Business reference    |
| `date_key`           | INTEGER       | FK to dim_date        |
| `customer_key`       | VARCHAR       | FK to dim_customers   |
| `location_key`       | VARCHAR       | FK to dim_locations   |
| `seller_staff_key`   | VARCHAR       | FK to dim_staff — người chốt (Sapo assignee), primary for sales attribution |
| `creator_staff_key`  | VARCHAR       | FK to dim_staff — người tạo đơn (Sapo account), operational/fallback |
| `status`             | VARCHAR       | Degenerate dimension  |
| `payment_status`     | VARCHAR       | Degenerate dimension  |
| `fulfillment_status` | VARCHAR       | Degenerate dimension  |
| `source_name`        | VARCHAR       | Order channel         |
| `gross_amount`       | DECIMAL(15,2) | Total before discount |
| `discount_amount`    | DECIMAL(15,2) | Discount applied      |
| `tax_amount`         | DECIMAL(15,2) | Tax amount            |
| `net_amount`         | DECIMAL(15,2) | Final amount          |
| `line_item_count`    | INTEGER       | Number of items       |
| `created_at`         | TIMESTAMP     | Order creation time   |

**Grain:** One row per order

---

### `fact_sales`

Line item level fact table for detailed analysis.

| Column             | Type          | Description                        |
| ------------------ | ------------- | ---------------------------------- |
| `sales_key`        | VARCHAR       | Surrogate key                      |
| `order_key`        | VARCHAR       | FK to fact_orders                  |
| `date_key`         | INTEGER       | FK to dim_date                     |
| `customer_key`     | VARCHAR       | FK to dim_customers_base           |
| `product_key`      | VARCHAR       | FK to dim_products (Variant level) |
| `product_type_key` | VARCHAR       | FK to dim_product_types            |
| `location_key`     | VARCHAR       | FK to dim_branch_location          |
| `quantity`         | INTEGER       | Units sold                         |
| `unit_price`       | DECIMAL(15,2) | Price per unit                     |
| `line_amount`      | DECIMAL(15,2) | quantity \* unit_price             |
| `discount_amount`  | DECIMAL(15,2) | Line discount                      |
| `net_amount`       | DECIMAL(15,2) | After discount                     |
| `cost_amount`      | DECIMAL(15,2) | Cost of goods                      |
| `margin_amount`    | DECIMAL(15,2) | net - cost                         |

**Grain:** One row per order line item

---

### `fact_targets`

Sales targets for performance tracking.

| Column          | Type          | Description                  |
| --------------- | ------------- | ---------------------------- |
| `target_key`    | VARCHAR       | Surrogate key                |
| `date_key`      | INTEGER       | FK to dim_date (month start) |
| `staff_key`     | VARCHAR       | FK to dim_staff              |
| `location_key`  | VARCHAR       | FK to dim_locations          |
| `target_amount` | DECIMAL(15,2) | Target sales amount          |
| `period`        | VARCHAR       | YYYY-MM format               |

**Grain:** One row per staff/location/month

---

### `fact_marketing_spend` (Planned: Manual Ingestion)

> **Status:** Specification Only (Use Google Sheets Ingestion)
> **Goal:** Track ad spend for CAC and ROAS calculations.
> **Ingestion Method:** Google Sheets (Similar to `targets`).

| Column         | Type          | Description                    |
| -------------- | ------------- | ------------------------------ |
| `spend_key`    | VARCHAR       | Surrogate key                  |
| `date_key`     | INTEGER       | FK to dim_date                 |
| `channel_key`  | VARCHAR       | FK to `dim_channels`           |
| `channel_code` | VARCHAR       | Raw Code from Sheet (e.g 'fb') |
| `campaign_id`  | VARCHAR       | Campaign identifier            |
| `spend_amount` | DECIMAL(15,2) | Cost in VND                    |

**Grain:** Daily per Campaign per Channel

---

## Reference Data (Seeds)

### `ref_order_sources` (Enriched)

The **Single Source of Truth** for all Sales and Marketing Channels.
Contains both Sapo-defined sources and User-defined sub-channels (Suffix IDs).

| Column              | Description                                       | Example                 |
| :------------------ | :------------------------------------------------ | :---------------------- |
| `id`                | **(PK)** Source ID (BigInt) or Suffix ID (String) | `8075219` or `113567_1` |
| `name`              | Source/Channel Name                               | `Shopee Shop A`         |
| `platform`          | **[NEW]** Specific Platform                       | `Shopee`, `Facebook`    |
| `platform_group`    | Aggregation Group                                 | `Social`, `Ecom`        |
| `mapping_tag`       | **[NEW]** Tag used to map Orders to Suffix IDs    | `Shopee_ShopA`          |
| `is_generic_source` | Flag for generic aggregators (requires splitting) | `false`                 |

### `ref_spend_category`

Standardized Marketing Spend Categories for reporting.

| Column                | Description      | Example          |
| :-------------------- | :--------------- | :--------------- |
| `spend_category_code` | **(PK)** Code    | `media_facebook` |
| `spend_category_name` | Display Name     | `Media Facebook` |
| `cost_group`          | High-level Group | `Media`, `KOLs`  |
| `owning_department`   | Responsible Dept | `Performance`    |

### `ref_branch_locations`

List of physical stores and warehouses. Used for mapping generic sources (POS).

| Column | Description          | Example          |
| :----- | :------------------- | :--------------- |
| `id`   | **(PK)** Location ID | `452566`         |
| `name` | Branch/Store Name    | `16 Trương Định` |

## Business Metrics

### Sales Metrics

| Metric                        | Formula                    | Description            |
| ----------------------------- | -------------------------- | ---------------------- |
| **Gross Sales**               | SUM(gross_amount)          | Total before discounts |
| **Net Sales**                 | SUM(net_amount)            | Total after discounts  |
| **Average Order Value (AOV)** | Net Sales / COUNT(orders)  | Average per order      |
| **Discount Rate**             | SUM(discount) / SUM(gross) | Discount percentage    |
| **Margin**                    | SUM(margin_amount)         | Profit margin          |
| **Margin Rate**               | Margin / Net Sales         | Margin percentage      |

### Customer Metrics

| Metric                            | Formula                              | Description            |
| --------------------------------- | ------------------------------------ | ---------------------- |
| **Customer Count**                | COUNT(DISTINCT customer_id)          | Unique customers       |
| **New Customers**                 | Customers with first order in period | Acquisition            |
| **Repeat Customers**              | Customers with >1 order              | Retention              |
| **Customer Lifetime Value (CLV)** | AVG(total_spent)                     | Average lifetime value |
| **Repeat Rate**                   | Repeat / Total Customers             | Loyalty indicator      |

### Performance Metrics

| Metric                 | Formula                         | Description           |
| ---------------------- | ------------------------------- | --------------------- |
| **Target Achievement** | Actual / Target \* 100          | % of target reached   |
| **YoY Growth**         | (Current - Previous) / Previous | Year-over-year change |
| **MoM Growth**         | Month-over-month change         | Trend indicator       |

---

## Naming Conventions

See [GLOSSARY.md](../development/glossary.md#naming-conventions) for detailed naming standards.

### Quick Reference

| Object Type   | Prefix            | Example                       |
| ------------- | ----------------- | ----------------------------- |
| Source model  | `src_`            | `src_sapo_orders`             |
| Staging model | `stg_`            | `stg_sapo_orders`             |
| Intermediate  | `int_`            | `int_orders_enriched`         |
| Dimension     | `dim_`            | `dim_customers`               |
| Fact          | `fact_`           | `fact_orders`                 |
| Primary key   | `*_id` or `*_key` | `customer_id`, `customer_key` |
| Foreign key   | `*_key`           | `customer_key`                |
| Boolean       | `is_*` or `has_*` | `is_active`                   |
| Timestamp     | `*_at`            | `created_at`                  |
| Amount        | `*_amount`        | `net_amount`                  |
