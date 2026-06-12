# Plan: Sapo V2 Rename + Partition Isolation

**Status:** PENDING  
**Priority:** High  
**Trigger:** (1) Incident 2026-06-12 — `drop_pipeline_state` wiped shared order/ dir. (2) Forward-path: Sapo V3 ingestion incoming — rename everything upstream of std_* to `sapo_v2_*` convention to make room.

---

## Convention Decision

**Target convention: `sapo_v2_*`** (not `sapov2_*`)

- Word boundaries via underscores: `sapo_v2_orders` not `sapov2_orders`
- Cross-version grep is natural: `grep "sapo_v[0-9]"` finds all versions
- Future: `sapo_v3_orders` alongside `sapo_v2_orders` reads clearly

**Problem:** Dagster layer was already renamed to `sapov2_*` (wrong convention) in a previous session. Initiative A includes fixing those back to `sapo_v2_*`.

---

## Two Initiatives (same plan, sequential)

| # | Initiative | Scope | Risk |
|---|---|---|---|
| A | **sapo_v2_* rename** | Fix Dagster `sapov2_*` → `sapo_v2_*`, rename ingestion scripts, dlt pipeline names, src/stg dbt models, sources.yml, schema.yml, sapo_assets imports, definitions.py | Medium — dbt full-refresh needed |
| B | **Partition isolation** | dlt resource names → separate table names per pipeline, data lake dir rename, dbt glob update | Medium — data lake migration |

**Order:** A first (rename), then B (isolation). A is pure rename — no data moves. B moves data.

---

## Initiative A — sapo_v2_* Rename

### Rule
> Everything **upstream of `std_*`** gets renamed to `sapo_v2_*` prefix.  
> `std_*` and all downstream (`int_*`, `dim_*`, `fact_*`, `mart_*`) — **unchanged**.

---

### A0 — Fix Dagster layer (`sapov2_*` → `sapo_v2_*`) — 11 files

These were already renamed to `sapov2_*` (wrong convention) — fix back.

#### `orchestration/assets/sapo_assets.py` — function names + asset_key_str

| Old | New |
|---|---|
| `def ingest_sapov2_orders_batch_asset` | `def ingest_sapo_v2_orders_batch_asset` |
| `def ingest_sapov2_customers_batch_asset` | `def ingest_sapo_v2_customers_batch_asset` |
| `def ingest_sapov2_accounts_batch_asset` | `def ingest_sapo_v2_accounts_batch_asset` |
| `def ingest_sapov2_products_batch_asset` | `def ingest_sapo_v2_products_batch_asset` |
| `def ingest_sapov2_history_log_asset` | `def ingest_sapo_v2_history_log_asset` |
| `def ingest_sapov2_inventory_transactions_asset` | `def ingest_sapo_v2_inventory_transactions_asset` |
| `def ingest_sapov2_webhook_consumer_asset` | `def ingest_sapo_v2_webhook_consumer_asset` |
| `asset_key_str = "sapo/ingest_sapov2_*"` (7 strings) | `"sapo/ingest_sapo_v2_*"` |

#### `orchestration/definitions.py` — job vars + schedule vars + job names

| Old | New |
|---|---|
| `pipeline_sapov2_realtime_job` | `pipeline_sapo_v2_realtime_job` |
| `pipeline_sapov2_incremental_job` | `pipeline_sapo_v2_incremental_job` |
| `pipeline_sapov2_hourly_job` | `pipeline_sapo_v2_hourly_job` |
| `pipeline_sapov2_realtime_schedule` | `pipeline_sapo_v2_realtime_schedule` |
| `pipeline_sapov2_incremental_schedule` | `pipeline_sapo_v2_incremental_schedule` |
| `pipeline_sapov2_hourly_schedule` | `pipeline_sapo_v2_hourly_schedule` |
| `AssetSelection.assets(sapo_assets.ingest_sapov2_*)` (7×) | `sapo_assets.ingest_sapo_v2_*` |
| 1× stale AssetKey: `["staging", "src_sapo_inventory_transactions_v2"]` | `["staging", "src_sapo_v2_inventory_transactions"]` |

#### `orchestration/asset_checks/__init__.py` — 6 string keys

`"sapo/ingest_sapov2_*"` → `"sapo/ingest_sapo_v2_*"` (6 entries), attribute refs updated to match.

#### `orchestration/asset_checks/cursor_checks.py` — 5 string keys

