# Phase 2 — Scaffolding

**Status:** pending
**Depends on:** Phase 1 (DONE)
**Blocks:** Phase 3
**Estimated effort:** 30 min

## Mục tiêu

Tạo khung folder + file rỗng cho cấu trúc mới. **Chưa di chuyển nội dung gốc** — Phase 4 mới làm. Phase này chỉ thêm, không phá vỡ gì.

## Steps

### 2.1 Tạo folders mới
```bash
cd D:/Vantt/app/data-integration/.skills/data-pipeline
mkdir -p playbooks references templates/ingest templates/model templates/serve templates/trust templates/ops
```

### 2.2 Tạo placeholder files (sẽ fill nội dung ở Phase 3)
```bash
touch playbooks/00-skill-meta.md   # NEW: meta-layer (hook, Self-Learning Protocol)
touch playbooks/01-ingest.md
touch playbooks/02-model.md
touch playbooks/03-serve.md
touch playbooks/04-trust.md
touch playbooks/05-ops.md
touch playbooks/cross-cutting.md
touch lesson-index.md
touch templates/INDEX.md
```

### 2.3 Viết ARCHITECTURE.md (nội dung đầy đủ — không phải placeholder)

File `.skills/data-pipeline/ARCHITECTURE.md` với cấu trúc:

```markdown
# Data Pipeline Architecture — 5 Functional Groups

## Mental Model

Toàn bộ ecosystem data-pipeline chia thành 5 nhóm chức năng + 1 meta-layer.
Mỗi lần triển khai (thêm source, fix bug, deploy) phải xác định work area thuộc nhóm nào → đọc playbook
tương ứng để không miss kiến thức. Meta-layer là kỷ luật về cách skill tự duy trì
(hook auto-reminder, lesson protocol, naming convention).

## Critical Path (5-group view — NEW)

[ASCII diagram: External Source → INGEST → MODEL → SERVE → Consumers
                                  ↑           ↑
                                  TRUST monitors throughout
                                  ↑
                                  OPS keeps platform alive]

## Pipeline Flow (preserved verbatim từ SKILL.md gốc)

**REQUIRED:** Copy NGUYÊN VĂN ASCII diagram + notes từ SKILL.md gốc lines 36-66:

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

## Meta-Layer (skill self-maintenance)

- **Vai trò:** Cơ chế skill tự duy trì (deploy hook, ghi lesson sau fix, đánh số Lxx)
- **Components:**
  - `hooks/data-pipeline-lesson-reminder.cjs` — PostToolUse hook fire sau `fix:` commit
  - `scripts/setup-lesson-reminder-hook.cjs` — idempotent installer
  - SKILL.md `## Environment Setup` section — runbook
  - Self-Learning Protocol format (Symptom / Root cause / Fix / Rules / Reference)
- **Playbook:** `playbooks/00-skill-meta.md`
- **Tại sao tách riêng:** Đây là agent infrastructure, không phải data infrastructure → không thuộc 5 nhóm.

## 5 Groups

### 1. INGEST [thu thập]
- **Trách nhiệm:** Kéo dữ liệu thô từ nguồn ngoài → data lake (Parquet)
- **Đặc tính:** Parallel-safe (DLT writes Parquet)
- **Chiến lược 3-channel cho Sapo:** webhook (3min) + history_log (10min) + batch (nightly)
- **Playbook:** `playbooks/01-ingest.md`

### 2. MODEL [mô hình hóa]
- **Trách nhiệm:** Raw Parquet → analytical models (DuckDB warehouse)
- **Đặc tính:** Single-writer (dbt_rw slot serial)
- **Layers:** src_(INCREMENTAL) → stg_(VIEW) → std_(VIEW) → mart_(INCREMENTAL)
- **Playbook:** `playbooks/02-model.md`

### 3. SERVE [phân phối]
- **Trách nhiệm:** Models → Metabase/Rill (last mile)
- **Đặc tính:** Dual DuckDB (warehouse vs serving) chống lock
- **Playbook:** `playbooks/03-serve.md`

### 4. TRUST [kiểm soát chất lượng]
- **Trách nhiệm:** 4-tier pyramid (got it? reasonable? matches? correct?)
- **Đặc tính:** Read-only, graceful degrade
- **Playbook:** `playbooks/04-trust.md`

### 5. OPS [vận hành nền]
- **Trách nhiệm:** Self-healing platform (alerts, slot janitor, purge, backup)
- **Đặc tính:** Reactive sensors + scheduled maintenance
- **Playbook:** `playbooks/05-ops.md`

## Cross-cutting concerns

[Link to playbooks/cross-cutting.md]
- DuckDB locking (canonical here)
- Env vars / config resolution
- Docker mount paths
- File locking Windows vs Linux

## Decision Tree: Tôi đang làm gì?

| Task | Read first |
|------|-----------|
| Setup skill lần đầu / hook không nhắc / cần ghi lesson Lxx mới | playbooks/00-skill-meta.md |
| Thêm source mới (API/file/sheet) | playbooks/01-ingest.md → checklist.md |
| Thêm/fix dbt model | playbooks/02-model.md |
| Fix Metabase nhìn dữ liệu sai/cũ | playbooks/03-serve.md |
| Thêm asset check / health alert | playbooks/04-trust.md |
| Schedule mới / sensor mới / fix stuck run | playbooks/05-ops.md |
| Lock issue / Docker path / env var | playbooks/cross-cutting.md |
| Tra cứu lesson Lxx | lesson-index.md |
```

### 2.4 Verify scaffolding
```bash
tree .skills/data-pipeline/ -L 3 --dirsfirst
# Expected:
# - playbooks/ với 6 .md files
# - references/ trống (Phase 4 sẽ fill)
# - templates/{ingest,model,serve,trust,ops}/ trống
# - ARCHITECTURE.md có nội dung
# - SKILL.md, checklist.md, *.md hiện tại vẫn ở root (chưa move)
```

## Files modified/created

| File | Type | Status |
|---|---|---|
| `.skills/data-pipeline/ARCHITECTURE.md` | NEW | Có nội dung (theo template trên) |
| `.skills/data-pipeline/playbooks/` | NEW DIR | 6 placeholder .md |
| `.skills/data-pipeline/references/` | NEW DIR | Trống |
| `.skills/data-pipeline/templates/{ingest,model,serve,trust,ops}/` | NEW DIRS | Trống |
| `.skills/data-pipeline/lesson-index.md` | NEW (placeholder) | Trống |
| `.skills/data-pipeline/templates/INDEX.md` | NEW (placeholder) | Trống |

## Definition of done

- [ ] Tất cả folder mới tồn tại
- [ ] ARCHITECTURE.md có nội dung đầy đủ (không phải placeholder)
- [ ] 6 playbook placeholder + 2 INDEX placeholder tồn tại (cho phép symlink/reference từ ARCHITECTURE.md không bị broken)
- [ ] `git status` cho thấy tất cả thay đổi là **thêm mới**, không có file nào được modify hoặc delete
- [ ] Skill hiện tại vẫn hoạt động bình thường (đọc SKILL.md, hook chạy ok)

## Rollback

```bash
rm -rf .skills/data-pipeline/{playbooks,references,templates/ingest,templates/model,templates/serve,templates/trust,templates/ops}
rm .skills/data-pipeline/{ARCHITECTURE.md,lesson-index.md,templates/INDEX.md}
```
