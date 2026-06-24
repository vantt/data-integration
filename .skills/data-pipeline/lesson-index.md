# Lesson Index — All Lessons by Functional Group

Master cross-reference: every lesson with group assignment and canonical file.
Total: 77 lessons from lessons-learned.md (L1-L84, gaps L34, L77-L80) + 14 dagster-patterns + 14 dbt-patterns = **105 entries**.

Update protocol: after adding any new Lxx → append row to correct group table here.
Canonical format for lessons-learned.md anchors: `references/lessons-learned.md` (post-Phase 4 path).

---

## INGEST

Lessons covering data collection: API calls, dlt pipelines, envelope schema, auth, pagination.

| ID | Title | File |
|----|-------|------|
| L1 | Early-stop pagination (đừng dùng total_count) | `references/lessons-learned.md#L1` |
| L2 | Incremental cursor phải là path đầy đủ trong record | `references/lessons-learned.md#L2` |
| L3 | Envelope append-only, dedup ở transform layer | `references/lessons-learned.md#L3` |
| L6 | Empty page: retry 1 lần trước khi stop | `references/lessons-learned.md#L6` |
| L7 | Luôn support `--full-refresh` | `references/lessons-learned.md#L7` |
| L8 | `argv=[]` trong Dagster asset (critical) | `references/lessons-learned.md#L8` |
| L9 | `os.chdir(DLT_DIR)` trước khi run pipeline | `references/lessons-learned.md#L9` |
| L10 | `load_dlt_configuration()` phải gọi trước pipeline | `references/lessons-learned.md#L10` |
| L13 | Cookie TTL + In-Place Session Refresh | `references/lessons-learned.md#L13` |
| L14 | Webhook ACK: At-Least-Once + Dedup as Safety Net | `references/lessons-learned.md#L14` |
| L15 | Consumer Loop vs One-Off Mode | `references/lessons-learned.md#L15` |
| L16 | History Log URI Inference Mapping | `references/lessons-learned.md#L16` |
| L24 | Entity Registry pattern cho history log URI resolution | `references/lessons-learned.md#L24` |
| L25 | KHÔNG BAO GIỜ dùng `refresh="drop_sources"` — xóa toàn bộ dataset | `references/lessons-learned.md#L25` |
| L26 | Smart rate limiting cho cookie-based web scraping | `references/lessons-learned.md#L26` |
| L27 | Cookie TTL nên dài, dựa vào 401/403 để refresh on-demand | `references/lessons-learned.md#L27` |
| L33 | dlt incremental có 2 lớp filter — phải reset CẢ HAI khi full-refresh | `references/lessons-learned.md#L33` |
| L57 | history_log double-fetch + `min_overlap_items` reset behavior | `references/lessons-learned.md#L57` |
| L59 | Config snapshot tables: dùng fixed path, KHÔNG phân vùng theo year/month | `references/lessons-learned.md#L59` |
| L76 | Sapo orders API silently ignores `created_on_min/max` filter | `references/lessons-learned.md#L76` |

---

## MODEL

Lessons covering dbt transformations: dedup correctness, incremental patterns, schema migration, materialization.