`"sapo/ingest_sapov2_*"` → `"sapo/ingest_sapo_v2_*"` (5 entries)

#### `orchestration/asset_checks/freshness_checks.py` — docstring only

Update example string in docstring.

#### `orchestration/asset_checks/__tests__/test_check_factories_smoke.py` — test data

All `"sapo/ingest_sapov2_*"` strings + `sapo_assets.ingest_sapov2_*` attribute refs.

#### `orchestration/ops/morning_digest.py` — 7 asset_key strings

`"sapo/ingest_sapov2_*"` → `"sapo/ingest_sapo_v2_*"` (7 entries)

#### `orchestration/ops/__tests__/test_morning_digest_smoke.py` — test data

All `"sapo/ingest_sapov2_*"` strings.

#### `orchestration/assets/dbt.py` — 5 AssetKey arrays

`AssetKey(["sapo", "ingest_sapov2_*"])` → `AssetKey(["sapo", "ingest_sapo_v2_*"])`

#### `orchestration/config/ingestion_sla.yaml` — 6 keys

`sapo/ingest_sapov2_*:` → `sapo/ingest_sapo_v2_*:`

#### `orchestration/sensors/health_db_watchdog_sensor.py` — comment

Update comment referencing `ingest_sapov2_webhook_consumer_asset`.

---

### A1 — Ingestion runner scripts (7 files renamed + pipeline_name updated)

| Old filename | New filename | dlt pipeline_name change |
|---|---|---|
| `run_orders_batch.py` | `run_sapo_v2_orders_batch.py` | `sapo_orders_batch` → `sapo_v2_orders_batch` |
| `run_history_log.py` | `run_sapo_v2_history_log.py` | `sapo_history_log_pipeline` → `sapo_v2_history_log` |
| `run_webhook_consumer.py` | `run_sapo_v2_webhook_consumer.py` | `sapo_webhook_consumer` → `sapo_v2_webhook_consumer` |
| `run_customers_batch.py` | `run_sapo_v2_customers_batch.py` | `sapo_customers_batch` → `sapo_v2_customers_batch` |
| `run_accounts_batch.py` | `run_sapo_v2_accounts_batch.py` | `sapo_accounts_batch` → `sapo_v2_accounts_batch` |
| `run_products_batch.py` | `run_sapo_v2_products_batch.py` | `sapo_products_batch` → `sapo_v2_products_batch` |
| `run_inventory_transactions_v2_batch.py` | `run_sapo_v2_inventory_transactions_batch.py` | `sapo_inventory_transactions_v2_batch` → `sapo_v2_inventory_transactions_batch` |

**Note on dlt pipeline_name change:** Renaming `pipeline_name` invalidates existing dlt state files (cursor position). Must delete old state files before first run — new state files created automatically under new names.

---

### A2 — sapo_assets.py imports (7 import lines + .run() calls)

File: `orchestration/assets/sapo_assets.py`

```python
# Old                                        → New
import run_orders_batch                      → import run_sapo_v2_orders_batch
import run_history_log                       → import run_sapo_v2_history_log
import run_webhook_consumer                  → import run_sapo_v2_webhook_consumer
import run_customers_batch                   → import run_sapo_v2_customers_batch
import run_accounts_batch                    → import run_sapo_v2_accounts_batch
import run_products_batch                    → import run_sapo_v2_products_batch
import run_inventory_transactions_v2_batch   → import run_sapo_v2_inventory_transactions_batch
```

Each `.run(argv=...)` call updated to use new module name.

---

### A3 — src/sapo internal modules (2 files, resolved: yes)

| Old | New |
|---|---|
| `src/sapo/inventory_transactions_v2.py` | `src/sapo/sapo_v2_inventory_transactions.py` |
| `src/sapo/_inventory_v2_window.py` | `src/sapo/_sapo_v2_inventory_window.py` |

Update import in `run_sapo_v2_inventory_transactions_batch.py`.  
Update function name: `sapo_inventory_transactions_v2_source` → `sapo_v2_inventory_transactions_source`.

---

### A4 — dbt sources.yml (resolved: rename to sapo_v2_raw + split gsheet_raw)

File: `transformation/models/sources.yml`

