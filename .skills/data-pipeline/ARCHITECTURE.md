# Data Pipeline Architecture — 5 Functional Groups

## Mental Model

Toàn bộ ecosystem data-pipeline chia thành 5 nhóm chức năng + 1 meta-layer.
Mỗi lần triển khai (thêm source, fix bug, deploy) phải xác định work area thuộc nhóm nào → đọc playbook
tương ứng để không miss kiến thức. Meta-layer là kỷ luật về cách skill tự duy trì
(hook auto-reminder, lesson protocol, naming convention).

```
┌─────────────────────────────────────────────────────────────────┐
│  Meta-Layer  (agent infrastructure — hook, lesson protocol)     │
│  playbooks/00-skill-meta.md                                     │
└─────────────────────────────────────────────────────────────────┘

┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐
│  INGEST  │ →  │  MODEL   │ →  │  SERVE   │ →  │  Consumers   │
│  01      │    │  02      │    │  03      │    │  (Metabase)  │
└──────────┘    └──────────┘    └──────────┘    └──────────────┘
      ↑               ↑
      └───────────────┴──── TRUST monitors throughout (04)
                            OPS keeps platform alive (05)
```

---

## Critical Path (5-group view)

```
External Source → [INGEST] → [MODEL] → [SERVE] → Consumers
                                ↑
                           TRUST monitors throughout
                                ↑
                           OPS keeps platform alive
```

| Group | Input | Output | Failure impact |
|-------|-------|--------|---------------|
| INGEST | API / file / sheet | Parquet in data_lake/ | No raw data → MODEL starved |
| MODEL | Parquet | DuckDB warehouse models | Stale/wrong analytics |
| SERVE | DuckDB warehouse | olap.duckdb views | Metabase sees nothing/stale |
| TRUST | All layers (read-only) | Alerts / digest | Silent data quality rot |
| OPS | Platform events | Self-healed platform | Stuck runs, lock contention |

---

## Pipeline Flow (preserved verbatim từ SKILL.md)

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

## Meta-Layer (skill self-maintenance)

- **Vai trò:** Cơ chế skill tự duy trì (deploy hook, ghi lesson sau fix, đánh số Lxx)
- **Components:**
  - `hooks/data-pipeline-lesson-reminder.cjs` — PostToolUse hook fire sau `fix:` commit
  - `scripts/setup-lesson-reminder-hook.cjs` — idempotent installer
  - SKILL.md `## Environment Setup` section — runbook
  - Self-Learning Protocol format (Symptom / Root cause / Fix / Rules / Reference)
- **Playbook:** `playbooks/00-skill-meta.md`
- **Tại sao tách riêng:** Đây là agent infrastructure, không phải data infrastructure → không thuộc 5 nhóm.

---

## 5 Groups

### 1. INGEST [thu thập]

- **Trách nhiệm:** Kéo dữ liệu thô từ nguồn ngoài → data lake (Parquet)
- **Đặc tính:** Parallel-safe (DLT writes Parquet)
- **Chiến lược 3-channel cho Sapo:** webhook (3min) + history_log (10min) + batch (nightly)
- **Key files:**
  - `references/lessons-learned.md` — L1-L48 phần lớn là INGEST
  - `templates/ingest/` — source, run-entry-point, dagster-asset templates
- **Playbook:** `playbooks/01-ingest.md`

### 2. MODEL [mô hình hóa]

- **Trách nhiệm:** Raw Parquet → analytical models (DuckDB warehouse)
- **Đặc tính:** Single-writer (dbt_rw slot serial)
- **Layers:** src_(INCREMENTAL) → stg_(VIEW) → std_(VIEW) → mart_(INCREMENTAL)
- **Key files:**
  - `references/dbt-patterns.md` — 14 lessons MODEL deep-dive
  - `templates/model/` — src, dim, fact, sources.yml, schema.yml templates
- **Playbook:** `playbooks/02-model.md`

### 3. SERVE [phân phối]

- **Trách nhiệm:** Models → Metabase/Rill (last mile)
- **Đặc tính:** Dual DuckDB (warehouse vs serving) chống lock
- **Key files:**
  - `references/serving-layer.md` — SERVE deep-dive
  - `templates/serve/` — dagster-serving-asset template
- **Playbook:** `playbooks/03-serve.md`

### 4. TRUST [kiểm soát chất lượng]

- **Trách nhiệm:** 4-tier pyramid (got it? reasonable? matches? correct?)
- **Đặc tính:** Read-only, graceful degrade
- **Key files:**
  - `references/ingestion-health-digest.md` — TRUST deep-dive
  - `templates/trust/` — health recorder, digest, row-count, backfill templates
- **Playbook:** `playbooks/04-trust.md`

### 5. OPS [vận hành nền]

- **Trách nhiệm:** Self-healing platform (alerts, slot janitor, purge, backup)
- **Đặc tính:** Reactive sensors + scheduled maintenance
- **Key files:**
  - `references/dagster-patterns.md` — 14 lessons OPS deep-dive
  - `templates/ops/` — reactive-sensor, stuck-run-alerter templates
- **Playbook:** `playbooks/05-ops.md`

---

## Cross-cutting concerns

See `playbooks/cross-cutting.md` — canonical home for:
- DuckDB locking (exclusive lock on VACUUM, WAL behavior)
- Env vars / config resolution (`.env` sections, documented defaults)
- Docker mount paths (Windows vs Linux host, named volume overlay)
- File locking Windows vs Linux (SQLite WAL, DuckDB WAL)

---

## Decision Tree: Tôi đang làm gì?

| Task | Read first |
|------|-----------|
| Setup skill lần đầu / hook không nhắc / cần ghi lesson Lxx mới | `playbooks/00-skill-meta.md` |
| Thêm source mới (API/file/sheet) | `playbooks/01-ingest.md` → `checklist.md` |
| Thêm/fix dbt model | `playbooks/02-model.md` |
| Fix Metabase nhìn dữ liệu sai/cũ | `playbooks/03-serve.md` |
| Thêm asset check / health alert | `playbooks/04-trust.md` |
| Schedule mới / sensor mới / fix stuck run | `playbooks/05-ops.md` |
| Lock issue / Docker path / env var | `playbooks/cross-cutting.md` |
| Tra cứu lesson Lxx | `lesson-index.md` |
