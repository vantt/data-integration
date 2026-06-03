# Transformation Layer Agents Guidelines

**Scope**: This document establishes specific rules and heuristics for AI Agents working within the `data-integration/transformation` (dbt) directory.

> **Source versioning & the std gate (Sapo v2→v3):** before adding/changing any Sapo entity, read `docs/architecture/std-layer-conventions.md` (std gate rule, faithful pass-through, `_v2`/`_v3` suffix, std contract, checksum+fresh-run verification, never move raw/dlt state). Column/model names: `docs/architecture/naming-conventions.md`.

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

- **Sources (`models/staging/src_*`)**:
  - Default: `incremental` (delete+insert)
  - Purpose: JSON extraction + dedup from raw parquet. Output flat columns, no payload.
- **Staging (`models/staging/stg_*`)**:
  - Default: `view`
  - Purpose: Enrichment joins, unnest. Reads from src_ (flat data). Lightweight.
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

- **Cause**: Processing heavy JSON payload + dedup + enrichment in a single model = single SQL query = single memory budget. CTEs don't materialize to disk.
- **Fix**: Split into `src_` (INCREMENTAL: extract + dedup) and `stg_` (VIEW: enrichment). Each model = separate query = separate memory budget. Peak = max(model1, model2) instead of sum().

### Optimization Strategies (Applied & Proven)

 1.  **src_/stg_ Split (Primary OOM Fix)**:
     - `src_` model (INCREMENTAL): reads raw parquet, tech dedup by entity_id, extracts all JSON fields, biz dedup by order_id on flat data. Payload discarded after extraction.
     - `stg_` model (VIEW): reads from src_ (flat data, no payload). Only enrichment joins.
     - Memory peak of src_ ≈ 1.1GB. Memory peak of stg_ ≈ 210MB. Both well under 5GB limit.
     - See `transformation/docs/ARCHITECTURE_DETAIL.md` for full architecture details.

 2.  **Profile Tuning (`profiles.yml`)**:
     - **`memory_limit`**: Set to `5GB` (lower than container limit). Forces DuckDB to **Spill to Disk** early instead of crashing.
     - **`threads`**: Set to `1`. High threads = High concurrent buffer usage = OOM. Sequential processing is slower but stable.

 3.  **Incremental Processing**:
     - src_ models use 7-day lookback window: `WHERE event_timestamp > (SELECT MAX(event_timestamp) - INTERVAL 7 DAY FROM {{ this }})`
     - Full refresh processes all data — may need temporarily higher memory_limit.

 4.  **Handling Exact Duplicates**:
     - Use `QUALIFY ROW_NUMBER() ... = 1` on flat extracted data (no payload). Safe because biz dedup runs AFTER JSON extraction.

---
**Note**: These rules supplement the global `AGENTS.md`. In case of conflict regarding *dbt specifics*, this file takes precedence.