| ID | Title | File |
|----|-------|------|
| L4 | Ingest method priority khi dedup | `references/lessons-learned.md#L4` |
| L5 | 7-day incremental buffer trong dbt | `references/lessons-learned.md#L5` |
| L28 | Dedup phải dùng `modified_on` của entity, KHÔNG phải `event_timestamp` | `references/lessons-learned.md#L28` |
| L29 | Incremental filter: dùng `_dlt_load_id`, KHÔNG phải `event_timestamp` | `references/lessons-learned.md#L29` |
| L30 | Compare-before-overwrite cho incremental dedup | `references/lessons-learned.md#L30` |
| L31 | DuckDB incremental schema migration: 3 bẫy khi thêm column mới | `references/lessons-learned.md#L31` |
| L32 | Nightly incremental vs manual full-refresh — separate jobs, shared cursor | `references/lessons-learned.md#L32` |
| dbt-Lesson-1 | Two-Phase Dedup (OOM-Safe) | `references/dbt-patterns.md` |
| dbt-Lesson-2 | src_/stg_ Split (Primary OOM Fix) | `references/dbt-patterns.md` |
| dbt-Lesson-3 | Incremental Filter bằng `_dlt_load_id` (thay 7-Day Lookback) | `references/dbt-patterns.md` |
| dbt-Lesson-4 | Ingest Method Priority khi Dedup | `references/dbt-patterns.md` |
| dbt-Lesson-5 | Rolling Location cho Marts (CRITICAL) | `references/dbt-patterns.md` |
| dbt-Lesson-6 | Circular Dependency Breaking | `references/dbt-patterns.md` |
| dbt-Lesson-7 | Unknown Key Handling | `references/dbt-patterns.md` |
| dbt-Lesson-8 | sources.yml với Hive Partitioning | `references/dbt-patterns.md` |
| dbt-Lesson-9 | Post-Hook Pattern (Alternative Export) | `references/dbt-patterns.md` |
| dbt-Lesson-10 | JSON Extraction — Coalesce Fallbacks | `references/dbt-patterns.md` |
| dbt-Lesson-11 | Testing Strategy theo Layer | `references/dbt-patterns.md` |
| dbt-Lesson-12 | Reference Seeds Pattern | `references/dbt-patterns.md` |
| dbt-Lesson-13 | Partition Pruning với Hive Partitioning | `references/dbt-patterns.md` |
| dbt-Lesson-14 | Generated Time Dimension Pattern (SQL, không CSV) | `references/dbt-patterns.md` |

---

## SERVE

Lessons covering serving layer: Rolling Self-Refresh Views, DuckDB dual-file, GC, Metabase integration.

| ID | Title | File |
|----|-------|------|
| L18 | DuckDB read_only mode KHÔNG acquire file lock | `references/lessons-learned.md#L18` |
| L109 | Cost embedded in an aggregate must not also be a sibling deduction (waterfall double-count) | `references/lessons-learned.md#L109` |
| dbt-Lesson-5 | Rolling Location cho Marts (CRITICAL) | `references/dbt-patterns.md` |

**Full SERVE knowledge base:** `references/serving-layer.md` (all sections — canonical SERVE reference)
- §1 Rolling Snapshots từ dbt
- §2 Rolling Self-Refresh View Pattern
- §3 Garbage Collection
- §4 DuckDB Lock Behavior
- §5 Empty Folder → Drop View
- §6 Pre-Create Rolling Directories
- §7 Dagster Integration
- Checklist khi thêm mart model mới
- Debug Commands

*Note: dbt-Lesson-5 appears in both MODEL and SERVE — primary home is MODEL (dbt-patterns.md), cross-ref from SERVE.*

---

## TRUST

Lessons covering data trust: health recording, digest, composite PK, KPI closure, runner entry points.

| ID | Title | File |
|----|-------|------|
| L36 | Runner entry point PHẢI `return run_pipeline(...)` — không return = silent "skipped" | `references/lessons-learned.md#L36` |
| L37 | Dashboard SQL phải handle "asset chưa từng chạy" — không dùng cross join | `references/lessons-learned.md#L37` |
| L40 | Health checks phải mutual-exclude với ingestion/dbt jobs | `references/lessons-learned.md#L40` |
| L41 | Health recording: datetime serialization và rows_written semantics | `references/lessons-learned.md#L41` |
| L42 | dlt LoadInfo does NOT expose row counts for filesystem destinations | `references/lessons-learned.md#L42` |
| L43 | Digest window must be business-TZ calendar day, not rolling 24h | `references/lessons-learned.md#L43` |
| L44 | `ingestion_runs` composite PK: always filter BOTH asset_key AND run_id | `references/lessons-learned.md#L44` |
| L55 | `asset_check_executions` table not cleaned by `delete_run()` | `references/lessons-learned.md#L55` |
| L66 | `MetadataValue.float()` rejects Python int — `or 0` fallback is a trap | `references/lessons-learned.md#L66` |
| L83 | KPI và recon window phải dùng ICT midnight, không phải UTC midnight | `references/lessons-learned.md#L83` |
| L84 | UTC storage + ICT display là architecture chuẩn cho pipeline Việt Nam | `references/lessons-learned.md#L84` |
| L110 | MISA `invoice_no` resets monthly — never a standalone join key (use invoice_no+month+amount) | `references/lessons-learned.md#L110` |
| L111 | MISA `VCSC*` = Sapo `VTSC*` same product — alias gap inflates reconciliation variance | `references/lessons-learned.md#L111` |

