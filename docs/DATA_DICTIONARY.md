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

### Orders (`sapo_raw.order`)

The core transactional entity representing customer purchases.

| Column            | Type      | Description             | Example                     |
| ----------------- | --------- | ----------------------- | --------------------------- |
| `entity_id`       | VARCHAR   | Unique order identifier | `"12345678"`                |
| `entity_type`     | VARCHAR   | Always `"order"`        | `"order"`                   |
| `ingest_method`   | VARCHAR   | Data source             | `"webhook"`, `"batch_sync"` |
| `event_type`      | VARCHAR   | Event action            | `"create"`, `"update"`      |
| `event_timestamp` | TIMESTAMP | When event occurred     | `2026-01-28T10:30:00Z`      |
| `payload`         | JSON      | Full order snapshot     | See below                   |

**Payload Structure:**

```json
{
  "id": 12345678,
  "code": "SON000001",
  "status": "confirmed",
  "fulfillment_status": "pending",
  "payment_status": "paid",
  "total": 500000,
  "total_discount": 50000,
  "total_tax": 0,
  "customer_id": 9876543,
  "location_id": 12345,
  "source_id": 1,
  "source_name": "web",
  "created_on": "2026-01-28T10:00:00Z",
  "modified_on": "2026-01-28T10:30:00Z",
  "order_line_items": [
    {
      "id": 111,
      "product_id": 222,
      "variant_id": 333,
      "quantity": 2,
      "price": 250000,
      "line_amount": 500000
    }
  ],
  "shipping_address": {
    "address1": "123 Main St",
    "ward": "Ward 1",
    "district": "District 1",
    "city": "Ho Chi Minh"
  }
}
```

**Business Rules:**

- `status`: draft → confirmed → processing → completed/cancelled
- `fulfillment_status`: pending → partial → fulfilled
- `payment_status`: pending → partial → paid → refunded

---

### Customers (`sapo_raw.customer`)

Customer master data.

| Column            | Type      | Description                | Example                |
| ----------------- | --------- | -------------------------- | ---------------------- |
| `entity_id`       | VARCHAR   | Unique customer identifier | `"9876543"`            |
| `entity_type`     | VARCHAR   | Always `"customer"`        | `"customer"`           |
| `ingest_method`   | VARCHAR   | Data source                | `"webhook"`            |
| `event_timestamp` | TIMESTAMP | When event occurred        | `2026-01-28T09:00:00Z` |
| `payload`         | JSON      | Full customer snapshot     | See below              |

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

---

### Accounts (`sapo_raw.account`)

Staff/employee accounts.

| Column        | Type    | Description               | Example     |
| ------------- | ------- | ------------------------- | ----------- |
| `entity_id`   | VARCHAR | Unique account identifier | `"1001"`    |
| `entity_type` | VARCHAR | Always `"account"`        | `"account"` |
| `payload`     | JSON    | Full account snapshot     | See below   |

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
| `staff_key`          | VARCHAR       | FK to dim_staff       |
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

See [GLOSSARY.md](./GLOSSARY.md#naming-conventions) for detailed naming standards.

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
