# Plan: Sapo V2 Rename

**Status:** DONE — all C1–C4 completed 2026-06-12. Gate: fact_orders 15,462 unchanged.  
**Priority:** High  
**Trigger:** Sapo V3 ingestion incoming — rename everything upstream of std_* to `sapo_v2_*` convention to make room. (Partition isolation dropped — risk accepted, manual-only trigger.)

---

## Convention Decision

**Target convention: `sapo_v2_*`** (not `sapov2_*`)

- Word boundaries via underscores: `sapo_v2_orders` not `sapov2_orders`
- Cross-version grep is natural: `grep "sapo_v[0-9]"` finds all versions
- Future: `sapo_v3_orders` alongside `sapo_v2_orders` reads clearly

**Problem:** Dagster layer was already renamed to `sapov2_*` (wrong convention) in a previous session. Initiative A includes fixing those back to `sapo_v2_*`.

---

## Initiative A — sapo_v2_* Rename (only initiative)

**Partition isolation (Initiative B) — dropped.** Risk analysis confirmed: `--full-refresh --force` is manual-only, never triggered by automation. Dagster nightly uses `--reset-cursor` (safe). Existing warning guard sufficient. dlt hard constraint also makes method-first layout impossible.

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

## Risk Assessment

| Rủi ro | Khả năng | Impact | Mitigation |
|---|---|---|---|
| Dagster ticks fired mid-rename (wrong import) | Medium | Medium | Stop schedules before rename |
| dlt state not reset → wrong cursor on new pipeline_name | High | High | Delete all old state files before first run after A1 |
| dbt broken ref() after partial rename | High | High | `dbt compile` before `dbt run` — fails fast |
| Manifest cache: Dagster loads old model names | Medium | Medium | Restart data_platform container after Initiative A |
| gsheet parquet files misrouted after folder split | Medium | Medium | Pause gsheet ingestion during A10 |

---

## Resolved Questions

- **Q1** (A3 rename src/sapo modules): Yes — rename for consistency.
- **Q2** (data lake folder): **Option B** — rename `sapo_raw/` → `sapo_v2_raw/`, split gsheet data to `gsheet_raw/`. Single rename op; update `dataset_name` in runner scripts.
---

## Chunked Execution

> Replaces the inline migration steps above. This is the actual execution roadmap.

### Design principles
- Each chunk is **atomic** — a partial chunk leaves the system in a broken state
- Each chunk ends with a **real Dagster run** before proceeding to the next
- Data-moving chunks use **copy-verify-delete**, never direct move
- Irreplaceable data (`order_text`, `order_history_log`) gets an explicit count gate

### Pre-flight: discovered bug
`orchestration/assets/dbt.py:37` checks `source_name == "sapo_raw"` but `sources.yml` already has `name: sapo_v2_raw`. The Dagster→dbt lineage (dependency edges from ingestion assets to dbt models) is **currently broken**. Fixed in C1 below.

