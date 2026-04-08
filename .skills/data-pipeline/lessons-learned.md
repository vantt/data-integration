# Lessons Learned — DLT Ingestion

## Cấu hình DLT (quan trọng)

### Tổ chức file config

```
ingestion/
└── .dlt/
    ├── config.toml         # Non-secret: domain, delays, layout, selectors
    ├── secrets.toml        # Secret: credentials, tokens, bucket_url (GITIGNORED)
    └── secrets.toml.sample # Template secrets.toml (committed to git)
```

**Nguyên tắc phân chia:**
- `config.toml` → mọi thứ không nhạy cảm (URL, delay, selector CSS, layout)
- `secrets.toml` → credentials, API tokens, bucket paths (gitignored)
- Không bao giờ commit secrets.toml

### Resolution chain (priority thấp → cao)

```
secrets.toml.sample   (template, git-committed)
       ↓
.dlt/secrets.toml     (gitignored, local dev / server)
       ↓
ingestion/.env.local  (gitignored, loaded bởi load_dlt_configuration())
       ↓
Environment variables (Docker, CI/CD, Dagster launch env)
```

Khi Dagster chạy: `.env.local` không tự load — phải gọi `load_dlt_configuration()` đầu mỗi asset.

### Mapping env var ↔ config key

dlt dùng double underscore (`__`) để map env var vào nested config:

| Env Var | config.toml / secrets.toml key |
|---------|-------------------------------|
| `SOURCES__SAPO__USERNAME` | `[sources.sapo]` → `username` |
| `DESTINATION__FILESYSTEM__BUCKET_URL` | `[destination.filesystem]` → `bucket_url` |
| `SOURCES__SAPO__REQUEST_DELAY` | `[sources.sapo]` → `request_delay` |

Format: `SECTION__SUBSECTION__KEY` → uppercase, double underscore.

### Partition layout — phải đặt trong config.toml, không phải env var

```toml
# ingestion/.dlt/config.toml
[destination.filesystem]
loader_file_format = "parquet"
layout = "{table_name}/ingest_method={ingest_method}/year={year}/month={month}/{file_id}.{ext}"
extra_placeholders = { "ingest_method" = "text", "year" = "text", "month" = "text" }
```

`extra_placeholders` phải khai báo tên và type của custom partition fields.  
`bucket_url` đặt trong `secrets.toml` (vì chứa path cụ thể của server).

### Đọc config trong source code

```python
import dlt

# Đọc từ [sources.sapo] trong config/secrets
domain = dlt.config["sources.sapo.domain"]
username = dlt.secrets["sources.sapo.username"]  # secrets cho sensitive data
```

---

## Ingestion Patterns

### L1 — Early-stop pagination (đừng dùng total_count)

Sapo API sort DESC theo `modified_on`. Thay vì tính tổng pages, đếm `consecutive_old_items`:
```python
if consecutive_old_items >= min_overlap_items:  # default 500
    break  # đủ safety buffer, dừng
```
**Tại sao:** total_count không đáng tin (API có thể trả sai); early-stop ổn định hơn và tránh scan toàn lịch sử.

### L2 — Incremental cursor phải là path đầy đủ trong record

```python
# SAI — field không có ở root
first_timestamp = dlt.sources.incremental("event_timestamp")

# ĐÚNG — field nằm trong sync_metadata
first_timestamp = dlt.sources.incremental("sync_metadata.event_timestamp")
```

### L3 — Envelope append-only, dedup ở transform layer

Không UPDATE trong data lake. Mọi version của entity đều append. Dedup thực hiện trong dbt `src_` model.  
**Tại sao:** Giữ full audit trail; nhiều ingest channel (batch + webhook + history_log) cùng ghi vào một table.

### L4 — Ingest method priority khi dedup

```sql
CASE ingest_method
    WHEN 'webhook' THEN 3      -- Real-time event, tin nhất
    WHEN 'history_log' THEN 2  -- Gap-fill, tin thứ hai
    ELSE 1                     -- batch_sync
END DESC
```

### L5 — 7-day incremental buffer trong dbt

