# Transformation Logic & Process Documentation

This document details the architecture, business logic, and development process for the dbt transformation layer.

## 1. Architecture Overview (The 3-Layer Approach)

We follow a strict 3-layer pattern ("Hop 5" in our Data Pipeline):

### Layer 1: Staging (`models/staging/sapo/`)

- **Purpose**: Cleaning & Extraction.
- **Input**: `src_` views (Raw Data Lake).
- **Actions**:
  - **JSON Extraction**: Unnesting complex JSON payloads (e.g., `payload` -> `item_json`).
  - **Type Casting**: `try_cast` to ensure data types (Decimal, Timestamp).
  - **Flattening**: Bringing nested fields (Shipping Address, Customer Info) to the root level.
- **Naming**: `stg_[source]_[entity]`.

### Layer 2: Standard (`models/staging/standard/`)

- **Purpose**: Verification & Standardization ("Gold Standard").
- **Input**: `stg_` models.
- **Actions**:
  - **Business Logic**: Applying mapping rules (e.g., `fulfillment_status`).
  - **Renaming**: Standardizing column names across sources (e.g., `total_amount` is consistent regardless of source).
  - **Tests**: Primary location for `unique`, `not_null`, and `accepted_values` tests.
- **Naming**: `std_[entity]`.

### Layer 3: Marts (`models/marts/`)

- **Purpose**: Serving & Analytics (Star Schema).
- **Input**: `std_` models.
- **Actions**:
  - **Modeling**: Creating `fact_` and `dim_` tables.
  - **Keys**: Generating Surrogate Keys (`md5`) for relationships.
  - **Logic**: Aggregations or specific join logic for analysis.
- **Naming**: `dim_[entity]`, `fact_[process]`.

---

## 2. Key Business Logic Patterns

### A. Hybrid Fulfillment Status (in `std_orders.sql`)

We use a **Hybrid Logic** combining Sapo's logistics status with Legacy's financial completeness logic.

- **Why?** Sapo's `fulfilled` only means "shipped", but we want `COMPLETED` to mean "Shipped + Paid + Received".
- **Priority Order**:
  1.  **Lifecycle**: `CANCELLED`.
  2.  **Logistics Exceptions**: `RETURNED`, `PARTIALLY_FULFILLED`.
  3.  **Legacy Complete**: `COMPLETED` (Paid + Packed + Received).
  4.  **Legacy Shipped**: `SHIPPED_PAID` vs `SHIPPED_COD`.
  5.  **Payment Processing**: `PAID_PROCESSING`.
  6.  **Default**: `IN_PROGRESS`.

### B. "Virtual" Product Dimension (in `dim_products.sql`)

Since we don't have a direct Product Sync pipeline yet, we **derive** products from historical Order Items.

- **Strategy**: "Last Record Wins" (Deduplication).
- **Implementation**: Window Function `ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY extracted_at DESC)`.
- **Benefit**: Always have the latest names/prices even if they changed over time.

### C. Generated Time Dimension (in `dim_time.sql`)

- **Granularity**: **Minute** (1440 rows).
- **Attributes**: Includes Business Logic flags for retail analysis:
  - `is_business_hour` (09:00 - 17:00).
  - `is_peak_hour` (Lunch 11-14h, Dinner 16-19h).
  - `day_period` (Morning, Afternoon, Evening, Night).
- **Source**: Generated via DuckDB SQL (no static CSV needed).

---

## 3. Development Process

### Adding a New Field

1.  **Staging**: Add `json_extract_string` in `stg_sapo_orders.sql` (or relevant file).
2.  **Standard**: Add col to `std_orders.sql`. Add description in `schema.yml`.
3.  **Marts**: Add to `fact` or `dim`. Run `dbt compile` to verify.

### Testing

- **Schema Tests**: Always defined in `models/staging/standard/schema.yml`.
- **Run**: `dbt test --select std_orders` (typically run via pipeline script).

### Deployment

- Run `./scripts/run_pipeline.ps1` to build, test, and export Parquet files to `data_lake/export`.
