# Transformation Layer Agents Guidelines

**Scope**: This document establishes specific rules and heuristics for AI Agents working within the `data-integration/transformation` (dbt) directory.

## Core Mandates

### 1. Mart Location Configuration (CRITICAL)

All models in `models/marts/` MUST explicitly define their export location to support the Serving Layer (Rolling Snapshots).

- **Pattern**: `location="{{ get_rolling_location() }}"`
- **Location**: Inside the `{{ config(...) }}` block of the `.sql` file.
- **Why**: The global `dbt_project.yml` sets `materialized: external`, but the specific *path* logic resides in the macro. Without this explicit config, dbt may default to internal paths, causing the Serving Script (`generate_serving_db.py`) to miss the file.

**❌ BAD (Missing Location):**
```sql
{{ config(
    tags=['mart', 'dim']
) }}
SELECT ...
```

**✅ GOOD:**
```sql
{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}
SELECT ...
```

### 2. Golden Sample Heuristic

When creating or Fixing a model, **ALWAYS** comparison against a working "Golden Sample" in the same directory.

- **Action**: Run `diff` or visually compare with a sibling file.
- **Example**: If creating `dim_new.sql` in `models/marts/core/`, compare it with `dim_products.sql` or `dim_staff.sql` to verify config patterns.

### 3. Materialization Rules

- **Staging (`models/staging/`)**:
  - Default: `view`
  - Purpose: Deduplication and cleaning. Lightweight.
- **Intermediate (`models/intermediate/`)**:
  - Default: `ephemeral` or `table` (if reused heavily).
  - Purpose: Business logic, heavy joins.
  - **Note**: Intermediate models are NOT exported to the data lake for Serving.
- **Marts (`models/marts/`)**:
  - Default: `external` (Parquet).
  - Required Config: `location="{{ get_rolling_location() }}"`.
  - Purpose: Final BI tables.

### 4. File Naming Conventions

- **Sources**: `src_source_entity.sql` (e.g., `src_sapo_orders.sql`)
- **Staging**: `stg_source_entity.sql` (e.g., `stg_sapo_orders.sql`)
- **Intermediate**: `int_entity_description.sql` (e.g., `int_customer_metrics.sql`)
- **Marts (Dimension)**: `dim_entity.sql` (e.g., `dim_products.sql`)
- **Marts (Fact)**: `fact_process.sql` (e.g., `fact_orders.sql`)

### 5. Testing

- **Unique Keys**: Every model must have at least `unique` and `not_null` tests on its primary key in `schema.yml`.
- **Relationships**: Foreign keys in Marts must have `relationships` tests to Dimensions.

## Troubleshooting Common Issues

### "Empty folder / View Dropped" in Serving Script

- **Symptom**: `generate_serving_db.py` reports `[!] Empty folder: dim_xyz` and drops the view, even after dbt run success.
- **Cause**: The model `dim_xyz.sql` is missing `location="{{ get_rolling_location() }}"`.
- **Fix**: Add the config and re-run.

### dbt OOM (Out of Memory)

- **Cause**: Deduplicating heavy JSON columns (`payload`) in DuckDB.
- **Fix**: Use Strict Late Materialization.

### Optimization Strategies (Applied & Proven)

 1.  **Strict Late Materialization (Double Deduplication)**:
     - **Concept**: Never `SELECT *` or select heavy columns (JSON) in the deduplication CTE.
     - **Step 1**: Extract ONLY lightweight keys (`id`, `timestamp`) -> Dedup -> Get `winner_ids`.
     - **Step 2**: Join `winner_ids` back to Source to get Payload -> Extract fields -> **DROP Payload immediately**.
     - **Step 3 (Critical)**: Ensure NO further sorting/deduplication happens after the heavy payload is read. Using `QUALIFY` on the final dataset triggers a massive sort -> **OOM**.
 
 2.  **Profile Tuning (`profiles.yml`)**:
     - **`memory_limit`**: Set LOWER than container limit (e.g., `5GB` or `7GB` for a 16GB machine). This forces DuckDB to **Spill to Disk** early instead of crashing.
     - **`threads`**: Set to `1` or `2`. High threads = High concurrent buffer usage = OOM. Sequential processing is slower but stable.
 
 3.  **Handling Exact Duplicates**:
     - If source has 100% duplicate rows, a JOIN will multiply them. Use `QUALIFY ROW_NUMBER() ... = 1` solely on the UNIQUE ID constraint at the very end, but ensure the dataset is ALREADY pruned of heavy columns if possible.

---
**Note**: These rules supplement the global `AGENTS.md`. In case of conflict regarding *dbt specifics*, this file takes precedence.
