# Phase 3 — Write Group Playbooks

**Status:** pending
**Depends on:** Phase 2
**Blocks:** Phase 4
**Estimated effort:** 4-6 giờ (lượng nội dung lớn)

## Mục tiêu

Viết nội dung đầy đủ cho **6 playbook (5 nhóm + 1 meta)** + cross-cutting + lesson-index + templates/INDEX.
Mỗi playbook phải tự đủ để 1 agent fresh-context có thể: (a) hiểu group's role,
(b) chạy pre-flight checklist trước implement, (c) follow templates, (d) tra cross-ref tới deep references.

**Quan trọng:** Playbook = navigation + checklist + pointers, KHÔNG copy nguyên nội dung từ references.
Mục đích là "gateway" tới deep knowledge, không phải clone của nó.

## Playbook template (áp dụng cho 5 nhóm)

```markdown
# [Group Code] Playbook — [Vietnamese name]

## Trách nhiệm
[1-2 đoạn: nhóm này handle gì, đầu vào, đầu ra]

## Pre-flight Checklist (đọc TRƯỚC khi implement)
- [ ] [Critical item 1 — đã từng gây production issue]
- [ ] [Critical item 2]
- [ ] [...]

## Mental model & patterns
[Patterns chính của nhóm — ngắn gọn, link tới references cho deep-dive]

## Templates
[Link tới templates/{group}/ với mô tả khi nào dùng cái nào]

## Lessons cross-reference
[Bảng L_xx → 1-line summary → link tới references/lessons-learned.md#L_xx]

## Common pitfalls
[Từ troubleshooting.md, phần liên quan group này]

## When this group interacts with others
[Cross-references — ví dụ INGEST writes Parquet → MODEL reads Parquet]

## Related cross-cutting concerns
[Pointers tới cross-cutting.md sections relevant]
```

## 3.0 Viết `playbooks/00-skill-meta.md` (META-LAYER)

**Trách nhiệm:** Document skill self-maintenance — hook deployment, lesson recording protocol, naming conventions. Kỷ luật ghi nhận kinh nghiệm để skill không bị stale.

### Pre-flight checklist (khi join project mới hoặc setup máy mới)
- [ ] Hook đã deploy chưa: `ls "$HOME/.claude/hooks/data-pipeline-lesson-reminder.cjs"`
- [ ] Nếu MISSING → `node .skills/data-pipeline/scripts/setup-lesson-reminder-hook.cjs`
- [ ] Reload Claude Code (`/hooks` hoặc restart) để hook active
- [ ] Verify hook trigger bằng `fix:` commit thử nghiệm — phải thấy "📝 LESSON TRIGGER" reminder
- [ ] `.claude/settings.local.json` có entry hook (setup script tự merge)

### Cơ chế hook
- **Trigger:** `PostToolUse` matcher `Bash`, fire sau khi `git commit -m "fix:..."` chạy
- **Logic:**
  1. Parse stdin JSON từ Claude harness
  2. Check command có `git commit` không
  3. Extract `-m` message; check prefix `fix:` hoặc `fix(`
  4. Đọc `references/lessons-learned.md` (sau Phase 4 reorganization), tìm Lxx cuối cùng
  5. Output `additionalContext` reminder cho agent
- **Fail-open:** lỗi parse → `process.exit(0)`, không block commit

### Self-Learning Protocol (format ghi lesson)

Mỗi lesson Lxx mới thêm vào `references/lessons-learned.md` PHẢI có 5 phần:

```markdown
### Lxx — [Title ngắn gọn, mô tả pattern/bug]

**Symptom:** [Triệu chứng quan sát được — log error, behavior bất thường]
**Root cause:** [Nguyên nhân gốc rễ — tại sao xảy ra, không phải fix gì]
**Fix:** [Code/config thay đổi cụ thể; link commit nếu có]
**Rules (rút ra):** [Generalize thành rule/anti-pattern để áp dụng tương lai]
**Reference:** [Files/lines bị ảnh hưởng, post-mortem date, related Lxx]
```

### Naming conventions

| Convention | Áp dụng | Ví dụ |
|-----------|---------|-------|
| Lessons trong `lessons-learned.md` | `### L<n> — Title` | `### L57 — history_log double-fetch` |
| Số Lxx KHÔNG fill gap | Append-only | L34 đã skip — không reuse |
| Lessons trong `dagster-patterns.md` | `## Lesson <n>: Title` | `## Lesson 14: Maintenance Schedule Topology` |
| Lessons trong `dbt-patterns.md` | `## Lesson <n>: Title` | `## Lesson 5: Rolling Location` |
| Post-mortem date | Trong section header | `## Stuck Run Prevention (post-mortem 2026-04-24)` |

