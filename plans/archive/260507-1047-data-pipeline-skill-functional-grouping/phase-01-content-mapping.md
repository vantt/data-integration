# Phase 1 — Content Mapping

**Status:** DONE (executed in conversation, documented here as audit trail)
**Owner:** Vantt
**Output:** Mapping table — every lesson, pattern, template → 1+ functional group

## Phương pháp

1. Đọc TOC của 7 .md files chính bằng `grep ^##+`.
2. Phân loại từng heading: thuần 1 group hay cross-cutting.
3. Cross-cutting → quyết định canonical home + reference từ nhóm khác.

## Mapping — `lessons-learned.md` (76 lessons, L1-L76 gap L34)

### Section: Cấu hình DLT (config setup, lines 3-69)
| Sub | Group | Note |
|---|---|---|
| Tổ chức file config | INGEST | Canonical |
| Resolution chain | INGEST | + cross-ref OPS (deployment env) |
| Mapping env var ↔ config key | INGEST | Canonical |
| Partition layout | INGEST | Canonical |
| Đọc config trong source code | INGEST | Canonical |

### Section: Ingestion Patterns (L1-L7)
| L | Group | Note |
|---|---|---|
| L1 Early-stop pagination | INGEST | + cross-ref L57 (history_log double-fetch) |
| L2 Incremental cursor path | INGEST | |
| L3 Envelope append-only | INGEST | + bridges MODEL (dedup transform) |
| L4 Ingest method priority dedup | MODEL | + cross-ref INGEST |
| L5 7-day incremental buffer | MODEL | About dbt incremental, not ingest |
| L6 Empty page retry | INGEST | |
| L7 --full-refresh support | INGEST | + cross-ref L33 |

### Section: Dagster Integration (L8-L11)
| L | Group | Note |
|---|---|---|
| L8 argv=[] | INGEST | Asset wiring detail |
| L9 os.chdir(DLT_DIR) | INGEST | |
| L10 load_dlt_configuration | INGEST | |
| L11 DuckDB concurrency lock | OPS (canonical) | Cross-cutting; affects MODEL writes |

### Section: Storage (no L)
| Sub | Group |
|---|---|
| Parquet output path | INGEST/MODEL |
| DuckDB | MODEL/SERVE |

### Section: Multi-Process & Recovery (L12-L16)
| L | Group | Note |
|---|---|---|
| L12 Cross-Platform File Locking | OPS | Cross-cutting infra |
| L13 Cookie TTL | INGEST | Auth |
| L14 Webhook ACK | INGEST | At-least-once + dedup |
| L15 Consumer Loop vs One-Off | INGEST | Webhook consumer |
| L16 History Log URI Inference | INGEST | Sapo-specific |

### Section: Operational Hardening 2026-04-08 (L17-L23)
| L | Group | Note |
|---|---|---|
| L17 Subprocess pipe deadlock | OPS | Templates đã fix; lesson 11 SKILL.md |
| L18 DuckDB read_only no lock | SERVE | Lock semantics |
| L19 QueuedRunCoordinator queue | OPS | |
| L20 Slot leak on cancel | OPS | Janitor pattern |
| L21 Reactive sensor hash polling | OPS | + INGEST (sheet sensor) |
| L22 AssetSelection.downstream | OPS | Cascade selectivity |
| L23 DagsterRun no start_time | OPS | get_run_records |

### Section: History Log & Web Scraping (L24-L27)
| L | Group | Note |
|---|---|---|
| L24 Entity Registry pattern | INGEST | Sapo history_log |
| L25 NEVER drop_sources | INGEST | dlt API trap |
| L26 Smart rate limiting | INGEST | |
| L27 Cookie TTL strategy | INGEST | Auth |

### Section: Dedup & Incremental Correctness (L28-L31)
| L | Group | Note |
|---|---|---|
| L28 Dedup modified_on not event_timestamp | MODEL | dbt dedup correctness |
| L29 Incremental filter _dlt_load_id | MODEL | |
| L31 Schema migration self-heal | MODEL | DuckDB+read_parquet edge cases |
| L30 Compare-before-overwrite | MODEL | Idempotent dedup |

### Section: Full-Refresh vs Nightly (L32-L33, L35)
| L | Group | Note |
|---|---|---|
| L32 Nightly incremental vs full-refresh | OPS (job design) + MODEL | Job topology |
| L33 dlt incremental 2-layer filter | INGEST | |
| L35 Config ecosystem | cross-cutting | Layered defaults |

### Section: Health Monitoring (L36-L37)
| L | Group | Note |
|---|---|---|
| L36 Runner entry point return | TRUST | + INGEST (entry point) |
| L37 Dashboard SQL handle no-runs | TRUST | |

