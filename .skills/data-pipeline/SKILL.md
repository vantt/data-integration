---
name: data-pipeline
description: End-to-end data pipeline work across ingestion, modeling, serving, trust, and operations in the data-integration2 project.
---

# Data Pipeline Skill (5 Functional Groups)

Skill hỗ trợ thêm/fix/deploy data pipeline end-to-end.  
Tổ chức theo **5 nhóm chức năng**: INGEST · MODEL · SERVE · TRUST · OPS.

---

## Kích hoạt

**INGEST:**
- "thêm source mới", "add new ingestion", "integrate [source_name]"
- "envelope schema", "dedup strategy", "auth dlt"
- "webhook consumer", "history log", "file-drop"

**MODEL:**
- "tạo dbt model mới", "thêm src_/stg_/dim_/fact_ model"
- "incremental dbt", "OOM dbt", "rolling snapshots"

**SERVE:**
- "Metabase nhìn dữ liệu cũ", "rolling self-refresh views", "serving DB lock"
- "empty folder", "GC parquet"

**TRUST:**
- "morning digest", "health report", "ingestion_runs", "rows_written=0 bug"
- "daily health card", "Lark/Slack health alert", "per-source SLA", "recon drift report"
- "asset check", "KPI closure"

**OPS:**
- "schedule", "sensor", "stuck run", "concurrency", "purge", "backup"
- "Dagster asset fail", "schedule offset", "zombie thread"

**Cross-cutting:**
- "DuckDB lock", "Docker mount", "env var", "Windows file lock"

**Meta:**
- "setup hook", "ghi lesson Lxx", "Self-Learning Protocol"

---

## Quick Start

### Tôi đang làm gì?

| Task | Đọc trước |
|------|-----------|
| Setup máy mới / hook không nhắc / ghi lesson Lxx mới | `playbooks/00-skill-meta.md` |
| Thêm source mới | `playbooks/01-ingest.md` + `checklist.md` |
| Fix dbt model | `playbooks/02-model.md` |
| Fix Metabase data sai/cũ | `playbooks/03-serve.md` |
| Health monitoring / digest / recon | `playbooks/04-trust.md` |
| Schedule / sensor / stuck run | `playbooks/05-ops.md` |
| Lock / Docker path / env var issue | `playbooks/cross-cutting.md` |
| Tra cứu lesson Lxx | `lesson-index.md` |

---

## Architecture

Xem `ARCHITECTURE.md` — bản đồ 5 nhóm, critical path diagram, và decision tree đầy đủ.

---

## Environment Setup (one-time per machine)

Hook `data-pipeline-lesson-reminder` auto-reminds after `fix:` commits to record lessons.

**Check:** does it exist?
```bash
ls "$HOME/.claude/hooks/data-pipeline-lesson-reminder.cjs" 2>/dev/null && echo "OK" || echo "MISSING"
```

**If MISSING — run setup (idempotent):**
```bash
node .skills/data-pipeline/scripts/setup-lesson-reminder-hook.cjs
```

Then reload: open `/hooks` in Claude Code or restart.

Source lives at `.skills/data-pipeline/hooks/data-pipeline-lesson-reminder.cjs` — always reflects the latest version.

**Deep-dive:** `playbooks/00-skill-meta.md` — hook setup, Self-Learning Protocol, Lxx workflow.

---

## Quick Reference

### Playbooks (group-specific deployment guides)

| File | Role |
|------|------|
| `playbooks/00-skill-meta.md` | META: hook setup, Self-Learning Protocol, Lxx workflow |
| `playbooks/01-ingest.md` | INGEST: thu thập (Sapo 3-channel, file-drop, sheets) |
| `playbooks/02-model.md` | MODEL: dbt 5-hop (src→stg→std→int→mart) |
| `playbooks/03-serve.md` | SERVE: rolling views, dual DuckDB, GC |
| `playbooks/04-trust.md` | TRUST: 4-tier pyramid, digest, recon, KPI closure |
| `playbooks/05-ops.md` | OPS: sensors, schedules, concurrency, maintenance |
| `playbooks/cross-cutting.md` | Shared concerns (DuckDB lock, paths, env vars) |

### Deep references (source-of-truth, đọc khi cần chi tiết)