### Workflow: thêm lesson Lxx mới

1. Sau commit `fix:` → hook nhắc → check root cause non-trivial
2. Tìm Lxx cuối: `grep "^### L" references/lessons-learned.md | tail -5`
3. Append `### L<next> — Title` ở section phù hợp (chronological hoặc topical)
4. Điền 5-part Self-Learning Protocol
5. **PHẢI update `lesson-index.md`** — thêm dòng với group(s) gán
6. Nếu cross-cutting → thêm vào `playbooks/cross-cutting.md` section liên quan
7. Nếu lesson liên quan template → update template docstring `See:` line

### Mở rộng tương lai (không in scope của reorganization này)

- Hook detect commit file paths để suggest target group khi reminder fire (e.g., commit chạm `transformation/` → "consider MODEL group")
- Auto-update lesson-index.md từ git log
- Linter check Lxx format compliance

### Files của meta-layer

| File | Vai trò | Khi nào sửa |
|------|---------|-------------|
| `hooks/data-pipeline-lesson-reminder.cjs` | Hook source | Khi đổi reminder text/path/trigger logic |
| `scripts/setup-lesson-reminder-hook.cjs` | Idempotent installer | Khi đổi hook entry trong settings.local.json |
| `~/.claude/hooks/data-pipeline-lesson-reminder.cjs` | Deployed copy | Re-run setup script sau update source |
| `.claude/settings.local.json` (project) | Hook registration | Setup script tự merge |
| `references/lessons-learned.md` | Lessons store | Append Lxx mỗi fix non-trivial |
| `lesson-index.md` | Cross-ref index | Update mỗi lần thêm Lxx |

### Cross-cutting refs

- KHÔNG có (meta-layer độc lập, không phụ thuộc DuckDB/Docker/env)

---

## 3.1 Viết `playbooks/01-ingest.md`

**Nội dung phải có:**

### Bước 0 — Chọn Pattern (PRESERVE từ SKILL.md gốc)

```
Source đã có trong dlt hub?
(dlthub.com/docs/dlt-ecosystem/verified-sources)
        │
   YES  │  NO
        │
 Pattern B ─── Pattern A (FOCUS)
 (note ngắn)   (custom envelope)
```

#### Pattern B — Native dlt source (note ngắn)
```python
from dlt.sources.facebook_ads import facebook_ads_source
pipeline = dlt.pipeline(pipeline_name="...", destination="duckdb", dataset_name="...")
pipeline.run(facebook_ads_source(account_id=..., chunk_size=1000))
```
Reference: `ingestion/run_facebook_ads_batch.py`

#### Pattern A — Custom API (full guide)
Theo 6-phase trong `../checklist.md`. Pre-flight checklist bên dưới = Phase 1-2 details.

### Pre-flight checklist
- [ ] Source authentication: API token / cookie / OAuth strategy chọn xong
- [ ] Envelope schema: `event_timestamp`, `entity_id`, `modified_on`, `ingest_method`, `sync_metadata` defined
- [ ] Incremental cursor field xác định (use full path: `sync_metadata.event_timestamp`)
- [ ] `--full-refresh` support: phải reset BOTH last_value AND `.dlt/pipelines/{name}/` state dir (L33)
- [ ] Partition layout `{table_name}/ingest_method=*/year=*/month=*/{file_id}.parquet` declared trong config.toml `extra_placeholders`
- [ ] Health recorder wired: `record_run(asset_key, run_id, ...)` với composite PK (L41, L44)
- [ ] Dagster asset wiring: `argv=[]`, `os.chdir(DLT_DIR)`, `load_dlt_configuration()` (L8-L10)
- [ ] Concurrency tag: nếu asset write DuckDB → `op_tags={"dagster/concurrency_key": "duckdb_lock"}` (L11)
- [ ] Telemetry disabled: `DLT_TELEMETRY_DISABLED=true` (Lesson 4 dagster-patterns) — tránh zombie thread

### Patterns
- 3-channel resilience cho Sapo (webhook/history_log/batch)
- Early-stop pagination thay vì total_count (L1)
- Empty page retry trước khi stop (L6)
- Cookie TTL + 401/403 refresh on-demand (L13, L27)
- Webhook ACK at-least-once + dedup safety net (L14)
- Consumer loop vs one-off mode (L15)
- File-drop sensor cold-start handling (L67)
- Config snapshot fixed path cho Google Sheets (L59)

### Templates
- `templates/ingest/source-template.py` — DLT source + envelope builder
- `templates/ingest/run-entry-point-template.py` — entry point wrapper, MUST `return run_pipeline(...)` (L36)
- `templates/ingest/dagster-asset-template.py` — Dagster ingestion asset

