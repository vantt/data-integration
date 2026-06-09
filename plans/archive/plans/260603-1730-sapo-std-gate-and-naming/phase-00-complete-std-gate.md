---
title: "Phase 0 — Complete the std gate (structural, no renames)"
description: "Create 6 missing std models, repoint 8 bypassing consumers, add source_version='v2', schema tests, validation harness."
status: complete
priority: P1
effort: 6h
---

# Phase 0 — Complete the std gate

## Context links
- Analysis: `plans/reports/arch-260603-1730-sapo-v2-v3-migration-gate.md` §§ T0.1–T0.7
- Naming rules: `docs/architecture/naming-conventions.md`
- Verification toolkit: `plans/260603-1730-sapo-std-gate-and-naming/verification-protocol.md`
- Existing std models: `transformation/models/staging/standard/`
- Existing schema tests: `transformation/models/staging/standard/schema.yml`

---

## Overview
- **Priority:** P1 — blocks all rename phases and future v3 union
- **Status:** complete (2026-06-04)
- **Risk level:** Low — pure structural refactor; v2 data flows unchanged through thin pass-through models
- **Validation gate:** byte-identical row counts + key-column checksums before/after (T3 harness)
- **Lock strategy:** Strategy A (pause both realtime + incremental schedules) for Steps that run `dbt build`. Steps that only run `dbt parse` or read parquet are lock-free.

---

## Key insights
- The std layer currently has 6 models (`std_orders, std_order_items, std_fulfillments, std_payments, std_customers, std_accounts`). Six entities bypass std entirely and feed dims/facts directly from `stg_sapo_*`.
- `fact_orders` reads `stg_sapo_order_discount_items` directly (a v2 leak past the gate).
- `int_order_tags` reads `src_sapo_orders` directly — a src-level bypass. Decision: defer to v3 work (T0.4 option a).
- Principle: new std models are **thin pass-through** — same column names as the stg source, plus `source_system='sapo'` and `source_version='v2'`. No renames here; renaming is Phase 1+.
- **Decomposition order:** one entity at a time. Create std_X → checkpoint → repoint its consumers → checkpoint → commit. A failure isolates to one entity.

---

## Architecture — data flow after P0

```
src_sapo_products
  └─ stg_sapo_products ──→ std_products ──→ dim_products
  └─ stg_sapo_variants ──→ std_variants ──→ dim_products, dim_sku_alias
       └─ stg_sapo_inventories ──→ std_inventories ──→ int_sapo_inventories
       └─ stg_sapo_variant_prices ──→ std_variant_prices ──→ dim_price_lists, fact_variant_prices_snapshot

src_sapo_order_returns
  └─ stg_sapo_order_returns ──→ std_order_returns ──→ fact_order_returns

src_sapo_orders
  └─ stg_sapo_orders ──→ stg_sapo_order_discount_items ──→ std_order_discount_items ──→ fact_order_costs, fact_orders

(int_order_tags: keep reading src_sapo_orders for now — T0.4 deferred)
```

---

## Implementation steps

### PRE-STEP: Capture parquet baseline (T3 harness)

Before touching any SQL, capture baseline checksums for ALL affected marts. Save to `plans/260603-1730-sapo-std-gate-and-naming/snapshots/pre_p0.txt`.

Run T3 checksum script (see verification-protocol.md §T3) covering:
`dim_products, dim_sku_alias, dim_price_lists, fact_variant_prices_snapshot, fact_order_returns, fact_order_costs, fact_orders, mart_inventory_health`

This is lock-free — runs anytime.

**PASS:** File written, all marts return row counts > 0. No exceptions.
**ROLLBACK:** n/a — read-only.

---

### STEP 0.1 — Add `source_version='v2'` to 6 existing std models

**Change:** For each of `std_orders, std_order_items, std_fulfillments, std_payments, std_customers, std_accounts`:
- Add `'v2' AS source_version` to the SELECT list.
- Also add `'sapo' AS source_system` to models that lack it (`std_order_items`, `std_fulfillments`, `std_payments`, `std_accounts` — verify by reading each).

