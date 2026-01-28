# Transformation Layer Documentation

> SQL-based data transformation using dbt + DuckDB

## Overview

The transformation layer cleans, deduplicates, and models data using dbt with DuckDB adapter. It transforms raw Parquet files into dimensional models (Kimball star schema) for analytics.

## Quick Start

```bash
cd transformation

# Install dbt packages
python scripts/run_dbt.py deps

# Run all models
python scripts/run_dbt.py run

# Run specific models
python scripts/run_dbt.py run --select stg_sapo_orders+

# Run tests
python scripts/run_dbt.py test
```

## Directory Structure

```
transformation/
├── models/
│   ├── staging/           # Source & staging models
│   │   ├── src_sapo_*.sql # Read from Parquet
│   │   ├── stg_sapo_*.sql # Deduplicated data
│   │   └── standard/      # Standardized dimensions
│   ├── intermediate/      # Business logic
│   └── marts/
│       ├── core/          # Core dimensions
│       └── sales/         # Sales facts & dims
├── macros/                # dbt macros
├── tests/                 # Custom tests
├── seeds/                 # Reference data
├── scripts/
│   └── run_dbt.py         # dbt wrapper script
├── dbt_project.yml        # Project configuration
└── profiles.yml           # Connection profiles
```

## Documentation

### Technical Reference

| Document | Description |
|----------|-------------|
| [MODELS.md](./MODELS.md) | Model catalog and dependencies |
| [DEDUPLICATION.md](./DEDUPLICATION.md) | Deduplication strategy details |
| [TESTING.md](./TESTING.md) | Data quality testing |
| [MATERIALIZATION.md](./MATERIALIZATION.md) | Materialization configurations |

### Business Logic & Architecture

| Document | Description |
|----------|-------------|
| [ARCHITECTURE_DETAIL.md](./ARCHITECTURE_DETAIL.md) | Data lineage diagrams, entity definitions, incremental strategy |
| [BUSINESS_LOGIC.md](./BUSINESS_LOGIC.md) | Fulfillment status mapping, virtual dimensions, development process |

## Model Layers

### Sources (src_*)

Read raw Parquet files with hive partitioning:

```sql
-- src_sapo_orders.sql
SELECT * FROM read_parquet(
    '{{ var("data_lake_path") }}/sapo_raw/order/**/*.parquet',
    hive_partitioning = true
)
```

### Staging (stg_*)

Deduplicate and clean data:

```sql
-- stg_sapo_orders.sql
-- Uses Last-Write-Wins deduplication
-- One row per entity_id with latest state
```

### Intermediate (int_*)

Apply business logic and joins:

```sql
-- int_orders_enriched.sql
-- Join orders with customers, geography, etc.
```

### Marts (dim_*, fact_*)

Final dimensional model:

- **Dimensions:** dim_date, dim_customers, dim_products, dim_geography, dim_staff
- **Facts:** fact_orders, fact_sales, fact_targets

## Key Concepts

### Strict Late Materialization

Memory-efficient deduplication for DuckDB:

1. Select only key columns for ranking
2. Apply ROW_NUMBER() window function
3. Filter to winners
4. Join back to get full payload

### Rolling Snapshots

Zero-downtime serving updates:

1. Export marts to timestamped Parquet files
2. Smart views auto-select latest snapshot
3. Old files cleaned up after confirmation

### Tags

| Tag | Purpose | Models |
|-----|---------|--------|
| `staging` | First layer | src_*, stg_* |
| `intermediate` | Business logic | int_* |
| `mart` | Final tables | dim_*, fact_* |
| `otp` | Operational pipeline | Staging + critical marts |
| `olap` | Full analytics | All marts |

## Common Commands

```bash
# Run by tag
python scripts/run_dbt.py run --select tag:staging
python scripts/run_dbt.py run --select tag:mart

# Run with dependencies
python scripts/run_dbt.py run --select +fact_orders

# Full refresh
python scripts/run_dbt.py run --full-refresh

# Generate docs
python scripts/run_dbt.py docs generate
python scripts/run_dbt.py docs serve
```

## Configuration

### profiles.yml

```yaml
sapo_analytics:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "{{ env_var('DATA_LAKE_PATH') }}/sapo_warehouse.duckdb"
```

### dbt_project.yml

```yaml
models:
  sapo_analytics:
    staging:
      +materialized: view
      +tags: ['staging', 'otp']
    marts:
      +materialized: external
      +tags: ['mart', 'olap']
```

## Troubleshooting

### Out of Memory

Use Strict Late Materialization pattern or reduce batch size.

### Schema Changes

Handle with COALESCE and TRY_CAST for backward compatibility.

### Debug Mode

```bash
python scripts/run_dbt.py run --select model_name --debug
```

## Related

- [Main Documentation](../../docs/README.md)
- [Data Dictionary](../../docs/DATA_DICTIONARY.md)
- [Data Flow](../../docs/DATA_FLOW.md)