### Supporting scripts (từ references/supporting-scripts.md — INGEST relevant)
- `scripts/clean_dlt_state.py` — Drop pending dlt packages (debug stuck pipeline)
- `scripts/inspect_customer_parquet.py` — Inspect raw Parquet output
- **Decision logic:** Xem `references/supporting-scripts.md` "Khi Nào Gọi Script Nào" — bảng tình huống → script chain.

### Debug recipes (từ references/troubleshooting.md "Debug Recipes")
- Check data lake content
- Check dlt state
- Full pipeline dry run (local)

### Lessons cross-reference
[Bảng L1-L7, L8-L10, L13-L16, L24-L27, L33, L57, L59, L76 + config setup section]

### Sapo-specific notes
- Sapo orders API silently ignores `created_on` filter (L76) — dùng `modified_on` window
- history_log truncation risk → keep raw lâu hơn (xem plan 260422 raw-layer-compaction)
- min_overlap_items: KHÔNG raise lên 500 (L57)
- NEVER `refresh="drop_sources"` (L25)

### Rollback scenarios (cross-ref `../checklist.md` "Rollback Plan")

Khi pipeline fail, đọc 4 scenarios trong `checklist.md` Rollback Plan section:
1. **dlt state corrupt** → `python scripts/clean_dlt_state.py` hoặc `--full-refresh`
2. **dbt incremental stuck** → `dbt run --full-refresh --select src_{source}_{entity}`
3. **Serving view dropped** → fix mart `location` config + rerun dbt + `generate_serving_db.py`
4. **Xóa source hoàn toàn** → 5-step cleanup (config, code, dbt, Dagster, parquet)

### Cross-cutting refs
- `cross-cutting.md#duckdb-locking` (nếu DuckDB write)
- `cross-cutting.md#env-vars-config` (canonical config docs)
- `cross-cutting.md#cwd-load-dlt-configuration`

---

## 3.2 Viết `playbooks/02-model.md`

### Pre-flight checklist
- [ ] sources.yml entry với external Parquet glob (Hive partition)
- [ ] src_ model: incremental, dedup ORDER BY `modified_on DESC` first, then `ingest_method` priority (L4, L28)
- [ ] Incremental filter dùng `_dlt_load_id`, KHÔNG `event_timestamp` (L29)
- [ ] src_/stg_ split: payload chỉ ở src_ → tránh OOM (Lesson 2 dbt-patterns)
- [ ] Mart models có `location="{{ get_rolling_location() }}"` (Lesson 5 dbt-patterns) — thiếu là drop view
- [ ] Pre-create rolling dirs trong `@dbt_assets` function (Lesson 3 dagster-patterns)
- [ ] Schema migration self-heal cho thêm column (L31): `on_schema_change='append_new_columns'`, `adapter.get_columns_in_relation`, guard UNION ALL, cursor CTE
- [ ] Tests trong `schema.yml`: unique, not_null, relationships
- [ ] Reference seeds nếu cần (Lesson 12 dbt-patterns)
- [ ] `op_tags={"dagster/concurrency_key": "duckdb_lock"}` cho dbt assets (L11) — single-writer constraint
- [ ] Telemetry disabled: `DBT_SEND_ANONYMOUS_USAGE_STATS=false` (Lesson 4 dagster-patterns)

### Patterns
- 5-hop flow: src_ → stg_ → std_ → int_ → dim_/fact_
- Two-phase dedup OOM-safe (Lesson 1 dbt-patterns)
- Compare-before-overwrite cho idempotent dedup (L30)
- Post-hook pattern (Lesson 9 dbt-patterns)
- JSON extraction với coalesce fallbacks (Lesson 10)
- Partition pruning với Hive partitioning (Lesson 13)
- Generated time dimension SQL (Lesson 14)
- Nightly incremental ≠ full-refresh — separate jobs (L32, Lesson 9 dagster)
- dlt incremental 2-layer filter — reset both for full-refresh (L33)

### Templates
- `templates/model/src-model-template.sql`
- `templates/model/dim-model-template.sql`
- `templates/model/fact-model-template.sql`
- `templates/model/sources-yml-template.yml`
- `templates/model/schema-yml-template.yml`

### Reference sections (từ references/dbt-patterns.md — non-lesson material)
- **Project Configuration** (lines 3-54) — `profiles.yml` (memory=5GB, threads=1), `dbt_project.yml` materialization by layer
- **5-Hop Transformation Flow** (lines 55-67) — overview architecture
- **Quick Reference: Materialization Decision Tree** (line 465+) — `view` vs `incremental` vs `external_parquet`