**Why first:** These are views with no downstream column impact (no consumer reads `source_version` yet). Zero risk; establishes the pattern before new models.

**Checkpoint (lock-free parse then Strategy A build):**

```bash
# T1 — parse
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"

# Strategy A: pause schedules, then build
docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select std_orders std_order_items std_fulfillments std_payments std_customers std_accounts --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"

# T4 — confirm next realtime run is green
docker logs data_platform --since 5m 2>&1 | grep -iE "RUN_SUCCESS|RUN_FAILURE|tests:|ERROR"
```

**PASS:** `dbt build` exits 0; next realtime run shows RUN_SUCCESS.
**ROLLBACK:** `git checkout -- transformation/models/staging/standard/std_*.sql` (the 6 existing ones); re-parse; no serving rebuild.
**COMMIT:** `git add transformation/models/staging/standard/std_{orders,order_items,fulfillments,payments,customers,accounts}.sql && git commit -m "feat(std): add source_version='v2' to existing 6 std models"`

---

### STEP 0.2 — Create `std_order_discount_items` + repoint `fact_orders` + `fact_order_costs`

**Why this entity first:** `fact_orders` is the highest-value mart. Closing this v2-leak is the single most important structural fix.

**Change A — create `transformation/models/staging/standard/std_order_discount_items.sql`:**

```sql
{{ config(materialized='view', tags=['standard', 'orders', 'discounts']) }}
WITH source_data AS (SELECT * FROM {{ ref('stg_sapo_order_discount_items') }})
SELECT
    order_id,
    order_code,
    created_at,
    discount_source,
    discount_rate,
    discount_value,
    amount,
    reason,
    'sapo' AS source_system,
    'v2'   AS source_version
FROM source_data
```

Add to `transformation/models/staging/standard/schema.yml`:
```yaml
- name: std_order_discount_items
  description: "Standardized order discount items. Grain: 1/(order_id × discount_source × reason)."
  columns:
    - name: order_id
      tests: [not_null]
    - name: order_code
      tests: [not_null]
```

**Checkpoint A (parse + build std only):**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"
# Then Strategy A:
docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select std_order_discount_items --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
```
PASS: exits 0, `std_order_discount_items` schema tests pass.

**Change B — repoint consumers:**
- `transformation/models/marts/sales/fact_order_costs.sql`: `ref('stg_sapo_order_discount_items')` → `ref('std_order_discount_items')`
- `transformation/models/marts/sales/fact_orders.sql` (in `discount_classified` CTE): `ref('stg_sapo_order_discount_items')` → `ref('std_order_discount_items')`

**Checkpoint B (parse + build consumers + parquet checksum):**
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"
# Strategy A:
docker exec data_platform sh -c "dagster schedule stop ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule stop ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
docker exec data_platform sh -c "cd /app && dbt build --select fact_order_costs fact_orders --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -15"
docker exec data_platform sh -c "dagster schedule start ingest_sapo_realtime_schedule -f /app/orchestration/definitions.py && dagster schedule start ingest_sapo_incremental_schedule -f /app/orchestration/definitions.py"
# T3 — parquet checksum for fact_orders + fact_order_costs — must match pre_p0.txt baseline
```

PASS: `dbt build` exits 0; parquet checksums for `fact_orders` and `fact_order_costs` match pre_p0.txt baseline exactly.
**ROLLBACK:** `git checkout -- transformation/models/marts/sales/fact_order_costs.sql transformation/models/marts/sales/fact_orders.sql`; delete `std_order_discount_items.sql`; re-build the two marts.
**COMMIT:** `git add ... && git commit -m "feat(std): add std_order_discount_items; repoint fact_orders + fact_order_costs"`

---

### STEP 0.3 — Create `std_order_returns` + repoint `fact_order_returns`

**Change A:**
```sql
-- transformation/models/staging/standard/std_order_returns.sql
{{ config(materialized='view', tags=['standard', 'returns']) }}
WITH source_data AS (SELECT * FROM {{ ref('stg_sapo_order_returns') }})
SELECT
    return_id,
    order_id,
    order_code,
    return_status,
    refund_status,
    return_reason,
    refund_amount,
    return_quantity,
    issued_at,
    received_at,
    created_at,
    modified_at,
    'sapo' AS source_system,
    'v2'   AS source_version
FROM source_data
```

