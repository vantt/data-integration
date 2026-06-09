# Sapo Products Pipeline — Wiring Audit

## Executive Summary

`sapo_products_batch_asset` has correct Dagster asset plumbing (health recording, job inclusion, SLA, alerting all wired), but has **two critical gaps**: (1) no Dagster asset lineage link between `sapo_products_batch_asset` and its downstream dbt models (`src_sapo_products` → `stg_sapo_products` → variants/prices/inventories) because `SapoDbtTranslator` omits `product` source mapping; (2) the four staging models in the product chain (`stg_sapo_products`, `stg_sapo_variants`, `stg_sapo_variant_prices`, `stg_sapo_inventories`) are **orphaned — not referenced by any mart** including `dim_products`, which still reads from `std_order_items` (order-item-extracted products, not the dedicated product sync).

---

## Chain-by-Chain Audit

### 1. Asset Definition + Scheduling

**Status: ⚠️**

**Findings:**
- `sapo_products_batch_asset` defined at line 194 in `orchestration/assets/sapo_assets.py`.
- `group_name="sapo_ingestion"`, `key_prefix=["sapo"]` — correct.
- `load_dlt_configuration()` called ✅
- `os.chdir(DLT_DIR)` + `finally: os.chdir(cwd)` pattern ✅
- `argv=["--full-refresh"] if is_full_refresh else []` — reads `context.run.tags.get("full_refresh")` ✅
- `_record_health()` called in `finally` block with correct `asset_key="sapo/sapo_products_batch_asset"` and `run_id=context.run_id` — composite PK (`asset_key + run_id`) matches `ingestion_runs` schema ✅
- `load_info = run_products_batch.run(argv=argv)` — return value captured ✅ (L36 pattern: `return run_pipeline()` is the runner's responsibility; this audit notes it's in scope of the fix being done by the other agent)

**Missing: `op_tags={"dagster/concurrency_key": "duckdb_lock"}`**
- None of the sapo ingestion assets have this tag; they rely solely on `concurrency_group: dbt_rw` at the job level.
- Orders batch also lacks `duckdb_lock` — consistent behavior, but **inconsistent with dbt.py** which has it.
- In practice, `dbt_rw=1` mutex prevents concurrent DuckDB writes. But if a batch asset is launched **standalone** (not via its job), the `duckdb_lock` concurrency pool is not engaged → potential lock collision with dbt runs.

**Compare vs orders.py asset:** Identical pattern — products is a faithful copy of customers/accounts. No structural gap vs orders.

---

### 2. Job + Schedule

**Status: ✅**

**Findings:**
- `sapo_products_batch_asset` included in `_nightly_batch_selection` (definitions.py line 156) ✅
- `transform_batch_nightly_job` uses `_nightly_batch_selection` → products is in nightly job ✅
- `transform_batch_fullrefresh_job` also uses `_nightly_batch_selection` → full-refresh wired ✅
- `fullrefresh_job` tags `{"full_refresh": "true"}` → asset reads this tag correctly ✅
- Schedule: `transform_batch_nightly_schedule` fires `0 3 * * *` (3 AM ICT) ✅
- Self-overlap check via `_has_active_run()` ✅
- `SYNC_TAGS = {"concurrency_group": "dbt_rw"}` applied to both nightly and fullrefresh jobs ✅

**Downstream mart lineage in nightly job:** `all_dbt_assets` is included in `_nightly_batch_selection` (line 162) → `sapo_dbt_assets` (dbt build) runs after all batch ingestion assets → `src_sapo_products` → `stg_sapo_products` → variants/prices/inventories will be built. But note: these staging models are **not consumed by any mart** (see Chain 4).

---

### 3. SLA + Health Monitoring

**Status: ✅ (with one soft gap)**

**Findings:**
- `ingestion_sla.yaml`: `sapo/sapo_products_batch_asset` entry present with `freshness_hours: 28` ✅
- Default `trend_min_ratio: 0.5` applies (not null) → row trend check WILL fire ✅
- `trend_window_days: 7` default applies ✅
- `cursor_empty_streak: 3` default applies ✅
- `__init__.py`: `sapo/sapo_products_batch_asset` mapped to `sapo_assets.sapo_products_batch_asset` ✅
- All 4 check types wired: freshness, not_empty, row_trend, cursor_stall ✅
- `cursor_checks.py`: `sapo/sapo_products_batch_asset` in `CURSOR_CHECK_ASSET_KEYS` ✅