### Supporting scripts (từ references/supporting-scripts.md — MODEL relevant)
- `scripts/ensure_dbt_directories.py` — Pre-create rolling/ dirs trước dbt run
- `transformation/scripts/run_dbt.py` — dbt build wrapper (handles env, logs, target)
- `transformation/check_view.py` — Inspect dbt model state
- `scripts/maintenance/sync_seeds.py` — Refresh seed CSVs
- **Decision logic:** Xem `references/supporting-scripts.md` "Khi Nào Gọi Script Nào" — bảng tình huống → script chain. Đặc biệt: thêm mart model mới → chuỗi `ensure_dbt_directories.py → run_dbt.py --select {model} → generate_serving_db.py`.

### Cross-ref tới SERVE
- Khi thêm/sửa mart model: `references/serving-layer.md` "Checklist khi thêm mart model mới" — overlap với checklist Phase 3.5; cả 2 PHẢI satisfy.

### Debug recipes (từ references/troubleshooting.md "Debug Recipes")
- Check dbt incremental state
- Check rolling snapshot latest
- Verify DuckDB file lock status empirically

### Lessons cross-reference
[L4, L5, L28-L31, L32-L33, Lesson 1-14 dbt-patterns, Lesson 3 + 9 dagster-patterns]

### Cross-cutting refs
- `cross-cutting.md#duckdb-locking` (canonical — dbt là writer chính)
- `cross-cutting.md#docker-mount-paths` (rolling output paths)
- `cross-cutting.md#dbt-target-cache-after-mount-change`

---

## 3.3 Viết `playbooks/03-serve.md`

### Pre-flight checklist
- [ ] Mart models có `location="{{ get_rolling_location() }}"` — KIỂM TRA trước serve
- [ ] Serving asset `deps=[dbt_assets]` (Critical Rule 7 SKILL.md)
- [ ] Dual DuckDB: warehouse khác serving file
- [ ] Serving views regen sau Docker mount path change (Critical Rules SKILL.md)
- [ ] `bootstrap_serving_views.py` chạy với Metabase đã stop (release lock)
- [ ] dbt target cache cleared sau mount change (`rm -rf transformation/target/`, sau đó `dbt parse` TRƯỚC khi Dagster restart)
- [ ] Empty folder → drop view (serving-layer.md §5)
- [ ] Pre-create rolling dirs (serving-layer.md §6)

### Patterns
- Rolling Self-Refresh Views (serving-layer.md §2)
- Garbage collection cho rolling parquets (§3)
- DuckDB lock behavior cho read_only (L18) — read_only KHÔNG acquire lock
- Zero-downtime swap

### Templates
- `templates/serve/dagster-serving-asset-template.py`

### Supporting scripts (từ references/supporting-scripts.md — SERVE relevant)
- `scripts/provisioning/generate_serving_db.py` — Rolling → Self-Refresh Views + GC
- `scripts/provisioning/bootstrap_serving_views.py` — Alternative safer view gen (dùng khi mount path đổi)
- `scripts/provisioning/metabase_provisioner.py` — Metabase admin provisioning
- `scripts/provisioning/refresh_rolling.py` — Roll forward Parquet exports
- `scripts/debug_duckdb.py` — Query debugging on serving DB
- **Decision logic:** Xem `references/supporting-scripts.md` "Khi Nào Gọi Script Nào".

### Mart-add checklist (cross-ref)
- `references/serving-layer.md` "Checklist khi thêm mart model mới" — phải satisfy cùng với MODEL playbook + checklist Phase 3.5.

### Debug recipes (từ references/troubleshooting.md "Debug Recipes")
- Check serving view
- `references/serving-layer.md` "Debug Commands" section

### Lessons cross-reference
[L18, Lesson 5 dbt-patterns, full serving-layer.md]

### Cross-cutting refs
- `cross-cutting.md#duckdb-locking` (read vs write semantics)
- `cross-cutting.md#docker-mount-paths` (view paths bake absolute)

---

## 3.4 Viết `playbooks/04-trust.md`

### Pre-flight checklist
- [ ] Health recorder: composite PK `(asset_key, run_id)` — UPDATE/DELETE filter BOTH (L44)
- [ ] datetime serialization: dùng ISO string, `or 0` fallback cho `MetadataValue.float()` (L41, L66)
- [ ] Row count extraction 3-layer fallback: metric walk → file_id glob → `_dlt_load_id` scan (L42)
- [ ] Digest window: business-TZ calendar day, KHÔNG rolling 24h (L43)
- [ ] Dashboard SQL handle "asset chưa từng chạy" — không cross join (L37)
- [ ] Runner entry point MUST `return run_pipeline(...)` — không return = silent skip (L36)
- [ ] `asset_check_executions` cleanup trong purge (L55)
- [ ] Health checks job: `in_process_executor`, exclude dbt tests, mutual-exclude với ingestion (L40, L65, Lesson 11 dagster)
- [ ] Trust pyramid: Tier 1 (got it?) + Tier 2 (reasonable?) + Tier 3 (matches?) + Tier 4 (correct?)

