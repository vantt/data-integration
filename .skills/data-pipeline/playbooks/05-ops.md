# OPS Playbook — Vận hành & Orchestration

## Trách nhiệm

OPS quản lý toàn bộ lifecycle của Dagster jobs, sensors, schedules, và maintenance tasks. Nhóm này đảm bảo pipeline chạy đúng thứ tự, tự hồi phục khi bị stuck, không tốn tài nguyên dư thừa, và disk không đầy. OPS không viết data — OPS điều phối những nhóm khác (INGEST, MODEL, SERVE, TRUST) chạy đúng lúc, đúng thứ tự, với đúng concurrency constraints.

Đây là nhóm dễ có latent bugs nhất vì: (a) Dagster không warn khi schedule không được start, (b) stuck runs tích lũy im lặng, (c) disk đầy chỉ phát hiện khi SQLite I/O error làm API stop responding (thực tế 2026-04-28).

---

## Pre-flight Checklist (đọc TRƯỚC khi implement)

- [ ] Dagster asset writes DuckDB → `op_tags={"dagster/concurrency_key": "duckdb_lock"}`, pool limit=1 (L11). Thiếu = concurrent writes → DuckDB corruption
- [ ] Schedules trong `Definitions(schedules=[...])` phải explicit start sau deploy — `DECLARED_IN_CODE` ≠ running (L49). Verify bằng `schedules.db` query
- [ ] Ingestion job tổng hợp: inject upstream keys qua `DagsterDbtTranslator.get_upstream_asset_keys()` (Lesson 1 dagster, Critical Rule 10). Thiếu = dbt start trước ingestion xong
- [ ] Schedule offset tránh start-time race: realtime `*/3`-offset, incremental `*/10`, lệch nhau (Lesson 2 dagster). Hai job trigger cùng giây → cả hai check "active?" = race condition
- [ ] Self-overlap skip: `_has_active_run()` trong mỗi schedule function (Lesson 5 dagster). Schedule tạo RunRequest kể cả khi đang chạy dở
- [ ] Yield-to-batch: realtime/incremental skip khi `pipeline_batch_nightly_job` đang chạy (yield logic trong Lesson 2 dagster)
- [ ] Telemetry disabled tại process level: `DLT_TELEMETRY_DISABLED=true`, `DBT_SEND_ANONYMOUS_USAGE_STATS=false` (Lesson 4 dagster) — tránh zombie thread giữ process alive
- [ ] dbt subprocess timeout watchdog `DBT_TIMEOUT_SEC=900` trong `@dbt_assets` function (L45) — hard kill sau 15 min
- [ ] `finally` block kill dbt subprocess sau `watchdog.cancel()` — external Dagster cancellation disarms watchdog nhưng không kill dbt → zombie cascade (L60)
- [ ] Stuck-run alerter: kill ACTUAL dbt subprocess via `psutil` + free concurrency slot + cancel Dagster run (L46). `report_run_canceled()` alone chỉ update state, không kill process
- [ ] Stuckrun sensor cover ALL non-terminal states: Pass 1 (`STARTED` + inactivity > 5 min) + Pass 2 (`NOT_STARTED`/`QUEUED`/`STARTING` > 2h) (L52, L61)
- [ ] Backup job: acquire `duckdb_lock` (L47); rotation trong `trap … EXIT` (L50); exclude `dagster_home/history/` (L51)
- [ ] Purge job cleans dbt target dirs (`_cleanup_dbt_target_dirs`) — thiếu = `transformation/target/` tích lũy ~5 GB/day (post-mortem 2026-04-28)
- [ ] Concurrency pool janitor mỗi 5 min (L20, L39) — slot leak khi cancel run; janitor auto-free
- [ ] Health DB watchdog 10 min: detect ghost lock + stale > 2h (L62 pattern)
- [ ] Read-only jobs (recon, kpi, digest) dùng `in_process_executor` — `ChildProcessCrashException` = per-step subprocess OOM (L65)
- [ ] `run_status_sensor` cho hard ordering (backup-after-purge) — cron offset không đủ khi purge duration variable (L54)
- [ ] `MetadataValue.float()` int trap: `or 0.0` fallback (float), không phải `or 0` (int) (L66)
- [ ] Reactive sensor cho external source: hash polling (L21, Lesson 7 dagster) — không cần Drive API; sensor check content hash, fire khi changed
- [ ] `QUEUE_STUCK_THRESHOLD` sized theo schedule topology thực tế (L61) — nightly batch hold `dbt_rw=1` 30-60 min → threshold 2h an toàn