**Soft gap — `trend_min_ratio` may false-positive on full-refresh bootstrap:**
- After a full-refresh run ingests thousands of rows, the 7-day median will be high. Next nightly incremental (few dozen rows changed) triggers trend check WARN. Not a bug but expected behavior to tolerate.

**No `max_age_hours` key:** SLA YAML has no separate `max_age_hours` — freshness is the single staleness signal. Consistent with all other batch assets.

**No `trend_min_ratio: null` override:** Unlike file-drop assets, products has trend check enabled. If business has days with zero product updates, this will WARN. Expected but worth noting.

---

### 4. dbt Sources + Downstream

**Status: ❌ (two critical gaps)**

**Findings:**

**Gap A — `SapoDbtTranslator` missing `product` source mapping:**

`orchestration/assets/dbt.py` maps:
- `sapo_raw.order` → `sapo_orders_batch_asset` ✅
- `sapo_raw.customer` → `sapo_customers_batch_asset` ✅
- `sapo_raw.account` → `sapo_accounts_batch_asset` ✅
- `sapo_raw.product` → **NOT MAPPED** ❌

The `product` source falls through to `super().get_asset_key()` → gets a generic dbt source key, not `["sapo", "sapo_products_batch_asset"]`. Dagster asset graph **does not show lineage** between `sapo_products_batch_asset` and `src_sapo_products`. This means:
- No DAG edge: Dagster won't auto-downstream `src_sapo_products` after `sapo_products_batch_asset` materializes.
- In nightly job with `all_dbt_assets`, dbt still runs and rebuilds `src_sapo_products` — so data still flows. But lineage visibility in Dagster UI is broken.
- Asset catalog shows `sapo_products_batch_asset` as isolated from the dbt graph.

**Gap B — `dim_products` does NOT consume the product batch pipeline:**

`transformation/models/marts/core/dim_products.sql` reads from `std_order_items` only:
- Comment at line 17: *"Since we don't have a dedicated Product Sync yet, we extract products from Order Items."*
- **This comment is stale** — `sapo_products_batch_asset` exists and the full staging chain is built. But `dim_products` still uses order-item-extracted product metadata.
- `stg_sapo_products`, `stg_sapo_variants`, `stg_sapo_variant_prices`, `stg_sapo_inventories` are **never referenced** by any mart or intermediate model.
- The pipeline builds these 4 staging models on every nightly run, but they are **dead-end models** — no downstream consumer exists.

**Downstream dependency graph (actual):**
```
sapo_products_batch_asset → [parquet files] → src_sapo_products (dedup)
                                               → stg_sapo_products (orphan, no mart consumer)
                                               → stg_sapo_variants (orphan)
                                                  → stg_sapo_variant_prices (orphan)
                                                  → stg_sapo_inventories (orphan)

dim_products ← std_order_items ← fact_sales / std_orders  [INDEPENDENT CHAIN, no product batch]
```

**Source definition:** `sources.yml` defines `sapo_raw.product` with `external_location: "read_parquet(...)/sapo_raw/product/ingest_method=*/**/*.parquet"` ✅. Pattern requires parquet — JSONL output (the current bug) would cause `src_sapo_products` to silently find 0 files → empty table → all downstream views empty. This **confirms the severity** of the mechanism bug being fixed.

**ingest_method priority in `src_sapo_products.sql`:**
- Tech dedup (lines 58-65): `webhook=3, history_log=2, else=1` ORDER BY DESC → webhook wins ✅
- Business dedup (lines 136-140): `webhook=1, history_log=2, else=3` ORDER BY ASC → webhook=1=first row wins ✅ (different encoding, same result)

---

### 5. Serving Layer

**Status: ⚠️ (indirect gap)**

**Findings:**
- `bootstrap_serving_views.py` auto-discovers subdirs under `rolling/` and creates views for any mart that writes a parquet file there ✅
- `dim_products` is materialized as external parquet (`tags=['mart', 'dim']`, `location="{{ get_rolling_location() }}"`) → a view for `dim_products` IS created and served to Metabase ✅
- BUT `dim_products` reads from `std_order_items` (order-extracted), not from `stg_sapo_products` → product batch data never reaches Metabase even when pipeline is fixed.
- No explicit "refresh-after-build" hook beyond the nightly job running dbt → serving → view auto-refresh at query time (rolling view pattern) ✅
- `stg_sapo_products` / `stg_sapo_variants` / `stg_sapo_inventories` / `stg_sapo_variant_prices` are staging views (not external parquet) → no serving layer exposure needed for them.

