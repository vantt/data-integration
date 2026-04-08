# Dagster Orchestration Patterns

Lessons quan trọng khi orchestrate pipeline dlt + dbt trong Dagster. Đây là phần **dễ sai nhất** vì không có warning từ Dagster.

---

## Lesson 1: Hybrid Job Race Condition — Explicit Upstream Key Injection

**Problem:** Trong job chạy nhiều loại ingestion + dbt cùng lúc, dbt có thể start **trước khi** một số ingestion asset xong → dbt đọc stale data.

**Root cause:** dbt models declare source qua `{{ source('sapo_raw', 'order') }}`. `SapoDbtTranslator.get_asset_key()` map source đó tới `sapo_orders_batch_asset`. Nhưng nếu job chỉ chứa `sapo_history_log_asset` (không có batch asset), Dagster thấy source không có dependency trong scope job → dbt start ngay lập tức song song với history_log.

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
            upstream_keys.add(AssetKey(["sapo", "sapo_orders_batch_asset"]))
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
def realtime_schedule(context):
    priority_jobs = [
        "sheets_sync_job",
        "sapo_nightly_reconciliation_job",
        "sapo_incremental_sync_job",
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
def realtime_schedule(context):
    active = _has_active_run(context, "sapo_realtime_sync_job")
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

**Rule of thumb:** Cancel run ≠ release slot. Phải verify pool state sau bất kỳ incident nào.

---

## Summary: Dagster Integration Checklist

Khi add job/asset mới vào Dagster, kiểm tra:

- [ ] Nếu job chứa nhiều ingestion methods → inject upstream keys trong `get_upstream_asset_keys()`
- [ ] Cron schedule không collide với existing schedules (offset minute marks)
- [ ] Schedule function check **self** active runs trước khi `RunRequest` (cross-job mutex giao cho coordinator tag, không cần priority chain) — xem Lesson 5
- [ ] DuckDB writer assets có `op_tags={"dagster/concurrency_key": "duckdb_lock"}`
- [ ] Sau mọi cancel batch / container restart: chạy `scripts/maintenance/unstick_concurrency_pools.py` để clear leaked slots — xem Lesson 6
- [ ] `DLT_TELEMETRY_DISABLED=true` và `DBT_SEND_ANONYMOUS_USAGE_STATS=false` set ở process level
- [ ] Ingestion assets: `argv=[]`, `os.chdir(DLT_DIR)`, `load_dlt_configuration()`
- [ ] Mart dirs được pre-create trong `@dbt_assets` function
- [ ] Serving asset có `deps=[dbt_assets]`

---

## Reference Files

| File | Purpose |
|------|---------|
| `orchestration/assets/dbt.py` | `SapoDbtTranslator` với upstream injection + mart dir pre-create |
| `orchestration/definitions.py` | Schedule offset + priority yielding logic |
| `orchestration/assets/serving.py` | Serving asset với `deps=[sapo_dbt_assets]` |
| `docker-compose.yml` | Telemetry env vars (line 20-21) |
| `run_dagster.ps1` | Windows local telemetry vars (line 10-11) |
