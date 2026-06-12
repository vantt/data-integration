# Dagster Orchestration Patterns

Lessons quan trọng khi orchestrate pipeline dlt + dbt trong Dagster. Đây là phần **dễ sai nhất** vì không có warning từ Dagster.

---

## Lesson 1: Hybrid Job Race Condition — Explicit Upstream Key Injection

**Problem:** Trong job chạy nhiều loại ingestion + dbt cùng lúc, dbt có thể start **trước khi** một số ingestion asset xong → dbt đọc stale data.

**Root cause:** dbt models declare source qua `{{ source('sapo_raw', 'order') }}`. `SapoDbtTranslator.get_asset_key()` map source đó tới `ingest_sapov2_orders_batch_asset`. Nhưng nếu job chỉ chứa `sapo_history_log_asset` (không có batch asset), Dagster thấy source không có dependency trong scope job → dbt start ngay lập tức song song với history_log.

**Fix:** Override `get_upstream_asset_keys()` để **inject explicit upstream keys** cho tất cả staging/src models.

```python
# orchestration/assets/dbt.py
class SapoDbtTranslator(DagsterDbtTranslator):
    def get_upstream_asset_keys(self, dbt_resource_props):
        upstream_keys = super().get_upstream_asset_keys(dbt_resource_props)
        name = dbt_resource_props.get("name")

        if name in ["stg_sapo_orders", "stg_sapo_customers", "src_sapo_orders", ...]:
            # Force dbt to wait for ALL ingestion methods trong cùng job
            upstream_keys.add(AssetKey(["sapo", "sapo_history_log_asset"]))
            upstream_keys.add(AssetKey(["sapo", "sapo_webhook_consumer_asset"]))
            upstream_keys.add(AssetKey(["sapo", "ingest_sapov2_orders_batch_asset"]))
            upstream_keys.add(AssetKey(["sapo", "sapo_customers_batch_asset"]))
            upstream_keys.add(AssetKey(["sapo", "sapo_accounts_batch_asset"]))

        return upstream_keys
```

**Insight quan trọng:** Nếu asset không có trong job, Dagster **skip** dependency check → không block dbt. Injection này làm dbt block **chỉ khi asset có trong cùng job** (Dagster tự resolve).

**Khi nào apply:** Job chứa multiple ingestion sources (batch + webhook + history_log) + dbt → cần strict serial order.

---

## Lesson 2: Schedule Start-Time Race — Offset Cron + Priority Yielding

**Problem:** Hai job cùng trigger lúc `10:00:00` — cả hai check "có job nào đang chạy không?" cùng lúc → **cả hai thấy "no"** → cả hai proceed → deadlock ở `duckdb_lock` hoặc resource exhaustion.

**Root cause:** Dagster scheduler không enforce mutual exclusion at trigger time. Check active runs là race condition khi hai schedule cùng fire.

**Fix: 2 tầng bảo vệ**

### Tầng 1: Cron Schedule Offset (physical guarantee)

```python
# Realtime job: skip 0,10,20,30,40,50 marks để không collide với */10 Incremental
@schedule(cron_schedule="1,4,7,11,14,17,21,24,27,31,34,37,41,44,47,51,54,57 * * * *", ...)

# Incremental job: skip toàn bộ hour 04 để không collide với Nightly (04:00)
@schedule(cron_schedule="*/10 0-3,5-23 * * *", ...)

# Nightly job: đơn giản 04:00
@schedule(cron_schedule="0 4 * * *", ...)
```

Kết quả: **không bao giờ** có 2 job trigger cùng một giây.

### Tầng 2: Priority Yielding (defensive)

Mỗi schedule check active runs của **higher-priority jobs** trước khi proceed:

```python
def ingest_sapo_realtime_schedule(context):
    priority_jobs = [
        "ingest_sheets_sync_job",
        "pipeline_batch_nightly_job",
        "ingest_sapo_incremental_job",
    ]
    for job_name in priority_jobs:
        active = context.instance.get_runs(filters=RunsFilter(
            job_name=job_name,
            statuses=[DagsterRunStatus.STARTING, DagsterRunStatus.STARTED, DagsterRunStatus.QUEUED]
        ), limit=1)
        if active:
            return SkipReason(f"Yielding to higher-priority '{job_name}'")

    # Also check self (overlap prevention)
    active_self = ...
    if active_self:
        return SkipReason("Previous run still active")

    return RunRequest(run_key=None)
```

**Priority hierarchy:**
```
Nightly (04:00)          ← highest
   ↑
Manual (Sheets sync)
   ↑
Incremental (every 10m)
   ↑
Realtime (every ~3m)     ← lowest, yields to all above
```

**Lưu ý:** `NOT_STARTED` status bắt buộc include khi check self, tránh miss runs đã queued nhưng chưa start.

---

## Lesson 3: Pre-Create Mart Directories IN Asset (Idempotent Setup)

**Problem:** dbt `COPY TO '{rolling_location}/{file}.parquet'` fail với "directory not found" khi:
- Lần đầu chạy mart model mới
- Rolling folder bị xóa (e.g., GC quá aggressive)
- Developer chạy dbt trực tiếp không qua wrapper

**Fix:** Pre-create directories **trong `@dbt_assets` function**, không chỉ trong standalone script.