Add to `schema.yml`:
```yaml
- name: std_order_returns
  description: "Standardized order returns. Grain: 1/return_id."
  columns:
    - name: return_id
      tests: [unique, not_null]
    - name: order_id
      tests: [not_null]
```

**Checkpoint A (parse + build std):** same pattern as Step 0.2 checkpoint A, targeting `std_order_returns`.
PASS: exits 0, PK unique test passes.

**Change B:** `transformation/models/marts/sales/fact_order_returns.sql`: `ref('stg_sapo_order_returns')` → `ref('std_order_returns')`

**Checkpoint B:**
```bash
# Parse, Strategy A build, parquet checksum
docker exec data_platform sh -c "cd /app && dbt build --select fact_order_returns --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
# T3 checksum for fact_order_returns — compare to pre_p0.txt
```
PASS: `fact_order_returns` parquet checksum matches baseline.
**ROLLBACK:** revert `fact_order_returns.sql`; delete `std_order_returns.sql`.
**COMMIT:** `git commit -m "feat(std): add std_order_returns; repoint fact_order_returns"`

---

### STEP 0.4 — Create `std_variants` + repoint `dim_products` (variants CTE) + `dim_sku_alias` + `int_sapo_inventories` (variants ref)

**Critical note:** `int_sapo_inventories` reads `stg_sapo_variants` directly and re-unnests `inventories_json`. `std_variants` MUST pass through `inventories_json`. Verify the column is in the SELECT below.

**Change A — create `std_variants.sql`:**
```sql
{{ config(materialized='view', tags=['standard', 'products', 'variants']) }}
WITH source_data AS (SELECT * FROM {{ ref('stg_sapo_variants') }})
SELECT
    variant_id,
    product_id,
    sku,
    barcode,
    variant_name,
    product_name,
    opt1_value, opt2_value, opt3_value,
    variant_status,
    is_sellable,
    is_composite,
    retail_price,
    wholesale_price,
    import_price,
    init_price,
    unit,
    weight_value,
    weight_unit,
    is_taxable,
    is_tax_included,
    input_vat_rate,
    output_vat_rate,
    is_packsize,
    packsize_quantity,
    packsize_root_id,
    packsize_root_sku,
    product_type,
    created_at,
    modified_at,
    variant_prices_json,
    inventories_json,       -- CRITICAL: int_sapo_inventories reads this
    composite_items_json,
    source_timestamp,
    'sapo' AS source_system,
    'v2'   AS source_version
FROM source_data
```

Add to `schema.yml`:
```yaml
- name: std_variants
  description: "Standardized variant catalog. Grain: 1/variant_id."
  columns:
    - name: variant_id
      tests: [unique, not_null]
```

**Checkpoint A:** parse + build `std_variants` + schema test.
PASS: unique test on `variant_id` passes.

**Change B — repoint consumers (all in one edit batch; same entity group):**
- `dim_products.sql`: `ref('stg_sapo_variants')` → `ref('std_variants')`
- `dim_sku_alias.sql`: `ref('stg_sapo_variants')` → `ref('std_variants')`
- `int_sapo_inventories.sql`: `ref('stg_sapo_variants')` → `ref('std_variants')`

**Checkpoint B:**
```bash
# Strategy A
docker exec data_platform sh -c "cd /app && dbt build --select dim_products dim_sku_alias int_sapo_inventories --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -15"
# T3 checksum for dim_products, dim_sku_alias, mart_inventory_health (int_sapo_inventories is intermediate)
```
PASS: all three build; parquet checksums for `dim_products` and `dim_sku_alias` match baseline.
**ROLLBACK:** revert the 3 consumer files; delete `std_variants.sql`.
**COMMIT:** `git commit -m "feat(std): add std_variants; repoint dim_products, dim_sku_alias, int_sapo_inventories"`

---

### STEP 0.5 — Create `std_products` + repoint `dim_products` (products CTE)

