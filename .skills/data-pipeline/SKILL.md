# Data Pipeline Skill (dlt + dbt + Serving)

Skill hỗ trợ thêm data source mới vào pipeline end-to-end:  
**ingestion (dlt) → transformation (dbt) → serving layer (DuckDB) → orchestration (Dagster)**.

## Kích hoạt

- "thêm source mới", "add new ingestion", "integrate [source_name]"
- "tạo dbt model mới", "thêm src_/stg_/dim_/fact_ model"
- Hỏi về envelope schema, dedup strategy, incremental dbt, OOM, rolling snapshots, rolling self-refresh views
- Debug: dlt auth, dbt memory, Dagster asset fail, serving DB lock, empty folder

---

## Architecture Overview

```
API Source ─┐
            ▼
     [dlt pipeline]  →  data_lake/{entity}/ingest_method=*/year=*/month=*/*.parquet
                              │
                              ▼
                  [dbt src_]  (incremental, tech+biz dedup, JSON extract)
                              │
                              ▼
                  [dbt stg_]  (view, enrichment, unnest)
                              │
                              ▼
                  [dbt std_]  (golden layer, multi-source consolidation)
                              │
                              ▼
               [dbt int_] ←→ [dbt dim_/fact_]  (external parquet to rolling/)
                              │
                              ▼
         DBT_EXPORT_PATH/rolling/{model}/{model}_{timestamp}.parquet
                              │
                              ▼
              [generate_serving_db.py]  (Rolling Self-Refresh Views + GC)
                              │
                              ▼
               data_lake/serving/olap.duckdb  (Metabase query here)
```

**5-hop transform flow:** `src_ → stg_ → std_ → int_ → dim_/fact_`  
**Dagster DAG:** `{source}_ingestion_asset → dbt_assets → serving_db_asset`

---

## Bước 1: Chọn Pattern Ingestion

```
Source đã có trong dlt hub?
(dlthub.com/docs/dlt-ecosystem/verified-sources)
        │
   YES  │  NO
        │
 Pattern B ─── Pattern A (FOCUS)
 (note ngắn)   (custom envelope)
```

### Pattern B — Native dlt source (note ngắn)
```python
from dlt.sources.facebook_ads import facebook_ads_source
pipeline = dlt.pipeline(pipeline_name="...", destination="duckdb", dataset_name="...")
pipeline.run(facebook_ads_source(account_id=..., chunk_size=1000))
```
Reference: `ingestion/run_facebook_ads_batch.py`

### Pattern A — Custom API (full guide)
Xem `checklist.md` — thực hiện theo 6 phase.

---

## Quick Reference

### Docs
| File | Nội dung |
|------|----------|
| `checklist.md` | Checklist 6-phase: config → code → dbt → serving → dagster → verify |
| `lessons-learned.md` | Lessons ingestion: dlt config, incremental, auth |
| `dbt-patterns.md` | **Lessons dbt**: OOM fix, materialization, dedup, rolling location, partition pruning, time dim |
| `dagster-patterns.md` | **Lessons Dagster**: hybrid job race, schedule offset, zombie threads, upstream injection |
| `serving-layer.md` | **Cơ chế serving DB**: Rolling Self-Refresh Views, GC, zero-downtime swap |
| `supporting-scripts.md` | **Supporting scripts**: generate_serving_db, run_dbt, clean_dlt_state... |
| `troubleshooting.md` | Symptom → Cause → Fix (dlt + dbt + serving + Dagster) |

### Templates
| File | Mục đích |
|------|----------|
| `templates/source-template.py` | dlt source + resource + envelope builder |
| `templates/run-entry-point-template.py` | dlt entry point wrapper |
| `templates/dagster-asset-template.py` | Dagster ingestion asset |
| `templates/dagster-serving-asset-template.py` | Dagster serving asset (deps=[dbt_assets]) |
| `templates/src-model-template.sql` | dbt src_: incremental, dedup, JSON extract |
| `templates/dim-model-template.sql` | dbt dim_ với `location=get_rolling_location()` |
| `templates/fact-model-template.sql` | dbt fact_ với surrogate keys + rolling |
| `templates/sources-yml-template.yml` | dbt sources config (external Parquet glob) |
| `templates/schema-yml-template.yml` | dbt tests (unique, not_null, relationships) |

---

## Key Paths

### Local Development