```python
@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=SapoDbtTranslator(),
    op_tags={"dagster/concurrency_key": "duckdb_lock"}
)
def sapo_dbt_assets(context, dbt: DbtCliResource):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    export_base_dir = os.path.join(project_root, "data_lake", "export", "marts", "rolling")

    # Idempotent directory creation
    os.makedirs(export_base_dir, exist_ok=True)

    # Scan marts/ và pre-create mỗi model folder
    marts_dir = os.path.join(DBT_PROJECT_DIR, "models", "marts")
    for root, dirs, files in os.walk(marts_dir):
        for file in files:
            if file.endswith(".sql"):
                model_name = os.path.splitext(file)[0]
                os.makedirs(os.path.join(export_base_dir, model_name), exist_ok=True)

    # Inject env var cho dbt process
    os.environ["DBT_EXPORT_PATH"] = export_base_dir

    yield from dbt.cli(["build"], context=context).stream()
```

**Why inside asset vs standalone script:**
- Standalone script (`ensure_dbt_directories.py`) chỉ chạy khi dev nhớ invoke
- Asset-level setup đảm bảo **mỗi dbt run trong Dagster** đều có dirs sẵn
- Idempotent: `exist_ok=True` — safe to call multiple times

---

## Lesson 4: Zombie Background Threads — Disable Telemetry

**Problem:** Dagster job hoàn thành nhưng process không exit → timeout → job bị mark failed dù logic đã xong.

**Root cause:** dlt và dbt cả hai spawn background threads để gửi usage analytics. Threads này giữ process sống sau khi main code xong → Dagster executor timeout.

**Fix:** Set 2 env vars trước khi Dagster start.

```bash
# docker-compose.yml
environment:
  - DLT_TELEMETRY_DISABLED=true
  - DBT_SEND_ANONYMOUS_USAGE_STATS=false
```

```powershell
# run_dagster.ps1 (Windows)
$Env:DLT_TELEMETRY_DISABLED = "true"
$Env:DBT_SEND_ANONYMOUS_USAGE_STATS = "false"
```

**Scope:** Set ở **process level** (docker-compose, shell wrapper), KHÔNG trong Python code — vì threads spawn ngay khi import library, trước khi code của bạn chạy.

**Impact thực tế:** Production blocker trước đó — jobs hang random vài phút rồi timeout. Sau khi set, job exit sạch sẽ ngay sau khi xong.

---

## Lesson 5: QueuedRunCoordinator KHÔNG thay được self-overlap skip

**Misconception (đã mắc phải):** "Sau khi có `QueuedRunCoordinator` + `tag_concurrency_limits`, có thể xóa toàn bộ SkipReason logic trong schedule. Coordinator sẽ tự handle."

**Thực tế:**
- `tag_concurrency_limits` enforce ở **launch time**, chỉ giới hạn N runs cùng tag được dequeue đồng thời
- KHÔNG giới hạn queue size — schedule cứ tick là queue thêm
- Khi 1 run pending lâu → queue tích lũy unbounded (observed: 28+ runs queued sau 1h20m)

**Pattern đúng:**

| Concern | Ai handle |
|---|---|
| Cross-job mutex (job A đang chạy, không cho job B chạy) | Coordinator `tag_concurrency_limits` + tag chung trong `define_asset_job(tags=...)` |
| Self-overlap (job A đang chạy, không tạo thêm job A) | Schedule body với `_has_active_run()` check |
| Queue size cap | Self-overlap skip (nếu đã có active run, không queue thêm) |

**Code:**

```python
_ACTIVE_STATUSES = [
    DagsterRunStatus.QUEUED, DagsterRunStatus.NOT_STARTED,
    DagsterRunStatus.STARTING, DagsterRunStatus.STARTED,
]

def _has_active_run(context, job_name: str) -> str | None:
    runs = context.instance.get_runs(
        filters=RunsFilter(job_name=job_name, statuses=_ACTIVE_STATUSES),
        limit=1,
    )
    return runs[0].run_id if runs else None

@schedule(...)
def ingest_sapo_realtime_schedule(context):
    active = _has_active_run(context, "ingest_sapo_realtime_job")
    if active:
        return SkipReason(f"previous run still active ({active[:8]})")
    return RunRequest(run_key=None)
```

**LOC tradeoff:** Schedule có ~5 dòng skip logic, nhưng đơn giản hơn old version với priority chain (~30 dòng). Cross-job priority đã delegate cho coordinator, schedule chỉ cần check self.

---

## Lesson 6: Asset-level concurrency pool slot leak khi cancel runs

**Symptom:** Run mới chạy STARTED nhưng kẹt với log "Step blocked by limit for pool `duckdb_lock`". Dagster pool API hiển thị `active=1 pending=N` nhưng không có run nào active thực sự.

**Root cause:** `report_run_canceled()` **không tự release** asset-level concurrency pool slots (từ `op_tags={"dagster/concurrency_key": "duckdb_lock"}`). Container restart, force-kill, OOM cũng leak. Khác với run-level tag concurrency (coordinator handle release).

**Verify pool state:**

```python
from dagster import DagsterInstance
inst = DagsterInstance.get()
els = inst.event_log_storage
for key in els.get_concurrency_keys():
    info = els.get_concurrency_info(key)
    print(f"{key}: slot={info.slot_count} active={info.active_slot_count} "
          f"pending={info.pending_step_count}")
    print(f"  active_runs: {info.active_run_ids}")
```