**Full TRUST knowledge base:** `references/ingestion-health-digest.md` (canonical TRUST reference)

*Note: L40 appears in both OPS (schedule design) and TRUST (health checks) — listed in TRUST as primary; L55 in both OPS (purge) and TRUST (cleanup); L66 in both OPS and TRUST.*

---

## OPS

Largest group — Dagster orchestration, schedules, sensors, concurrency, maintenance, backup.

### Dagster Integration & Asset Wiring

| ID | Title | File |
|----|-------|------|
| L8 | `argv=[]` trong Dagster asset (critical) | `references/lessons-learned.md#L8` |
| L11 | DuckDB concurrency lock | `references/lessons-learned.md#L11` |
| L12 | Cross-Platform File Locking cho Shared State | `references/lessons-learned.md#L12` |
| L17 | Subprocess pipe deadlock từ `capture_output=True` | `references/lessons-learned.md#L17` |
| L19 | QueuedRunCoordinator KHÔNG ngăn được queue buildup | `references/lessons-learned.md#L19` |
| L20 | Asset-level concurrency pool slot leak khi cancel runs | `references/lessons-learned.md#L20` |
| L21 | Reactive sensor cho external source bằng content hash (không cần Drive API) | `references/lessons-learned.md#L21` |
| L22 | `AssetSelection.downstream()` cho cascade có chọn lọc | `references/lessons-learned.md#L22` |
| L23 | `DagsterRun` không có `start_time`, phải dùng `get_run_records()` | `references/lessons-learned.md#L23` |
| L32 | Nightly incremental vs manual full-refresh — separate jobs, shared cursor | `references/lessons-learned.md#L32` |
| L38 | Activity-based stuck detection vs fixed timeout | `references/lessons-learned.md#L38` |
| L39 | Concurrency pool janitor auto-cleanup | `references/lessons-learned.md#L39` |
| L40 | Health checks phải mutual-exclude với ingestion/dbt jobs | `references/lessons-learned.md#L40` |
| L144 | UTF-8 BOM in YAML config breaks strict PyYAML; ParserError points at wrong line | `references/lessons-learned.md#L144` |

### Stuck Run Prevention

| ID | Title | File |
|----|-------|------|
| L45 | dbt subprocess timeout watchdog — prevent infinite hang | `references/lessons-learned.md#L45` |
| L46 | stuck_run_alerter must kill actual subprocess, not just Dagster state | `references/lessons-learned.md#L46` |
| L47 | Backup job must acquire duckdb_lock to prevent I/O collision | `references/lessons-learned.md#L47` |
| L48 | Zombie NOT_STARTED runs block schedules indefinitely | `references/lessons-learned.md#L48` |
| L52 | `health_alert_stuckrun_sensor` must cover ALL non-terminal states (Pass 2) | `references/lessons-learned.md#L52` |
| L60 | `finally: watchdog.cancel()` orphans dbt subprocess khi run bị kill ngoài | `references/lessons-learned.md#L60` |
| L61 | QUEUE_STUCK_THRESHOLD phải sizing dựa vào topology schedule thực tế | `references/lessons-learned.md#L61` |
| L63 | Purge job bị stuck-run alerter kill do VACUUM chạy im lặng quá 5 phút | `references/lessons-learned.md#L63` |
| L64 | Ingestion NOT_STARTED 90 min: dbt_rw slot contention | `references/lessons-learned.md#L64` |
| L75 | Dagster ops without `context.log` invisible to inactivity watchdog | `references/lessons-learned.md#L75` |

### Maintenance Cron & Schedule Design