```sql
{% if is_incremental() %}
WHERE event_timestamp > (SELECT MAX(event_timestamp) - INTERVAL 7 DAY FROM {{ this }})
{% endif %}
```
**Tại sao:** Late-arriving events từ history_log hoặc webhook có thể đến sau batch sync. Buffer 7 ngày đảm bảo không bỏ sót.

### L6 — Empty page: retry 1 lần trước khi stop

```python
if not items_data:
    if empty_retries < 1:
        empty_retries += 1
        time.sleep(2)
        continue  # retry cùng page
    break  # thật sự hết data
empty_retries = 0  # reset khi có data
```
**Tại sao:** Network fluke có thể trả empty page tạm thời — retry 1 lần tránh false early-stop.

### L7 — Luôn support --full-refresh

```python
# run_pipeline() đã built-in sẵn:
if args.full_refresh:
    pipeline.drop()  # xóa state, load lại từ đầu
```
Dùng khi: debug, backfill, schema change, state bị corrupt.

---

## Dagster Integration

### L8 — `argv=[]` trong Dagster asset (critical)

```python
# SAI — pick up Dagster's sys.argv, gây lỗi argparse
load_info = run_orders_batch.run()
load_info = run_orders_batch.run(argv=None)

# ĐÚNG
load_info = run_orders_batch.run(argv=[])
```

### L9 — `os.chdir(DLT_DIR)` trước khi run pipeline

```python
cwd = os.getcwd()
try:
    os.chdir(DLT_DIR)           # dlt tìm .dlt/config.toml từ CWD
    load_info = run_entity.run(argv=[])
finally:
    os.chdir(cwd)               # restore để không ảnh hưởng asset khác
```
**Tại sao:** dlt resolve `.dlt/` relative to CWD. Dagster CWD không phải `ingestion/`.

### L10 — `load_dlt_configuration()` phải gọi trước pipeline

```python
@asset(...)
def my_asset(context):
    load_dlt_configuration(context.log.info)  # load .env.local + secrets.toml
    os.chdir(DLT_DIR)
    run_entity.run(argv=[])
```
Hàm này trong `orchestration/assets/utils.py`. Dagster không tự load `.env.local`.

### L11 — DuckDB concurrency lock

```python
@asset(
    op_tags={"dagster/concurrency_key": "duckdb_lock"},  # REQUIRED nếu write DuckDB
    ...
)
```
Dagster concurrency key = `duckdb_lock`, limit = 1 trong Dagster config.  
**Tại sao:** DuckDB single-file storage không support concurrent writes → deadlock nếu thiếu.

---

## Storage

### Parquet output path
```
DESTINATION__FILESYSTEM__BUCKET_URL=file:///app/data_lake
Layout: {table_name}/ingest_method={x}/year={y}/month={m}/{file_id}.parquet
```

### DuckDB (dbt reads từ Parquet)
```
DBT_DATA_LAKE_PATH=/app/data_lake    # dbt đọc Parquet từ đây
DBT_EXPORT_PATH=/app/data_lake/export/marts  # dbt xuất marts ra đây
```

dbt không ghi vào Parquet — dbt đọc Parquet qua DuckDB filesystem extension và ghi vào DuckDB tables.

---

## Multi-Process & Recovery Semantics

### L12 — Cross-Platform File Locking cho Shared State

**Problem:** SharedCookieManager cần cho dlt, Dagster asset, ad-hoc script cùng đọc/write cookie file. Corruption → tất cả process lock out.

**Fix:** Lock file bằng OS primitive riêng mỗi platform.

```python
# src/utils/shared_cookie_manager.py
import os
if os.name == "nt":
    import msvcrt
    def _acquire_lock(fd):
        # Windows: non-blocking, retry 10 lần
        for _ in range(10):
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                return True
            except OSError:
                time.sleep(0.1)
        return False
else:
    import fcntl
    def _acquire_lock(fd):
        # Linux: non-blocking exclusive lock
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False
```

**Pattern áp dụng chung:** Bất kỳ shared file nào (cookies, state, cache) — dùng `msvcrt.locking` Windows / `fcntl.flock` Linux thay vì Python `threading.Lock` (chỉ in-process).

### L13 — Cookie TTL + In-Place Session Refresh

**Pattern:** Khi session expired giữa pipeline run (pipeline chạy > TTL), **refresh in-place** — không tạo session mới.