Two changes:
1. Rename source: `sapo_v2_raw` → `sapo_v2_raw` (physical folder will be `sapo_v2_raw/` per Q2 decision)
2. Split gsheet tables into new source `gsheet_raw` (physical folder `gsheet_raw/`):
   - Move: `targets_raw`, `marketing_spend_raw`, `teams_raw`, `team_members_raw`, `us_shipment_prices_raw`, `overhead_account_classification_raw`
   - Models using these: `stg_targets.sql`, `stg_marketing_spend.sql`, `stg_teams.sql`, `stg_team_members.sql`, `stg_us_shipment_prices.sql`, `stg_overhead_account_classification.sql` — update `source('sapo_v2_raw', ...)` → `source('gsheet_raw', ...)`

All remaining `source('sapo_v2_raw', ...)` in src_* models → `source('sapo_v2_raw', ...)`.

**Count:** ~18 files with `source(...)` calls to update.

---

### A5 — dbt src models (11 files to rename + update)

| Old filename | New filename |
|---|---|
| `src_sapo_orders_v2.sql` | `src_sapo_v2_orders.sql` |
| `src_sapo_customers_v2.sql` | `src_sapo_v2_customers.sql` |
| `src_sapo_accounts_v2.sql` | `src_sapo_v2_accounts.sql` |
| `src_sapo_fulfillments_v2.sql` | `src_sapo_v2_fulfillments.sql` |
| `src_sapo_products_v2.sql` | `src_sapo_v2_products.sql` |
| `src_sapo_customer_groups_v2.sql` | `src_sapo_v2_customer_groups.sql` |
| `src_sapo_inventory_transactions_v2.sql` | `src_sapo_v2_inventory_transactions.sql` |
| `src_sapo_order_returns_v2.sql` | `src_sapo_v2_order_returns.sql` |
| `src_sapo_price_lists_v2.sql` | `src_sapo_v2_price_lists.sql` |
| `src_sapo_purchase_orders_v2.sql` | `src_sapo_v2_purchase_orders.sql` |
| `src_sapo_stock_adjustments_v2.sql` | `src_sapo_v2_stock_adjustments.sql` |

---

### A6 — dbt stg models (12 files to rename + update internal refs)

| Old filename | New filename | Internal ref() to update |
|---|---|---|
| `stg_sapo_orders_v2.sql` | `stg_sapo_v2_orders.sql` | `ref('src_sapo_orders_v2')` → `ref('src_sapo_v2_orders')` |
| `stg_sapo_customers_v2.sql` | `stg_sapo_v2_customers.sql` | `ref('src_sapo_customers_v2')` → `ref('src_sapo_v2_customers')` |
| `stg_sapo_accounts_v2.sql` | `stg_sapo_v2_accounts.sql` | `ref('src_sapo_accounts_v2')` → `ref('src_sapo_v2_accounts')` |
| `stg_sapo_products_v2.sql` | `stg_sapo_v2_products.sql` | `ref('src_sapo_products_v2')` → `ref('src_sapo_v2_products')` |
| `stg_sapo_variants_v2.sql` | `stg_sapo_v2_variants.sql` | `ref('src_sapo_products_v2')` → `ref('src_sapo_v2_products')` |
| `stg_sapo_variant_prices_v2.sql` | `stg_sapo_v2_variant_prices.sql` | `ref('stg_sapo_variants_v2')` → `ref('stg_sapo_v2_variants')` |
| `stg_sapo_inventories_v2.sql` | `stg_sapo_v2_inventories.sql` | `ref('stg_sapo_variants_v2')` → `ref('stg_sapo_v2_variants')` |
| `stg_sapo_order_items_v2.sql` | `stg_sapo_v2_order_items.sql` | `ref('src_sapo_orders_v2')` → `ref('src_sapo_v2_orders')` |
| `stg_sapo_order_discount_items_v2.sql` | `stg_sapo_v2_order_discount_items.sql` | `ref('src_sapo_orders_v2')` → `ref('src_sapo_v2_orders')` |
| `stg_sapo_payments_v2.sql` | `stg_sapo_v2_payments.sql` | `ref('src_sapo_orders_v2')` → `ref('src_sapo_v2_orders')` |
| `stg_sapo_fulfillments_v2.sql` | `stg_sapo_v2_fulfillments.sql` | `ref('src_sapo_orders_v2')` → `ref('src_sapo_v2_orders')` |
| `stg_sapo_order_returns_v2.sql` | `stg_sapo_v2_order_returns.sql` | `ref('src_sapo_order_returns_v2')` → `ref('src_sapo_v2_order_returns')` |

---

### A7 — std_* models: update ref() only (12 files, no rename)

