# Transformation Layer Agents Guidelines

**Scope**: This document establishes specific rules and heuristics for AI Agents working within the `data-integration/transformation` (dbt) directory.

> **Source versioning & the std gate (Sapo v2→v3):** before adding/changing any Sapo entity, read `docs/architecture/std-layer-conventions.md` (std gate rule, faithful pass-through, `_v2`/`_v3` suffix, std contract, checksum+fresh-run verification, never move raw/dlt state). Column/model names: `docs/architecture/naming-conventions.md`.

## Module layout (read first)

Models live in `models/<module>/<layer>/` (design: `docs/architecture/modules.md`):

| Module folder | Bucket | Reads |
|---|---|---|
| `connectors/<source>/` | `connector:<source>` | its own dbt sources and models |
| `cdm/` | `cdm` (the `std_*` canonical layer) | connectors |
| `core/` | `core` | `cdm`, `core` |
| `packs/<pack>/` | `pack:<pack>` | `cdm`, `core`, its declared connector (`crm`, `hug`, `finance`, `sales_playbook`, `marketplace`, `facebook_*`; each has a README) |
| `tenants/<tenant>/` | `tenant:<tenant>` | anything (`tenants/fine_japan/`: US shipment only) |
| `monitoring/` | `monitoring` | anything (read only) |

The layer folder (`staging`, `intermediate`, `marts`) decides schema, materialization and tags
through the layer anchors in `dbt_project.yml`; the module folder never does, so moving a model
between modules keeps its relation. Every model is listed in `scripts/checks/model_buckets.yaml`
and `python3 scripts/checks/check_boundaries.py --manifest target/manifest.json` must pass.
The old top-level `staging/`, `intermediate/`, `marts/` folders are gone; a new model goes into
a module folder. Logic is product (pack), data and configuration belong to the business
(tenant): Fine Japan's business seeds live in `seeds/tenants/fine_japan/`. Core reading a tenant
is a hook that must be listed in `scripts/checks/boundary_allowlist.yaml`.

Packs can be switched off (design: `docs/architecture/modules.md` §8.1):

- **Core reads a pack only through `pack_ref`.** Write it literally and positionally:
  `{{ pack_ref('<pack>', '<model>') }}` (optionally a third argument, a subset of the contract
  columns). `check_boundaries.py` accepts a core -> pack edge only for that spelling, only when
  the model has no direct `ref('<model>')` and only when the model has a contract. Never add a
  direct `ref()` from core to a pack model (none is allowlisted any more). A core model that needs
  only revenue reads core (e.g. `int_sku_sales_monthly`, the revenue half of the finance mart
  `mart_sku_economics_monthly`), not the pack.
- Gate step 6b (`scripts/shadow/gate.sh`) builds the project with every pack off; it must stay
  green.
- **The contract lives in `pack_contracts()`** (`macros/packs/pack_contracts.sql`): one entry
  `'<model>': {'pack': '<pack>', 'columns': {'<column>': '<DuckDB type>', ...}}` per pack model
  core reads, listing only the columns core uses. Attach `data_tests: - pack_contract` to that
  model in the pack's properties file so a type or column change in the pack fails the build.
  With the pack on, `pack_ref` compiles to exactly what `ref()` did; off, to an empty relation
  with these columns, so read pack data with `LEFT JOIN` (an inner or cross join returns no rows).
- **The switch is declared three times and checked** (`check_boundaries.py` rule
  `module-config`): `packs:` in `orchestration/config/modules.yaml` (source), `vars.enabled_packs`
  in `dbt_project.yml`, and the default list inside the `+enabled` of every
  `models: sapo_warehouse: packs: <id>:` (dbt renders `dbt_project.yml` before its own `vars:`,
  so the default must be repeated there). A new pack folder needs its `+enabled` line and an
  entry in `pack_ids()` (`macros/packs/pack_enabled.sql`); the check prints the block to paste.
- A pack may still `ref()` another pack it depends on (hug -> finance, finance -> marketplace,
  sales_playbook -> crm): turning the target off fails `dbt parse`, by design.
- Tests that `ref` a disabled model are disabled by dbt silently. Keep singular tests where they
  are; scripts reading `manifest.nodes` must skip `config.enabled = false`.

Seeds: every module may read `seeds/taxonomy/`. A tenant seed (`seeds/tenants/<tenant>/`) may be
read by packs, `monitoring` and that tenant only; `cdm` and connectors may not, and **core only
through `{{ tenant_ref('<seed>') }}`** (written literally; rule `dbt-seed`). `tenant_ref` reads the
tenant's seed when the dbt variable `tenant` is set (Fine Japan: `fine_japan`, equal to `tenants:`
in `orchestration/config/modules.yaml`) and the core default `seeds/defaults/<seed>__default.csv`
(header only, 0 rows) when it is empty. Today: `dim_channel_targets` (`seed_channel_targets`),
`dim_sku_alias` (`seed_sku_alias_manual`), `int_customer_sku_supply_tracking`
(`seed_sku_regimen_config`). A new seed read by core needs a default with the same header and a
`+column_types` entry for **every** column under `seeds: sapo_warehouse: defaults:` (an untyped
header-only CSV loads as INTEGER); a new tenant must ship every seed core reads, header copied
from the default (rule `tenant-seed-contract`; `seeds/defaults/README.md`).