```
ingestion/                             # dlt pipeline layer
├── run_{entity}_{method}.py           # Entry points
├── src/{source}/{entity}.py           # Source code
├── src/utils/pipeline_runner.py       # Standard runner
└── .dlt/
    ├── config.toml                    # Non-secret config
    ├── secrets.toml                   # Gitignored credentials
    └── secrets.toml.sample            # Template (committed)

transformation/                        # dbt layer
├── dbt_project.yml                    # Model configs by layer
├── profiles.yml                       # DuckDB (memory=5GB, threads=1)
├── packages.yml                       # dbt_utils 1.1.1
├── models/
│   ├── sources.yml                    # External Parquet sources
│   ├── staging/
│   │   ├── src_{entity}.sql           # Incremental + dedup
│   │   ├── stg_{entity}.sql           # View + enrichment
│   │   └── standard/std_{entity}.sql  # Golden layer
│   └── marts/
│       ├── core/dim_{entity}.sql      # External parquet (rolling)
│       └── sales/fact_{process}.sql   # External parquet (rolling)
├── seeds/ref_*.csv                    # Static reference data
├── macros/get_rolling_location.sql    # REQUIRED macro
└── scripts/run_dbt.py                 # dbt build wrapper

scripts/                               # Project-level scripts
├── provisioning/
│   └── generate_serving_db.py         # Rolling → Rolling Self-Refresh Views + GC
│   └── bootstrap_serving_views.py     # Alternative: safer serving view gen
├── ensure_dbt_directories.py          # Pre-create rolling/ dirs
├── clean_dlt_state.py                 # Drop pending dlt packages
└── debug_duckdb.py                    # Query debugging

orchestration/                         # Dagster layer
├── assets/
│   ├── {source}_assets.py             # Ingestion assets
│   ├── dbt.py                         # dbt_assets
│   ├── serving.py                     # serving_db asset
│   └── utils.py                       # load_dlt_configuration, DLT_DIR, PROJECT_ROOT
└── definitions.py                     # Jobs, schedules

data_lake/                             # Runtime data (LOCAL)
├── {entity}/ingest_method=*/          # Raw Parquet (dlt output)
├── sapo_warehouse.duckdb              # dbt working DB
├── export/marts/rolling/              # dbt mart exports
│   └── {model}/{model}_{ts}.parquet
└── serving/olap.duckdb                # Rolling Self-Refresh Views (Metabase reads)
```

### Docker Volume Mapping

**Convention:** Code at `/app/`, Data at `/app/var/` (inside container).

```
Host (app_data/)                      Container (/app/var/)
├── data_lake/                    →   /app/var/data_lake
├── dagster_home/                 →   /app/var/dagster_home
├── logs/                         →   /app/var/logs
├── backups/                      →   /app/var/backups
└── input_source/                 →   /app/var/input_source

Host (code)                            Container (/app/)
├── transformation/               →   /app/transformation
├── ingestion/                    →   /app/ingestion
├── orchestration/                →   /app/orchestration
└── scripts/                      →   /app/scripts
```

**Path Resolution Pattern:**

Python scripts use env vars with Docker defaults:

```python
# Example: get data lake path
data_lake_path = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
```

Env vars set in container via docker-compose `environment:` section or `.env.docker` file.

---

## Critical Rules

### Serving Views & Absolute Paths

**⚠️ CRITICAL AFTER DOCKER MOUNT CHANGES:**

Serving views (`olap.duckdb`) bake absolute paths into their SQL. If you change Docker volume mount paths or directory structure:

1. **Stop Metabase first** (releases DuckDB lock):
   ```bash
   docker compose down
   ```

2. **Regenerate serving views** on the data_platform container:
   ```bash
   docker compose up -d data_platform
   docker compose exec data_platform python scripts/provisioning/bootstrap_serving_views.py
   ```

3. **Restart Metabase** (will connect to updated views):
   ```bash
   docker compose up -d metabase
   ```

**Why?** Views contain embedded paths like:
```sql
CREATE VIEW dim_customers AS SELECT * FROM '/app/var/data_lake/export/marts/rolling/dim_customers/*.parquet'
```

If `/app/var/data_lake` changes to `/app/data_lake`, view paths break and Metabase queries fail.

### dbt Target Cache & Rolling Parquet Paths

**⚠️ CRITICAL AFTER DOCKER MOUNT CHANGES:**

dbt's `target/` directory caches compiled SQL and model state including **absolute parquet output paths** from `get_rolling_location()`. When Docker mount paths change (e.g. `/app/data_lake` → `/app/var/data_lake`):

- Cached state still references old paths → dbt tries to read/write to non-existent old paths
- Error: `IO Error: Cannot open file "/app/data_lake/export/marts/rolling/...": No such file or directory`