| File | Old ref | New ref |
|---|---|---|
| `std_orders.sql` | `stg_sapo_orders_v2` | `stg_sapo_v2_orders` |
| `std_customers.sql` | `stg_sapo_customers_v2` | `stg_sapo_v2_customers` |
| `std_accounts.sql` | `stg_sapo_accounts_v2` | `stg_sapo_v2_accounts` |
| `std_fulfillments.sql` | `stg_sapo_fulfillments_v2` | `stg_sapo_v2_fulfillments` |
| `std_order_items.sql` | `stg_sapo_order_items_v2` | `stg_sapo_v2_order_items` |
| `std_order_discount_items.sql` | `stg_sapo_order_discount_items_v2` | `stg_sapo_v2_order_discount_items` |
| `std_payments.sql` | `stg_sapo_payments_v2` | `stg_sapo_v2_payments` |
| `std_order_returns.sql` | `stg_sapo_order_returns_v2` | `stg_sapo_v2_order_returns` |
| `std_products.sql` | `stg_sapo_products_v2` | `stg_sapo_v2_products` |
| `std_variants.sql` | `stg_sapo_variants_v2` | `stg_sapo_v2_variants` |
| `std_variant_prices.sql` | `stg_sapo_variant_prices_v2` | `stg_sapo_v2_variant_prices` |
| `std_inventory_movements.sql` | `src_sapo_inventory_transactions_v2` | `src_sapo_v2_inventory_transactions` |

---

### A8 — Non-std downstream ref() updates (2 files, no rename)

| File | Old ref | New ref |
|---|---|---|
| `intermediate/tags/int_order_tags.sql` | `src_sapo_orders_v2` | `src_sapo_v2_orders` |
| `marts/sales/fact_order_transitions.sql` | `stg_sapo_orders_v2` | `stg_sapo_v2_orders` |

---

### A9 — schema.yml (staging/schema.yml)

Update all 13 `- name: stg_sapo_*_v2` and `src_sapo_*_v2` entries to new names.

---

### A10 — Data lake folder rename (resolved: Option B)

- Rename `data_lake/sapo_raw/` → `data_lake/sapo_v2_raw/`
- Create `data_lake/gsheet_raw/` — move Google Sheets parquet directories:
  - `targets_raw/`, `marketing_spend_raw/`, `teams_raw/`, `team_members_raw/`, `us_shipment_prices_raw/`, `overhead_account_classification_raw/`
- Update dlt runner scripts: `dataset_name="sapo_raw"` → `dataset_name="sapo_v2_raw"`
- Update gsheet ingestion scripts (if any): `dataset_name` → `"gsheet_raw"`
- Update `transformation/models/sources.yml` `external_location` base path accordingly

**Note:** `data_lake/` rename is a robocopy + del operation — stop all pipelines first.

---

### A — Total impact summary

| Layer | Files renamed | Files with internal edits only |
|---|---|---|
| Dagster assets/jobs/schedules (A0 fix) | — | 11 |
| Ingestion runner scripts (A1) | 7 | — |
| sapo_assets.py imports (A2) | — | 1 |
| src/sapo internal modules (A3) | 2 | — |
| dbt sources.yml (A4) | — | 1 |
| dbt src models (A5) | 11 | — |
| dbt stg models (A6) | 12 | — |
| dbt std_* models ref only (A7) | — | 12 |
| dbt non-std ref updates (A8) | — | 2 |
| staging/schema.yml (A9) | — | 1 |
| Data lake folder + dataset_name (A10) | — | 8+ |
| **Total** | **32 files** | **36+ files** |

---

### A — Migration steps

1. **Stop Dagster** (set all schedules to OFF or stop container)
2. **A0** — Fix Dagster `sapov2_*` → `sapo_v2_*` in all 11 files (find-replace)
3. **A1** — Rename 7 ingestion runner files + update `pipeline_name` strings inside
4. **Delete old dlt state files** for all renamed pipeline names:
   ```
   _dlt_pipeline_state/sapo_orders_batch__*.jsonl  → delete
   _dlt_pipeline_state/sapo_history_log_pipeline__*.jsonl  → delete
   _dlt_pipeline_state/sapo_customers_batch__*.jsonl  → delete
   _dlt_pipeline_state/sapo_accounts_batch__*.jsonl  → delete
   _dlt_pipeline_state/sapo_products_batch__*.jsonl  → delete
   _dlt_pipeline_state/sapo_webhook_consumer__*.jsonl  → delete
   _dlt_pipeline_state/sapo_inventory_transactions_v2_batch__*.jsonl  → delete
   ```