---

## ⭐ Stuck Run Prevention (highlighted callout)

**Source: `../references/dagster-patterns.md` Lesson 10-13**

Đây là vòng lặp tự phục hồi 4 lớp khi dbt process hung:

| Layer | Mechanism | Trigger |
|-------|-----------|---------|
| Layer 1 | dbt subprocess timeout watchdog (`threading.Timer`, 15 min) | In `@dbt_assets` function |
| Layer 2 | `health_alert_stuckrun_sensor` kills via `psutil` + free slot + cancel run | Sensor tick mỗi 60s |
| Layer 3 | `health_concurrency_pool_janitor` auto-free leaked slots | Sensor tick mỗi 5 min |
| Layer 4 | Boot-time cleanup: cancel zombie `NOT_STARTED` runs > 30 min | Container/Dagster restart |

**Critical:** `report_run_canceled()` only changes Dagster state — nó KHÔNG kill dbt subprocess. Phải dùng `psutil.Process(pid).terminate()` + `wait(timeout=5)` + `kill()`.

**psutil must be in `requirements.txt`** — không có = `ImportError` khi sensor fire.

---

## ⭐ Maintenance Cron Topology (highlighted callout)

**Source: `../references/dagster-patterns.md` Lesson 14 + L49-L52 + Synthesis section**

Post-mortem 2026-04-28: disk D: 100% full → SQLite I/O error → Dagster API stopped responding. Root cause: `maintain_purge_runs_schedule` defined nhưng NEVER started (L49), `backup.sh` rotation step unreachable sau ENOSPC (L50), `dagster_home/history/` 18 GB included in backup (L51), stuck sensor missed `NOT_STARTED` zombies (L52).

**Standard daily topology (ICT timezone):**

| Job/Sensor | Cron / Trigger | Rationale |
|---|---|---|
| `maintain_cleanup_schedule` | `0 1 * * *` ICT | Quietest window; finishes before 03:00 nightly |
| `trigger_backup_after_purge` (sensor) | purge SUCCESS | Hard ordering — backup after purge, not cron-guessed |
| `maintain_backup_fallback_schedule` | `0 6 * * *` ICT | Fallback if purge fails; `run_key=date` deduplicates with sensor |
| `pipeline_batch_nightly_schedule` | `0 3 * * *` ICT | Default nightly batch |
| `health_report_digest_schedule` | `0 6 * * *` ICT | After all overnight jobs; read-only different DB |

Full schedule topology 01:00 → 03:00 → 04:30 → 04:45 → 06:00:
- 01:00 — purge (quiet zone, before nightly)
- 03:00 — batch ingest + dbt transform
- 04:30 — recon (cross-check source vs warehouse)
- 04:45 — KPI closure
- 06:00 — digest + backup fallback

---

## ⭐ Synthesis: Maintenance Cron Design Principles

**Source: `../references/lessons-learned.md` "Maintenance Cron Design Principles (synthesis)" (line ~1595)**
**Đây là synthesis sub-section, KHÔNG phải numbered Lxx — dễ bị bỏ qua.**

Lessons L49-L52 + L47 crystallize 8 design principles cho daily maintenance schedules. PHẢI đọc khi thiết kế lịch chạy mới hoặc thay đổi schedule:

