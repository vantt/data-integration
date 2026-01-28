# Glossary

> Terminology, abbreviations, and naming conventions for the Data Integration Pipeline

## Table of Contents

1. [Terminology](#terminology)
2. [Abbreviations](#abbreviations)
3. [Naming Conventions](#naming-conventions)
4. [Data Concepts](#data-concepts)

---

## Terminology

### Architecture Terms

| Term | Definition |
|------|------------|
| **Hop** | A stage in the data pipeline (7 hops total from source to serving) |
| **Data Lake** | Raw data storage using Parquet files (`data_lake/sapo_raw/`) |
| **Data Lakehouse** | Architecture combining data lake flexibility with warehouse features |
| **Serving Layer** | Final database optimized for BI queries (`olap.duckdb`) |
| **Rolling Snapshot** | Immutable timestamped exports for zero-downtime updates |

### Technology Terms

| Term | Definition |
|------|------------|
| **dlt** | Data Load Tool - Python library for data ingestion |
| **dbt** | Data Build Tool - SQL-based transformation framework |
| **DuckDB** | In-process OLAP database (embedded, no server) |
| **Dagster** | Data orchestration platform for scheduling jobs |
| **Parquet** | Columnar storage format optimized for analytics |
| **D1** | Cloudflare's serverless SQLite database |

### Pipeline Terms

| Term | Definition |
|------|------------|
| **Batch Sync** | Periodic full or incremental data extraction via API |
| **Webhook** | Real-time HTTP callback when events occur |
| **History Log** | Sapo API endpoint for retrieving historical change events |
| **Gap Filling** | Process of fetching missed events via history log |
| **Incremental Load** | Loading only new/changed data since last sync |
| **Full Refresh** | Complete reload of all data |

### Transformation Terms

| Term | Definition |
|------|------------|
| **Staging** | First transformation layer - deduplication and cleaning |
| **Intermediate** | Business logic layer - joins and calculations |
| **Marts** | Final analytical tables - dimensions and facts |
| **Materialization** | How dbt persists model results (view, table, incremental, external) |
| **Deduplication** | Removing duplicate records, keeping latest version |

### Modeling Terms

| Term | Definition |
|------|------------|
| **Kimball** | Dimensional modeling methodology (star schema) |
| **Star Schema** | Fact tables surrounded by dimension tables |
| **Fact Table** | Measures/metrics (e.g., `fact_orders`, `fact_sales`) |
| **Dimension Table** | Descriptive attributes (e.g., `dim_customers`, `dim_products`) |
| **Surrogate Key** | Artificial unique identifier (e.g., `customer_key`) |
| **Natural Key** | Business identifier from source (e.g., `customer_id`) |
| **SCD** | Slowly Changing Dimension - handling attribute changes over time |

---

## Abbreviations

| Abbreviation | Full Form |
|--------------|-----------|
| **API** | Application Programming Interface |
| **BI** | Business Intelligence |
| **CDC** | Change Data Capture |
| **CLI** | Command Line Interface |
| **CTE** | Common Table Expression |
| **DAG** | Directed Acyclic Graph |
| **DDL** | Data Definition Language |
| **DML** | Data Manipulation Language |
| **ELT** | Extract, Load, Transform |
| **ETL** | Extract, Transform, Load |
| **OLAP** | Online Analytical Processing |
| **OLTP** | Online Transaction Processing |
| **OTP** | Operational (our staging layer tag) |
| **PII** | Personally Identifiable Information |
| **SQL** | Structured Query Language |
| **SCD** | Slowly Changing Dimension |
| **TTL** | Time To Live |
| **UUID** | Universally Unique Identifier |

---

## Naming Conventions

### File Naming

| Type | Convention | Example |
|------|------------|---------|
| dbt source model | `src_{system}_{entity}.sql` | `src_sapo_orders.sql` |
| dbt staging model | `stg_{system}_{entity}.sql` | `stg_sapo_orders.sql` |
| dbt intermediate | `int_{entity}_{action}.sql` | `int_orders_enriched.sql` |
| dbt dimension | `dim_{entity}.sql` | `dim_customers.sql` |
| dbt fact | `fact_{entity}.sql` | `fact_orders.sql` |
| Parquet export | `{table}_{timestamp}.parquet` | `dim_customers_20260128_1001.parquet` |
| dlt pipeline | `run_{entity}_{method}.py` | `run_orders_batch.py` |

### Database Naming

| Object | Convention | Example |
|--------|------------|---------|
| Schema | lowercase | `staging`, `marts` |
| Table/View | snake_case | `fact_orders`, `dim_customers` |
| Column | snake_case | `customer_id`, `order_total` |
| Primary key | `{entity}_id` or `{entity}_key` | `order_id`, `customer_key` |
| Foreign key | `{referenced_entity}_id` | `customer_id` in `fact_orders` |
| Boolean | `is_*` or `has_*` | `is_active`, `has_discount` |
| Date | `*_date` | `order_date`, `ship_date` |
| Timestamp | `*_at` or `*_timestamp` | `created_at`, `event_timestamp` |
| Amount/Money | `*_amount` or `*_total` | `order_amount`, `discount_total` |
| Count | `*_count` | `line_item_count` |

### Partition Naming

```
data_lake/sapo_raw/{entity}/ingest_method={method}/year={YYYY}/month={MM}/
```

| Component | Values | Example |
|-----------|--------|---------|
| `entity` | `order`, `customer`, `account` | `order` |
| `ingest_method` | `batch_sync`, `webhook`, `history_log` | `webhook` |
| `year` | 4-digit year | `2026` |
| `month` | 2-digit month | `01` |

### Tag Naming (dbt)

| Tag | Purpose | Models |
|-----|---------|--------|
| `staging` | First layer models | `stg_*` |
| `intermediate` | Business logic | `int_*` |
| `mart` | Final tables | `dim_*`, `fact_*` |
| `otp` | Operational pipeline | Staging + critical marts |
| `olap` | Analytics pipeline | All marts |
| `core` | Core dimensions | `dim_date`, `dim_geography` |
| `sales` | Sales domain | `fact_orders`, `fact_sales` |

---

## Data Concepts

### Ingestion Methods

| Method | Source | Timing | Reliability | Use Case |
|--------|--------|--------|-------------|----------|
| `batch_sync` | JSON API | Scheduled | High (idempotent) | Daily reconciliation |
| `webhook` | Sapo Push | Real-time | Medium (may miss) | Immediate updates |
| `history_log` | History API | 5-10 min | High | Gap filling |

### Time Fields

| Field | Origin | Purpose |
|-------|--------|---------|
| `created_on` | Source (Sapo) | When entity was created |
| `modified_on` | Source (Sapo) | When entity was last changed |
| `event_timestamp` | Pipeline | Business time of event (for ordering) |
| `processing_timestamp` | Pipeline | When dlt wrote the file |
| `_dlt_load_id` | dlt | Load batch identifier |
| `_dlt_id` | dlt | Unique record identifier |

### Deduplication Priority

When multiple records exist for the same entity:

1. **Latest `event_timestamp`** - Most recent business event wins
2. **Source priority** (tie-breaker):
   - `webhook` (3) > `history_log` (2) > `batch_sync` (1)

### Entity Lifecycle States

**Orders:**
```
draft → confirmed → processing → shipped → completed
                 ↘ cancelled
```

**Customers:**
```
created → active → inactive
```

### Data Quality Rules

| Rule | Description |
|------|-------------|
| Uniqueness | Primary keys must be unique |
| Not null | Key fields cannot be null |
| Referential | Foreign keys must exist in dimension |
| Range | Amounts must be >= 0 |
| Freshness | Data must be updated within SLA |

---

## Quick Reference

### Common Queries

```sql
-- Check latest data timestamp
SELECT MAX(event_timestamp) FROM stg_sapo_orders;

-- Count by ingest method
SELECT ingest_method, COUNT(*)
FROM read_parquet('data_lake/sapo_raw/order/**/*.parquet')
GROUP BY ingest_method;

-- Find duplicate entities
SELECT entity_id, COUNT(*)
FROM stg_sapo_orders
GROUP BY entity_id
HAVING COUNT(*) > 1;
```

### Common Commands

```bash
# Check dbt model tags
dbt ls --select tag:mart

# Run specific model
dbt run --select stg_sapo_orders+

# Test data quality
dbt test --select stg_sapo_orders
```