### ⭐ Production Checklist (12 items, từ `references/ingestion-health-digest.md` "Production checklist")

Bắt buộc verify TẤT CẢ 12 items trước khi enable digest schedule production:
1. Health DB path resolves trong **cả** host dev (`.env.local`) + container (`.env.docker`) — mismatch = silent empty digest
2. Health DB included trong daily backup rotation (post-mortem 2026-04-22 recovery)
3. `record_run` wrapped trong try/except mọi call site — grep verify
4. `extract_rows_written` chạy với `DBT_DATA_LAKE_PATH` set — thiếu = Layer 2/3 silently None
5. Digest schedule SAU recon/KPI (typical: recon 04:30 → KPI 04:45 → digest 06:00 business TZ)
6. Digest wrapped try/except quanh `send_*_card` — log, don't raise
7. Dry-run via `DIGEST_DRY_RUN=1` verified TRƯỚC khi enable schedule
8. Asset registry include TẤT CẢ assets với `asset_type` (cursor/batch/file_drop) + `unit_label` đúng
9. SLA hours per pipeline cadence (12h cho daily batches; cursor có thể 6h)
10. Zero-streak detection có threshold N >= 2 (thấp hơn = noisy)
11. Backfill script tồn tại với composite-PK UPDATE
12. Code review rule: mọi UPDATE/DELETE on `ingestion_runs` phải BOTH `asset_key AND run_id`

### Patterns
- 4-tier trust pyramid (freshness/not-empty → row-trend/cursor-stall → recon → KPI closure)
- Asset-type-aware messaging trong digest
- Graceful degrade khi live API unavailable (RECON_LIVE_API)
- Composite-PK recovery playbook (ingestion-health-digest.md)

### Templates
- `templates/trust/ingestion-health-recorder-template.py`
- `templates/trust/ingestion-health-digest-template.py`
- `templates/trust/dlt-row-count-extractor-template.py`
- `templates/trust/backfill-health-rows-written-template.py`

### Supporting scripts (từ references/supporting-scripts.md — TRUST relevant)
- `scripts/maintenance/backfill_ingestion_health_rows_written.py` — Recovery script khi extractor fix
- `scripts/testing/verify_hops_readonly.py` — Smoke test row counts qua các hops
- **Decision logic:** Xem `references/supporting-scripts.md` "Khi Nào Gọi Script Nào".

### Debug recipes (từ references/troubleshooting.md "Health Monitoring DB" + "Debug Recipes")
- `references/troubleshooting.md` Health Monitoring DB section — symptom→cause→fix cụ thể

### Lessons cross-reference
[L36, L37, L40, L41, L42, L43, L44, L55, L66, Lesson 11 dagster-patterns, Lesson 11 dbt-patterns, full ingestion-health-digest.md]

### Cross-cutting refs
- `cross-cutting.md#sqlite-wal-safety` (health DB)
- `cross-cutting.md#composite-pk-update-trap`

---

## 3.5 Viết `playbooks/05-ops.md`

### Pre-flight checklist
- [ ] Dagster asset writes DuckDB → `op_tags={"dagster/concurrency_key": "duckdb_lock"}`, limit=1 (L11)
- [ ] Schedules trong `defs.schedules=[...]` phải explicit start (L49)
- [ ] Ingestion job tổng hợp: inject upstream keys qua DagsterDbtTranslator (Lesson 1 dagster, Critical Rule 10)
- [ ] Schedule offset tránh start-time race (Lesson 2 dagster: realtime `*/3`, incremental `*/10`, lệch nhau)
- [ ] Self-overlap skip: `_has_active_run()` trong schedule fn (Lesson 5 dagster)
- [ ] Yield-to-batch: realtime/incremental skip khi long batch đang chạy (yield logic)
- [ ] Telemetry disabled tại process level: `DLT_TELEMETRY_DISABLED=true`, `DBT_SEND_ANONYMOUS_USAGE_STATS=false` (Lesson 4 dagster) — tránh zombie thread
- [ ] dbt subprocess timeout watchdog (`DBT_TIMEOUT_SEC=900`) (L45)
- [ ] stuck-run alerter: kill ACTUAL subprocess via psutil + free slot + cancel run (L46)
- [ ] stuckrun sensor cover ALL non-terminal states (Pass 2: queue-stuck) (L52, L61)
- [ ] Backup acquire `duckdb_lock` (L47); `trap … EXIT` rotation (L50); exclude `dagster_home/history/` (L51)
- [ ] Purge cleans dbt target dirs (post-mortem 2026-04-28 disk-full)
- [ ] Concurrency pool janitor every 5 min (L20, L39)
- [ ] Health DB watchdog 10 min: ghost lock + stale > 2h
- [ ] Read-only jobs (recon, kpi, digest) dùng `in_process_executor` (L65)
- [ ] `run_status_sensor` cho hard ordering (backup-after-purge) (L54)
- [ ] `MetadataValue.float()` int trap: `or 0` fallback (L66)
- [ ] Reactive sensor cho external source: hash polling (L21, Lesson 7 dagster) — không cần Drive API