5. **A2** — Update sapo_assets.py imports + .run() calls
6. **A3** — Rename src/sapo modules + update imports
7. **A4** — Update sources.yml (source name + gsheet split)
8. **A5** — Rename 11 src_* sql files + update `source(...)` calls inside
9. **A6** — Rename 12 stg_* sql files + update `ref(...)` calls inside
10. **A7** — Update ref() in 12 std_* files (no rename)
11. **A8** — Update ref() in 2 non-std files
12. **A9** — Update staging/schema.yml model names
13. **A10** — Rename data lake folders + update `dataset_name` in runner scripts
14. **dbt compile** — verify no broken refs
15. **Restart Dagster** (manifest reloads with new model names)
16. **dbt run --select src_sapo_v2_orders+ --full-refresh** (clean state)
17. **Verify**: row counts match pre-rename baseline
18. **Re-enable Dagster schedules**

---

## Initiative B — Partition Isolation

*(Execute after Initiative A is fully merged and verified)*

### Problem recap

4 pipelines write to shared `sapo_v2_raw/order/` directory. dlt DROP TABLE on any pipeline wipes all 4 partitions.

### Solution: Separate table names per pipeline

```
sapo_v2_raw/
├── order_batch/          ← sapo_v2_orders_batch (was: batch_sync partition)
├── order_history_log/    ← sapo_v2_history_log
├── order_webhook/        ← sapo_v2_webhook_consumer
└── order_text/           ← historical, read-only, never re-ingested
```

### B — Files to change

| File | Change |
|---|---|
| `ingestion/src/sapo/orders.py` | dlt resource name: `"order"` → `"order_batch"` |
| `ingestion/src/sapo/history_log.py` | resource name: `"order"` → `"order_history_log"` |
| `ingestion/src/sapo/webhook_consumer.py` | `table_name = 'order'` → `'order_webhook'` |
| `transformation/models/staging/src_sapo_v2_orders.sql` | glob: `order/ingest_method=*` → `order_*/ingest_method=*` (or separate globs) |
| `transformation/models/sources.yml` | source table `order` → `order_batch`; add `order_history_log`, `order_webhook`, `order_text` |

### B — Migration steps

1. Stop all Dagster order-ingestion jobs
2. Rename data lake directories:
   ```
   sapo_v2_raw/order/ingest_method=batch_sync   → sapo_v2_raw/order_batch/ingest_method=batch_sync
   sapo_v2_raw/order/ingest_method=history_log  → sapo_v2_raw/order_history_log/ingest_method=history_log
   sapo_v2_raw/order/ingest_method=webhook      → sapo_v2_raw/order_webhook/ingest_method=webhook
   sapo_v2_raw/order/ingest_method=text         → sapo_v2_raw/order_text/ingest_method=text
   ```
   Move `_delta_log/` alongside each partition (Q3: yes).
3. Update dlt resource names in source code
4. Delete dlt state files for affected pipelines (schema mismatch after rename)
5. Update dbt glob in `src_sapo_v2_orders.sql` + sources.yml
6. `dbt run --select src_sapo_v2_orders+ --full-refresh`
7. `bootstrap_serving_views.py` (stop Metabase first)
8. Verify row counts match pre-B baseline

---

## Risk Assessment

| Rủi ro | Khả năng | Impact | Mitigation |
|---|---|---|---|
| Dagster ticks fired mid-rename (wrong import) | Medium | Medium | Stop schedules before rename |
| dlt state not reset → wrong cursor on new pipeline_name | High | High | Delete all old state files before first run after A1 |
| dbt broken ref() after partial rename | High | High | `dbt compile` before `dbt run` — fails fast |
| Manifest cache: Dagster loads old model names | Medium | Medium | Restart data_platform container after Initiative A |
| `order_text` overwritten during B migration | Low | Critical | Move (not copy) — verify count before/after |
| gsheet parquet files misrouted after folder split | Medium | Medium | Pause gsheet ingestion during A10 |

---

## Resolved Questions

- **Q1** (A3 rename src/sapo modules): Yes — rename for consistency.
- **Q2** (data lake folder): **Option B** — rename `sapo_raw/` → `sapo_v2_raw/`, split gsheet data to `gsheet_raw/`. Single rename op; update `dataset_name` in runner scripts.
- **Q3** (`_delta_log/` during B migration): Yes — move alongside each partition.