**Change A — create `std_products.sql`:**
```sql
{{ config(materialized='view', tags=['standard', 'products']) }}
WITH source_data AS (SELECT * FROM {{ ref('stg_sapo_products') }})
SELECT
    product_id,
    tenant_id,
    product_name,
    product_status,
    product_type,
    description,
    brand_id,
    brand,
    category_id,
    category,
    category_code,
    opt1, opt2, opt3,
    is_medicine,
    tags,
    image_path,
    image_name,
    created_at,
    modified_at,
    variants_json,
    options_json,
    images_json,
    source_timestamp,
    'sapo' AS source_system,
    'v2'   AS source_version
FROM source_data
```

Add to `schema.yml`:
```yaml
- name: std_products
  description: "Standardized product catalog. Grain: 1/product_id."
  columns:
    - name: product_id
      tests: [unique, not_null]
```

**Checkpoint A:** parse + build `std_products`.
PASS: unique PK test passes.

**Change B:** `dim_products.sql`: `ref('stg_sapo_products')` → `ref('std_products')`

**Checkpoint B:**
```bash
docker exec data_platform sh -c "cd /app && dbt build --select dim_products --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
# T3 checksum for dim_products — must match baseline
```
PASS: parquet checksum for `dim_products` matches pre_p0.txt.
**ROLLBACK:** revert `dim_products.sql`; delete `std_products.sql`.
**COMMIT:** `git commit -m "feat(std): add std_products; repoint dim_products (products CTE)"`

---

### STEP 0.6 — SKIPPED (2026-06-03): `stg_sapo_inventories` is dead code

> **⚠️ SKIPPED.** Grep confirms `stg_sapo_inventories` has ZERO consumers (no `ref()` anywhere in the project). `int_sapo_inventories` reads inventory from `std_variants.inventories_json` (gated in Step 0.4), NOT from `stg_sapo_inventories`. So the inventory entity is ALREADY gated via std_variants; creating `std_inventories` over an unused source would violate YAGNI. `stg_sapo_inventories` is flagged as dead code for a future cleanup (out of scope). The original 0.6 below is obsolete.

#### (obsolete) STEP 0.6 — Create `std_inventories` + repoint `int_sapo_inventories` (inventories ref)

**Change A — create `std_inventories.sql`:**
```sql
{{ config(materialized='view', tags=['standard', 'products', 'inventory']) }}
WITH source_data AS (SELECT * FROM {{ ref('stg_sapo_inventories') }})
SELECT
    variant_id,
    product_id,
    sku,
    location_id,
    on_hand,
    available,
    committed,
    incoming,
    onway,
    mac,
    bin_location,
    inventory_modified_at,
    source_timestamp,
    'sapo' AS source_system,
    'v2'   AS source_version
FROM source_data
```

Add to `schema.yml`:
```yaml
- name: std_inventories
  description: "Standardized inventory snapshot. Grain: 1/(variant_id × location_id)."
  columns:
    - name: variant_id
      tests: [not_null]
    - name: location_id
      tests: [not_null]
```

**Checkpoint A:** parse + build `std_inventories`.
PASS: not_null tests pass.

**Change B:** `int_sapo_inventories.sql`: `ref('stg_sapo_inventories')` → `ref('std_inventories')`

**Checkpoint B:**
```bash
docker exec data_platform sh -c "cd /app && dbt build --select int_sapo_inventories --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
# T3 checksum for mart_inventory_health (downstream of int_sapo_inventories)
```
PASS: `mart_inventory_health` parquet checksum matches baseline.
**ROLLBACK:** revert `int_sapo_inventories.sql`; delete `std_inventories.sql`.
**COMMIT:** `git commit -m "feat(std): add std_inventories; repoint int_sapo_inventories"`

---

### STEP 0.7 — Create `std_variant_prices` + repoint `dim_price_lists` + `fact_variant_prices_snapshot`

**Critical note:** `fact_variant_prices_snapshot.sql` has TWO separate references to `stg_sapo_variant_prices` (one in `prices` CTE, one in `gianhap` CTE). Both must be updated. Use grep to confirm zero remaining `stg_sapo_variant_prices` refs in that file after edit.