### Section: Auto-Recovery & Self-Healing (L38-L41)
| L | Group | Note |
|---|---|---|
| L38 Activity-based stuck detection | OPS | |
| L39 Concurrency pool janitor | OPS | |
| L40 Health checks mutual exclusion | OPS + TRUST | Schedule design |
| L41 Health recording datetime serialize | TRUST | Composite PK |

### Section: Stuck Run Prevention 2026-04-24 (L45-L48)
All → OPS
- L45 dbt subprocess timeout
- L46 stuck_run_alerter kill subprocess
- L47 Backup acquire duckdb_lock
- L48 Zombie NOT_STARTED runs

### Section: Ingestion Health Digest 2026-04-22 (L42-L44)
All → TRUST
- L42 dlt LoadInfo no row counts
- L43 Digest window business-TZ
- L44 ingestion_runs composite PK

### Section: Disaster Recovery & Maintenance Cron 2026-04-28 (L49-L52 + synthesis)
All → OPS
- L49 Schedules not auto-enabled
- L50 Backup rotation trap..EXIT
- L51 Exclude regenerable from backup
- L52 stuckrun sensor cover all states
- Maintenance Cron Design Principles synthesis

### Section: Cleanup & Schedule Management 2026-04-28/29 (L53-L58)
| L | Group | Note |
|---|---|---|
| L53 Phantom Dagster instigator | OPS | |
| L54 run_status_sensor pattern | OPS | Hard ordering |
| L55 asset_check_executions cleanup | OPS + TRUST | Purge gap |
| L56 SQLite WAL safety | OPS | |
| L57 history_log double-fetch | INGEST | min_overlap reset behavior |
| L58 Backup pre-flight disk check | OPS | |

### Section: Config Snapshot Ingestion (L59)
| L | Group |
|---|---|
| L59 Config snapshot fixed path | INGEST |

### Section: Stuck Run Zombie Subprocess 2026-05-05 (L60-L61)
All → OPS
- L60 finally watchdog.cancel orphans
- L61 QUEUE_STUCK_THRESHOLD sizing

### Section: Health DB Lock Windows 2026-05-05 (L62-L64)
| L | Group | Note |
|---|---|---|
| L62 Windows dllhost locks DuckDB bind-mount | OPS + cross-cutting | Platform-specific |
| L63 Purge stuck-run kill VACUUM | OPS | |
| L64 Ingestion NOT_STARTED 90min | OPS | dbt_rw slot contention |

### Section: Dagster Job Executor & Type Safety (L65-L66)
| L | Group | Note |
|---|---|---|
| L65 in_process_executor read-only jobs | OPS | |
| L66 MetadataValue.float trap | TRUST + OPS | Metadata reporting |

### Section: File-Drop Sensor (L67)
| L | Group |
|---|---|
| L67 Cold-start skip | OPS + INGEST |

### Section: Backup Edge Cases (L68-L74, L76, L75 in disorder)
All → OPS except L76
- L68 cp -a non-zero with WAL → OPS
- L69 run_key=date dedups failed runs → OPS
- L70 Windows dllhost bind-mount → OPS
- L71 Sensor ManagedGrpcPythonEnv ticking → OPS
- L72 Defender exclusion entire data_lake → OPS
- L73 Bind-mounted DuckDB Windows NTFS → OPS
- L74 SQLite VACUUM exclusive lock → OPS
- L76 Sapo orders API created_on bug → INGEST
- L75 context.log invisibility → OPS

## Mapping — `dagster-patterns.md` (14 lessons)

| Lesson | Group | Note |
|---|---|---|
| 1 Hybrid Job Race | OPS | Upstream injection |
| 2 Schedule Start-Time Race | OPS | |
| 3 Pre-Create Mart Directories | MODEL | dbt mart prep |
| 4 Zombie Background Threads | OPS | Telemetry |
| 5 QueuedRunCoordinator vs self-overlap | OPS | |
| 6 Asset slot leak | OPS | |
| 7 Reactive trigger external source | OPS | + INGEST sheet sensor |
| 8 DagsterRun.start_time | OPS | |
| 9 Separate Jobs Nightly vs Full-Refresh | OPS + MODEL | |
| 10 Auto-Termination + Janitor | OPS | |
| 11 Health Checks Mutual Exclusion | OPS + TRUST | |
| 12 Backup Job duckdb_lock | OPS | |
| 13 Zombie NOT_STARTED | OPS | |
| 14 Maintenance Schedule Topology | OPS | |

## Mapping — `dbt-patterns.md` (14 lessons)