| File | Group | Lines | Lessons |
|------|-------|-------|---------|
| `references/lessons-learned.md` | INGEST + others | 2557 | 76 lessons (L1-L76, gap L34) |
| `references/dagster-patterns.md` | OPS | 836 | 14 lessons |
| `references/dbt-patterns.md` | MODEL | 479 | 14 lessons |
| `references/serving-layer.md` | SERVE | 269 | — |
| `references/ingestion-health-digest.md` | TRUST | 333 | — |
| `references/supporting-scripts.md` | cross-cutting | 197 | — |
| `references/troubleshooting.md` | cross-cutting | 211 | — |

### Index

- `lesson-index.md` — Master cross-ref L1-L76 + 14 dagster + 14 dbt → group(s)
- `templates/INDEX.md` — Templates organized by group

### Docs (nội dung cụ thể)

| File | Nội dung |
|------|----------|
| `checklist.md` | Checklist 6-phase: config → code → dbt → serving → dagster → verify |
| `references/lessons-learned.md` | Lessons ingestion: dlt config, incremental, auth |
| `references/dbt-patterns.md` | **Lessons dbt**: OOM fix, materialization, dedup, rolling location, partition pruning, time dim |
| `references/dagster-patterns.md` | **Lessons Dagster**: hybrid job race, schedule offset, zombie threads, upstream injection |
| `references/serving-layer.md` | **Cơ chế serving DB**: Rolling Self-Refresh Views, GC, zero-downtime swap |
| `references/supporting-scripts.md` | **Supporting scripts**: generate_serving_db, run_dbt, clean_dlt_state... |
| `references/troubleshooting.md` | Symptom → Cause → Fix (dlt + dbt + serving + Dagster) |
| `references/ingestion-health-digest.md` | **Health digest pattern**: per-source observability card (schema → recorder → 3-layer row-count fallback → yesterday-ICT window → classification → delivery), plus backfill + composite-PK recovery playbook |
| `references/dagster-patterns.md` Lesson 10-13 | **Stuck run prevention**: dbt subprocess timeout, subprocess killing via psutil, backup concurrency lock, zombie NOT_STARTED cleanup |
| `references/dagster-patterns.md` Lesson 14 + `references/lessons-learned.md` L49-L52 | **Maintenance cron topology**: schedule must be explicitly started, backup `trap … EXIT` rotation, `prune_dagster_history`, stuck-run sensor Pass 2 (queue-stuck), purge cleans dbt target dirs (post-mortem 2026-04-28 disk-full) |

### Templates (organized by group)

| File | Mục đích |
|------|----------|
| `templates/ingest/source-template.py` | dlt source + resource + envelope builder |
| `templates/ingest/run-entry-point-template.py` | dlt entry point wrapper |
| `templates/ingest/dagster-asset-template.py` | Dagster ingestion asset |
| `templates/serve/dagster-serving-asset-template.py` | Dagster serving asset (deps=[dbt_assets]) |
| `templates/model/src-model-template.sql` | dbt src_: incremental, dedup, JSON extract |
| `templates/model/dim-model-template.sql` | dbt dim_ với `location=get_rolling_location()` |
| `templates/model/fact-model-template.sql` | dbt fact_ với surrogate keys + rolling |
| `templates/model/sources-yml-template.yml` | dbt sources config (external Parquet glob) |
| `templates/model/schema-yml-template.yml` | dbt tests (unique, not_null, relationships) |
| `templates/trust/ingestion-health-recorder-template.py` | Health DB recorder (`record_run` API + DDL, composite PK `(asset_key, run_id)`) |
| `templates/trust/dlt-row-count-extractor-template.py` | 3-layer fallback: metric walk → file_id glob → `_dlt_load_id` scan |
| `templates/trust/ingestion-health-digest-template.py` | Morning digest op: SQL window + classification + asset-type-aware messaging |
| `templates/trust/backfill-health-rows-written-template.py` | One-shot backfill for fixed extractor (composite-PK-safe UPDATE) |
| `templates/ops/stuck-run-alerter-template.py` | Auto-terminate stuck runs: activity detection → cancel → kill subprocess → free slots |

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

> **Runbooks** (Serving Views + dbt Target Cache after Docker mount changes) → `playbooks/cross-cutting.md`