### Patterns
- Self-healing chain: stuck → kill → alert → janitor → unblock
- Schedule topology: 01:00 purge → 03:00 batch → 04:30 recon → 04:45 kpi → 06:00 digest+backup
- Layered Defense (timeout watchdog → stuckrun sensor → janitor)
- File-drop sensor mtime cursor (L67)
- Phantom Dagster instigator state cleanup (L53)
- Subprocess pipe deadlock fix: tee piping thay capture_output=True (L17)

### ⭐ Synthesis: Maintenance Cron Design Principles
**Source:** `references/lessons-learned.md` line 1595+ (sub-section, KHÔNG phải numbered Lxx — easy to miss)

8 design principles + topology table — **đây là canonical pattern cho daily maintenance jobs.** PHẢI đọc khi thiết kế lịch chạy mới hoặc thay đổi schedule:
1. Order by mutual exclusion (purge → backup)
2. Window in quiet zone (01:00-01:59 ICT)
3. Enforce ordering via sensor, not cron offset
4. Bound resource cost (concurrency tags + pre-flight)
5. Always-run cleanup via `trap … EXIT`
6. Exclude regenerable data
7. Auto-recovery sensors cover ALL non-terminal states
8. Pre-flight disk check excludes backup destination from source size

### ⭐ Stuck Run Prevention (highlighted callout — preserved từ SKILL.md gốc)
- **Lesson 10-13** trong `references/dagster-patterns.md`: dbt subprocess timeout, subprocess killing via psutil, backup concurrency lock, zombie NOT_STARTED cleanup

### ⭐ Maintenance Cron Topology (highlighted callout — preserved từ SKILL.md gốc)
- **Lesson 14 + L49-L52**: schedule must be explicitly started, backup `trap … EXIT` rotation, `prune_dagster_history`, stuck-run sensor Pass 2 (queue-stuck), purge cleans dbt target dirs (post-mortem 2026-04-28 disk-full)

### Templates
- `templates/ops/dagster-reactive-sensor-template.py`
- `templates/ops/stuck-run-alerter-template.py`

### Supporting scripts (từ references/supporting-scripts.md — OPS relevant)
- `scripts/maintenance/unstick_concurrency_pools.py` — Manual janitor cho stuck slots
- `scripts/maintenance/cleanup_and_verify.py` — Cleanup + state verification
- `scripts/maintenance/reset_ingestion.py` — Reset ingestion state khi corrupt
- `scripts/run_pipeline.ps1` — PowerShell pipeline runner
- `scripts/backup/` — Hot backup scripts (`trap…EXIT` rotation)
- **Decision logic:** Xem `references/supporting-scripts.md` "Khi Nào Gọi Script Nào".

### Debug recipes (từ references/troubleshooting.md "Debug Recipes")
- Verify DuckDB file lock status empirically (Windows dllhost detection)
- Full pipeline dry run (local)

### ⚠️ External tool drift warning (preserved)
- "CLI Versioning: Commands like `set-concurrency-limit` may change between Dagster versions. **Always verify** inside container." (từ AGENTS.md → preserved trong OPS playbook làm reminder)

### Reference sections (từ references/dagster-patterns.md — non-lesson material)
- **Summary: Dagster Integration Checklist** (line 773) — pull-once tổng hợp
- **Reference Files** (line 821) — pointer tới source files

### Lessons cross-reference
[Hầu hết L8, L11, L12, L17-L23, L32, L38-L40, L45-L58, L60-L75, all 14 Lessons dagster-patterns]

### Cross-cutting refs
- `cross-cutting.md#duckdb-locking` (canonical — slot management)
- `cross-cutting.md#docker-mount-paths` (volumes)
- `cross-cutting.md#file-locking-windows-vs-linux` (L62, L70-L73)
- `cross-cutting.md#sqlite-wal-safety` (purge VACUUM L74)
- `cross-cutting.md#telemetry-zombie-threads` (canonical here)

---