Nếu thấy `active_run_ids` chứa run đã CANCELED/FAILURE → leak.

**Fix:** `els.free_concurrency_slots_for_run(run_id)` cho run terminal.

**Tự động hóa:** `scripts/maintenance/unstick_concurrency_pools.py` — scan mọi pool, free slot cho mọi run không còn active. Idempotent. Chạy sau cancel batch hoặc container restart.

```bash
docker compose exec data_platform python scripts/maintenance/unstick_concurrency_pools.py
```

**Wire vào container boot** (recommended — loại bỏ bước manual sau restart):

```yaml
# docker-compose.yml
command: sh -c "... && dagster instance concurrency set duckdb_lock 1 \
  && (python scripts/maintenance/unstick_concurrency_pools.py || true) \
  && dagster dev -h 0.0.0.0 -p 3001 -f orchestration/definitions.py"
```

`|| true` quan trọng: first-boot chưa có pool → script báo "No concurrency pools configured" → exit 0, không block container. Nếu đã có pool và có slot leak → auto-free trước khi Dagster start. Verified 2026-04-09 boot log:
```
Pool 'duckdb_lock': slot=1 active=0 pending=0
Total slots freed: 0
```

**Rule of thumb:** Cancel run ≠ release slot. Phải verify pool state sau bất kỳ incident nào. Wire auto-unstick vào boot để cover container restart case tự động.

---

## Lesson 7: Reactive trigger cho external source — hash polling beats schedule + beats Drive API

**Khi nào:** Job cần chạy ngay khi external source thay đổi (Google Sheet, public CSV, REST dataset) thay vì chờ schedule định kỳ.

**Anti-pattern 1:** Thêm schedule 5-phút → 99% tick là no-op, ngập log, lãng phí dbt cycle.

**Anti-pattern 2:** Dùng Drive API `modifiedTime` → cần setup service account + API key. Tệ hơn: `modifiedTime` bump với mọi thao tác (format cell, sort, rename tab) → **false positive** trigger.

**Pattern đúng:** Sensor poll content hash của source, fire RunRequest chỉ khi hash đổi thực sự.

```python
@sensor(
    job_name="ingest_sheets_sync_job",
    minimum_interval_seconds=300,
    default_status=DefaultSensorStatus.RUNNING,  # auto-on — sensor mới default STOPPED
)
def sheets_modified_sensor(context):
    prev = json.loads(context.cursor) if context.cursor else {}
    current = {name: hashlib.sha256(requests.get(url).content).hexdigest()
               for name, url in SHEET_URLS.items()}

    if not prev:  # Cold start: record baseline, đừng fire
        context.update_cursor(json.dumps(current))
        return SkipReason("Cold start")

    changed = [k for k, v in current.items() if prev.get(k) != v]
    if not changed:
        return SkipReason("No changes")

    context.update_cursor(json.dumps(current))
    return RunRequest(
        run_key=f"sheets-{'-'.join(f'{n}:{current[n][:12]}' for n in sorted(changed))}",
        tags={"concurrency_group": "dbt_rw", "source": "ingest_sheets_modified_sensor"},
    )
```

**Key invariants:**
- **Cold start phải skip** (không có `prev`) — tránh flood runs sau deploy.
- **Fetch error phải preserve cursor cũ** — không được trigger false khi endpoint recover.
- **`run_key` embed hash** → Dagster dedup tự động.
- **`default_status=RUNNING`** → bắt buộc, không thì sensor mới tạo vẫn STOPPED.

**Cascade job selection với `.downstream()`:** Khi sensor fire job, job phải rebuild **chỉ** những asset phụ thuộc vào source — không phải full dbt graph:

```python
_sources = AssetSelection.assets(sheets_targets_asset) | AssetSelection.assets(sheets_marketing_spend_asset)
ingest_sheets_sync_job = define_asset_job(
    name="ingest_sheets_sync_job",
    selection=_sources | _sources.downstream() | AssetSelection.assets(serving.build_serving_db),
    tags={"concurrency_group": "dbt_rw"},
)
```

→ Resolve thành 7 assets (2 raw + 2 staging + 2 marts + 1 serving_db) thay vì 400+ models.

**Gotcha bắt buộc verify sau deploy:** Sensor mới và sensor sửa logic phải `reloadRepositoryLocation` + theo dõi log daemon:

```bash
docker logs --since 5m data_platform 2>&1 | grep -iE "sensor" | grep -iE "error|traceback"
# Không output = sensors healthy. Có output = fix trước khi đi ngủ.
```

**Template:** `.skills/data-pipeline/templates/dagster-reactive-sensor-template.py` — copy, replace 3 markers, done.

**Chi tiết:** xem `lessons-learned.md` L21 (content-hash sensor), L22 (`AssetSelection.downstream()`), L23 (`get_run_records()` vs `get_runs()` — sensor `DagsterRun.start_time` trap).

**Sensor rename map:** `sheets_modified_sensor` → `ingest_sheets_modified_sensor`; `stuck_run_sensor` → `health_alert_stuckrun_sensor`; `lark_failure_sensor` → `health_alert_failure_sensor`.

---