**Change A — create `std_variant_prices.sql`:**
```sql
{{ config(materialized='view', tags=['standard', 'products', 'prices']) }}
WITH source_data AS (SELECT * FROM {{ ref('stg_sapo_variant_prices') }})
SELECT
    variant_id,
    product_id,
    sku,
    price_list_id,
    price_list_name,
    price_list_code,
    is_cost_price,
    price_value,
    price_incl_tax,
    source_timestamp,
    'sapo' AS source_system,
    'v2'   AS source_version
FROM source_data
```

Add to `schema.yml`:
```yaml
- name: std_variant_prices
  description: "Standardized variant prices. Grain: 1/(variant_id × price_list_id)."
  columns:
    - name: variant_id
      tests: [not_null]
    - name: price_list_id
      tests: [not_null]
```

**Checkpoint A:** parse + build `std_variant_prices`.
PASS: not_null tests pass.

**Change B:**
- `dim_price_lists.sql`: `ref('stg_sapo_variant_prices')` → `ref('std_variant_prices')`
- `fact_variant_prices_snapshot.sql`: BOTH `ref('stg_sapo_variant_prices')` → `ref('std_variant_prices')`. Verify with:
  ```bash
  grep "stg_sapo_variant_prices" transformation/models/marts/sales/fact_variant_prices_snapshot.sql
  # Must return 0 lines after edit
  ```

**Checkpoint B:**
```bash
docker exec data_platform sh -c "cd /app && dbt build --select dim_price_lists fact_variant_prices_snapshot --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -10"
# T3 checksum for dim_price_lists + fact_variant_prices_snapshot — must match baseline
```
PASS: both parquet checksums match pre_p0.txt.
**ROLLBACK:** revert `dim_price_lists.sql` + `fact_variant_prices_snapshot.sql`; delete `std_variant_prices.sql`.
**COMMIT:** `git commit -m "feat(std): add std_variant_prices; repoint dim_price_lists, fact_variant_prices_snapshot"`

---

### STEP 0.8 — Add `source_version` to `schema.yml` for existing 6 std models + T0.4 decision comment

**Change A:** Update `transformation/models/staging/standard/schema.yml` to add/update `source_version` column entries for `std_orders, std_order_items, std_fulfillments, std_payments, std_customers, std_accounts`.

**Change B:** Add T0.4 decision comment to `transformation/models/intermediate/tags/int_order_tags.sql`:
```sql
-- T0.4 DECISION (2026-06-03): int_order_tags reads src_sapo_orders directly to access
-- $.tags JSON. CURRENT DECISION: option (a) — defer to v3 work. When v3 arrives,
-- either expose tags via std_orders or add int_order_tags_v3.
-- Requires Q1-Q5 business answers before implementing the union path.
```

**Checkpoint:** `dbt parse` only (schema.yml + comment change — no build needed).
```bash
docker exec data_platform sh -c "cd /app && dbt parse --project-dir /app/transformation --profiles-dir /app/transformation 2>&1 | tail -5"
```
PASS: parse exits 0.
**ROLLBACK:** `git checkout -- transformation/models/staging/standard/schema.yml transformation/models/intermediate/tags/int_order_tags.sql`
**COMMIT:** `git commit -m "docs(std): update schema.yml source_version entries; document T0.4 int_order_tags decision"`

---

### STEP 0.9 — Full harness validation + Dagster green run confirmation

**Run T3 full checksum** against all 8 affected marts. Save to `snapshots/post_p0.txt`.

Compare `pre_p0.txt` vs `post_p0.txt`:
- Row counts must be identical for all 8 marts.
- Checksums must match exactly (pass-through added no columns that consumers select).

**Run T5 HOP counts:**
```bash
python scripts/testing/verify_hops_readonly.py
```

**Run T4 — confirm Dagster green:**
```bash
docker exec data_platform sh -c "dagster run list --limit 5"
docker logs data_platform --since 10m 2>&1 | grep -iE "RUN_SUCCESS|RUN_FAILURE|tests:|ERROR"
```