```python
def refresh_session(self, current_session: requests.Session):
    new_cookies = self._login_and_get_cookies()  # playwright login
    current_session.cookies.clear()
    current_session.cookies.update(new_cookies)
    # current_session object không đổi — caller code không cần re-bind
```

**Lý do:** Pipeline có thể đã bind `session` vào closures, iterators, connection pool. Tạo session mới → phải re-bind khắp nơi → dễ bug.

### L14 — Webhook ACK: At-Least-Once + Dedup as Safety Net

**Pattern:** Consumer đọc message từ queue (Cloudflare D1), ghi parquet, rồi **batch-ACK**. Nếu ACK fail, message vẫn trong queue → lần sau reprocess.

```python
# webhook_consumer.py
messages = client.poll_messages(limit=100)
envelopes = [build_envelope(m) for m in messages]
pipeline.run(envelopes)                    # 1. Write parquet (commit point)
client.batch_ack([m.id for m in messages])  # 2. ACK (best effort)
```

**Safety net:** dbt `src_` layer dedup by `entity_id` với ingest_method priority → duplicate messages không gây duplicate rows downstream.

**Anti-pattern:** ACK trước write → message loss nếu write fail. ACK sau write + có dedup → at-least-once mà không cần exactly-once infrastructure.

### L15 — Consumer Loop vs One-Off Mode

**Pattern:** Một codebase, hai execution modes via CLI flag.

```python
# run_webhook_consumer.py
def run(argv=None):
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--loop", action="store_true")
    args, _ = parser.parse_known_args(argv)

    if args.once:
        return run_once()              # Return info, raise on error → Dagster-friendly
    elif args.loop:
        while True:
            try:
                run_once()
                time.sleep(MIN_SLEEP_INTERVAL)
            except Exception as e:
                print(f"Error (swallow): {e}")
                time.sleep(backoff())  # Exponential 10-60s
```

**Dùng khi:**
- `--once`: Dagster asset (mỗi trigger 1 lần, fail nếu lỗi)
- `--loop`: Standalone dev mode hoặc systemd service (continuous polling)

Tránh duplicating code giữa Dagster integration và standalone runner.

### L16 — History Log URI Inference Mapping

**Pattern:** History log chứa events dạng `{subject_type, subject_id, occur_at}`. Để fetch full entity, map `subject_type → API endpoint template`.

```python
# history_log.py
URI_MAP = {
    "order":    "/admin/orders/{id}.json",
    "customer": "/admin/customers/{id}.json",
    "product":  "/admin/products/{id}.json",
}

def infer_uri(subject_type: str, subject_id: str) -> str:
    template = URI_MAP.get(subject_type)
    if not template:
        # Fallback: pluralize + convention
        template = f"/admin/{subject_type}s/{{id}}.json"
    return template.format(id=subject_id)
```

**Lý do dùng mapping table:** Một số entity type không follow convention (e.g., `inventory_item` → `/admin/inventory_items.json`). Hard-coded map an toàn hơn pluralize heuristic.

**Gap-fill pattern:** History log dùng để catch events mà batch/webhook bỏ sót. Mọi entity đều đi qua cùng pipeline → envelope schema thống nhất, dedup ở dbt.

---

## Operational Hardening (post-mortem 2026-04-08)

### L17 — Subprocess pipe deadlock từ `capture_output=True`

**Symptom:** Job hang vô hạn (16h+) ở asset gọi subprocess. Không có log, không có error.

**Root cause:** `subprocess.run(cmd, capture_output=True, check=True)` buffer stdout/stderr qua OS pipe (~64KB Linux/Windows). Khi child in nhiều log → pipe đầy → child block trên `print()` → parent block trên `check=True` chờ return → **classic deadlock, không có timeout cứu cánh**.

**Fix pattern:**

```python
proc = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,  # gộp 1 pipe → loại deadlock 2-pipe
    text=True,
    bufsize=1,                  # line-buffered
)
output_lines: list[str] = []
try:
    for line in proc.stdout:    # streaming read, không bao giờ đầy buffer
        line = line.rstrip()
        output_lines.append(line)
        context.log.info(line)  # log ngay, không dump cuối
    proc.wait(timeout=1800)     # HARD CAP — bắt buộc, không bỏ
except subprocess.TimeoutExpired:
    proc.kill(); proc.wait()
    raise Exception(f"Script timeout after 1800s")
if proc.returncode != 0:
    raise Exception(f"Script failed exit={proc.returncode}")
```