## Lesson 8: `DagsterRun` không có `start_time` — sensor phải dùng `get_run_records()`

**Symptom:** Sensor code `inst.get_runs(filters=...)` rồi `run.start_time` → `AttributeError: 'DagsterRun' object has no attribute 'start_time'`. Sensor daemon error spam mỗi tick. Đặc biệt nguy hiểm: sensor silent-fail, log chỉ ở daemon layer, không ai để ý cả tháng.

**Root cause:** Dagster 1.x+ tách `DagsterRun` (run metadata core) khỏi `RunRecord` (record + timestamps). `start_time`/`end_time`/`create_timestamp` chỉ tồn tại trên `RunRecord`.

**Fix:**

```python
# SAI
runs = inst.get_runs(filters=RunsFilter(statuses=[DagsterRunStatus.STARTED]))
for run in runs:
    if run.start_time: ...  # AttributeError

# ĐÚNG
records = inst.get_run_records(filters=RunsFilter(statuses=[DagsterRunStatus.STARTED]))
for rec in records:
    run = rec.dagster_run
    if rec.start_time:  # epoch seconds float
        ...
```

**Rule:** Mọi sensor đụng vào run timing → dùng `get_run_records()`, không bao giờ `get_runs()`.

---

## Lesson 9: Separate Jobs for Nightly Incremental vs Manual Full-Refresh

**Problem:** Nếu gắn tag `full_refresh=true` vào nightly schedule → toàn bộ API bị scan mỗi đêm, lãng phí và không cần thiết. Nếu không tách job, operator phải truyền tag thủ công mỗi lần muốn full-refresh → error-prone.

**Pattern đúng: 2 job definitions riêng biệt**

```python
# Nightly — incremental (default behavior)
pipeline_batch_nightly_job = define_asset_job(
    name="pipeline_batch_nightly_job",
    selection=nightly_selection,
    tags={"concurrency_group": "dbt_rw"},
    # KHÔNG tag full_refresh — assets chạy incremental
)

# Manual full-refresh — one-click launch từ Dagster UI
pipeline_batch_fullrefresh_job = define_asset_job(
    name="pipeline_batch_fullrefresh_job",
    selection=nightly_selection,  # cùng assets
    tags={
        "concurrency_group": "dbt_rw",
        "full_refresh": "true",   # baked in — không cần truyền lúc launch
    },
)
```

**Asset đọc tag:**

```python
@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def ingest_sapov2_orders_batch_asset(context):
    full_refresh = context.run.tags.get("full_refresh") == "true"
    argv = ["--full-refresh"] if full_refresh else []

    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        load_info = run_orders_batch.run(argv=argv)
    finally:
        os.chdir(cwd)
```

**Cursor continuity:** Cả hai job dùng cùng `pipeline_name` → share dlt state file. Full-refresh cập nhật cursor sau khi load xong → nightly run tiếp theo chỉ scan từ đó trở đi.

```
[full_refresh run]  scan all → cursor = T_now
[nightly run]       scan from T_now → chỉ load data mới
```

**Lưu ý về batch source wiring:** `full_refresh` phải được wire xuyên suốt từ entry-point xuống resource function:

```python
# Entry point
def run(argv=None):
    parser.add_argument("--full-refresh", action="store_true")
    args = parser.parse_args(argv)
    sapo_orders_source(full_refresh=args.full_refresh)

# Source function
@dlt.source
def sapo_orders_source(full_refresh: bool = False):
    yield sapo_orders_resource(full_refresh=full_refresh)

# Resource function
@dlt.resource
def sapo_orders_resource(..., full_refresh: bool = False):
    last_value = None if full_refresh else first_timestamp.last_value
    ...
```

Nếu thiếu wire này → `--full-refresh` bị silently ignored, cursor vẫn dùng giá trị cũ → nightly finish instantly với 0 records mới.

**Xem thêm:** `lessons-learned.md` L32, L25.

---

## Lesson 10: Auto-Termination + Concurrency Pool Janitor — Self-Healing Infrastructure

**Problem:** Runs get stuck (subprocess hang, dbt bug) → block concurrency pool → cascade block all subsequent runs. Manual intervention required.

**Solution: 3-layer defense**

### Layer 1: dbt Subprocess Timeout Watchdog (prevent hang at source)

```python
# orchestration/assets/dbt.py
import threading

DBT_TIMEOUT_SEC = int(os.environ.get("DBT_TIMEOUT_SEC", "900"))  # 15 min

@dbt_assets(...)
def sapo_dbt_assets(context, dbt: DbtCliResource):
    invocation = dbt.cli(["build"], context=context)

    def _kill_on_timeout():
        context.log.error(f"dbt exceeded {DBT_TIMEOUT_SEC}s — killing")
        try:
            invocation.process.kill()
        except Exception:
            pass

    watchdog = threading.Timer(DBT_TIMEOUT_SEC, _kill_on_timeout)
    watchdog.daemon = True
    watchdog.start()
    try:
        yield from invocation.stream()
    finally:
        watchdog.cancel()
        # CRITICAL: Kill subprocess on ANY exit path (normal, timeout, or external
        # cancellation). Without this: alerter cancels the Dagster run → Python
        # generator cleanup fires `finally: watchdog.cancel()` → watchdog disarmed
        # → dbt subprocess orphaned, holds DuckDB WAL lock → every subsequent run
        # hangs immediately → cascade of stuck runs. See L60.
        try:
            if invocation.process.poll() is None:
                invocation.process.kill()
        except Exception:
            pass
```