1. `[MODEL]` **Mart models MUST have** `location="{{ get_rolling_location() }}"` — nếu thiếu, `generate_serving_db.py` báo "Empty folder" và drop view
2. `[MODEL]` **src_ phải incremental** với `_dlt_load_id` filter — xử lý late-arriving events (dùng `_dlt_load_id`, không phải `event_timestamp`; xem Rule 14)
3. `[MODEL]` **src_/stg_ split** — tránh OOM; payload chỉ ở src_, stg_ đọc flat data
4. `[OPS+MODEL]` **Dagster DuckDB writer assets** phải có `op_tags={"dagster/concurrency_key": "duckdb_lock"}`
5. `[INGEST]` **`argv=[]`** khi gọi `run_*.run()` từ Dagster — tránh pick up Dagster's sys.argv
6. `[INGEST]` **`os.chdir(DLT_DIR)` + `load_dlt_configuration()`** đầu mỗi Dagster ingestion asset
7. `[SERVE]` **Serving asset `deps=[dbt_assets]`** — serving phải chạy sau dbt mart export xong
8. `[MODEL]` **Pre-create rolling dirs** trong `@dbt_assets` function (idempotent) — dbt COPY fail nếu dir không tồn tại
9. `[OPS]` **Telemetry vars** (`DLT_TELEMETRY_DISABLED=true`, `DBT_SEND_ANONYMOUS_USAGE_STATS=false`) set ở process level — tránh zombie threads block Dagster job exit
10. `[OPS]` **Jobs với nhiều ingestion sources** phải inject upstream keys qua `DagsterDbtTranslator.get_upstream_asset_keys()` — nếu không dbt start trước ingestion
11. `[META]` **Khi fix anti-pattern trong prod code** → `grep` `templates/` cho cùng pattern và fix luôn. Templates là hạt giống bug tương lai — bất kỳ asset mới copy từ template cũ sẽ kế thừa bug. Đã xảy ra thực tế 2026-04-08: serving subprocess fix ở prod, nhưng template vẫn giữ `capture_output=True` cho tới audit 2026-04-09.
12. `[INGEST]` **KHÔNG BAO GIỜ dùng `refresh="drop_sources"`** — xóa TẤT CẢ tables trong shared dataset (sapo_raw). Dùng `full_refresh` flag để reset incremental cursor, giữ nguyên data. Xem L25.
13. `[MODEL]` **Dedup ORDER BY: `modified_on DESC` trước** (entity timestamp = source of truth), sau đó ingest_method priority. KHÔNG dùng `event_timestamp` làm primary sort cho dedup — event_timestamp là timestamp của log system, không phải entity. Xem L28.
14. `[MODEL]` **Incremental filter: dùng `_dlt_load_id`** không phải `event_timestamp` — catches late-arriving data từ full-refresh hoặc history_log backfill mà event_timestamp filter sẽ bỏ sót. Xem L29.
15. `[MODEL]` **Incremental schema migration phải self-heal** — khi thêm column mới vào src_ model: (a) `on_schema_change='append_new_columns'`, (b) `adapter.get_columns_in_relation(this)` check column tồn tại, (c) guard UNION ALL, (d) cursor CTE thay vì aggregate trong WHERE subquery. DuckDB + `read_parquet()` reject MAX() in WHERE subquery. Xem L31.
16. `[OPS+MODEL]` **Nightly reconciliation = incremental, KHÔNG phải full refresh.** Dùng `pipeline_batch_fullrefresh_job` (manual, tag baked in) cho one-time reload. Không bao giờ auto-tag `full_refresh=true` trên scheduled jobs. Batch source functions phải wire `full_refresh` param từ entry-point → source → resource — nếu không flag bị silently ignored. Xem L32.
17. `[INGEST]` **`--full-refresh` phải reset dlt pipeline state dir** (`.dlt/pipelines/{name}/`), không chỉ set flag. `dlt.sources.incremental` có 2 lớp filter: manual check (code) + internal transform (state file). Chỉ set `last_value=None` mà không xóa state = dlt silently drop items. KHÔNG dùng `pipeline.drop()` (gọi `destination.drop_storage()`). Xem L33.