| ID | Title | File |
|----|-------|------|
| L49 | Schedules in `defs.schedules=[...]` are NOT auto-enabled | `references/lessons-learned.md#L49` |
| L50 | Backup rotation MUST run via `trap … EXIT`, not after `cp` | `references/lessons-learned.md#L50` |
| L51 | Exclude regenerable data from backup (`dagster_home/history/`) | `references/lessons-learned.md#L51` |
| L53 | Phantom Dagster instigator states after code renames | `references/lessons-learned.md#L53` |
| L54 | `run_status_sensor` pattern for hard job ordering (backup-after-purge) | `references/lessons-learned.md#L54` |
| L55 | `asset_check_executions` table not cleaned by `delete_run()` | `references/lessons-learned.md#L55` |
| L56 | SQLite WAL safety in purge/cleanup scripts | `references/lessons-learned.md#L56` |
| L58 | Backup pre-flight disk check must exclude backup destination from source size | `references/lessons-learned.md#L58` |
| L65 | Lightweight read-only jobs must use `in_process_executor` to prevent OOM | `references/lessons-learned.md#L65` |
| L66 | `MetadataValue.float()` rejects Python int — `or 0` fallback is a trap | `references/lessons-learned.md#L66` |
| L67 | File-drop sensor cold-start skip silently ignores files already in drop zone | `references/lessons-learned.md#L67` |
| L69 | `run_key=date` deduplicates against previously FAILED runs — prevents retry | `references/lessons-learned.md#L69` |

### Windows / Platform-Specific

| ID | Title | File |
|----|-------|------|
| L62 | Windows dllhost.exe (COM Surrogate / Defender) locks DuckDB on bind-mount | `references/lessons-learned.md#L62` |
| L68 | `cp -a` returns non-zero when SQLite WAL/SHM files disappear mid-copy | `references/lessons-learned.md#L68` |
| L70 | Windows `dllhost.exe` locks bind-mounted DuckDB file, silently breaks monitoring | `references/lessons-learned.md#L70` |
| L71 | Dagster sensor via `ManagedGrpcPythonEnv` origin never ticks when daemon serves `GrpcServer` | `references/lessons-learned.md#L71` |
| L72 | Defender exclusion must cover ENTIRE `data_lake`, not just `monitoring/` | `references/lessons-learned.md#L72` |
| L73 | Bind-mounted DuckDB on Windows NTFS permanently vulnerable to host-side locks | `references/lessons-learned.md#L73` |
| L74 | Dagster jobs stuck when `maintain_purge_runs_job` holds SQLite exclusive lock (VACUUM) | `references/lessons-learned.md#L74` |

### All 14 dagster-patterns.md Lessons

| ID | Title | File |
|----|-------|------|
| dagster-Lesson-1 | Hybrid Job Race Condition — Explicit Upstream Key Injection | `references/dagster-patterns.md` |
| dagster-Lesson-2 | Schedule Start-Time Race — Offset Cron + Priority Yielding | `references/dagster-patterns.md` |
| dagster-Lesson-3 | Pre-Create Mart Directories IN Asset (Idempotent Setup) | `references/dagster-patterns.md` |
| dagster-Lesson-4 | Zombie Background Threads — Disable Telemetry | `references/dagster-patterns.md` |
| dagster-Lesson-5 | QueuedRunCoordinator KHÔNG thay được self-overlap skip | `references/dagster-patterns.md` |
| dagster-Lesson-6 | Asset-level concurrency pool slot leak khi cancel runs | `references/dagster-patterns.md` |
| dagster-Lesson-7 | Reactive trigger cho external source — hash polling beats schedule + Drive API | `references/dagster-patterns.md` |
| dagster-Lesson-8 | `DagsterRun` không có `start_time` — sensor phải dùng `get_run_records()` | `references/dagster-patterns.md` |
| dagster-Lesson-9 | Separate Jobs for Nightly Incremental vs Manual Full-Refresh | `references/dagster-patterns.md` |
| dagster-Lesson-10 | Auto-Termination + Concurrency Pool Janitor — Self-Healing Infrastructure | `references/dagster-patterns.md` |
| dagster-Lesson-11 | Health Checks Mutual Exclusion với Ingestion | `references/dagster-patterns.md` |
| dagster-Lesson-12 | Backup Job Must Acquire duckdb_lock | `references/dagster-patterns.md` |
| dagster-Lesson-13 | Zombie NOT_STARTED Runs After Container Restart | `references/dagster-patterns.md` |
| dagster-Lesson-14 | Maintenance Schedule Topology — Cleanup, Backup, Auto-Recovery | `references/dagster-patterns.md` |