**Why:** `dbt.cli().stream()` has no timeout. DuckDB WAL checkpoint can hang indefinitely under I/O pressure. Watchdog ensures hard upper bound. The `finally` kill ensures no orphan subprocess when run is cancelled externally (see L60 — the zombie cascade pitfall).

### Layer 2: Stuck Run Auto-Terminator (catch hangs that escape watchdog)

```python
# orchestration/sensors/stuck_run_alerter.py
INACTIVITY_THRESHOLD = timedelta(minutes=5)   # no log output → stuck
MIN_RUNTIME_BEFORE_KILL = timedelta(minutes=10)  # grace period

@sensor(minimum_interval_seconds=300)
def health_alert_stuckrun_sensor(context):
    for rec in instance.get_run_records(filters=RunsFilter(statuses=[STARTED])):
        if runtime < MIN_RUNTIME_BEFORE_KILL:
            continue
        last_event_time = _get_last_event_time(context, run.run_id)
        if (now - last_event_time) > INACTIVITY_THRESHOLD:
            # Auto-terminate sequence
            instance.report_run_canceled(run)
            instance.report_run_failed(run, "Auto-terminated: no activity")
            instance.event_log_storage.free_concurrency_slots_for_run(run.run_id)
            _terminate_subprocess_tree(run.run_id)  # CRITICAL: kill actual process
            send_lark_card(...)
```

**Critical addition (2026-04-24):** Must call `_terminate_subprocess_tree()` using `psutil` to send actual OS signals. `report_run_canceled()` only updates Dagster state — subprocess survives.

```python
def _terminate_subprocess_tree(run_id: str) -> bool:
    """Kill subprocess tree via psutil."""
    for proc in psutil.process_iter(['cmdline']):
        if run_id[:12] in " ".join(proc.info.get('cmdline') or []):
            parent = psutil.Process(proc.pid)
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()
            psutil.wait_procs([parent] + parent.children(), timeout=3)
            return True
    return False
```

**Key insight:** Activity-based detection (no log output 5+ min) beats fixed timeout. Legitimate long runs produce continuous output; hung processes go silent.

### 2. Concurrency Pool Janitor

```python
# orchestration/sensors/concurrency_pool_janitor.py
@sensor(minimum_interval_seconds=300)
def health_concurrency_pool_janitor(context):
    for key in els.get_concurrency_keys():
        info = els.get_concurrency_info(key)
        for run_id in info.active_run_ids | info.pending_run_ids:
            run = instance.get_run_by_id(run_id)
            if run is None or run.status not in ACTIVE_STATUSES:
                els.free_concurrency_slots_for_run(run_id)
```

**Covers:** Container crash, OOM kill, `report_run_canceled()` không release slot, boot-time leak.

### Layered Defense

| Layer | Mechanism | Coverage |
|-------|-----------|----------|
| Boot | `unstick_concurrency_pools.py` trong docker-compose command | Pre-existing leaks |
| Runtime (5 min) | `health_concurrency_pool_janitor` sensor | Mid-runtime leaks |
| Stuck (5 min) | `health_alert_stuckrun_sensor` → free slots after kill | Hung process leaks |

**Result:** Zero manual intervention for stuck runs. System self-heals within 10 minutes.

**Reference:** `orchestration/sensors/stuck_run_alerter.py`, `orchestration/sensors/concurrency_pool_janitor.py`

---

## Lesson 11: Health Checks Mutual Exclusion với Ingestion

**Problem:** Health checks job (`all_asset_checks()`) block ingestion 55+ min vì include dbt tests → compete `duckdb_lock`.

**Solution: 3 layers**

### 1. Exclude dbt tests từ health checks

```python
health_checks_asset_job = define_asset_job(
    name="health_checks_asset_job",
    selection=(
        AssetSelection.all_asset_checks()
        - AssetSelection.checks_for_assets(dbt.sapo_dbt_assets)
    ),
    executor_def=in_process_executor,
)
```

### 2. Schedule mutual exclusion

```python
def _has_active_ingestion(context) -> str | None:
    for job_name in ["ingest_sapo_realtime_job", "pipeline_batch_nightly_job", ...]:
        runs = context.instance.get_runs(filters=RunsFilter(job_name=job_name, statuses=_ACTIVE_STATUSES), limit=1)
        if runs:
            return runs[0].run_id
    return None

@schedule(cron_schedule="5 */2 * * *", ...)  # offset :05
def health_checks_schedule(context):
    if active := _has_active_ingestion(context):
        return SkipReason(f"Ingestion active ({active[:8]})")
    return RunRequest(run_key=None)
```

### 3. Cron offset

`:05` thay vì `:00` → không trigger cùng lúc với ingestion schedules.

**Priority:** Ingestion > Health checks. Data freshness quan trọng hơn monitoring freshness.

---

## Lesson 12: Backup Job Must Acquire duckdb_lock

**Problem:** Backup job runs `cp -a` on DuckDB files while dbt is writing → I/O pressure causes DuckDB WAL checkpoint to stall (uninterruptible I/O sleep) → dbt hangs indefinitely.