Before committing, run `scripts/checks/run-all.sh` (dbt parse, boundaries, Dagster definitions,
pytest). Decisions behind this layout: `docs/decisions/015-module-boundaries.md`,
`016-taxonomy-module.md`, `017-packs-and-tenants.md`.

## Classification rules (taxonomy)

Every rule that assigns a business label (`customer_type`, `value_group`, `channel_category`,
`discount_type`, tag category, ...) is inventoried in `docs/TAXONOMY.md`: where it lives, how many
real variants exist, exact semantics, and what is still SQL versus data. Read it before changing or
adding such a rule, and update it in the same change.

- Seeds that classify live in `seeds/taxonomy/`; business data of a tenant in `seeds/tenants/<tenant>/`. Python code finds a seed by name with
  `seed_path("<name>")` from `ingestion/src/utils/seed_paths.py`; never hard-code the folder.
  Seed names stay unique across folders (`check_boundaries.py` rule `seed-duplicate`).
- `+column_types` for a seed in a subfolder goes under that folder's key in the `seeds:` block of
  `dbt_project.yml` (the key is the folder path, not the seed name alone).
- `python3 scripts/checks/check_taxonomy_inventory.py` compares the `CASE` blocks and expressions
  with `scripts/checks/taxonomy_inventory.yaml` (warn only, exit 0), next to `check_boundaries.py`.
  `WARN changed` means a rule was edited: update `TAXONOMY.md` and re-record the hash
  in the inventory file (`--list` prints the current line and sha256 of every `CASE` block).
  `WARN new` means a new `CASE` assigns a known taxonomy column: add it to the inventory and the
  spec, or reuse the existing rule. The shadow gate prints these warnings in step 3c.
- Do not change a classification rule while moving files; a rule change alters numbers and goes
  through the S gate with the impact stated.

## Core Mandates

### 1. Mart Location Configuration (CRITICAL)

All models in a `marts/` layer folder (`models/*/marts/`, `models/packs/*/marts/`, ...) that are served MUST explicitly define their export location to support the Serving Layer (Rolling Snapshots).

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
- **Example**: If creating `dim_new.sql` in `models/core/marts/`, compare it with `dim_products.sql` or `dim_staff.sql` to verify config patterns.

### 3. Materialization Rules

- **Sources (`models/connectors/<source>/staging/src_*`)**:
  - Default: `incremental` (delete+insert)
  - Purpose: JSON extraction + dedup from raw parquet. Output flat columns, no payload.
- **Staging (`models/connectors/<source>/staging/stg_*`)**:
  - Default: `view`
  - Purpose: Enrichment joins, unnest. Reads from src_ (flat data). Lightweight.
- **Intermediate (`models/<module>/intermediate/`)**:
  - Default: `ephemeral` or `table` (if reused heavily).
  - Purpose: Business logic, heavy joins.
  - **Note**: Intermediate models are NOT exported to the data lake for Serving.
- **Marts (`models/<module>/marts/`)**:
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

### Rolling Parquet Files Accumulating (Direct Reads Return Inflated Data)

- **Symptom**: `read_parquet('rolling/fact_orders/*.parquet')` returns N× duplicate rows. `ls` shows >3 files per table (e.g., 12 files instead of 3).
- **Root cause**: `refresh_rolling.py` (GC logic, `ROLLING_KEEP_VERSIONS=3`) is called by the Dagster `serving_asset`, which depends on `sapo_dbt_assets`. When `sapo_dbt_assets` is materialized manually or selectively without triggering the downstream `serving_asset`, new parquet files are written but old ones are never deleted.
- **Serving DB unaffected**: `olap.duckdb` views point to `MAX(filename)` (latest file) — not a glob. Metabase reads are always correct. Only direct `read_parquet('/*.parquet')` glob queries are affected.
- **Manual fix**: `docker exec data_platform python3 /app/scripts/provisioning/refresh_rolling.py` — runs GC immediately, safe to run at any time.
- **Permanent fix**: See `plans/260609-1213-rolling-parquet-cleanup/` — move GC into dbt asset post-execution so it runs on every materialization.

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
| `scope_sales` | `semantic/segments.md` | is_sales_channel (pure channel, no status gate) |
| `scope_retail` | `semantic/segments.md` | scope_sales AND customer_type='RETAIL' |
| `scope_b2b` | `semantic/segments.md` | scope_sales AND customer_type IN (WHOLESALE, PARTNER) |
| `is_active_order` | `semantic/segments.md` | status != 'CANCELLED' — revenue gate, combine with scope_* |
| `net_revenue` | `semantic/metrics.md` | total_collected − vat_amount |
| `date_key` | `semantic/dimensions.md` | ICT timezone, NOT UTC |
| `is_completed` | `semantic/rules.md` | fulfilled AND paid |

---
**Note**: These rules supplement the global `AGENTS.md`. In case of conflict regarding *dbt specifics*, this file takes precedence.