*Note: dagster-Lesson-3 primary home is MODEL (pre-create dirs for dbt); dagster-Lesson-11 primary home is TRUST (health checks). Listed in OPS as orchestration owner.*

---

## Cross-cutting

Lessons that cut across multiple groups — canonical home is `playbooks/cross-cutting.md`.

| ID | Title | Canonical home | Referenced from |
|----|-------|----------------|-----------------|
| L9 | `os.chdir(DLT_DIR)` trước khi run pipeline | `playbooks/cross-cutting.md#cwd-load-dlt-configuration` | INGEST, OPS |
| L10 | `load_dlt_configuration()` phải gọi trước pipeline | `playbooks/cross-cutting.md#cwd-load-dlt-configuration` | INGEST, OPS |
| L11 | DuckDB concurrency lock | `playbooks/cross-cutting.md#duckdb-locking` | OPS, MODEL, SERVE |
| L12 | Cross-Platform File Locking cho Shared State | `playbooks/cross-cutting.md#file-locking-windows-vs-linux` | OPS, INGEST |
| L18 | DuckDB read_only mode KHÔNG acquire file lock | `playbooks/cross-cutting.md#duckdb-locking` | SERVE, OPS |
| L35 | Config ecosystem: layered defaults, single .env, no duplication | `playbooks/cross-cutting.md#env-vars-config` | INGEST, OPS |
| L44 | `ingestion_runs` composite PK: always filter BOTH asset_key AND run_id | `playbooks/cross-cutting.md#composite-pk-update-trap` | TRUST, OPS |
| L56 | SQLite WAL safety in purge/cleanup scripts | `playbooks/cross-cutting.md#sqlite-wal-safety` | OPS, TRUST |
| L62 | Windows dllhost.exe locks DuckDB on bind-mount | `playbooks/cross-cutting.md#file-locking-windows-vs-linux` | OPS, SERVE |
| L68 | `cp -a` returns non-zero when SQLite WAL/SHM disappear mid-copy | `playbooks/cross-cutting.md#sqlite-wal-safety` | OPS |
| L70 | Windows dllhost.exe locks bind-mounted DuckDB, silently breaks monitoring | `playbooks/cross-cutting.md#duckdb-locking` | OPS |
| L73 | Bind-mounted DuckDB on Windows NTFS permanently vulnerable | `playbooks/cross-cutting.md#duckdb-locking` | OPS |
| L74 | Dagster jobs stuck when VACUUM holds SQLite exclusive lock | `playbooks/cross-cutting.md#sqlite-wal-safety` | OPS |
| L83 | KPI/recon window phải dùng ICT midnight, không phải UTC midnight | `playbooks/cross-cutting.md#timezone-window-alignment` | TRUST, OPS |
| L84 | UTC storage + ICT display — architecture chuẩn cho pipeline VN | `playbooks/cross-cutting.md#timezone-window-alignment` | TRUST, MODEL |

---

## Inventory Summary

| Group | lessons-learned.md | dagster-patterns.md | dbt-patterns.md | Total |
|-------|--------------------|---------------------|-----------------|-------|
| INGEST | 20 | 0 | 0 | 20 |
| MODEL | 9 | 0 | 14 | 23 |
| SERVE | 1 + serving-layer.md | 0 | 1 (shared) | 2 + full doc |
| TRUST | 11 | 0 | 0 | 11 |
| OPS | 39 | 14 | 0 | 53 |
| Cross-cutting | 15 (overlap from above) | 0 | 0 | 15 |
| **Total unique** | **78** | **14** | **14** | **105** |

*Gaps: L34 (skipped), L77-L80 (reserved) — append-only numbering, audit trail preserved*
*Lessons appearing in multiple groups are listed in primary group; cross-cutting table notes secondary references.*