| Lesson | Group | Note |
|---|---|---|
| Project Configuration | MODEL | profiles.yml + dbt_project.yml |
| 5-Hop Transformation Flow | MODEL | |
| 1 Two-Phase Dedup OOM-Safe | MODEL | |
| 2 src_/stg_ Split | MODEL | |
| 3 Incremental Filter _dlt_load_id | MODEL | |
| 4 Ingest Method Priority | MODEL | |
| 5 Rolling Location | MODEL + SERVE | |
| 6 Circular Dependency | MODEL | |
| 7 Unknown Key Handling | MODEL | |
| 8 sources.yml Hive Partition | MODEL | |
| 9 Post-Hook Pattern | MODEL | |
| 10 JSON Extraction Coalesce | MODEL | |
| 11 Testing Strategy | MODEL + TRUST | |
| 12 Reference Seeds | MODEL | |
| 13 Partition Pruning | MODEL | |
| 14 Generated Time Dimension | MODEL | |

## Mapping — Other docs

| File | Group(s) |
|---|---|
| serving-layer.md (full) | SERVE (canonical) |
| ingestion-health-digest.md (full) | TRUST (canonical) |
| supporting-scripts.md sections | scripts/provisioning → SERVE; clean_dlt_state → INGEST; ensure_dbt_directories → MODEL; run_dbt → MODEL; maintenance/, backup/ → OPS; debug_duckdb → cross-cutting |
| troubleshooting.md sections | dlt → INGEST; dbt → MODEL; serving → SERVE; Dagster → OPS; Health Monitoring → TRUST; Metabase → SERVE; Rate Limiting → INGEST; Debug Recipes → cross-cutting |

## Mapping — Templates

| Template | Group | Subfolder |
|---|---|---|
| source-template.py | INGEST | templates/ingest/ |
| run-entry-point-template.py | INGEST | templates/ingest/ |
| dagster-asset-template.py | INGEST | templates/ingest/ |
| src-model-template.sql | MODEL | templates/model/ |
| dim-model-template.sql | MODEL | templates/model/ |
| fact-model-template.sql | MODEL | templates/model/ |
| sources-yml-template.yml | MODEL | templates/model/ |
| schema-yml-template.yml | MODEL | templates/model/ |
| dagster-serving-asset-template.py | SERVE | templates/serve/ |
| ingestion-health-recorder-template.py | TRUST | templates/trust/ |
| ingestion-health-digest-template.py | TRUST | templates/trust/ |
| dlt-row-count-extractor-template.py | TRUST | templates/trust/ |
| backfill-health-rows-written-template.py | TRUST | templates/trust/ |
| dagster-reactive-sensor-template.py | OPS | templates/ops/ |
| stuck-run-alerter-template.py | OPS | templates/ops/ |

## Cross-cutting concerns (canonical homes)

| Concern | Canonical home | Referenced from |
|---|---|---|
| DuckDB locking | cross-cutting.md (anchor) | MODEL, SERVE, OPS playbooks |
| Env vars / config resolution | cross-cutting.md | INGEST playbook (primary user) |
| Docker mount paths | cross-cutting.md | MODEL (rolling), SERVE (views), OPS (volumes) |
| Telemetry / zombie threads | OPS playbook | INGEST, MODEL (process spawn) |
| File locking (Windows vs Linux) | cross-cutting.md | OPS, INGEST |
| SQLite WAL safety | OPS playbook | TRUST (health DB), OPS (purge/backup) |
| CWD + load_dlt_configuration | INGEST playbook | OPS (asset wiring) |
| dbt_rw concurrency policy | OPS playbook | MODEL (asset tags) |

## Inventory totals (audit baseline)

- 76 lessons in lessons-learned.md (L1-L76, gap L34) — all mapped
- 14 lessons in dagster-patterns.md — all mapped
- 14 lessons in dbt-patterns.md — all mapped
- 9 markdown docs — all mapped to ≥1 group
- 15 templates — all mapped to exactly 1 group
- 8 cross-cutting concerns identified with canonical home

**Total atomic items mapped:** 76 + 14 + 14 + ~30 sub-headings = ~134 items.
**Group distribution:**
- INGEST: ~25 lessons + 3 templates
- MODEL: ~17 lessons + 5 templates
- SERVE: 2 lessons + 1 template + serving-layer.md
- TRUST: ~8 lessons + 4 templates + ingestion-health-digest.md
- OPS: ~50 lessons + 2 templates
- Cross-cutting: 8 concerns

## Definition of done

- [x] Mỗi item trong inventory có ≥1 group gán (audit complete).
- [x] Cross-cutting concerns identified và có canonical home.
- [x] Phase 2+ có thể bắt đầu mà không cần tra cứu thêm.