**Run T6 — DQ mart:**
```python
# Quick check — total_orders unchanged means the pipeline ran end-to-end correctly
import duckdb, glob, os
folder = r"app_data\data_lake\export\marts\rolling\mart_data_quality"
newest = sorted(glob.glob(os.path.join(folder, "*.parquet")))[-1]
print(duckdb.query(f"SELECT total_orders, cogs_rate_pct FROM read_parquet('{newest}')").df())
```

**PASS criteria (all required):**
- All 8 mart checksums match baseline
- HOP counts within expected bounds
- At least one `ingest_sapo_realtime_job` RUN_SUCCESS since changes were applied
- DQ mart `total_orders` unchanged

**If any fail:** Stop. Identify which step introduced the delta. `git revert` to that step's commit. Investigate before proceeding to Phase 1.

**COMMIT:** `git commit -m "test(std): full harness validation post-P0 — all checksums pass"`

---

### STEP 0.10 — T0.7: Document std contracts (v3 interface spec)

For each new std model SQL file, add a header comment block listing all exposed columns — this is the interface that v3 `stg_sapo_v3_*` models must satisfy.

Example for `std_order_discount_items.sql`:
```sql
-- STD CONTRACT v2 (2026-06-03)
-- Interface for v3: stg_sapo_v3_order_discount_items must produce:
--   order_id (BIGINT), order_code (VARCHAR), created_at (TIMESTAMPTZ),
--   discount_source (VARCHAR), discount_rate (DOUBLE), discount_value (DOUBLE),
--   amount (DOUBLE), reason (VARCHAR)
-- Plus: source_system='sapo', source_version IN ('v2','v3')
```

No dbt build needed — comment-only change.

**Checkpoint:** `dbt parse` exits 0.
**COMMIT:** `git commit -m "docs(std): add v3 interface contract comments to all 6 new std models"`

---

## File ownership

| File type | Files |
|-----------|-------|
| Create | `std_products.sql`, `std_variants.sql`, `std_variant_prices.sql`, `std_inventories.sql`, `std_order_returns.sql`, `std_order_discount_items.sql` |
| Modify (std) | `std_orders.sql`, `std_order_items.sql`, `std_fulfillments.sql`, `std_payments.sql`, `std_customers.sql`, `std_accounts.sql`, `schema.yml` |
| Modify (consumers) | `dim_products.sql`, `dim_sku_alias.sql`, `int_sapo_inventories.sql`, `dim_price_lists.sql`, `fact_variant_prices_snapshot.sql`, `fact_order_returns.sql`, `fact_order_costs.sql`, `fact_orders.sql`, `int_order_tags.sql` |

---

## Success criteria

- `dbt build` clean after each step (zero errors, zero test failures)
- All 6 new std model PK tests pass
- Full harness (Step 0.9): row counts + checksums byte-identical for all 8 affected marts
- `int_sapo_inventories` still materializes correctly (parquet, rolling location)
- `fact_orders` and `fact_order_costs` discount logic unchanged (same row counts, same amounts)
- At least one Dagster realtime run RUN_SUCCESS post-all-changes

---

## Risk assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `int_sapo_inventories` breaks (reads `inventories_json` from variants) | Medium | High | `std_variants` explicitly passes `inventories_json`; tested in Step 0.4 checkpoint B |
| `fact_variant_prices_snapshot` misses one of its two refs | Medium | Medium | Grep verification in Step 0.7 Change B |
| Surrogate keys in dim_products recalculate differently | Low | High | No column renames in P0 → key inputs unchanged; verified by T3 checksum |
| DuckDB write-lock conflict during manual build | Medium | Medium | Strategy A (pause schedules) for all build steps |

---

## Rollback plan (per step)

Each step has its own rollback in the step definition above. The global rollback for the entire phase:
1. `git revert` each step's commit in reverse order.
2. `dbt build --select` the affected models to restore original state.
3. No serving rebuild needed (no published column changes in P0).

---

## Next steps
After P0 passes Step 0.9 harness: proceed to Phase 1 (P1 term renames). The std contract is now complete — Phase 1 renames at std first (cheap) then cascades to published marts.