## 3.6 Viết `playbooks/cross-cutting.md`

**Sections (canonical homes cho 8 cross-cutting concerns):**

### DuckDB locking
- Single-writer storage → `duckdb_lock` slot (limit=1)
- read_only mode KHÔNG acquire lock (L18)
- Bind-mount Windows NTFS vulnerable (L62, L70, L73)
- Defender exclusion entire `data_lake` (L72)
- Asset-level concurrency (op_tags), KHÔNG job-level (concurrency_group)
- Slot leak khi cancel runs (L20) → janitor (L39)
- Purge VACUUM exclusive lock 5+ phút (L74)

### Env vars / config resolution
- Config layered: secrets.toml.sample → secrets.toml → .env.local → process env
- Single .env organization: sections, no per-service split (memory: feedback_config_organization)
- DLT mapping `__` double underscore: `SECTION__SUBSECTION__KEY`
- `extra_placeholders` cho custom partition fields
- `bucket_url` trong secrets.toml (path nhạy cảm)
- L35 Config ecosystem: layered defaults, single .env

### Docker mount paths
- Convention: code at `/app/`, data at `/app/var/`
- Path resolution pattern: env var với Docker default
- Cross-platform: `os.path.join()` hoặc forward slashes; never hardcoded backslash

#### Runbook A: Serving Views absolute paths — sau mount change (PRESERVE từ SKILL.md gốc)

Serving views (`olap.duckdb`) BAKE absolute paths vào SQL. Khi mount path thay đổi:

```bash
# 1. Stop Metabase first (releases DuckDB lock)
docker compose down

# 2. Regenerate serving views
docker compose up -d data_platform
docker compose exec data_platform python scripts/provisioning/bootstrap_serving_views.py

# 3. Restart Metabase
docker compose up -d metabase
```

Why? Views chứa embedded paths kiểu:
```sql
CREATE VIEW dim_customers AS SELECT * FROM '/app/var/data_lake/export/marts/rolling/dim_customers/*.parquet'
```
Nếu `/app/var/data_lake` đổi thành `/app/data_lake`, view paths broken → Metabase queries fail.

#### Runbook B: dbt Target Cache — sau mount change (PRESERVE từ SKILL.md gốc)

dbt `target/` cache compiled SQL + model state với absolute parquet paths từ `get_rolling_location()`. Khi mount đổi:
- Cached state references old paths → `IO Error: Cannot open file "/app/data_lake/...": No such file or directory`

```bash
# Clean target + regenerate manifest BEFORE Dagster restart
docker exec data_platform bash -c "rm -rf /app/transformation/target"
docker exec data_platform bash -c "cd /app/transformation && dbt deps && dbt parse"
docker compose restart data_platform
```

**⚠️ Order matters:** `dbt parse` MUST run trước Dagster restart — Dagster import `manifest.json` lúc startup. Nếu `rm -rf target/` rồi restart không parse, Dagster crash với `DagsterDbtManifestNotFoundError`.

Hoặc selectively rebuild các models bị fail:
```bash
docker exec data_platform bash -c "cd /app/transformation && dbt build --select model_name_1 model_name_2"
```

### Telemetry / zombie threads
- DLT/dbt telemetry threads keep process alive
- Set process-level: `DLT_TELEMETRY_DISABLED=true`, `DBT_SEND_ANONYMOUS_USAGE_STATS=false`
- Lesson 4 dagster-patterns

### File locking Windows vs Linux
- Windows: advisory locks → PermissionError trên locked files
- Linux container: NO advisory lock → handle explicitly (retry, swap, graceful skip)
- Windows dllhost.exe (COM Surrogate / Defender) locks DuckDB on bind-mount (L62, L70)
- L12 Cross-platform file locking primitive

### SQLite WAL safety
- L56 SQLite WAL safety in purge/cleanup
- L68 cp -a returns non-zero with WAL/SHM disappearing mid-copy
- L74 SQLite VACUUM exclusive lock blocks Dagster
- Health DB watchdog detect ghost lock (L62)

### CWD + load_dlt_configuration
- L9 os.chdir(DLT_DIR) trước run
- L10 load_dlt_configuration() phải gọi đầu mỗi asset
- `.env.local` ở project root (KHÔNG ingestion/)

### Composite PK update trap (ingestion_runs)
- L44 always filter BOTH `asset_key AND run_id`
- run_id is shared across assets in Dagster jobs
- Memory: feedback_ingestion_runs_composite_pk

---

## 3.7 Viết `lesson-index.md`