**Rules:**
1. **Không bao giờ** dùng `subprocess.run(capture_output=True)` cho command có thể in nhiều log
2. Luôn có `timeout=` parameter — không có cứu cánh = hang vô hạn
3. Gộp `stderr=STDOUT` thay vì 2 pipe riêng (đỡ deadlock)
4. Stream read line-by-line, log real-time vào Dagster context

Reference: `orchestration/assets/serving.py` post-fix.

### L18 — DuckDB read_only mode KHÔNG acquire file lock

**Misconception trước đó:** "Metabase JDBC giữ exclusive lock trên `olap.duckdb` → block writer". Sai.

**Thực tế đã verified empirically:**
- DuckDB driver mode `read_only=true` **không acquire bất kỳ file lock nào** — chỉ mmap để read
- Khác SQLite (dùng shared lock cho readers)
- Test: while Metabase up + giữ connection, Python `duckdb.connect(path)` (default RW) succeed trong 15ms
- 2 reader + 1 writer cùng một file = OK, không xung đột

**Hệ quả thiết kế:**
- Pipeline writer + Metabase reader có thể coexist trên cùng `olap.duckdb`
- Best-effort lock catch trong serving script là defensive only — trong production hiện tại có thể chưa bao giờ fire
- Pattern C (split bootstrap + runtime refresh) vẫn có giá trị, nhưng vì design cleanliness chứ không phải vì lock contention

**Cảnh báo:** Hypothesis về locking phải verify bằng test thực tế trước khi build plan lớn. "Catch + warning" trong code cũ không tự động chứng minh bug tồn tại — defensive code có thể không fire bao giờ.

### L19 — QueuedRunCoordinator KHÔNG ngăn được queue buildup

**Symptom:** Schedule tick mỗi 3 phút. Khi 1 run pending lâu, queue tích lũy unbounded — observed 28+ runs queued sau 1h20m.

**Misconception:** "QueuedRunCoordinator + tag_concurrency_limits sẽ tự handle mutual exclusion → schedule có thể tối giản."

**Thực tế:**
- `tag_concurrency_limits` chỉ giới hạn **dequeue throughput** — chỉ N runs với cùng tag được LAUNCH cùng lúc
- KHÔNG giới hạn **queue size** — schedule cứ tick là queue thêm
- Queue tích lũy nhanh khi có run hung hoặc slow

**Fix:** Vẫn cần self-overlap skip trong schedule body. Cross-job mutex giao cho coordinator (đơn giản hơn old priority chain), self-overlap giao cho schedule:

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

**Rule of thumb:**
- Cross-job mutex → coordinator tag (`concurrency_group: dbt_rw`)
- Self-overlap skip → schedule body check
- **Không bao giờ** rely solely on coordinator để chống queue accumulation

### L20 — Asset-level concurrency pool slot leak khi cancel runs

**Symptom:** Sau khi cancel runs, runs mới `STARTED` nhưng kẹt với "Step blocked by limit for pool duckdb_lock". Pool show `slot_count=1 active=1 pending=N` — slot bị hold bởi run đã CANCELED.

**Root cause:** Dagster `report_run_canceled()` **không tự release** asset-level concurrency pool slots (từ `op_tags={"dagster/concurrency_key": ...}`). Force-kill (container restart, OOM) cũng leak. Khác với tag-based run-level concurrency (coordinator handle release).

**Verify state:**

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

**Fix:** Free slot manually từ run đã terminal:

```python
els.free_concurrency_slots_for_run(ghost_run_id)
```

**Tự động hóa:** Helper script `scripts/maintenance/unstick_concurrency_pools.py` scan mọi pool, free slot từ run không còn active. Idempotent. Chạy sau bất kỳ incident nào có cancel/kill runs.

```bash
docker compose exec data_platform python scripts/maintenance/unstick_concurrency_pools.py
```

**Rule:** Sau mỗi container restart hoặc cancel batch, **luôn** chạy unstick script trước khi resume schedules.