---

### 6. Telemetry + Alerting

**Status: ✅**

**Findings:**
- `record_health` writes to `ingestion_health.db` (SQLite WAL), table `ingestion_runs`, PK `(asset_key, run_id)` ✅
- `morning_digest.py`: `sapo_products` included in `KNOWN_ASSETS` (line 36) as `("sapo_products", "sapo/sapo_products_batch_asset", None)` ✅
- `ASSET_DISPLAY`: `"sapo_products": ("Sapo sản phẩm", "batch", "sản phẩm")` ✅ — classified as `batch` type, correct interpretation
- No recon pair for products (recon_key=None in morning digest) — orders and customers have recon, products does not. Acceptable given products change infrequently.
- Failure alerting: `health_alert_failure_sensor` is `@run_failure_sensor(minimum_interval_seconds=60)` with no job filter → fires on ALL job failures including nightly job when products asset fails ✅
- Lark alert sent via `send_lark_card` with job name + run link ✅
- `health_concurrency_pool_janitor` sensor monitors pool slots to auto-free stale duckdb_lock slots ✅

---

## Critical Gaps (Ranked by Severity)

1. **[CRITICAL] Mechanism bug: `run_products_batch.run()` outputs JSONL.GZ not parquet** — being fixed by other agent. Until fixed: `src_sapo_products` reads 0 files → entire staging chain empty → dim_products unaffected (still reads from orders) but product-specific marts/reports would be empty if they existed.

2. **[CRITICAL] `dim_products` still reads from `std_order_items` — does NOT consume `stg_sapo_products`** — the dedicated product sync pipeline ends at staging, no mart integrates it. `dim_products` still carries the "no dedicated product sync yet" comment as if the pipeline doesn't exist. After the mechanism fix, product data still won't reach `dim_products` or any fact table via the product chain.

3. **[HIGH] `SapoDbtTranslator` missing `product` source → no Dagster lineage** — Dagster asset graph won't show `sapo_products_batch_asset → src_sapo_products` edge. No operational impact on data flow (dbt build runs all models regardless), but lineage tracking, asset freshness propagation, and downstream re-run cascades are broken.

4. **[MED] Orphaned staging models** — `stg_sapo_products`, `stg_sapo_variants`, `stg_sapo_variant_prices`, `stg_sapo_inventories` build on every nightly run (dbt build rebuilds all `otp`-tagged models) but have zero downstream consumers. Wasted dbt compute + misleading dbt DAG.

5. **[MED] No `op_tags={"dagster/concurrency_key": "duckdb_lock"}` on batch assets** — All sapo batch assets (including products) lack asset-level concurrency pool protection. Safe in normal operation (job-level `dbt_rw` mutex suffices), but standalone manual launches bypass the pool. Consistent with orders/customers/accounts but inconsistent with the dbt asset and backup op.

6. **[LOW] No reconciliation check for products** — Orders and customers have `recon` assets that cross-check API counts vs warehouse. Products has no recon. Silent data gap (missing products) won't be caught by health monitoring. Morning digest shows `recon_key=None`.

---

## Recommendations (per gap, with concrete fix)

**Gap 2 (CRITICAL — dim_products not consuming product batch):**
- Edit `transformation/models/marts/core/dim_products.sql`:
  - Replace `std_order_items` CTE with join to `stg_sapo_products` + `stg_sapo_variants` as primary source.
  - Fall back to `std_order_items` for products not in `stg_sapo_products` (COALESCE pattern).
  - Remove stale comment "Since we don't have a dedicated Product Sync yet".
- This is the highest-value change: unlocks variant SKU, barcode, category, brand, inventory data that orders cannot provide.

**Gap 3 (HIGH — translator missing product mapping):**
- Edit `orchestration/assets/dbt.py`, `SapoDbtTranslator.get_asset_key()`:
  - Add `elif name == "product": return AssetKey(["sapo", "sapo_products_batch_asset"])` after the `account` branch (line 38).