**Fix:** Clean dbt target cache and regenerate manifest before Dagster uses it:
```bash
docker exec data_platform bash -c "rm -rf /app/transformation/target"
docker exec data_platform bash -c "cd /app/transformation && dbt deps && dbt parse"
docker compose restart data_platform
```

**⚠️ Order matters:** `dbt parse` MUST run before Dagster restarts — Dagster imports `manifest.json` at startup. If you `rm -rf target/` and restart without `dbt parse`, Dagster crashes with `DagsterDbtManifestNotFoundError`.

Or selectively rebuild only failing models (no target nuke needed):
```bash
docker exec data_platform bash -c "cd /app/transformation && dbt build --select model_name_1 model_name_2"
```

### Other Rules

1. **Mart models MUST have** `location="{{ get_rolling_location() }}"` — nếu thiếu, `generate_serving_db.py` báo "Empty folder" và drop view
2. **src_ phải incremental** với `_dlt_load_id` filter — xử lý late-arriving events (dùng `_dlt_load_id`, không phải `event_timestamp`; xem Rule 14)
3. **src_/stg_ split** — tránh OOM; payload chỉ ở src_, stg_ đọc flat data
4. **Dagster DuckDB writer assets** phải có `op_tags={"dagster/concurrency_key": "duckdb_lock"}`
5. **`argv=[]`** khi gọi `run_*.run()` từ Dagster — tránh pick up Dagster's sys.argv
6. **`os.chdir(DLT_DIR)` + `load_dlt_configuration()`** đầu mỗi Dagster ingestion asset
7. **Serving asset `deps=[dbt_assets]`** — serving phải chạy sau dbt mart export xong
8. **Pre-create rolling dirs** trong `@dbt_assets` function (idempotent) — dbt COPY fail nếu dir không tồn tại
9. **Telemetry vars** (`DLT_TELEMETRY_DISABLED=true`, `DBT_SEND_ANONYMOUS_USAGE_STATS=false`) set ở process level — tránh zombie threads block Dagster job exit
10. **Jobs với nhiều ingestion sources** phải inject upstream keys qua `DagsterDbtTranslator.get_upstream_asset_keys()` — nếu không dbt start trước ingestion
11. **Khi fix anti-pattern trong prod code** → `grep` `templates/` cho cùng pattern và fix luôn. Templates là hạt giống bug tương lai — bất kỳ asset mới copy từ template cũ sẽ kế thừa bug. Đã xảy ra thực tế 2026-04-08: serving subprocess fix ở prod, nhưng template vẫn giữ `capture_output=True` cho tới audit 2026-04-09.
12. **KHÔNG BAO GIỜ dùng `refresh="drop_sources"`** — xóa TẤT CẢ tables trong shared dataset (sapo_raw). Dùng `full_refresh` flag để reset incremental cursor, giữ nguyên data. Xem L25.
13. **Dedup ORDER BY: `modified_on DESC` trước** (entity timestamp = source of truth), sau đó ingest_method priority. KHÔNG dùng `event_timestamp` làm primary sort cho dedup — event_timestamp là timestamp của log system, không phải entity. Xem L28.
14. **Incremental filter: dùng `_dlt_load_id`** không phải `event_timestamp` — catches late-arriving data từ full-refresh hoặc history_log backfill mà event_timestamp filter sẽ bỏ sót. Xem L29.
15. **Incremental schema migration phải self-heal** — khi thêm column mới vào src_ model: (a) `on_schema_change='append_new_columns'`, (b) `adapter.get_columns_in_relation(this)` check column tồn tại, (c) guard UNION ALL, (d) cursor CTE thay vì aggregate trong WHERE subquery. DuckDB + `read_parquet()` reject MAX() in WHERE subquery. Xem L31.
16. **Nightly reconciliation = incremental, KHÔNG phải full refresh.** Dùng `transform_batch_fullrefresh_job` (manual, tag baked in) cho one-time reload. Không bao giờ auto-tag `full_refresh=true` trên scheduled jobs. Batch source functions phải wire `full_refresh` param từ entry-point → source → resource — nếu không flag bị silently ignored. Xem L32.
17. **`--full-refresh` phải reset dlt pipeline state dir** (`.dlt/pipelines/{name}/`), không chỉ set flag. `dlt.sources.incremental` có 2 lớp filter: manual check (code) + internal transform (state file). Chỉ set `last_value=None` mà không xóa state = dlt silently drop items. KHÔNG dùng `pipeline.drop()` (gọi `destination.drop_storage()`). Xem L33.
