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
├── ensure_dbt_directories.py          # Pre-create rolling/ dirs
├── clean_dlt_state.py                 # Drop pending dlt packages
└── debug_duckdb.py                    # Query debugging

orchestration/                         # Dagster layer
├── assets/
│   ├── {source}_assets.py             # Ingestion assets
│   ├── dbt.py                         # dbt_assets
│   ├── serving.py                     # serving_db asset
│   └── utils.py                       # load_dlt_configuration, DLT_DIR
└── definitions.py                     # Jobs, schedules

data_lake/                             # Runtime data
├── {entity}/ingest_method=*/          # Raw Parquet (dlt output)
├── sapo_warehouse.duckdb              # dbt working DB
├── export/marts/rolling/              # dbt mart exports
│   └── {model}/{model}_{ts}.parquet
└── serving/olap.duckdb                # Rolling Self-Refresh Views (Metabase reads)
```

---

## Critical Rules

1. **Mart models MUST have** `location="{{ get_rolling_location() }}"` — nếu thiếu, `generate_serving_db.py` báo "Empty folder" và drop view
2. **src_ phải incremental** với 7-day lookback — xử lý late-arriving events
3. **src_/stg_ split** — tránh OOM; payload chỉ ở src_, stg_ đọc flat data
4. **Dagster DuckDB writer assets** phải có `op_tags={"dagster/concurrency_key": "duckdb_lock"}`
5. **`argv=[]`** khi gọi `run_*.run()` từ Dagster — tránh pick up Dagster's sys.argv
6. **`os.chdir(DLT_DIR)` + `load_dlt_configuration()`** đầu mỗi Dagster ingestion asset
7. **Serving asset `deps=[dbt_assets]`** — serving phải chạy sau dbt mart export xong
8. **Pre-create rolling dirs** trong `@dbt_assets` function (idempotent) — dbt COPY fail nếu dir không tồn tại
9. **Telemetry vars** (`DLT_TELEMETRY_DISABLED=true`, `DBT_SEND_ANONYMOUS_USAGE_STATS=false`) set ở process level — tránh zombie threads block Dagster job exit
10. **Jobs với nhiều ingestion sources** phải inject upstream keys qua `DagsterDbtTranslator.get_upstream_asset_keys()` — nếu không dbt start trước ingestion
11. **Khi fix anti-pattern trong prod code** → `grep` `templates/` cho cùng pattern và fix luôn. Templates là hạt giống bug tương lai — bất kỳ asset mới copy từ template cũ sẽ kế thừa bug. Đã xảy ra thực tế 2026-04-08: serving subprocess fix ở prod, nhưng template vẫn giữ `capture_output=True` cho tới audit 2026-04-09.