- One-line fix restores Dagster lineage edge.

**Gap 4 (MED — orphaned staging models):**
- After fixing dim_products (Gap 2), staging models will have consumers → no longer orphaned.
- No separate action needed; Gap 2 fix resolves this.

**Gap 5 (MED — no duckdb_lock op tag on batch assets):**
- Edit `orchestration/assets/sapo_assets.py`, all `@asset()` decorators:
  - Add `op_tags={"dagster/concurrency_key": "duckdb_lock"}` to `sapo_products_batch_asset` (and other batch assets for consistency).
- Prevents lock collision in standalone launches.

**Gap 6 (LOW — no products recon):**
- Add `recon_sapo_products_daily` asset to `orchestration/assets/reconciliation.py` following same pattern as orders recon.
- Wire into `health_recon_daily_job` and morning digest `KNOWN_ASSETS`.
- Defer until product sync is stable (after Gap 2 fix).

---

## Comparison Matrix vs `sapo_orders_batch`

| Aspect | Orders | Products | Match? |
|--------|--------|----------|--------|
| Asset decorator tags | `group_name`, `key_prefix` only | same | ✅ |
| `op_tags` duckdb_lock | Missing (same gap) | Missing | ✅ consistent gap |
| `load_dlt_configuration()` | ✅ | ✅ | ✅ |
| `os.chdir(DLT_DIR)` + restore | ✅ | ✅ | ✅ |
| `argv=[]` / `--full-refresh` | ✅ | ✅ | ✅ |
| `_record_health()` in finally | ✅ | ✅ | ✅ |
| Composite PK `asset_key+run_id` | ✅ | ✅ | ✅ |
| SLA freshness_hours | 28h | 28h | ✅ |
| `trend_min_ratio` | 0.5 (default) | 0.5 (default) | ✅ |
| Cursor stall check | ✅ | ✅ | ✅ |
| Dagster lineage (translator) | ✅ mapped | ❌ NOT mapped | ❌ |
| dbt `src_` model | ✅ `src_sapo_orders` | ✅ `src_sapo_products` | ✅ |
| Source → mart consumption | ✅ `fact_orders` | ❌ staging orphaned | ❌ |
| `dim_products` consumes it | N/A | ❌ still reads orders | ❌ |
| Reconciliation check | ✅ `recon_sapo_orders_daily` | ❌ none | ❌ |
| Morning digest entry | ✅ | ✅ | ✅ |
| Job inclusion (nightly) | ✅ | ✅ | ✅ |
| Full-refresh job | ✅ | ✅ | ✅ |

---

## Unresolved Questions

1. **After Gap 2 fix (dim_products), is `std_order_items` still the right fallback for historical products?** Orders date back to 2021; products batch only covers what's ingested. Without a full-refresh products load, some old products may be missing from `stg_sapo_products`. Need to confirm full-refresh has run or plan one post-fix.

2. **Does `stg_sapo_variants` correctly extract all variant-level fields needed by `dim_products`?** Current `dim_products` uses `variant_id`, `sku`, `barcode`, `variant_name` from `std_order_items`. `stg_sapo_variants` has all these fields — but `dim_products` redesign needs careful column reconciliation.

3. **Should `stg_sapo_inventories` power a `fact_inventory` model?** The staging model extracts on_hand/available/committed stock by location. No fact table uses it. If the intent was a real-time inventory snapshot, this needs a mart design decision before the pipeline fix is considered "end-to-end complete".

4. **Has `run_products_batch.run()` ever successfully written parquet?** If the JSONL.GZ mechanism was the original (never-fixed) state, `src_sapo_products` may have never had data. Post-fix will require a full-refresh run to bootstrap the data lake partition.

---

**Status:** DONE_WITH_CONCERNS
**Summary:** Wiring is structurally sound at the Dagster level (job, schedule, SLA, alerting all correct), but two critical semantic gaps exist: `dim_products` doesn't consume the product sync (still order-extracted), and `SapoDbtTranslator` is missing the `product` source mapping. After the mechanism fix, product data will still not reach `dim_products` without additional dbt changes.
**Concerns:** Gap 2 (dim_products) is likely the primary business value gap — the pipeline fix alone will not deliver product data to dashboards without updating `dim_products` to consume `stg_sapo_products`.