**Fix:** Add concurrency tag to backup op:

```python
@op(
    tags={
        "kind": "maintenance",
        "dagster/concurrency_key": "duckdb_lock",  # Wait for dbt
    },
)
def run_platform_backup(context):
    ...
```

**Effect:** Backup queues behind dbt/ingestion. No I/O collision during WAL checkpoint.

**Trade-off:** Backup may delay up to 15 min if dbt running. Acceptable for maintenance job.

---

## Lesson 13: Zombie NOT_STARTED Runs After Container Restart

**Problem:** Container restart leaves `NOT_STARTED` runs in Dagster SQLite. Every schedule tick finds this zombie via `_has_active_run()` → skips indefinitely.

**Why it happens:** Run enqueued → container restarts before run starts → after restart, run still `NOT_STARTED` but executor context lost → will never execute.

**Manual fix:**
```bash
docker exec data_platform python3 -c "
from dagster import DagsterInstance
instance = DagsterInstance.get()
run = instance.get_run_by_id('zombie-run-id')
instance.report_run_canceled(run)
"
```

**Auto-fix at boot:** Add to `unstick_concurrency_pools.py`:

```python
# Cancel NOT_STARTED runs older than 30 min
cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
for rec in instance.get_run_records(filters=RunsFilter(statuses=[DagsterRunStatus.NOT_STARTED])):
    if datetime.fromtimestamp(rec.create_timestamp, tz=timezone.utc) < cutoff:
        instance.report_run_canceled(rec.dagster_run)
```

**Reference:** `lessons-learned.md` L48

---

## Lesson 14: Maintenance Schedule Topology — Cleanup, Backup, Auto-Recovery

**Problem:** Daily maintenance jobs (purge, backup, vacuum) compete with each other and with active ingestion. Without explicit topology, you get:
- Backup mid-running while purge is deleting files → ENOENT noise + partial backup
- Purge competing with realtime tick (every 3 min) on event_logs SQLite → "database is locked"
- Schedules defined in code but never running (`DECLARED_IN_CODE` status)
- Auto-recovery sensor only watching `STARTED` runs — misses queue-stuck zombies

### Topology rules

```
02:30  purge_runs_job          (clears Dagster history + dbt target dirs)
03:00  transform_batch_nightly (holds dbt_rw=1)
04:30  health_recon_daily      (read-only on serving DB)
04:45  health_kpi_closure      (read-only)
06:00  backup_platform_job     (yields if purge still running)
06:00  health_report_digest    (read-only, parallel-safe with backup)
```

**Why this order:**
- **Purge first**: clears `history/` so backup snapshots a small dataset (`history/` excluded anyway, but smaller `index.db` reduces backup time)
- **02:30 quietest window**: realtime ticks every 3 min always; nightly at 03:00; recon at 04:30 — 02:00-02:59 has the lowest competing write pressure on Dagster's SQLite
- **Backup yields to purge**: if purge backlog runs >30 min (recovery scenario), backup skips this window rather than producing partial output
- **Digest parallel with backup**: both read-only on different DBs; OK to share the 06:00 slot

### Required wiring

**1. Schedule must yield to peer maintenance:**

```python
@schedule(
    job=maintain_backup_platform_job,
    cron_schedule="0 6 * * *",
    execution_timezone="Asia/Ho_Chi_Minh",
)
def maintain_backup_platform_schedule(context):
    if _has_active_run(context, "maintain_backup_platform_job"):
        return SkipReason("backup: previous run still active")
    if _has_active_run(context, "maintain_purge_runs_job"):
        return SkipReason("backup: yielding to active purge")
    return RunRequest(run_key=None)
```

**2. Stuck-run sensor covers ALL non-terminal states (not just `STARTED`):**

```python
@sensor(minimum_interval_seconds=60)  # cheap status-filter query
def health_alert_stuckrun_sensor(context):
    # Pass 1: STARTED + no log activity for 5+ min (caught by INACTIVITY_THRESHOLD)
    # ... existing logic ...

    # Pass 2: NOT_STARTED/QUEUED/STARTING for 2h+ (daemon never dequeued)
    queue_records = instance.get_run_records(
        filters=RunsFilter(statuses=[
            DagsterRunStatus.NOT_STARTED,
            DagsterRunStatus.QUEUED,
            DagsterRunStatus.STARTING,
        ])
    )
    for rec in queue_records:
        age = now - datetime.fromtimestamp(rec.create_timestamp, tz=timezone.utc)
        if age >= QUEUE_STUCK_THRESHOLD:  # 2h
            instance.report_run_canceled(rec.dagster_run)
```

**3. Backup script `trap … EXIT` for cleanup, pre-flight disk check:**

```bash
# scripts/backup/backup.sh
trap rotate_old_backups EXIT  # always rotate, even if cp fails

# Pre-flight: abort fast if free < source + 1 GB margin
NEED_KB=$(du -sk "$DATA_ROOT" | awk '{print $1}')
FREE_KB=$(df -Pk "$BACKUP_ROOT" | awk 'NR==2 {print $4}')
[ "$FREE_KB" -lt "$((NEED_KB + 1024*1024))" ] && exit 1

# After copying dagster_home, exclude regenerable run history
prune_dagster_history "${BACKUP_DIR}/app_data/dagster_home"
```