1. **Order by mutual exclusion**: `purge → backup` (purge clears history before backup snapshots).
2. **Window in the quiet zone**: avoid hours when realtime/nightly are running. For this project: 01:00-01:59 ICT (after midnight, before 03:00 nightly).
3. **Enforce ordering via sensor, not cron offset**: use `run_status_sensor` to chain `backup` after `purge` completes. Cron offset only works if both jobs are fast and predictable.
4. **Bound resource cost upfront** with concurrency tags (`duckdb_lock`) and pre-flight checks (free disk).
5. **Always-run cleanup via `trap … EXIT`** in shell scripts — never trust step-by-step linear execution to reach the rotation step.
6. **Exclude regenerable data** from anything that gets persisted (backups, snapshots).
7. **Auto-recovery sensors cover ALL non-terminal states**, not just `STARTED`.
8. **Pre-flight disk check must measure only source dirs, not parent dir**: if backup destination lives under the same parent as source, `du -sk parent` includes the existing backups in "required size" (circular over-estimate → false ENOSPC abort every run). See L58.

---

## Mental model & patterns

### Self-healing chain

```
dbt hung
  → Layer 1: timeout watchdog fires (15 min)
  → Layer 2: stuckrun sensor detects inactivity (5 min pass, next tick ~6 min)
      → kill dbt subprocess via psutil
      → free concurrency slot
      → cancel Dagster run
      → alert Lark
  → Layer 3: pool janitor verifies slots free (next 5 min tick)
  → Next schedule tick: fresh run starts unblocked
```

### Layered Defense

```
Timeout watchdog (preventive, 15 min)
  └── Stuckrun sensor (detective, 6 min cadence)
        └── Pool janitor (corrective, 5 min cadence)
              └── Boot-time cleanup (reset, on restart)
```

### File-drop sensor mtime cursor (L67)

Do NOT add cold-start skip guard. Files present at deploy time are silently ignored if guard exists. Use `current_mtime > prev_mtime` cursor pattern instead — first tick sees all existing files as "new".

### Phantom Dagster instigator state (L53)

Renaming a schedule/sensor in code does NOT migrate `schedules.db` row. Old name stays `RUNNING`, new name stuck at `DECLARED_IN_CODE`. Fix:
```python
from dagster import DagsterInstance, InstigatorStatus
instance = DagsterInstance.get()
for s in instance.all_instigator_state():
    if s.name in PHANTOM_NAMES:
        instance.update_instigator_state(s.with_status(InstigatorStatus.STOPPED))
```
**Rule:** When renaming, stop in UI BEFORE renaming code → deploy → start under new name.

### Subprocess pipe deadlock fix (L17)

`subprocess.run(..., capture_output=True)` deadlocks when subprocess output exceeds pipe buffer. Fix: redirect to `tee` piping instead, or use `stdout=PIPE, stderr=STDOUT` with non-blocking reads. See L17 for full pattern.

### Long-running silent ops heartbeat (L63)

VACUUM / large SELECT DISTINCT / cross-db DELETE emit no logs → stuck-run alerter kills after 5 min. Fix: wrap in `threading.Thread` + `_done.wait(timeout=30)` loop to emit progress logs at regular intervals.

---

## Templates

| Template | Khi nào dùng |
|----------|-------------|
| `../templates/ops/dagster-reactive-sensor-template.py` | Hash polling sensor cho external source (Google Sheets, file-drop). `default_status=DefaultSensorStatus.RUNNING`, check content hash, fire khi changed |
| `../templates/ops/stuck-run-alerter-template.py` | Activity-based stuck detection: Pass 1 (STARTED + inactivity) + Pass 2 (queue-stuck). Includes psutil kill + slot free + cancel |

---

## Supporting scripts

Xem `../references/supporting-scripts.md` "Khi Nào Gọi Script Nào" để tra bảng tình huống → script chain.

Scripts liên quan trực tiếp đến OPS:
- `scripts/maintenance/unstick_concurrency_pools.py` — Manual janitor cho stuck slots (cũng wire vào boot-time `docker-compose.yml` command)
- `scripts/maintenance/cleanup_and_verify.py` — Cleanup + state verification sau incident
- `scripts/maintenance/reset_ingestion.py` — Reset ingestion state khi corrupt
- `scripts/run_pipeline.ps1` — PowerShell pipeline runner (Windows local dev)
- `scripts/backup/` — Hot backup scripts với `trap…EXIT` rotation + pre-flight disk check