**Format:**
```markdown
# Lesson Index — All lessons by Functional Group

## INGEST
| ID | Title | Date | File |
|----|-------|------|------|
| L1 | Early-stop pagination | 2026-04-08 | references/lessons-learned.md#L1 |
| L2 | Incremental cursor path | ... | ... |
| ...

## MODEL
| ID | Title | Date | File |
|----|-------|------|------|
| L4 | Ingest method priority dedup | ... | ... |
| L5 | 7-day incremental buffer | ... | ... |
| L28-L31 | Dedup correctness | ... | ... |
| dbt-Lesson-1 | Two-Phase Dedup OOM-Safe | ... | references/dbt-patterns.md#lesson-1 |
| ...

## SERVE
| ID | Title | Date | File |
|----|-------|------|------|
| L18 | DuckDB read_only no lock | ... | ... |
| ...

## TRUST
| ID | Title | Date | File |
|----|-------|------|------|
| L36, L37, L40-L44, L55, L66 | ... | ... |

## OPS
| ID | Title | Date | File |
|----|-------|------|------|
| L8, L11, L12, L17-L23, L32, L38-L40, L45-L75 | ... | ... |
| dagster-Lesson-1..14 | All 14 dagster-patterns lessons |

## Cross-cutting
| ID | Title | Canonical home | Referenced from |
|----|-------|----------------|-----------------|
| L11 | DuckDB concurrency lock | cross-cutting.md#duckdb-locking | OPS, MODEL |
| L35 | Config ecosystem | cross-cutting.md#env-vars-config | INGEST |
| ...
```

**Mỗi lesson có 1 dòng**, tổng ~104 dòng (76 + 14 + 14).

---

## 3.8 Viết `templates/INDEX.md`

```markdown
# Templates by Functional Group

## INGEST — `templates/ingest/`
- `source-template.py` — DLT source + resource + envelope builder. Pattern A custom envelope.
- `run-entry-point-template.py` — DLT entry point wrapper. MUST `return run_pipeline(...)` (L36).
- `dagster-asset-template.py` — Dagster ingestion asset. Includes `argv=[]`, `os.chdir`, `load_dlt_configuration`.

## MODEL — `templates/model/`
- `src-model-template.sql` — dbt src_: INCREMENTAL, dedup, JSON extract, _dlt_load_id filter.
- `dim-model-template.sql` — dbt dim_ với `location=get_rolling_location()`.
- `fact-model-template.sql` — dbt fact_ với surrogate keys + rolling.
- `sources-yml-template.yml` — dbt sources với Hive partitioning glob.
- `schema-yml-template.yml` — dbt tests (unique, not_null, relationships).

## SERVE — `templates/serve/`
- `dagster-serving-asset-template.py` — serving asset, `deps=[dbt_assets]`.

## TRUST — `templates/trust/`
- `ingestion-health-recorder-template.py` — record_run API + DDL, composite PK.
- `dlt-row-count-extractor-template.py` — 3-layer fallback for filesystem destinations.
- `ingestion-health-digest-template.py` — Morning digest op + classification.
- `backfill-health-rows-written-template.py` — One-shot backfill, composite-PK-safe UPDATE.

## OPS — `templates/ops/`
- `dagster-reactive-sensor-template.py` — Hash polling sensor for external source.
- `stuck-run-alerter-template.py` — Activity-based stuck detection + cancel + kill subprocess + free slots.
```

## Definition of done

- [ ] **6 playbook files** (00-skill-meta + 5 nhóm) có nội dung đầy đủ (00-skill-meta ≥120 dòng vì compact hơn; 5 nhóm ≥200 dòng mỗi cái)
- [ ] cross-cutting.md có 8 sections + L_xx references
- [ ] lesson-index.md liệt kê tất cả ~104 lessons với group + canonical link
- [ ] templates/INDEX.md liệt kê 15 templates theo group
- [ ] Mỗi playbook có "Pre-flight checklist" + "Templates" (5 nhóm) + "Lessons cross-reference" + "Cross-cutting refs"
- [ ] 00-skill-meta.md có "Self-Learning Protocol format" + "Workflow thêm lesson Lxx mới"
- [ ] Tất cả links nội bộ (đến references/) còn valid TRƯỚC Phase 4 — các path tham chiếu reference/X phải khớp với những gì sẽ move ở Phase 4

## Risk

**Risk 1:** Playbook nội dung dài/lan man → mất tính "checklist". Mitigation: enforce template structure ở từng file.

**Risk 2:** Cross-reference tới `references/lessons-learned.md#L_xx` sai anchor. Mitigation: Phase 4 verify `grep "^### L\d" references/lessons-learned.md` ra đúng 76 lessons.

**Risk 3:** Nội dung playbook trùng quá nhiều với references → bloat. Mitigation: playbook = checklist + 1-2 dòng summary + link, KHÔNG copy code/giải thích chi tiết.