**4. `purge_runs_job` must clean BOTH Dagster history AND dbt target dirs:**

```python
# orchestration/ops/purge_runs.py
def maintain_purge_runs_op(context):
    # ... delete runs older than PURGE_KEEP_DAYS ...
    # ... cleanup orphan .db files in history/runs/ ...
    # ... VACUUM index.db to reclaim space after mass deletes ...
    _cleanup_dbt_target_dirs(keep_days=1)  # transformation/target/sapo_dbt_assets-*
```

`sapo_dbt_assets-*` accumulates ~480 dirs/day × 10 MB = ~4.8 GB/day untouched. Purge cleanup is the only thing keeping it bounded.

### Operational gotcha

**Schedule listed in `defs.schedules=[...]` but never starts:** Dagster does NOT auto-enable on first detection. New schedules sit in `DECLARED_IN_CODE` status and only tick after explicit start. Verify with:

```bash
docker exec data_platform sh -c '
python -c "
import sqlite3, json
c = sqlite3.connect(\"/app/var/dagster_home/schedules/schedules.db\").cursor()
c.execute(\"SELECT job_body, status FROM jobs WHERE job_type=\x27SCHEDULE\x27\")
for body, status in c.fetchall():
    print(status, json.loads(body)[\"origin\"][\"job_name\"])
"'
```

If a schedule from your `definitions.py` is missing → never enabled. Start it:

```bash
dagster schedule start -f orchestration/definitions.py <schedule_name>
```

**Cron edited in code but storage shows old value:** schedule storage caches cron from FIRST start. Daemon evaluates the NEW cron from in-memory definitions (storage cron is just a snapshot). To align them, `dagster schedule stop && dagster schedule start` after any cron edit.

**Reference:** `lessons-learned.md` L49 (DECLARED_IN_CODE pitfall), L50 (`trap … EXIT`), L51 (exclude `dagster_home/history`), L52 (Pass 2 stuck sensor).

---

## Summary: Dagster Integration Checklist

Khi add job/asset mới vào Dagster, kiểm tra:

- [ ] Nếu job chứa nhiều ingestion methods → inject upstream keys trong `get_upstream_asset_keys()`
- [ ] Cron schedule không collide với existing schedules (offset minute marks)
- [ ] Schedule function check **self** active runs trước khi `RunRequest` (cross-job mutex giao cho coordinator tag, không cần priority chain) — xem Lesson 5
- [ ] DuckDB writer assets có `op_tags={"dagster/concurrency_key": "duckdb_lock"}`
- [ ] `docker-compose.yml` command wire `unstick_concurrency_pools.py || true` trước `dagster dev` — auto-heal slot leak mỗi lần container restart — xem Lesson 6
- [ ] `DLT_TELEMETRY_DISABLED=true` và `DBT_SEND_ANONYMOUS_USAGE_STATS=false` set ở process level
- [ ] Ingestion assets: `argv=[]`, `os.chdir(DLT_DIR)`, `load_dlt_configuration()`
- [ ] Mart dirs được pre-create trong `@dbt_assets` function
- [ ] Serving asset có `deps=[dbt_assets]`
- [ ] **Sensor** mới có `default_status=DefaultSensorStatus.RUNNING` — sensor mới default STOPPED, phải set RUNNING không thì không tick — xem Lesson 7
- [ ] **Sensor** targeting specific job → job phải có trong `Definitions(jobs=[...])` — không auto-discover từ schedules
- [ ] **Sensor** đụng run timing → dùng `get_run_records()`, KHÔNG `get_runs()` (`DagsterRun` không có `start_time`) — xem Lesson 8
- [ ] **Sau mỗi edit sensor/definitions.py** → `reloadRepositoryLocation` via GraphQL + verify log daemon không có sensor error
- [ ] **Full-refresh** = `pipeline_batch_fullrefresh_job` (manual, tag baked in), KHÔNG tag nightly schedule — xem Lesson 9
- [ ] Batch source functions wire `full_refresh` param từ entry-point → source → resource (nếu thiếu: silently ignored)
- [ ] Job cascade "source → downstream" → dùng `_sources | _sources.downstream()`, không dùng full `all_dbt_assets`
- [ ] **Auto-recovery sensors** trong `Definitions(sensors=[...])`: `health_alert_stuckrun_sensor` + `health_concurrency_pool_janitor` — xem Lesson 10
- [ ] Health checks job exclude dbt tests: `AssetSelection.all_asset_checks() - AssetSelection.checks_for_assets(dbt_assets)` — xem Lesson 11
- [ ] Health checks schedule có `_has_active_ingestion()` check + offset `:05` cron — xem Lesson 11
- [ ] **dbt subprocess timeout watchdog** trong `@dbt_assets` — 15 min hard limit via `threading.Timer` — xem Lesson 10 Layer 1
- [ ] **`finally` block kill subprocess** sau `watchdog.cancel()` — không chỉ cancel watchdog; external cancellation disarms watchdog nhưng không kill dbt → zombie cascade (L60)
- [ ] **stuck_run_alerter must kill subprocess** via `psutil` — `report_run_canceled()` only updates state — xem Lesson 10 Layer 2
- [ ] **QUEUE_STUCK_THRESHOLD** sized dựa vào schedule topology thực tế, không phải "an toàn 2h mặc định" — xem L61
- [ ] **psutil** in `requirements.txt` for subprocess termination
- [ ] **Backup job** has `"dagster/concurrency_key": "duckdb_lock"` to prevent I/O collision — xem Lesson 12
- [ ] **Boot-time cleanup** cancels zombie NOT_STARTED runs older than 30 min — xem Lesson 13
- [ ] **Maintenance schedule explicitly started** (not just listed in `defs.schedules`) — verify `schedules.db` `jobs` table has row with `status='RUNNING'` — xem Lesson 14 / L49
- [ ] **Backup schedule yields to active purge** — `_has_active_run("maintain_purge_runs_job")` check before `RunRequest` — xem Lesson 14
- [ ] **Maintenance cron in quiet window** — purge 02:30 ICT (before nightly), backup 06:00 ICT (after recon/KPI)
- [ ] **stuck_run_alerter has Pass 2** for `NOT_STARTED`/`QUEUED`/`STARTING` >2h — Pass 1 alone misses queue-stuck zombies — xem Lesson 14 / L52
- [ ] **`backup.sh` rotation in `trap … EXIT`** + pre-flight `df` check + `prune_dagster_history` — xem L50, L51
- [ ] **`purge_runs_job` cleans dbt target dirs** (`_cleanup_dbt_target_dirs`) — without this, `transformation/target/` accumulates ~5 GB/day — xem Lesson 14
- [ ] **Long-running silent ops trong purge job dùng heartbeat thread** — VACUUM / large SELECT DISTINCT / cross-db DELETE không emit log → stuck-run alerter kill sau 5 min; dùng `threading.Thread` + `_done.wait(timeout=30)` loop để emit progress — xem L63
- [ ] **Schedules ngắn yield to long-running dbt_rw jobs** — realtime/incremental phải check `_long_dbt_rw_holder()` trước khi tạo RunRequest; không thì tạo NOT_STARTED zombie chặn ticks 90 min — xem L64
- [ ] **trigger_backup check `_has_active_ingestion`** — không backup DuckDB khi đang có ingestion job chạy (torn WAL + I/O contention) — xem L64
- [ ] **Lightweight read-only jobs dùng `in_process_executor`** — `ChildProcessCrashException` trên lightweight jobs = OOM từ per-step subprocess overhead; dùng `in_process_executor` cho health checks, recon, KPI — xem L65
- [ ] **`MetadataValue.float()` phải nhận `float`, không phải `int`** — `or 0` returns `int(0)` khi value là None/0.0; dùng `or 0.0` — xem L66
- [ ] **File-drop sensor KHÔNG có cold-start skip** — files present tại thời điểm deploy bị silently ignored nếu có cold-start guard; remove nó và dùng `current_mtime > prev_mtime` — xem L67
- [ ] **`cp -a` trên live SQLite dirs: check destination, không check exit code** — WAL/SHM có thể disappear mid-copy → non-zero exit; verify thành công bằng `[ -d "$dst" ] && [ "$(ls -A "$dst")" ]` — xem L68
- [ ] **Backup fallback schedule dùng `run_key=None` + manual success check** — `run_key=date` deduplicates against FAILED runs → no retry possible; dùng `run_key=None` + query SUCCESS runs for today — xem L69
- [ ] **Windows Defender exclusion phải cover TOÀN BỘ `data_lake/`, không chỉ `monitoring/`** — `sapo_warehouse.duckdb` cũng trên bind-mounted path; dllhost.exe lock nó → dbt subprocess D-state → stuck 24 min; exclusion chỉ `monitoring/` là không đủ — xem L72

---

## Reference Files

| File | Purpose |
|------|---------|
| `orchestration/assets/dbt.py` | `SapoDbtTranslator` với upstream injection + mart dir pre-create |
| `orchestration/definitions.py` | Schedule offset + priority yielding logic + explicit `jobs=[...]` cho sensors |
| `orchestration/assets/serving.py` | Serving asset với `deps=[sapo_dbt_assets]` |
| `orchestration/sensors/sheets_modified_sensor.py` | `ingest_sheets_modified_sensor` — Reactive content-hash sensor — xem Lesson 7 |
| `orchestration/sensors/stuck_run_alerter.py` | `health_alert_stuckrun_sensor` — Hang detector dùng `get_run_records()` — xem Lesson 8 |
| `orchestration/sensors/failure_alerting.py` | `health_alert_failure_sensor` — Lark alert cho terminal FAILURE runs |
| `orchestration/sensors/stuck_run_alerter.py` | `health_alert_stuckrun_sensor` — Activity-based auto-terminator — xem Lesson 10 |
| `orchestration/sensors/concurrency_pool_janitor.py` | `health_concurrency_pool_janitor` — Auto-free leaked slots — xem Lesson 10 |
| `.skills/data-pipeline/templates/dagster-reactive-sensor-template.py` | Copy-paste starter cho reactive sensor mới |
| `orchestration/definitions.py` | `pipeline_batch_nightly_job` + `pipeline_batch_fullrefresh_job` definitions — xem Lesson 9 |
| `docker-compose.yml` | Telemetry env vars (line 20-21) + auto-unstick on boot (line 33) |
| `run_dagster.ps1` | Windows local telemetry vars (line 10-11) |