---

## Reference sections

Đọc các section sau từ `../references/dagster-patterns.md` khi implement OPS features:

- **Summary: Dagster Integration Checklist** (line ~773) — comprehensive checklist cho mọi job/asset/sensor mới, bao gồm 40+ items
- **Reference Files** (line ~821) — bảng file → purpose, pointer tới source implementations

---

## Debug recipes

Xem `../references/troubleshooting.md` sections:
- "Dagster Asset/Job" — symptom → cause → fix cho stuck runs, sensor not ticking, schedule not firing
- "Verify DuckDB file lock empirically" — Windows: detect dllhost.exe lock, kill process, verify lock released

---

## ⚠️ External tool drift warning

**CLI Versioning:** Commands like `set-concurrency-limit` may change between Dagster versions. **Always verify** inside container:
```bash
docker exec data_platform dagster --help
docker exec data_platform dagster asset --help
```
Do NOT copy CLI commands from old runbooks without checking current Dagster version's syntax.

---

## Lessons cross-reference

| ID | Summary | Source |
|----|---------|--------|
| L8 | Dagster asset wiring: `argv=[]`, `os.chdir`, `load_dlt_configuration` | `../references/lessons-learned.md` |
| L11 | DuckDB concurrency: `op_tags={"dagster/concurrency_key": "duckdb_lock"}` | `../references/lessons-learned.md` |
| L12 | Cross-platform file locking primitive | `../references/lessons-learned.md` |
| L17 | Subprocess pipe deadlock: tee piping thay capture_output=True | `../references/lessons-learned.md` |
| L18 | DuckDB read_only KHÔNG acquire lock | `../references/lessons-learned.md` |
| L19 | Concurrency slot management pattern | `../references/lessons-learned.md` |
| L20 | Slot leak khi cancel run → janitor cần thiết | `../references/lessons-learned.md` |
| L21 | Reactive sensor hash polling (Google Sheets không cần Drive API) | `../references/lessons-learned.md` |
| L22 | Schedule coordination via priority yielding | `../references/lessons-learned.md` |
| L23 | Sensor `default_status=RUNNING` — mới tạo default STOPPED | `../references/lessons-learned.md` |
| L32 | Full-refresh vs incremental: separate jobs, không tag schedule | `../references/lessons-learned.md` |
| L38 | Backup hot-copy strategy | `../references/lessons-learned.md` |
| L39 | Pool janitor every 5 min | `../references/lessons-learned.md` |
| L40 | Health checks job mutual-exclude với ingestion | `../references/lessons-learned.md` |
| L45 | dbt subprocess timeout watchdog `DBT_TIMEOUT_SEC=900` | `../references/lessons-learned.md` |
| L46 | Stuck-run alerter: psutil kill + free slot + cancel | `../references/lessons-learned.md` |
| L47 | Backup acquires `duckdb_lock` để tránh torn WAL | `../references/lessons-learned.md` |
| L48 | Boot-time cleanup: cancel zombie NOT_STARTED > 30 min | `../references/lessons-learned.md` |
| L49 | Schedules trong `defs.schedules` KHÔNG auto-start — phải explicit start | `../references/lessons-learned.md` |
| L50 | Backup rotation MUST run via `trap … EXIT` | `../references/lessons-learned.md` |
| L51 | Exclude `dagster_home/history/` khỏi backup | `../references/lessons-learned.md` |
| L52 | Stuckrun sensor Pass 2: cover `NOT_STARTED`/`QUEUED`/`STARTING` > 2h | `../references/lessons-learned.md` |
| L53 | Phantom instigator state sau rename schedule/sensor | `../references/lessons-learned.md` |
| L54 | `run_status_sensor` cho hard job ordering (backup-after-purge) | `../references/lessons-learned.md` |
| L55 | `asset_check_executions` cleanup trong purge | `../references/lessons-learned.md` |
| L56 | SQLite WAL safety trong purge/cleanup | `../references/lessons-learned.md` |
| L57 | `min_overlap_items` KHÔNG raise lên 500 | `../references/lessons-learned.md` |
| L58 | Pre-flight disk check: measure source, NOT parent dir | `../references/lessons-learned.md` |
| L60 | `finally` block phải kill dbt subprocess sau watchdog.cancel() | `../references/lessons-learned.md` |
| L61 | `QUEUE_STUCK_THRESHOLD` sizing theo topology thực tế | `../references/lessons-learned.md` |
| L62 | Windows dllhost.exe lock DuckDB trên bind-mount | `../references/lessons-learned.md` |
| L63 | Long-running silent ops cần heartbeat thread để tránh stuckrun kill | `../references/lessons-learned.md` |
| L64 | Lightweight jobs yield to long-running dbt_rw holders | `../references/lessons-learned.md` |
| L65 | Read-only lightweight jobs dùng `in_process_executor` | `../references/lessons-learned.md` |
| L66 | `MetadataValue.float()` int trap: `or 0.0` không phải `or 0` | `../references/lessons-learned.md` |
| L67 | File-drop sensor KHÔNG có cold-start skip | `../references/lessons-learned.md` |
| L68 | `cp -a` trên live SQLite: check destination, không check exit code | `../references/lessons-learned.md` |
| L69 | Backup fallback schedule: `run_key=None` + manual success check | `../references/lessons-learned.md` |
| L70-L73 | Windows DuckDB bind-mount vulnerability series | `../references/lessons-learned.md` |
| L74 | SQLite VACUUM exclusive lock blocks Dagster | `../references/lessons-learned.md` |
| L75 | context.log visibility gap trong Dagster UI | `../references/lessons-learned.md` |
| dagster-Lesson-1 | Hybrid job race condition — explicit upstream key injection | `../references/dagster-patterns.md` |
| dagster-Lesson-2 | Schedule start-time race — offset cron + priority yielding | `../references/dagster-patterns.md` |
| dagster-Lesson-3 | Pre-create rolling dirs trong `@dbt_assets` | `../references/dagster-patterns.md` |
| dagster-Lesson-4 | Telemetry disabled at process level | `../references/dagster-patterns.md` |
| dagster-Lesson-5 | Self-overlap skip: `_has_active_run()` check | `../references/dagster-patterns.md` |
| dagster-Lesson-6 | Boot-time slot cleanup in docker-compose command | `../references/dagster-patterns.md` |
| dagster-Lesson-7 | Reactive sensor default_status=RUNNING + job explicit in Definitions | `../references/dagster-patterns.md` |
| dagster-Lesson-8 | Sensor timing: `get_run_records()` không `get_runs()` | `../references/dagster-patterns.md` |
| dagster-Lesson-9 | Full-refresh vs nightly: separate job definitions | `../references/dagster-patterns.md` |
| dagster-Lesson-10 | Stuck run 3-layer defense: watchdog + stuckrun sensor + janitor | `../references/dagster-patterns.md` |
| dagster-Lesson-11 | Health checks job: in_process_executor + exclude dbt tests | `../references/dagster-patterns.md` |
| dagster-Lesson-12 | Backup concurrency lock: `duckdb_lock` prevents torn WAL | `../references/dagster-patterns.md` |
| dagster-Lesson-13 | Boot-time cleanup: zombie NOT_STARTED cancellation | `../references/dagster-patterns.md` |
| dagster-Lesson-14 | Maintenance schedule topology: explicit start, Pass 2, purge cleans target dirs | `../references/dagster-patterns.md` |

---

## Cross-cutting refs

- `cross-cutting.md#duckdb-locking` — canonical home cho slot management, read_only semantics, slot leak
- `cross-cutting.md#docker-mount-paths` — volumes convention, absolute path bake issue
- `cross-cutting.md#file-locking-windows-vs-linux` — L62, L70-L73: dllhost.exe lock DuckDB trên bind-mount
- `cross-cutting.md#sqlite-wal-safety` — L56, L68, L74: purge VACUUM exclusive lock blocks Dagster
- `cross-cutting.md#telemetry-zombie-threads` — canonical home cho DLT/dbt telemetry zombie thread fix