### Cursor strategy (C2)
dlt state files are named `{pipeline_name}__{timestamp}__{hash}.jsonl`. The hash encodes pipeline identity — renaming the prefix **will not work** (dlt won't recognize the file). Strategy:
- Delete old state files after runner renames
- First run uses `--reset-cursor` (re-fetches from Sapo beginning)
- **Safe** because `src_sapo_orders_v2.sql` has 2-level dedup (tech dedup by `entity_id` + biz dedup by `order_id/modified_on`) — confirmed at lines 57–194. Other src models follow the same pattern.

---

### C1 — Dagster convention fix + lineage bug fix
**Scope:** A0 (partial)  
**Data risk:** Zero  
**Atomicity reason:** Dagster loads all assets as a unit — any broken attribute reference (e.g., `sapo_assets.ingest_sapov2_orders_batch_asset` no longer exists) crashes Dagster startup.

**Files changed (all internal edits, no renames):**

| File | Change |
|---|---|
| `orchestration/assets/sapo_assets.py` | 7 function names + 7 asset_key_str strings: `ingest_sapov2_*` → `ingest_sapo_v2_*` |
| `orchestration/definitions.py` | 3 job vars + 3 schedule vars: `pipeline_sapov2_*` → `pipeline_sapo_v2_*`; all `.assets(sapo_assets.ingest_sapov2_*)` refs updated |
| `orchestration/assets/dbt.py` | **Bug fix**: `source_name == "sapo_raw"` → `"sapo_v2_raw"`; AssetKey values: `ingest_sapov2_*` → `ingest_sapo_v2_*` |
| `orchestration/asset_checks/__init__.py` | 6 string keys |
| `orchestration/asset_checks/cursor_checks.py` | 5 string keys |
| `orchestration/asset_checks/freshness_checks.py` | docstring example |
| `orchestration/asset_checks/__tests__/test_check_factories_smoke.py` | test data strings + attribute refs |
| `orchestration/ops/morning_digest.py` | 7 asset_key strings |
| `orchestration/ops/__tests__/test_morning_digest_smoke.py` | test data strings |
| `orchestration/config/ingestion_sla.yaml` | 6 YAML keys |
| `orchestration/sensors/health_db_watchdog_sensor.py` | comment string |

**What does NOT change in C1:** runner script files, dlt pipeline_name strings, dbt model names, physical parquet files, dlt state files.

**Execution:**
1. Apply all edits above in one commit
2. `docker compose restart data_platform`
3. Check Dagster UI: assets appear under new `sapo_v2_*` names; jobs exist

**Verification (gate before C2):**
- Dagster UI: all 7 `ingest_sapo_v2_*` assets visible in asset catalog
- Dagster UI: asset lineage shows dbt source nodes linked to ingestion assets (proves dbt.py bug fixed)
- Jobs: `pipeline_sapo_v2_realtime_job`, `_incremental_job`, `_hourly_job` present
- `pytest orchestration/` — all tests green

**Rollback:** `git revert` + `docker compose restart data_platform`

---

### C2 — Ingestion runner renames
**Scope:** A1, A2, A3  
**Data risk:** Low (cursor reset → one re-fetch, dedup handles duplicates)  
**Atomicity reason:** Renaming `run_orders_batch.py` without updating the `import run_orders_batch` in `sapo_assets.py` = `ImportError` at Dagster startup. The file rename and the import update are the same atomic step.

**Files changed:**

| Old file | New file | Change inside |
|---|---|---|
| `run_orders_batch.py` | `run_sapo_v2_orders_batch.py` | `pipeline_name="sapo_orders_batch"` → `"sapo_v2_orders_batch"` |
| `run_history_log.py` | `run_sapo_v2_history_log.py` | `pipeline_name="sapo_history_log_pipeline"` → `"sapo_v2_history_log"` |
| `run_webhook_consumer.py` | `run_sapo_v2_webhook_consumer.py` | `pipeline_name="sapo_webhook_consumer"` → `"sapo_v2_webhook_consumer"` |
| `run_customers_batch.py` | `run_sapo_v2_customers_batch.py` | `pipeline_name="sapo_customers_batch"` → `"sapo_v2_customers_batch"` |
| `run_accounts_batch.py` | `run_sapo_v2_accounts_batch.py` | `pipeline_name="sapo_accounts_batch"` → `"sapo_v2_accounts_batch"` |
| `run_products_batch.py` | `run_sapo_v2_products_batch.py` | `pipeline_name="sapo_products_batch"` → `"sapo_v2_products_batch"` |
| `run_inventory_transactions_v2_batch.py` | `run_sapo_v2_inventory_transactions_batch.py` | `pipeline_name="sapo_inventory_transactions_v2_batch"` → `"sapo_v2_inventory_transactions_batch"` |
| `src/sapo/inventory_transactions_v2.py` | `src/sapo/sapo_v2_inventory_transactions.py` | function `sapo_inventory_transactions_v2_source` → `sapo_v2_inventory_transactions_source` |
| `src/sapo/_inventory_v2_window.py` | `src/sapo/_sapo_v2_inventory_window.py` | — |
| `orchestration/assets/sapo_assets.py` | (edit) | 7 import lines updated to new module names; .run() call sites updated |

**Cursor state cleanup (run before Dagster restart):**
```powershell
# Delete old state files — new pipelines will start fresh and --reset-cursor handles re-fetch
$stateDir = "app_data\data_lake\sapo_raw\_dlt_pipeline_state"
$oldPrefixes = @("sapo_orders_batch__", "sapo_history_log_pipeline__", "sapo_webhook_consumer__",
                  "sapo_customers_batch__", "sapo_accounts_batch__", "sapo_products_batch__",
                  "sapo_inventory_transactions_v2_batch__")
foreach ($prefix in $oldPrefixes) {
    Get-ChildItem $stateDir -Filter "${prefix}*.jsonl" | Remove-Item
    Write-Host "Deleted $prefix state files"
}
```

**Execution:**
1. Rename files + edit imports (one commit)
2. Run cursor cleanup PowerShell above
3. `docker compose restart data_platform`
4. Manually trigger `ingest_sapo_v2_orders_batch_asset` with tag `full_refresh=true` (triggers `--reset-cursor`)

**Verification (gate before C3):**
- Dagster run completes without ImportError
- Logs confirm pipeline ran: `[Pipeline Runner] Initialized pipeline: sapo_v2_orders_batch`
- Row count: `SELECT COUNT(DISTINCT order_id) FROM fact_orders` — must be ≥ 15,459 (pre-rename baseline)
- No duplicates: `SELECT order_id, COUNT(*) FROM fact_orders GROUP BY 1 HAVING COUNT(*) > 1` — must return 0 rows

**Rollback:**
- `git revert` C2 commit (restores old file names)
- Restore deleted state files from `backup/` (keep a copy before deleting)
- `docker compose restart data_platform`

**Data preservation note:** Parquet files in `sapo_raw/` are **never touched** in this chunk. Only state JSONL files are deleted. Worst case from cursor reset: extra parquet files appended → dedup in src model handles it.

---

### C3 — dbt full rename + gsheet source split
**Scope:** A4, A5, A6, A7, A8, A9, dbt.py gsheet split  
**Data risk:** Zero (all changes are view definitions over unchanged parquet files)  
**Atomicity reason:** Any broken `ref()` → `dbt compile` fails. All src/stg/std must be consistent in one commit. sources.yml source name and all `source(...)` call sites must match.

**Key insight:** `sources.yml` source name `sapo_v2_raw` stays `sapo_v2_raw` — it's already correct. Only the gsheet tables are split out and physical paths update in C4 (not C3).

**Files changed:**

| Layer | Files | Change |
|---|---|---|
| `sources.yml` | 1 | Add `gsheet_raw` source (pointing to current `sapo_raw/` path for now — path updates in C4); move 6 gsheet table entries to it |
| `stg_targets.sql`, `stg_marketing_spend.sql`, `stg_teams.sql`, `stg_team_members.sql`, `stg_us_shipment_prices.sql`, `stg_overhead_account_classification.sql` | 6 | `source('sapo_v2_raw', ...)` → `source('gsheet_raw', ...)` |
| src models (A5) | 11 renamed | `src_sapo_*_v2.sql` → `src_sapo_v2_*.sql` |
| stg models (A6) | 12 renamed + ref() updated | `stg_sapo_*_v2.sql` → `stg_sapo_v2_*.sql` |
| std models (A7) | 12 edited (no rename) | ref() args updated |
| non-std models (A8) | 2 edited (no rename) | ref() args updated |
| `staging/schema.yml` (A9) | 1 | 23 model name entries updated |
| `orchestration/assets/dbt.py` | 1 | Add `gsheet_raw` source block; remove `targets_raw`/`marketing_spend_raw` from `sapo_v2_raw` block |

**Execution:**
1. Apply all changes in one commit
2. `docker compose restart data_platform` (Dagster reloads dbt manifest)
3. Inside `data_platform` container: `dbt compile`
4. `dbt run --select src_sapo_v2_orders+ --full-refresh`

**Verification (gate before C4):**
- `dbt compile` exits 0 with 0 errors
- `dbt run --select src_sapo_v2_orders+` passes
- `SELECT COUNT(DISTINCT order_id) FROM fact_orders` — must equal C2 baseline
- Dagster UI: dbt lineage shows `src_sapo_v2_orders` → `stg_sapo_v2_orders` → `std_orders` → downstream

**Rollback:** `git revert` C3 commit + `docker compose restart data_platform`

---

### C4 — Data lake folder rename
**Scope:** A10  
**Data risk:** Medium — physical folder rename. Mitigated by copy-before-delete.  
**Atomicity reason:** `dataset_name` in runner scripts, `external_location` in sources.yml, and the physical folder must all switch at once. A pipeline writing to `sapo_v2_raw/` while dbt still reads from `sapo_raw/` = empty source tables.

**Pre-conditions before starting C4:**
- C1–C3 verified and stable for ≥1 full Dagster cycle (24h)
- Baseline row counts recorded: `SELECT COUNT(*) FROM fact_orders`, `fact_customers`, `fact_products` → save to file
- Verify gsheet ingestion runners: check if any `run_*.py` writes to `dataset_name="sapo_raw"` for gsheet data — update those to `"gsheet_raw"` in this chunk too
- Current state file count: note exact file count in `sapo_raw/_dlt_pipeline_state/`

**Execution (must be sequential, service pause required):**

```
Step 1: Pause services
  - Set all Dagster schedules to OFF (do not stop container)
  - Confirm no active runs: Dagster UI → Runs → filter "In Progress" = 0

Step 2: Copy sapo_raw → sapo_v2_raw  [~5-20 min depending on size]
  robocopy app_data\data_lake\sapo_raw app_data\data_lake\sapo_v2_raw /E /COPYALL /LOG:robocopy_c4.log
  
Step 3: Count verification
  PowerShell: (Get-ChildItem sapo_raw -Recurse -File).Count
  PowerShell: (Get-ChildItem sapo_v2_raw -Recurse -File).Count
  → Must be equal before proceeding

Step 4: Create gsheet_raw + move gsheet dirs from sapo_v2_raw
  mkdir app_data\data_lake\gsheet_raw
  Move-Item sapo_v2_raw\targets_raw             gsheet_raw\
  Move-Item sapo_v2_raw\marketing_spend_raw     gsheet_raw\
  Move-Item sapo_v2_raw\teams_raw               gsheet_raw\
  Move-Item sapo_v2_raw\team_members_raw        gsheet_raw\
  Move-Item sapo_v2_raw\us_shipment_prices_raw  gsheet_raw\
  Move-Item sapo_v2_raw\overhead_account_classification_raw  gsheet_raw\

Step 5: Code update (one commit)
  - All 7 Sapo runner scripts: dataset_name="sapo_raw" → "sapo_v2_raw"
  - Gsheet runner scripts (if any): dataset_name → "gsheet_raw"
  - sources.yml: update external_location base path sapo_raw/ → sapo_v2_raw/
                 update gsheet_raw source external_location to gsheet_raw/
  
Step 6: Restart + compile
  docker compose restart data_platform
  dbt compile  [inside container]
  dbt run --full-refresh  [all models]
  bootstrap_serving_views.py  [stop Metabase first]

Step 7: Verification (gate before delete)
  SELECT COUNT(DISTINCT order_id) FROM fact_orders  → must equal C3 baseline
  SELECT COUNT(DISTINCT customer_id) FROM dim_customers  → must equal baseline
  SELECT COUNT(*) FROM stg_targets  → must equal baseline (gsheet path correct)
  Trigger one manual Dagster run → confirm writes to sapo_v2_raw/

Step 8: Delete original sapo_raw (only after Step 7 passes)
  Move-Item app_data\data_lake\sapo_raw  app_data\data_lake\backup\sapo_raw_pre_c4
  [keep in backup/ for 48h before final delete]
```

**Rollback (if Step 7 fails):**
- `sapo_v2_raw/` still exists — revert code (git revert)
- Restore `dataset_name="sapo_raw"` in runners
- Restart Dagster → pipelines point to original sapo_raw/ again
- `sapo_raw/` was never deleted → no data loss

---

### Chunk summary

| Chunk | Scope | Data moves | Downtime needed | Verify with |
|-------|-------|-----------|-----------------|-------------|
| C1 | A0 (Dagster strings + dbt.py bug fix) | None | 1× restart | Dagster UI + pytest |
| C2 | A1+A2+A3 (runners + cursor) | None (state files deleted) | 1× restart | 1 manual Dagster run |
| C3 | A4–A9 (dbt rename + gsheet split) | None | 1× restart | dbt compile + dbt run |
| C4 | A10 (data lake folder rename) | robocopy copy + move | Schedule pause | Row count baseline match |
