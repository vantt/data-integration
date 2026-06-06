# Transformation Layer Agents Guidelines

**Scope**: This document establishes specific rules and heuristics for AI Agents working within the `data-integration/transformation` (dbt) directory.

> **Source versioning & the std gate (Sapo v2→v3):** before adding/changing any Sapo entity, read `docs/architecture/std-layer-conventions.md` (std gate rule, faithful pass-through, `_v2`/`_v3` suffix, std contract, checksum+fresh-run verification, never move raw/dlt state). Column/model names: `docs/architecture/naming-conventions.md`.

## Core Mandates

### 1. Mart Location Configuration (CRITICAL)

All models in `models/marts/` MUST explicitly define their export location to support the Serving Layer (Rolling Snapshots).

- **Pattern**: `location="{{ get_rolling_location() }}"`
- **Location**: Inside the `{{ config(...) }}` block of the `.sql` file.
- **Why**: The global `dbt_project.yml` sets `materialized: external`, but the specific *path* logic resides in the macro. Without this explicit config, dbt may default to internal paths, causing the Serving Script (`bootstrap_serving_views.py`) to miss the file.

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

**Schema Alignment Note:** Mart models have `+schema: marts` in dbt_project.yml, making them appear in the dbt manifest as `main_marts.fact_orders`. The serving DB (`olap.duckdb`) creates views in the `main` schema by default. To enable dbt-metabase lineage integration, `bootstrap_serving_views.py` will create dual views: `main.{table_name}` (for backward compatibility with Metabase cards) and `main_marts.{table_name}` (alias for dbt-metabase schema matching). This allows the tool to auto-populate `depends_on` references without requiring SQL card migrations. See `docs/ARCHITECTURE_DETAIL.md` section 6 for full details.

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

## dbt-metabase Integration

### Generating exposures.yml — STRICT RULE

**NEVER run `dbt-metabase exposures` directly.** The tool hardcodes `DEFAULT_SCHEMA = "PUBLIC"` (PostgreSQL convention), which does not match this project's DuckDB schema (`main_marts`). Running it directly produces `exposures.yml` where every card has `depends_on: []` — lineage is empty and useless.

**ALWAYS use the wrapper script:**

```bash
python tools/run-dbt-metabase-exposures.py
```

This script patches `dbtmetabase.manifest.DEFAULT_SCHEMA = "main_marts"` at runtime (in-process, no file modification), then runs the extraction. Result: `depends_on` is populated with the correct dbt node references.

**Why the schema must be `main_marts`:**
- dbt resolves schema as: target schema (`main`) + `+schema` override (`marts`) → `main_marts`
- Metabase native SQL cards write bare table names: `FROM fact_orders` (no schema prefix)
- dbt-metabase SQL parser defaults bare names to `DEFAULT_SCHEMA`
- `main_marts` is available in `olap.duckdb` as alias views (created by `bootstrap_serving_views.py`)

**Output:** `transformation/exposures.yml` — regenerate after adding/removing Metabase cards.

---

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

## Semantic Layer Contract

Mart models là **implementation** của semantic concepts được định nghĩa trong `docs/analytics-handbook/semantic/`. Transformation layer phải đảm bảo semantic contract không bị vi phạm.

### Nguyên tắc

Semantic concepts được define ở `docs/analytics-handbook/semantic/` — dbt mart implement chúng thành columns. Khi sửa mart, phải đọc semantic definition trước để hiểu đúng business rule.

```
docs/analytics-handbook/semantic/segments.md   → fact_orders.scope_retail, scope_b2b, scope_sales
docs/analytics-handbook/semantic/metrics.md    → fact_orders.net_revenue, gross_revenue, vat_amount
docs/analytics-handbook/semantic/rules.md      → cancellation convention, VAT treatment, is_completed
docs/analytics-handbook/semantic/dimensions.md → fact_orders.customer_type, date_key, channel_*
```

### Quy tắc khi làm mart

**Khi thêm/sửa semantic column (scope flags, metric columns):**
1. Đọc definition trong `docs/analytics-handbook/semantic/` trước
2. Implement đúng rule — không tự diễn giải
3. Nếu rule không rõ → hỏi, không đoán
4. Sau khi sửa → update `semantic/*.md` nếu definition thay đổi

**Khi thêm column mới mà BI cần dùng:**
1. Thêm definition vào `docs/analytics-handbook/semantic/` trước (đặt đúng file: segments/metrics/dimensions/rules)
2. Implement column trong mart
3. Báo cho analytics team biết column mới sẵn sàng

**Không được:**
- Tự rename semantic column mà không update `docs/analytics-handbook/semantic/`
- Thay đổi business rule của scope flag (scope_retail, scope_b2b, scope_sales) mà không update semantic docs
- Xóa column đang là semantic concept mà không có migration plan

### Semantic columns quan trọng — không sửa logic mà không có approval

| Column | File | Rule |
|---|---|---|
| `scope_sales` | `semantic/segments.md` | is_sales_channel AND NOT cancelled/voided |
| `scope_retail` | `semantic/segments.md` | scope_sales AND customer_type='RETAIL' |
| `scope_b2b` | `semantic/segments.md` | scope_sales AND customer_type IN (WHOLESALE, PARTNER) |
| `net_revenue` | `semantic/metrics.md` | total_collected − vat_amount |
| `date_key` | `semantic/dimensions.md` | ICT timezone, NOT UTC |
| `is_completed` | `semantic/rules.md` | fulfilled AND paid |

---
**Note**: These rules supplement the global `AGENTS.md`. In case of conflict regarding *dbt specifics*, this file takes precedence.
