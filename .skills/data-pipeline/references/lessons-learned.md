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
.env.local (project root, gitignored, loaded bởi load_dlt_configuration())
       ↓
Environment variables (Docker via .env.docker, CI/CD, Dagster launch env)
```

Khi Dagster chạy: `.env.local` không tự load — phải gọi `load_dlt_configuration()` đầu mỗi asset.
`.env.local` nằm ở **project root** (không phải `ingestion/`).

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
if consecutive_old_items >= min_overlap_items:  # default 50 (see L57 — do NOT raise to 500)
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
    load_dlt_configuration(context.log.info)  # load .env.local (root) + secrets.toml
    os.chdir(DLT_DIR)
    run_entity.run(argv=[])
```
Hàm này trong `orchestration/assets/utils.py`. Dagster không tự load `.env.local`.
`.env.local` nằm ở project root — loader resolve từ `PROJECT_ROOT`.

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

> **Đã superseded bởi L24.** L16 mô tả URI_MAP đơn giản; L24 mô tả ENTITY_REGISTRY đầy đủ với 3 resolve strategies.

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
def pipeline_sapov2_realtime_schedule(context):
    active = _has_active_run(context, "pipeline_sapov2_realtime_job")
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

### L21 — Reactive sensor cho external source bằng content hash (không cần Drive API)

**Vấn đề:** Google Sheets do analyst nhập tay, vài lần/tuần. Muốn dashboard refresh ngay sau edit mà không cần analyst bấm "Launch run". Options:
- **Schedule định kỳ (5 min)**: 99% tick là no-op → lãng phí dbt cycle + log noise.
- **Apps Script `onEdit` webhook → Dagster**: real-time nhưng overkill (setup từng sheet, expose endpoint, auth, 2 sheets không đáng).
- **Drive API `files.get(modifiedTime)`**: cần service account / API key. **Cạm bẫy**: `modifiedTime` bump với mọi thao tác (format cell, sort, rename tab) → false positive trigger.
- **Content hash polling** ✅ (chọn cái này).

**Pattern:** Dagster `@sensor` poll public CSV export URL mỗi N phút, sha256 body, so với cursor:

```python
import hashlib, json, requests
from dagster import sensor, RunRequest, SkipReason, DefaultSensorStatus

SHEET_URLS = {"targets": "https://.../export?format=csv", "marketing_spend": "..."}

def _fetch_hash(url: str) -> str | None:
    try:
        r = requests.get(url, timeout=15, allow_redirects=True)
        r.raise_for_status()
        return hashlib.sha256(r.content).hexdigest()
    except Exception:
        return None

@sensor(
    job_name="ingest_sheets_sync_job",
    minimum_interval_seconds=300,
    default_status=DefaultSensorStatus.RUNNING,  # auto-on sau deploy
)
def ingest_sheets_modified_sensor(context):
    prev = json.loads(context.cursor) if context.cursor else {}
    current, errors = {}, []
    for name, url in SHEET_URLS.items():
        h = _fetch_hash(url)
        if h is None:
            errors.append(name)
            if name in prev:
                current[name] = prev[name]  # giữ hash cũ, đừng trigger false
            continue
        current[name] = h

    # Cold start: record baseline, không fire
    if not prev:
        context.update_cursor(json.dumps(current))
        return SkipReason(f"Cold start — baseline {sorted(current)}")

    changed = [k for k, v in current.items() if prev.get(k) != v]
    if not changed:
        return SkipReason("No changes")

    context.update_cursor(json.dumps(current))
    # run_key chứa hash → Dagster tự dedup nếu tick lại cùng hash
    return RunRequest(
        run_key="sheets-" + "-".join(f"{n}:{current[n][:12]}" for n in sorted(changed)),
        tags={"concurrency_group": "dbt_rw", "source": "ingest_sheets_modified_sensor"},
    )
```

**Điểm then chốt:**
- **Cold start phải skip, không fire** → tránh ngập runs khi deploy mới hoặc clear cursor.
- **Fetch error phải preserve cursor cũ** → error tạm thời không được gây false trigger khi endpoint recover.
- **`run_key` chứa hash** → Dagster dedup tự động, không cần logic phụ.
- **`default_status=RUNNING`** → sensor mới default STOPPED, phải set RUNNING không thì không tick.
- **Content hash > `modifiedTime`** → format-only edit không đổi byte exported CSV → không false positive.
- **Cost**: ~10KB × 2 sheets × 288 tick/day ≈ 5.7 MB/day — tiếng muỗi.

**Chi phí: 0 new dependency (chỉ cần `requests`), 0 new credential.**

### L22 — `AssetSelection.downstream()` cho cascade có chọn lọc

**Vấn đề:** Muốn khi sheets update → tự động rebuild dbt models phụ thuộc + refresh serving, nhưng **không** muốn rebuild toàn bộ dbt graph (hàng trăm models).

**Giải pháp:** Dagster `AssetSelection` hỗ trợ `.downstream()` để trace xuống asset graph — chỉ bao gồm descendants của selection gốc.

```python
# definitions.py
_sheets_sources = (
    AssetSelection.assets(sheets_assets.sheets_targets_asset)
    | AssetSelection.assets(sheets_assets.sheets_marketing_spend_asset)
)

ingest_sheets_sync_job = define_asset_job(
    name="ingest_sheets_sync_job",
    selection=(
        _sheets_sources
        | _sheets_sources.downstream()           # staging + marts phụ thuộc
        | AssetSelection.assets(serving.build_serving_db)  # refresh parquet rolling
    ),
    tags={"concurrency_group": "dbt_rw"},  # serialize với các dbt write khác
)
```

Kết quả resolve: **7 assets** (2 raw sheets + 2 staging + 2 facts + 1 serving_db) thay vì 400+ models.

**Kiểm tra selection đã resolve đúng:**

```python
from orchestration import definitions
d = definitions.defs
job = d.get_repository_def().get_job("ingest_sheets_sync_job")
for k in sorted(str(x) for x in job.asset_layer.executable_asset_keys):
    print(k)
```

**Rule:** Khi trigger job cho "source thay đổi" → luôn dùng `source | source.downstream()` để rebuild đúng những gì cần. Tránh full `all_dbt_assets` trừ nightly reconciliation.

### L23 — `DagsterRun` không có `start_time`, phải dùng `get_run_records()`

**Symptom:** Sensor code `inst.get_runs(filters=...)` rồi `run.start_time` raise `AttributeError: 'DagsterRun' object has no attribute 'start_time'`. Sensor daemon log spam errors mỗi tick, sensor **chưa bao giờ** fire được kể từ ngày viết.

**Root cause:** Dagster 1.x+ tách `DagsterRun` (core run metadata) khỏi `RunRecord` (record + timestamps). `start_time` / `end_time` / `create_timestamp` / `update_timestamp` chỉ có trên `RunRecord`.

**Fix:** Dùng `get_run_records()` thay vì `get_runs()`:

```python
# SAI
runs = inst.get_runs(filters=RunsFilter(statuses=[DagsterRunStatus.STARTED]))
for run in runs:
    if run.start_time:  # AttributeError
        ...

# ĐÚNG
records = inst.get_run_records(filters=RunsFilter(statuses=[DagsterRunStatus.STARTED]))
for rec in records:
    run = rec.dagster_run          # core metadata (run_id, job_name, status, tags)
    if rec.start_time:              # epoch seconds (float)
        age = datetime.now(timezone.utc) - datetime.fromtimestamp(rec.start_time, tz=timezone.utc)
```

**Lesson meta:** Sensor code phải được verify bằng **live tick** sau deploy — không chỉ dựa vào unit test. `health_alert_stuckrun_sensor` silent-fail trong cả tháng vì không ai check log sensor daemon. Sau khi fix, thêm vào checklist verify post-deploy:

```bash
docker logs data_platform 2>&1 | grep -iE "sensor" | grep -iE "error|traceback" | head
# Không có output = sensors healthy
```

---

## History Log & Web Scraping

### L24 — Entity Registry pattern cho history log URI resolution

**Supersedes L16.** Thay URI_MAP đơn giản bằng `ENTITY_REGISTRY` data-driven với 3 resolve strategies.

```python
# ingestion/src/sapo/history_log.py
ENTITY_REGISTRY: Dict[str, Dict[str, Any]] = {
    "order":            {"api_resource": "orders",          "table": "order"},
    "customer_address": {"api_resource": None, "table": "customer", "resolve": "parent",
                         "parent_uri_pattern": "/addresses.json",
                         "parent_uri_replace": ".json"},
    "fulfillment_print_forms": {"resolve": "skip"},
    # ... 18 types total
}
```

**3 resolve strategies:**
- **standard** (default): pluralize subject_type thành API resource path
- **parent**: extract parent ID từ log URI (e.g., `customer_address` → re-fetch `customer`)
- **skip**: low-value entity type, bỏ qua không fetch

**Tại sao:** Một số entity cần re-fetch parent (customer_address → customer), một số không có giá trị (fulfillment_print_forms). Registry xử lý tất cả các case một cách declarative thay vì conditional logic rải rác.

### L25 — KHÔNG BAO GIỜ dùng `refresh="drop_sources"` — xóa toàn bộ dataset

```python
# NGUY HIỂM — xóa TẤT CẢ tables trong dataset (kể cả pipeline khác)
info = pipeline.run(source, refresh="drop_sources")

# AN TOÀN — chỉ reset cursor, data được giữ lại, dedup ở dbt
source_args["full_refresh"] = True  # flag truyền vào source
# Trong source: last_value = None if full_refresh else first_timestamp.last_value
info = pipeline.run(source)  # không có refresh parameter
```

**Tại sao:** Tất cả pipeline đều ghi vào cùng dataset (sapo_raw). `drop_sources` xóa trắng toàn bộ. Pattern đúng là append-only ingestion + dbt dedup.

### L26 — Smart rate limiting cho cookie-based web scraping

```python
def _delay_with_jitter():
    jitter = random.uniform(0, request_delay * 0.3)
    time.sleep(request_delay + jitter)

def _handle_auth_response(response, session, context):
    if "/login" in response.url or response.status_code in (401, 403):
        client.refresh_session(session)
        return None  # signal retry
    if response.status_code == 429:
        time.sleep(int(response.headers.get("Retry-After", 30)))
        raise requests.RequestException("429")
    return response
```

**Pattern:** jitter ±30% để tránh request pattern đều đặn, phát hiện 429 với Retry-After, tự recovery khi auth redirect/401/403, retry riêng cho entity fetch (tenacity 2 attempts).  
**Tại sao:** Cookie-based scraping (không phải official API) — cần request pattern giống human, xử lý session expiry gracefully.

### L27 — Cookie TTL nên dài, dựa vào 401/403 để refresh on-demand

```python
# BAD — TTL 6h gây Playwright login thường xuyên không cần thiết
'cookie_ttl_hours': 6

# GOOD — 7 ngày, 401/403 trigger refresh khi cần
'cookie_ttl_hours': 168
```

**Tại sao:** Sapo session sống hàng tuần/tháng. TTL ngắn = Playwright login nhiều = chậm + dễ bị detect. TTL dài + on-demand refresh = login tối thiểu.

---

## Dedup & Incremental Correctness

### L28 — Dedup phải dùng `modified_on` của entity, KHÔNG phải `event_timestamp` của log

```sql
-- BAD: event_timestamp = thời điểm LOG ghi lại (hệ thống trung gian)
ORDER BY event_timestamp DESC, modified_on DESC

-- GOOD: modified_on = thời điểm ENTITY thực sự thay đổi (source of truth)
ORDER BY try_cast(modified_on AS TIMESTAMPTZ) DESC NULLS LAST,
         CASE ingest_method WHEN 'webhook' THEN 1 WHEN 'history_log' THEN 2 ELSE 3 END
```

**Tại sao:** History log re-fetch có thể tạo record với `event_timestamp` mới nhưng `modified_on` cũ. Dùng `event_timestamp` để dedup → dữ liệu stale ghi đè dữ liệu mới.

### L29 — Incremental filter: dùng `_dlt_load_id`, KHÔNG phải `event_timestamp`

```sql
-- BAD: bỏ sót late-arriving data có event_timestamp cũ
WHERE event_timestamp > (SELECT MAX(event_timestamp) - INTERVAL 7 DAY FROM {{ this }})

-- GOOD: _dlt_load_id tăng đơn điệu theo từng load, catch tất cả data mới
WHERE _dlt_load_id > (SELECT COALESCE(MAX(_dlt_load_id), '') FROM {{ this }})
```

**Tại sao:** Full-refresh history_log tạo record với `event_timestamp` cũ nhưng `_dlt_load_id` mới. Filter theo `event_timestamp` bỏ sót chúng. `_dlt_load_id` là string sortable theo thứ tự thời gian (dlt format: `{timestamp}.{sequence}`).

### L31 — DuckDB incremental schema migration: 3 bẫy khi thêm column mới

**Symptom:** Thêm `_dlt_load_id` vào extracted CTE của src_ model → 3 lỗi cascade:
1. `Binder Error: WHERE clause cannot contain aggregates!` — DuckDB reject `MAX()` inside WHERE subquery trên `read_parquet()` source
2. `Binder Error: Referenced column "_dlt_load_id" not found` — table materialized trước khi column tồn tại
3. `Binder Error: Set operations can only apply to expressions with the same number of result columns` — UNION ALL giữa extracted (có column mới) và `{{ this }}` (chưa có)

**Fix pattern — self-healing migration:**

```sql
{{ config(
    on_schema_change='append_new_columns',  -- (1) dbt tự thêm column mới vào table
) }}

-- (2) Check column tồn tại ở compile-time
{% set existing_cols = (adapter.get_columns_in_relation(this) | map(attribute='name') | list) if is_incremental() else [] %}

WITH
{% if is_incremental() %}
_cursor AS (
    {% if '_dlt_load_id' in existing_cols %}
    SELECT COALESCE(MAX(_dlt_load_id), '') AS max_load_id FROM {{ this }}
    {% else %}
    SELECT '' AS max_load_id  -- fallback: reprocess all (one-time full refresh)
    {% endif %}
),
{% endif %}
raw_data AS (
    ...
    {% if is_incremental() %}
    WHERE _dlt_load_id > (SELECT max_load_id FROM _cursor)  -- (3) no aggregate in WHERE
    {% endif %}
),
...
-- (4) Guard UNION ALL against column mismatch
{% if is_incremental() and '_dlt_load_id' in existing_cols %}
UNION ALL
SELECT existing.* FROM {{ this }} existing ...
{% endif %}
```

**Self-heal sequence:**
- Run 1: column missing → cursor='' (process all) + skip UNION ALL → `on_schema_change` adds column
- Run 2+: column exists → normal incremental with UNION ALL

**Tại sao không `--full-refresh`:** Requires manual intervention. Self-healing migration = zero-touch, model tự recover sau 1 run.

### L30 — Compare-before-overwrite cho incremental dedup

```sql
-- Khi data mới đến cho entity đã tồn tại, so sánh trước khi thay thế
SELECT * FROM (
    SELECT * FROM new_extracted
    {% if is_incremental() %}
    UNION ALL
    SELECT existing.* FROM {{ this }} existing
    INNER JOIN (SELECT DISTINCT pk FROM new_extracted) k ON existing.pk = k.pk
    {% endif %}
)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY pk
    ORDER BY try_cast(modified_on AS TIMESTAMPTZ) DESC NULLS LAST,
             CASE ingest_method WHEN 'webhook' THEN 1 WHEN 'history_log' THEN 2 ELSE 3 END
) = 1
```

**Tại sao:** dbt `delete+insert` thay thế unconditionally. Nếu late-arriving data có `modified_on` cũ hơn row đang có, nó sẽ overwrite dữ liệu mới hơn. Union + re-dedup đảm bảo chỉ data thực sự mới hơn mới thắng.

---

## Full-Refresh vs Nightly Incremental

### L32 — Nightly incremental vs manual full-refresh — separate jobs, shared cursor

**Nguồn gốc:** Sau incident L25 (`drop_sources` xóa data), `--full-refresh` được làm safe (chỉ reset cursor, không drop data). Tiếp theo phát hiện batch source functions (orders, customers, accounts, products) không wire `full_refresh` param xuống resource — flag bị silently ignored. Fix: thêm `full_refresh` param vào tất cả batch source+resource functions (pattern giống `history_log` đã có sẵn).

**Anti-pattern (đã mắc phải):** Gắn tag `full_refresh=true` vào nightly schedule → full-refresh **mỗi đêm** — lãng phí, scan toàn bộ API không cần thiết.

**Pattern đúng: 2 jobs riêng biệt, shared cursor**

```python
# Job 1: Nightly — incremental từ cursor cuối cùng
pipeline_batch_nightly_job = define_asset_job(
    name="pipeline_batch_nightly_job",
    selection=...,
    # KHÔNG có full_refresh tag — chạy incremental bình thường
    tags={"concurrency_group": "dbt_rw"},
)

# Job 2: Manual full-refresh — launch thủ công khi cần reload lại toàn bộ
pipeline_batch_fullrefresh_job = define_asset_job(
    name="pipeline_batch_fullrefresh_job",
    selection=...,
    tags={
        "concurrency_group": "dbt_rw",
        "full_refresh": "true",  # baked vào job definition — không cần truyền lúc launch
    },
)
```

**Asset check tag:**

```python
@asset(...)
def ingest_sapov2_orders_batch_asset(context):
    full_refresh = context.run.tags.get("full_refresh") == "true"
    argv = ["--full-refresh"] if full_refresh else []
    run_orders_batch.run(argv=argv)
```

**Cursor continuity:**
```
full_refresh run:
  last_value = None  → scan toàn bộ API
  dlt load xong     → dlt cập nhật cursor = latest timestamp

nightly run sau đó:
  last_value = cursor từ full_refresh run → chỉ scan data mới
```

Cả hai job dùng cùng `pipeline_name` → share cùng dlt state file → cursor liên tục giữa full-refresh và incremental.

**Khi nào dùng `pipeline_batch_fullrefresh_job`:**
- Lần đầu bootstrap data
- Phát hiện data bị thiếu / corrupt
- Sau khi thêm field mới vào source cần backfill

**Rule:** Nightly job = incremental từ cursor. Full-refresh = manual, one-click, separate job definition.

### L33 — dlt incremental có 2 lớp filter — phải reset CẢ HAI khi full-refresh

**Symptom:** `--full-refresh` chạy nhưng kết thúc nhanh bất thường (vài phút thay vì cả ngày). Log show "0 new records" dù `last_value = None` đã pass tất cả items qua manual check.

**Root cause:** `dlt.sources.incremental` có **2 lớp filter song song**:

| Lớp | Vị trí | Cơ chế |
|-----|--------|--------|
| **Manual** | Resource function code | `if last_value is None or ts > last_value` — do dev kiểm soát |
| **dlt internal** | `dlt.sources.incremental` transform | Tự động drop items có cursor value `<=` stored `last_value` trong `.dlt/pipelines/{name}/state.json` |

Khi chỉ set `last_value = None` trong code (lớp 1), items pass manual check → yield → nhưng dlt transform (lớp 2) vẫn drop chúng vì state.json giữ cursor cũ.

**Fix: xóa pipeline state directory TRƯỚC khi khởi tạo pipeline:**

```python
# pipeline_runner.py
if args.full_refresh:
    import shutil
    state_dir = os.path.join(".dlt", "pipelines", pipeline_name)
    if os.path.exists(state_dir):
        shutil.rmtree(state_dir)
        print(f"[Pipeline Runner] --full-refresh: reset pipeline state ({state_dir})")
    source_args["full_refresh"] = True

# Pipeline init SAU khi xóa state → fresh state, no stored cursor
pipeline = dlt.pipeline(pipeline_name=..., destination="filesystem", ...)
```

**An toàn vì:**
- Data sống ở `data_lake/` (DESTINATION__FILESYSTEM__BUCKET_URL) — path riêng
- `.dlt/pipelines/{name}/` chỉ chứa state, schema, normalize info — KHÔNG chứa data
- `shutil.rmtree` xóa state → `dlt.pipeline()` tạo lại fresh → `first_timestamp.last_value = None` → dlt internal filter cũng disabled
- Data append-only, dedup ở dbt — safe

**KHÔNG dùng `pipeline.drop()`** — method này gọi thêm `destination.drop_storage()` có thể xóa data trên destination.

**Rule:** Khi implement `--full-refresh` cho dlt pipeline, phải reset cả 2 lớp: (1) `last_value = None` trong resource code, (2) xóa `.dlt/pipelines/{name}/` để reset dlt internal state. Chỉ set flag mà không xóa state = full-refresh bị silently ignored.

---

### L35 — Config ecosystem: layered defaults, single .env, no duplication

**Nguyên tắc cốt lõi:**

| Layer | Chứa gì | Ví dụ |
|-------|---------|-------|
| `config.toml` | Defaults ít thay đổi, không phụ thuộc environment | layout, format, selectors, delays, file patterns |
| `.env` | Credentials + bất cứ gì khác nhau giữa local/docker | passwords, API keys, paths, URLs |
| `docker-compose environment:` | Container constants gắn chặt volume mount/infra | BACKUP_ROOT, telemetry flags |
| `Dockerfile ENV` | Build-time immutable | DAGSTER_HOME, PYTHONPATH |

**Không lặp lại** — nếu `config.toml` đã có `loader_file_format = "parquet"`, `.env` không set lại. Nhưng `.env.example` **liệt kê commented-out** để operator biết có thể override.

**File locations:**
- `.env.docker` — Docker runtime (project root, gitignored)
- `.env.local` — Local dev (project root, gitignored)
- `.env.example` — Template (committed, sections + documented defaults)
- `config.toml` — dlt defaults (committed, `ingestion/.dlt/`)

**Loader** (`load_dlt_configuration()` trong `utils.py`):
- Docker: `.env.docker` đã inject qua `env_file:` → loader chỉ verify credentials
- Local dev: loader parse `.env.local` (project root) + `secrets.toml` → `os.environ`

**Path consistency:** Config files mount vào Docker tại **cùng relative path** với host (project root). `backup.sh` (Docker) và `backup.ps1` (Windows) dùng cùng logic `${PROJECT_ROOT}/${filename}`. Không mount vào subfolder riêng — tránh path khác nhau giữa 2 môi trường.

**docker-compose `environment:`:** Chỉ chứa vars gắn chặt volume mount (ví dụ `BACKUP_ROOT=/app/backups` ph���i match `./app_data/backups:/app/backups`). Nếu var có thể thay đổi độc lập → thuộc `.env`.

**Xem:** `docs/config-guide.md` cho chi tiết đầy đủ.

---

## Health Monitoring

### L36 — Runner entry point PHẢI `return run_pipeline(...)` — không return = silent "skipped"

**Symptom:** Ingestion Health Monitor dashboard trống — tất cả batch asset hiển thị "skipped" dù pipeline thực tế chạy thành công, data ghi đúng vào data lake.

**Root cause:** 5 file `run_*_batch.py` gọi `run_pipeline(...)` nhưng **thiếu `return`**. Dagster asset nhận `None` thay vì `LoadInfo`:

```python
# SAI — run_pipeline() trả LoadInfo nhưng run() trả None
def run(argv=None):
    run_pipeline(pipeline_name=..., ...)

# ĐÚNG
def run(argv=None):
    return run_pipeline(pipeline_name=..., ...)
```

**Chuỗi hậu quả:**
```
run() returns None
→ load_info.asdict() if hasattr(load_info, "asdict") else {} → {}
→ extract_loaded_packages({}) → []
→ status = "success" if loaded_packages else "skipped" → "skipped"
→ _record_health(status="skipped") → dashboard shows blank
```

**Detection:** Query `ingestion_runs` table:
```sql
SELECT asset_key, status, metadata_json::VARCHAR
FROM ingestion_runs WHERE asset_key LIKE 'sapo/%'
```
Nếu `load_info = {}` trong metadata_json → runner thiếu `return`.

**Rule:** Mọi runner entry point `run()` **PHẢI** `return run_pipeline(...)`. Template `run-entry-point-template.py` đã có sẵn `return` — đối chiếu khi tạo runner mới.

### L37 — Dashboard SQL phải handle "asset chưa từng chạy" — không dùng cross join

**Symptom:** Scalar card hiển thị blank khi asset chưa có bất kỳ run nào (không phải NULL mà là 0 rows).

**Root cause:** CTE pattern `FROM last_ok lo, last_run lr` là implicit CROSS JOIN. Khi `last_run` trả 0 rows (asset chưa run), cross join cũng trả 0 rows → Metabase scalar hiển thị blank.

**Fix:** Dùng scalar subqueries (luôn trả đúng 1 row):

```sql
SELECT
    COALESCE(ROUND(date_diff('hour',
        (SELECT MAX(run_ended_at) FROM ingestion_runs
         WHERE asset_key = '{key}' AND status IN ('success', 'partial')),
        now()), 1), 9999) AS "Giờ từ lần chạy OK",
    COALESCE(
        (SELECT rows_written FROM ingestion_runs
         WHERE asset_key = '{key}' ORDER BY run_started_at DESC LIMIT 1),
        0) AS "Rows Written"
```

**Rule:** Dashboard monitoring SQL phải handle 3 states: (1) asset có success run, (2) asset chỉ có skipped/failed, (3) asset chưa từng chạy. Sentinel values (9999h, 999%) trigger conditional formatting red → operator biết ngay.

---

## Auto-Recovery & Self-Healing

### L38 — Activity-based stuck detection vs fixed timeout

**Symptom:** Job STARTED 1h+ nhưng không fail/complete. Fixed timeout (e.g., 30 min) có thể false-positive trên nightly batch.

**Root cause:** dbt subprocess hang (e.g., dbt-duckdb rollback bug, deadlock, network stall). Process vẫn sống nhưng không produce output.

**Activity-based approach (đã implement):**
- Run đang chạy **phải** có log activity (stdout/stderr) mỗi vài giây
- Nếu không có output > `INACTIVITY_THRESHOLD` (5 min) = stuck
- Threshold nhỏ hơn nhiều so với runtime timeout → catch hang sớm

```python
# orchestration/sensors/stuck_run_alerter.py
INACTIVITY_THRESHOLD = timedelta(minutes=5)   # no log activity
MIN_RUNTIME_BEFORE_KILL = timedelta(minutes=10)  # grace period cho init

def _get_last_event_time(context, run_id) -> datetime | None:
    records = context.instance.get_event_records(EventRecordsFilter(), limit=100)
    for rec in records:
        if rec.dagster_run and rec.dagster_run.run_id == run_id:
            return datetime.fromtimestamp(rec.timestamp, tz=timezone.utc)
    return None
```

**Auto-terminate pattern:**
```python
# 1. Try graceful cancel
instance.report_run_canceled(run)

# 2. Force fail if still not terminal
if updated_run.status not in TERMINAL_STATUSES:
    instance.report_run_failed(run, "Auto-terminated: no activity for X minutes")

# 3. Free concurrency slots (critical — không free = pool leak)
instance.event_log_storage.free_concurrency_slots_for_run(run.run_id)

# 4. Alert
send_lark_card(...)
```

**Tại sao activity-based > fixed timeout:**
- Nightly batch có thể chạy 2h+ legitimately (continuous log output)
- Hung process im lặng trong vài phút → stuck signal rõ ràng
- False positive gần như zero nếu pipeline code in log thường xuyên

**Reference:** `orchestration/sensors/stuck_run_alerter.py`

### L39 — Concurrency pool janitor auto-cleanup

**Symptom:** Sau container restart/crash, run mới "Step blocked by limit for pool duckdb_lock" dù không có run nào active.

**Root cause:** Asset-level concurrency pool (`op_tags={"dagster/concurrency_key": ...}`) leak slot khi:
- Container restart/OOM kill
- `report_run_canceled()` call
- Force terminate

Dagster **không auto-release** pool slots — khác với run-level tag concurrency.

**Auto-cleanup sensor (đã implement):**

```python
# orchestration/sensors/concurrency_pool_janitor.py
@sensor(minimum_interval_seconds=300)  # every 5 min
def health_concurrency_pool_janitor(context):
    els = context.instance.event_log_storage
    for key in els.get_concurrency_keys():
        info = els.get_concurrency_info(key)
        for run_id in info.active_run_ids | info.pending_run_ids:
            run = context.instance.get_run_by_id(run_id)
            if run is None or run.status not in ACTIVE_STATUSES:
                els.free_concurrency_slots_for_run(run_id)
                logger.info("Freed leaked slot in pool '%s' from run %s", key, run_id[:8])
```

**Layered defense:**
1. **Boot-time:** `docker-compose.yml` command runs `unstick_concurrency_pools.py || true` trước `dagster dev`
2. **Runtime:** Janitor sensor chạy mỗi 5 min, cleanup bất kỳ leak nào phát sinh sau boot
3. **Stuck-run:** Auto-termination sensor free slot sau khi kill stuck run

**Tại sao runtime cleanup cần thiết:**
- Boot cleanup chỉ fire 1 lần
- Leak có thể xảy ra giữa runtime (cancel run, container partial restart)
- 5-min polling ít overhead, catch leak trước khi gây block chain

**Reference:** `orchestration/sensors/concurrency_pool_janitor.py`

### L40 — Health checks phải mutual-exclude với ingestion/dbt jobs

**Symptom:** Health checks job (dbt tests, asset checks) block ingestion/nightly batch > 55 min. Hoặc ngược lại: ingestion chạy dài, health checks queue tích lũy.

**Root cause:**
- `AssetSelection.all_asset_checks()` include dbt tests thông qua dagster-dbt integration
- dbt tests require `duckdb_lock` → compete với ingestion/nightly
- Health checks schedule `0 */2` collide với ingestion schedules

**Fix 3 layers:**

**1. Exclude dbt tests từ health checks job:**
```python
health_checks_asset_job = define_asset_job(
    name="health_checks_asset_job",
    selection=(
        AssetSelection.all_asset_checks()
        - AssetSelection.checks_for_assets(dbt.sapo_dbt_assets)  # exclude dbt tests
    ),
    executor_def=in_process_executor,  # no subprocess overhead for small checks
)
```

**2. Mutual exclusion check trong schedule:**
```python
def _has_active_ingestion(context) -> str | None:
    for job_name in [
        "pipeline_sapov2_realtime_job", "pipeline_sapov2_incremental_job",
        "pipeline_batch_nightly_job", "ingest_sheets_sync_job",
    ]:
        runs = context.instance.get_runs(
            filters=RunsFilter(job_name=job_name, statuses=_ACTIVE_STATUSES), limit=1
        )
        if runs:
            return runs[0].run_id
    return None

@schedule(cron_schedule="5 */2 * * *", ...)  # offset :05 để tránh collision
def health_checks_schedule(context):
    if active := _has_active_ingestion(context):
        return SkipReason(f"Ingestion/transform active ({active[:8]}), skipping health checks")
    return RunRequest(run_key=None)
```

**3. Schedule offset:** `5 */2` thay vì `0 */2` → không trigger cùng lúc với ingestion schedules.

**Priority hierarchy:**
```
Ingestion/Transform jobs > Health checks

Ingestion đang chạy → Health checks skip (sẽ retry 2h sau)
Health checks đang chạy → Ingestion vẫn queue (coordinator enforce duckdb_lock)
```

**Tại sao asymmetric:**
- Ingestion = business-critical, data freshness
- Health checks = monitoring, có thể delay vài giờ không sao
- Better to have stale health metrics than stale business data

**Reference:** `orchestration/definitions.py` — `health_checks_asset_job`, `health_checks_schedule`

### L41 — Health recording: datetime serialization và rows_written semantics

**Symptom:** Morning digest hiển thị "0 items" cho tất cả sources dù data có đồng bộ. Logs show `ingestion_health record_run failed: Object of type DateTime is not JSON serializable`.

**Root cause 1 — DateTime serialization:**
DLT `LoadInfo.asdict()` trả về objects pendulum/datetime trong metadata dict. `json.dumps(metadata)` fail vì standard encoder không handle datetime.

```python
# SAI — fail với pendulum DateTime
json.dumps(metadata)

# ĐÚNG — custom encoder handle datetime
class _DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "isoformat"):  # pendulum DateTime
            return obj.isoformat()
        if hasattr(obj, "total_seconds"):  # pendulum Duration
            return obj.total_seconds()
        return super().default(obj)

json.dumps(metadata, cls=_DateTimeEncoder)
```

**Root cause 2 — rows_written = None thay vì 0:**

```python
# SAI — empty packages trả None (unknown)
if not load_packages:
    return None  # downstream code coi là unknown, không tính vào SUM

# ĐÚNG — empty packages = 0 rows written (explicit)
if not load_packages:
    return 0  # DLT ran, no data to load → 0 rows written
```

**Hệ quả downstream:**
```sql
-- SUM(NULL) = NULL, SUM(0) = 0
-- Với rows_written = NULL cho mọi run → digest shows "0 items"
SUM(rows_written) FILTER (WHERE run_started_at >= now() - INTERVAL 1 DAY) AS r_24h
```

**Fix locations:**
1. `orchestration/ops/ingestion_health.py` — thêm `_DateTimeEncoder`, dùng trong `json.dumps()`
2. `orchestration/ops/dlt_metrics.py` — `extract_rows_written()` return 0 cho empty packages

**Verification query:**
```sql
-- Before fix: with_rows = 0, null_rows = N
-- After fix:  with_rows = N, null_rows = 0
SELECT 
    CASE WHEN run_started_at < '2026-04-18 16:27:00+07' THEN 'before' ELSE 'after' END as period,
    COUNT(*) as runs,
    COUNT(rows_written) as with_rows,
    COUNT(*) - COUNT(rows_written) as null_rows
FROM ingestion_runs 
WHERE run_started_at >= '2026-04-18 15:00:00+07'
GROUP BY 1
```

**Rule:** 
1. Mọi JSON serialization của DLT metadata **phải** dùng custom encoder handle datetime/pendulum
2. `rows_written` semantics: `0` = DLT ran, no data; `None` = truly unknown (không có DLT response)
3. Downstream code dùng `COALESCE(rows_written, 0)` để handle cả hai case

**Reference:** `orchestration/ops/ingestion_health.py`, `orchestration/ops/dlt_metrics.py`

---

## Stuck Run Prevention (post-mortem 2026-04-24)

### L45 — dbt subprocess timeout watchdog — prevent infinite hang

**Symptom:** `pipeline_sapov2_realtime_job` stuck 14+ min with 14 min inactive. Multiple runs stuck in single day. Jobs auto-terminated by stuck alerter but pattern keeps recurring.

**Root cause:** `dbt.cli(["build"]).stream()` at `orchestration/assets/dbt.py:136` had **no timeout**. When dbt subprocess enters DuckDB WAL checkpoint hang (I/O pressure from concurrent backup or Metabase reads), the `stream()` generator blocks indefinitely — stdout stalls, Dagster blocks waiting for next line.

**Evidence chain:**
- 3 stuck runs on 2026-04-23 (05:01, 09:25, 10:25 ICT) — all during morning hours when Metabase usage starts
- Stdout stopped at different model counts (24→69→73/73) — suggesting I/O resource pressure increasing
- Run #3 stuck at model 73/73 = dbt finished SQL execution but DuckDB connection close (WAL checkpoint) hung

**Fix: Watchdog timer with hard timeout**

```python
# orchestration/assets/dbt.py
import threading

DBT_TIMEOUT_SEC = int(os.environ.get("DBT_TIMEOUT_SEC", "900"))  # 15 min

@dbt_assets(...)
def sapo_dbt_assets(context, dbt: DbtCliResource):
    invocation = dbt.cli(["build"], context=context)

    def _kill_on_timeout():
        context.log.error(f"dbt subprocess exceeded {DBT_TIMEOUT_SEC}s — killing")
        try:
            invocation.process.kill()
        except Exception as e:
            context.log.warning(f"Failed to kill dbt subprocess: {e}")

    watchdog = threading.Timer(DBT_TIMEOUT_SEC, _kill_on_timeout)
    watchdog.daemon = True
    watchdog.start()
    try:
        yield from invocation.stream()
    finally:
        watchdog.cancel()
```

**Why 15 min:** Normal runs complete in <2 min. 15 min is generous safety margin that catches true hangs without false-positives on slow but legitimate runs.

**Configurable:** `DBT_TIMEOUT_SEC` env var allows tuning per environment.

### L46 — stuck_run_alerter must kill actual subprocess, not just Dagster state

**Problem:** `stuck_run_alerter.py` used `instance.report_run_canceled()` which only updates Dagster's SQLite state — it does NOT send SIGTERM/SIGKILL to the running subprocess. The dbt process survives "cancellation", continues holding DuckDB file handles, and can cause next run to also hang.

**Evidence:** After stuck alerter "killed" run, the next run that acquired `duckdb_lock` also hung at similar point — suggesting DuckDB was in inconsistent state from prior zombie process.

**Fix: Use psutil to kill process tree**

```python
# orchestration/sensors/stuck_run_alerter.py
import psutil

def _terminate_subprocess_tree(run_id: str) -> bool:
    """Kill subprocess tree associated with Dagster run."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'environ']):
        cmdline = " ".join(proc.info.get('cmdline') or [])
        if run_id[:12] in cmdline:
            parent = psutil.Process(proc.pid)
            children = parent.children(recursive=True)
            for child in children:
                child.terminate()
            parent.terminate()
            # Force kill survivors after 3s
            gone, alive = psutil.wait_procs(children + [parent], timeout=3)
            for p in alive:
                p.kill()
            return True
    return False

# In sensor, after state update:
subprocess_killed = _terminate_subprocess_tree(run.run_id)
```

**Dependency:** Requires `psutil` in container. Add to `ingestion/requirements.txt`, rebuild image.

**Graceful degradation:** If psutil unavailable, falls back to state-only update (still better than nothing).

### L47 — Backup job must acquire duckdb_lock to prevent I/O collision

**Problem:** `maintain_backup_platform_job` runs `cp -a` on DuckDB files while dbt is actively writing. The I/O pressure from sequential kernel read during backup causes DuckDB WAL checkpoint to stall (uninterruptible I/O sleep).

**Timeline correlation:** First stuck run on 2026-04-23 started at 05:01 ICT, backup job started at 06:01 ICT — backup ran while dbt was in progress.

**Fix: Add concurrency tag to backup op**

```python
# orchestration/ops/system_backup.py
@op(
    description="Run platform hot backup",
    tags={
        "kind": "maintenance",
        "dagster/concurrency_key": "duckdb_lock",  # Wait for dbt to finish
    },
)
def run_platform_backup(context):
    ...
```

**Effect:** Backup waits in queue until any dbt/ingestion job holding `duckdb_lock` completes. No I/O collision during WAL checkpoint.

**Trade-off:** Backup may be delayed up to 15 min (dbt timeout) if it fires during dbt run. Acceptable since backup is maintenance, not business-critical.

### L48 — Zombie NOT_STARTED runs block schedules indefinitely

**Symptom:** All scheduled jobs show "skipping: previous run still active" but no run is actually running. Health report shows 9/10 assets overdue.

**Root cause:** Container restart at 22:29 UTC left a `NOT_STARTED` run (`773eefde`) in Dagster's SQLite. This run was enqueued just before restart but never executed. After restart, Dagster loaded DB state and found the run still `NOT_STARTED`. Every schedule tick checks `_has_active_run()` which includes `NOT_STARTED` status → always finds this zombie → skips.

**Why NOT_STARTED is "active":**
```python
_ACTIVE_STATUSES = [
    DagsterRunStatus.QUEUED,
    DagsterRunStatus.NOT_STARTED,  # ← zombie lives here
    DagsterRunStatus.STARTING,
    DagsterRunStatus.STARTED,
]
```

`NOT_STARTED` is legitimately active during normal operation (run created, waiting for executor). But after container restart, a pre-restart `NOT_STARTED` run will never execute — it's zombie.

**Fix: Cancel zombie runs manually**
```bash
docker exec data_platform python3 -c "
from dagster import DagsterInstance
instance = DagsterInstance.get()
run = instance.get_run_by_id('773eefde-...')
instance.report_run_canceled(run)
"
```

**Prevention: Boot-time cleanup**

Add to `unstick_concurrency_pools.py` or separate boot script:

```python
# Cancel NOT_STARTED runs older than 30 min (zombie detection)
from datetime import datetime, timedelta, timezone
cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)

for rec in instance.get_run_records(filters=RunsFilter(statuses=[DagsterRunStatus.NOT_STARTED])):
    if rec.create_timestamp and datetime.fromtimestamp(rec.create_timestamp, tz=timezone.utc) < cutoff:
        instance.report_run_canceled(rec.dagster_run)
        logger.info(f"Canceled zombie NOT_STARTED run {rec.dagster_run.run_id[:8]}")
```

**Also update stuck_run_alerter:** Current sensor only checks `STARTED` runs. Should also check `NOT_STARTED` runs older than threshold.

**Reference:** `plans/reports/fix-260424-0810-realtime-job-stuck-prevention.md`

---

## Ingestion Health Digest (post-mortems 2026-04-22)

Reusable pattern doc: [`ingestion-health-digest.md`](ingestion-health-digest.md).

### L42 — dlt LoadInfo does NOT expose row counts for filesystem destinations

**Context:** `extract_rows_written(info_dict)` walked `load_packages[].jobs[].metrics.items_count` and persisted the result to `ingestion_runs.rows_written`. For ~6 weeks the health digest reported `"Batch hôm qua: không có đơn mới"` for Sapo orders while the actual parquet files had thousands of rows. Stakeholders escalated because the digest had lost credibility.

**Root cause:** current dlt + filesystem destination (plain parquet AND Delta Lake) does not populate `items_count` or `row_count` in either `load_packages[].jobs[].metrics` or top-level `job_metrics[]`. Each job record only carries `file_path`, `file_size`, `table_name`, `file_id`. The metric walk always returned `matched=False` → function returned `0`.

**Symptoms that should have triggered earlier investigation:**
- Every batch asset shows `rows_written=0` regardless of source state.
- Recon drift (-1%, -5%) shows source-vs-warehouse mismatch growing over time.
- `file_size` in the dlt metadata grows daily but `rows_written` stays 0.

**Fix:** 3-layer fallback in `extract_rows_written`:

1. **Metric walk** — future-proof for dlt versions that DO populate `items_count`.
2. **`file_id` glob** — fast path for plain-parquet destinations where filename = `{file_id}.parquet`. DuckDB `COUNT(*)` on parquet reads the footer only (~ms per file).
3. **`_dlt_load_id` scan** — Delta Lake rewrites file names (`part-00000-{uuid}-c000.snappy.parquet`) so `file_id` doesn't match on disk. Every dlt row still carries `_dlt_load_id`, so we glob all parquets under `{dataset}/{table}/` and `WHERE _dlt_load_id IN (loads_ids)`.

**Rule:**
1. Never trust `items_count` from dlt metadata — always have a fallback.
2. If your serving layer is parquet or Delta, `_dlt_load_id` filter is the canonical way to derive accurate row counts.
3. Monitor the ratio of `rows_written=0` runs per asset. Persistent zeros = extractor bug, NOT source silence.

**Reference:** `orchestration/ops/dlt_metrics.py`, `ingestion-health-digest.md` → "Row count extraction"

---

### L43 — Digest window must be business-TZ calendar day, not rolling 24h

**Context:** The digest fired at 08:00 ICT with SQL `WHERE run_started_at >= now() - INTERVAL 1 DAY`. Stakeholder complained: "bạn báo không có đơn hôm nay, nhưng tôi thấy đơn hôm qua rõ ràng được cập nhật." The label said "Batch hôm nay" (today) — but the rolling window covered 08:00 yesterday → 08:00 today, straddling two business days.

**Root cause:** rolling-24h semantics != "yesterday" semantics. At 08:00 the window misses the day's last 16 hours of yesterday's data and includes the first 8 of today. The label "Batch hôm nay" was plain wrong — people read "hôm qua" / "yesterday" as a complete calendar day in their business TZ.

**Fix:** anchor on business-TZ calendar day. Schedule fires at 06:00 local time AFTER overnight recon/KPI finish, so the digest describes the full previous day:

```sql
WHERE (run_started_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::DATE
    = ((now()          AT TIME ZONE 'Asia/Ho_Chi_Minh')::DATE - 1)
```

DuckDB ICU extension is auto-loaded and supports named IANA timezones. `AT TIME ZONE` applied to TIMESTAMPTZ returns wall-clock TIMESTAMP in that TZ; cast to DATE for calendar day. `DATE - 1` returns yesterday as DATE.

Labels also updated: "Batch hôm nay" → "Batch hôm qua", "X lần/24h" → "X lần hôm qua".

**Rule:**
1. Freshness (`last_ok` age) stays absolute — no window.
2. Volume/count metrics window by **calendar day in business TZ**, not rolling.
3. Schedule after all overnight jobs complete: recon → KPI closure → digest.
4. Labels must match the window semantics. "Today" when you report yesterday's data is worse than "no digest at all".

**Reference:** `orchestration/ops/morning_digest.py` → `_MAIN_QUERY`, `orchestration/definitions.py` → `health_report_digest_schedule`

---

### L44 — `ingestion_runs` composite PK: always filter BOTH asset_key AND run_id

**Context:** Wrote a backfill script to replay historical `load_info` through the fixed `extract_rows_written`. Used `UPDATE ingestion_runs SET rows_written = ? WHERE run_id = ?`. Script ran against 2899 rows, reported "175 updated". Minutes later discovered that shopee/misa/accounts/products/sheets all showed identical row counts to sapo_orders_batch for the same date. Data was corrupted across 182 rows. Had to restore from the daily backup at `app_data/backups/20260422-060050/…/ingestion_health.duckdb`.

**Root cause:** `ingestion_runs` PK is composite `(asset_key, run_id)`. Dagster fans out one `run_id` across every asset in the same scheduled job — the 03:00 daily batch writes 7 rows (orders + customers + products + accounts + shopee + misa + sheets), all sharing the same `run_id`, distinguished ONLY by `asset_key`. The UPDATE matched all 7 and overwrote siblings with the orders count.

**Fix:** every DML against the table MUST filter on BOTH columns:

```sql
-- ✅ Correct
UPDATE ingestion_runs SET rows_written = ?
WHERE asset_key = ? AND run_id = ?;

-- ❌ Silent data corruption
UPDATE ingestion_runs SET rows_written = ? WHERE run_id = ?;
```

Same rule applies to DELETE, MERGE, and any subquery that uses `run_id` alone to identify "this row".

**Recovery playbook** (if this happens again):
1. Stop all write paths to the health DB (pause Dagster if needed).
2. `ATTACH '{backup}' AS bak (READ_ONLY)` from the daily backup.
3. `UPDATE live SET rows_written = bak.rows_written FROM bak WHERE live.asset_key = bak.asset_key AND live.run_id = bak.run_id` restores the intersection.
4. Verify `COALESCE(live, -1) != COALESCE(bak, -1)` is 0 after restore.
5. Fix the bug.
6. Re-run the corrected backfill.

**Rule:**
1. Include the health DB in daily backup rotation. **The 2026-04-22 recovery would have been impossible without it.**
2. Code review checklist: any UPDATE/DELETE on `ingestion_runs` — is the WHERE composite?
3. When writing ad-hoc SQL against any table whose PK you don't know, query `information_schema.table_constraints` first.

**Reference:** `scripts/maintenance/backfill_ingestion_health_rows_written.py`, memory entry `feedback_ingestion_runs_composite_pk.md`

---

## Disaster Recovery & Maintenance Cron (post-mortem 2026-04-28)

Disk D: hit 100% full → SQLite `disk I/O error` on Dagster's daemon heartbeat → API stopped responding. Recovery surfaced four latent defects in the maintenance pipeline.

### L49 — Schedules in `defs.schedules=[...]` are NOT auto-enabled

**Symptom:** `maintain_purge_runs_job` had **0 runs ever** despite the schedule being defined in code for weeks. `dagster_home/history/` accumulated to 18 GB.

**Root cause:** Listing a schedule in `Definitions(schedules=[...])` makes it visible to the daemon but leaves it in `DECLARED_IN_CODE` state until someone explicitly starts it. Storage table `jobs` (in `schedules.db`) only has rows for schedules that have transitioned to `RUNNING`. The `DagsterDaemonScheduler` only ticks schedules whose row exists with `status='RUNNING'`.

**Detection query:**
```python
import sqlite3, json
c = sqlite3.connect('/app/var/dagster_home/schedules/schedules.db').cursor()
c.execute("SELECT job_body, status FROM jobs WHERE job_type='SCHEDULE'")
seen = set()
for body, status in c.fetchall():
    nm = json.loads(body)['origin']['job_name']
    seen.add(nm)
# Compare `seen` against the list in `defs.schedules` — any missing name is DECLARED_IN_CODE.
```

**Fix:** explicitly start each maintenance schedule:
```bash
docker exec data_platform sh -c 'cd /app && DAGSTER_HOME=/app/var/dagster_home \
    dagster schedule start -f orchestration/definitions.py maintain_purge_runs_schedule'
```

**Rule:**
1. After adding a new `@schedule` to `defs.schedules`, **manually start it** (UI or CLI). Never assume "listed in code = running".
2. Add a healthcheck or boot-time assertion that compares `defs.schedules` names against the storage table. Any schedule missing from storage = silently disabled.
3. Storage row also caches the cron from FIRST start. Editing the cron in code → daemon evaluates the NEW cron on each tick (in-memory definition wins), but the storage snapshot stays stale. To keep them aligned, `dagster schedule stop` + `dagster schedule start` after any cron edit.

**Reference:** today's recovery — `maintain_purge_runs_schedule` defined since the original commit but never started; `definitions.py` → `maintain_purge_runs_schedule`

---

### L50 — Backup rotation MUST run via `trap … EXIT`, not after `cp`

**Symptom:** Backup directory grew from 7 → 10 daily backups (104 GB total) over 4 days while disk was filling. Older backups (oldest 18 GB each) never got deleted.

**Root cause:** `backup.sh` had retention logic at the bottom of the script (Step 4 — keep 7 newest, delete rest). With `set -euo pipefail`, any failure of `cp -a app_data` mid-copy (most often `ENOSPC` once disk fills) causes the script to exit immediately. The rotation step at the bottom is never reached → old backups accumulate → next day disk is even fuller → `cp` fails earlier → vicious cycle.

**Fix:** move rotation into an `EXIT` trap so it fires regardless of how the script exits:

```bash
rotate_old_backups() {
    local rc=$?
    set +e  # cleanup must never bubble up an error
    # Drop incomplete current backup
    if [ "${BACKUP_DATA_OK:-false}" = false ] && [ -d "${BACKUP_DIR:-}" ]; then
        rm -rf "$BACKUP_DIR"
    fi
    # Rotate old backups
    cd "$BACKUP_ROOT" 2>/dev/null || return $rc
    ls -1d [0-9]*-[0-9]* 2>/dev/null | sort -r | tail -n +$((KEEP_COUNT + 1)) \
        | while read -r old; do rm -rf "${BACKUP_ROOT}/${old}"; done
    return $rc
}
trap rotate_old_backups EXIT
```

**Companion fix — pre-flight disk check** (fail fast, let trap rotate to free space):

```bash
NEED_KB=$(du -sk "$DATA_ROOT" | awk '{print $1}')
FREE_KB=$(df -Pk "$BACKUP_ROOT" | awk 'NR==2 {print $4}')
if [ "$FREE_KB" -lt "$((NEED_KB + 1024*1024))" ]; then  # +1 GB margin
    log "ABORT: insufficient disk; trap will rotate older backups"
    exit 1
fi
```

**Rule:**
1. Cleanup logic in any "create-then-rotate" script MUST live in a trap, not as final-step inline code.
2. Pre-flight resource checks belong before the resource-consuming step, not after.
3. A backup script that can leave the system worse than it found it is a foot-gun — design for graceful degradation under disk pressure.

**Reference:** `scripts/backup/backup.sh` → `rotate_old_backups()` + EXIT trap + pre-flight disk check.

---

### L51 — Exclude regenerable data from backup (`dagster_home/history/`)

**Symptom:** Each daily backup grew from 4 GB to 18 GB over 10 days. DuckDB itself was only 320 MB; the bulk was Dagster run history.

**Root cause:** `cp -a dagster_home` blindly included `history/` (per-run SQLite DBs + WAL + index.db) which had ballooned to 18 GB because the purge schedule was never running (L49). Restoring run history from a backup is undesirable anyway — old run records would confuse the queue coordinator and alerting sensors.

**Fix:** prune `history/` from the backup destination after copy:

```bash
prune_dagster_history() {
    local dh_dir="$1"
    if [ -d "${dh_dir}/history" ]; then
        rm -rf "${dh_dir}/history"
        log "Pruned ${dh_dir}/history (run records excluded from backup)"
    fi
}
# Call after each `cp -a` of dagster_home
```

**What we DO keep** in dagster_home backup:
- `dagster.yaml` — instance config
- `schedules/schedules.db` — schedule state (RUNNING/STOPPED, cursors)
- `storage/` — asset materialization records (small, ~500 MB)
- `logs/`, `.telemetry/`, `.nux/` — minor

**What we EXCLUDE:**
- `history/runs.db` + `history/runs/*.db` + `history/index.db` — run records (regenerable on next tick)

**Rule:**
1. Never back up data that's both (a) regenerable on demand and (b) the dominant size contributor.
2. Audit backup contents quarterly: `du -sh backup_dir/*` should look proportional to the operational data, not to historical noise.
3. After excluding regenerable data, verify a restore drill works with the slimmer backup.

**Reference:** `scripts/backup/backup.sh` → `prune_dagster_history`.

---

### L52 — `health_alert_stuckrun_sensor` must cover ALL non-terminal states (Pass 2)

**Symptom:** 4 zombie runs sat in `NOT_STARTED` status for 3-4 days during the disk-full incident. The stuck-run sensor never alerted on them.

**Root cause:** Sensor was filtering `RunsFilter(statuses=[DagsterRunStatus.STARTED])` — only catches runs that have already begun executing but lost activity. It missed runs that never even left the queue because the run coordinator daemon was frozen (SQLite I/O error).

There are **two failure modes** for stuck runs:
| Failure mode | Status | Pass 1 catches? | Pass 2 catches? |
|---|---|---|---|
| dbt subprocess hang | `STARTED` + no log activity 5+ min | ✅ | n/a |
| Daemon never dequeued | `NOT_STARTED` / `QUEUED` / `STARTING` for 2h+ | ❌ | ✅ |

**Fix:** add Pass 2 — iterate `NOT_STARTED` / `QUEUED` / `STARTING` runs and cancel any older than `QUEUE_STUCK_THRESHOLD = 2h`:

```python
# Pass 2: queue-stuck runs (never dequeued)
queue_records = instance.get_run_records(
    filters=RunsFilter(statuses=[
        DagsterRunStatus.NOT_STARTED,
        DagsterRunStatus.QUEUED,
        DagsterRunStatus.STARTING,
    ])
)
for rec in queue_records:
    age = now - datetime.fromtimestamp(rec.create_timestamp, tz=timezone.utc)
    if age < QUEUE_STUCK_THRESHOLD:
        continue
    instance.report_run_canceled(rec.dagster_run)
    instance.event_log_storage.free_concurrency_slots_for_run(rec.dagster_run.run_id)
    send_lark_card(title="🪦 Dagster Run AUTO-CANCELED (queue-stuck)", ...)
```

**Threshold choice — why 2 hours, not 30 min:**
- Nightly batch (`pipeline_batch_nightly_job`) holds `dbt_rw=1` for ~30-60 min. Realtime ticks queued behind it sit in `NOT_STARTED` legitimately.
- 2h gives wide safety margin while preventing days-long zombie accumulation.
- Different from Pass 1's `INACTIVITY_THRESHOLD=5min` because Pass 2 detects "daemon never picked it up", not "process stalled".

**Tighten interval:** `@sensor(minimum_interval_seconds=60)` (was 300) — list-runs is a cheap status-filtered query; faster cadence bounds Pass 1 detection latency to ~6 min instead of ~10 min.

**Rule:**
1. Auto-recovery sensors must cover EVERY non-terminal state, not just the obvious one.
2. Different stuck modes need different thresholds — don't conflate "process stalled" and "daemon never dequeued".
3. Boot-time cleanup (L48) handles restart-induced zombies; sensor (L52) handles steady-state zombies. Need both.

**Reference:** `orchestration/sensors/stuck_run_alerter.py` → Pass 1 (`STARTED` + inactivity) + Pass 2 (`NOT_STARTED`/`QUEUED`/`STARTING` + age).

---

### Maintenance Cron Design Principles (synthesis)

Lessons L49-L52 + the existing L47 (backup acquires `duckdb_lock`) crystallize a design pattern for daily maintenance schedules:

1. **Order by mutual exclusion**: `purge → backup` (purge clears history before backup snapshots).
2. **Window in the quiet zone**: avoid hours when realtime/nightly are running. For this project: 01:00-01:59 ICT (after midnight, before 03:00 nightly).
3. **Enforce ordering via sensor, not cron offset**: use `run_status_sensor` to chain `backup` after `purge` completes. Cron offset only works if both jobs are fast and predictable.
4. **Bound resource cost upfront** with concurrency tags (`duckdb_lock`) and pre-flight checks (free disk).
5. **Always-run cleanup via `trap … EXIT`** in shell scripts — never trust step-by-step linear execution to reach the rotation step.
6. **Exclude regenerable data** from anything that gets persisted (backups, snapshots).
7. **Auto-recovery sensors cover ALL non-terminal states**, not just `STARTED`.
8. **Pre-flight disk check must measure only source dirs, not parent dir**: if backup destination lives under the same parent as source, `du -sk parent` includes the existing backups in "required size" (circular over-estimate → false ENOSPC abort every run). See L58.

| Schedule/Sensor | Trigger | Rationale |
|---|---|---|
| `maintain_purge_runs_schedule` | `0 1 * * *` ICT | Quietest window; finishes before 03:00 nightly |
| `trigger_backup_after_purge` (sensor) | purge SUCCESS | Hard ordering — backup runs after purge, not cron-guessed |
| `maintain_backup_fallback_schedule` | `0 6 * * *` ICT | Fallback if purge fails; `run_key=date` deduplicates with sensor |
| `pipeline_batch_nightly_schedule` | `0 3 * * *` ICT | Default nightly batch |
| `health_report_digest_schedule` | `0 6 * * *` ICT | After all overnight jobs complete; read-only different DB |

---

## Cleanup & Schedule Management (post-mortem 2026-04-28/29)

### L53 — Phantom Dagster instigator states after code renames

**Symptom:** Old sensor/schedule names show `RUNNING` in UI even after being renamed in code. They never tick but hold state rows in `schedules.db`, confusing debugging. New names appear as `DECLARED_IN_CODE` even after daemon restart.

**Root cause:** Dagster stores instigator state in `schedules.db` by original name. Renaming in Python does NOT auto-migrate the DB row. Old row stays `RUNNING`, new row stays unregistered.

**Detect phantoms:**
```python
import sqlite3, json
conn = sqlite3.connect('/app/var/dagster_home/schedules/schedules.db')
for body, status in conn.execute("SELECT job_body, status FROM jobs WHERE job_type IN ('SCHEDULE','SENSOR')"):
    nm = json.loads(body)['origin']['job_name']
    print(f"{status:20s} | {nm}")
```
Any name no longer in `definitions.py` = phantom.

**Fix:**
```python
from dagster import DagsterInstance, InstigatorStatus
instance = DagsterInstance.get()
for s in instance.all_instigator_state():
    if s.name in PHANTOM_NAMES:
        instance.update_instigator_state(s.with_status(InstigatorStatus.STOPPED))
```
After stopping, Dagster cleans up phantom rows on next daemon tick.

**Rule:**
1. When renaming a schedule/sensor: stop it in UI BEFORE renaming code → deploy → start under new name.
2. After renaming: verify `dagster schedule list` shows only current names.
3. A phantom `RUNNING` sensor costs nothing (no ticks) but is misleading. Clean up proactively.

---

### L54 — `run_status_sensor` pattern for hard job ordering (backup-after-purge)

**Problem:** Backup must run AFTER purge completes — not at a fixed cron offset. Cron offset (`06:00`) is brittle: if purge runs long or is skipped, backup may run on stale DB or skip entirely.

**Solution:** `run_status_sensor` fires on purge SUCCESS → triggers backup immediately. Fallback schedule at 06:00 handles the case where purge failed.

```python
from dagster import run_status_sensor, RunStatusSensorContext, RunRequest, DagsterRunStatus, schedule, SkipReason
from datetime import datetime, timezone, timedelta

_ICT = timezone(timedelta(hours=7))

@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS,
    monitored_jobs=[maintain_purge_runs_job],
    request_job=maintain_backup_platform_job,
    minimum_interval_seconds=60,
)
def trigger_backup_after_purge(context: RunStatusSensorContext):
    date_key = datetime.now(tz=_ICT).strftime("%Y-%m-%d")
    return RunRequest(run_key=date_key)  # run_key deduplicates with fallback

@schedule(job=maintain_backup_platform_job, cron_schedule="0 6 * * *", execution_timezone="Asia/Ho_Chi_Minh")
def maintain_backup_fallback_schedule(context):
    if _has_active_run(context, "maintain_backup_platform_job"):
        return SkipReason("backup: already running")
    date_key = datetime.now(tz=_ICT).strftime("%Y-%m-%d")
    return RunRequest(run_key=date_key)  # same key as sensor → Dagster deduplicates
```

**Key points:**
- `run_key=date` in BOTH sensor and fallback → if sensor already triggered backup, fallback's `RunRequest` is silently deduplicated by Dagster.
- Sensor fires within ~1 min of purge SUCCESS → typical backup starts ~02:35 ICT.
- Fallback fires at 06:00 → catches missed backups without double-running.
- Use stdlib `datetime.timezone(timedelta(hours=7))` not `pytz` — pytz import failure breaks all of Dagster startup.

**New sensor registration:** after code deploy, new sensors may NOT auto-register in schedules.db. If UI shows "DECLARED_IN_CODE" instead of running, use GraphQL `startSensor` mutation or Dagster CLI.

---

### L55 — `asset_check_executions` table not cleaned by `delete_run()`

**Symptom:** After purging 18,000+ runs, `index.db` still 3.3 GB after VACUUM. Found `asset_check_executions` had 800,377 rows (800,160 orphaned).

**Root cause:** Dagster's `instance.delete_run()` cleans `runs.db` and `event_logs` but does NOT touch `asset_check_executions` in `index.db`. Rows accumulate indefinitely — one row per asset check per run.

**Fix — cross-SQLite delete using ATTACH:**
```python
def _cleanup_orphan_asset_check_executions(instance, log) -> int:
    run_dir = _get_run_db_dir(instance)
    index_path = os.path.join(run_dir, 'index.db')
    runs_path = os.path.join(os.path.dirname(run_dir), 'runs.db')
    conn = sqlite3.connect(index_path, timeout=30.0)
    conn.execute('PRAGMA busy_timeout = 30000')
    conn.execute(f"ATTACH DATABASE '{runs_path}' AS runsdb")
    conn.execute("""
        DELETE FROM asset_check_executions
        WHERE run_id NOT IN (SELECT run_id FROM runsdb.runs)
    """)
    conn.commit()
    deleted = conn.execute("SELECT changes()").fetchone()[0]
    conn.close()
    return deleted
```

After fix: index.db shrank to 43.7 MB (from 3.3 GB after VACUUM, 6 GB before).

**Rule:** Include `_cleanup_orphan_asset_check_executions` in every purge run — both the `count==0` path (maintenance-only) and the `count>0` path (active purge). See `orchestration/ops/purge_runs.py`.

---

### L56 — SQLite WAL safety in purge/cleanup scripts

**Key practices for SQLite operations during Dagster maintenance:**

1. **Always set both Python timeout AND SQLite busy_timeout:**
```python
conn = sqlite3.connect(index_path, timeout=30.0)      # Python-level wait
conn.execute('PRAGMA busy_timeout = 30000')            # SQLite-level wait (ms)
# Both needed: Python timeout handles connection; busy_timeout handles statement-level locks
```

2. **VACUUM + WAL checkpoint after mass delete:**
```python
conn.execute('VACUUM')
result = conn.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
if result and result[0] == 1:
    # busy=1 is NORMAL — daemon holds WAL readers; SQLite auto-truncates later
    log.info("wal_checkpoint(TRUNCATE): active readers present, WAL will auto-truncate later")
```
Log this as `info`, not `warning` — the daemon always holds WAL readers in production.

3. **WAL size at run start = early warning:**
```python
wal_path = os.path.join(run_dir, 'index.db-wal')
if os.path.exists(wal_path):
    wal_mb = os.path.getsize(wal_path) / (1024 * 1024)
    if wal_mb > 100:
        log.warning(f"index.db-wal is {wal_mb:.0f} MB — previous run may have been interrupted")
```
A >100 MB WAL at the START of a purge run = previous purge was killed mid-operation. SQLite will auto-apply the WAL on next DB open (recovery is safe).

4. **Offline VACUUM when online is impossible:** If Docker container holds an exclusive lock during cleanup, `docker compose stop data_platform` releases it. Then VACUUM directly on Windows host — the bind-mounted SQLite files are accessible from outside the container.

---

### L57 — history_log double-fetch + `min_overlap_items` reset behavior

**Double-fetch bug:**
```python
# BUG — first session.get response immediately discarded, 2x network calls
def _fetch_entity_inner(target_url, uri, current_session):
    _delay_with_jitter()
    resp = current_session.get(target_url, timeout=15)   # ← wasted
    _delay_with_jitter()
    resp = current_session.get(target_url, timeout=15)   # ← overwrites first

# FIX
def _fetch_entity_inner(target_url, uri, current_session):
    _delay_with_jitter()
    resp = current_session.get(target_url, timeout=15)
```
The bug doubled network calls and delay time, effectively halving throughput.

**`min_overlap_items` reset behavior (run never exits):**

The early-stop counter `consecutive_old_items` resets to 0 every time a NEW log item is seen. On an active store:
- `min_overlap_items=500` requires 500 consecutive-old items in a row
- Any single new event resets the counter → need 500 more
- On a busy log stream = the loop effectively never exits until `max_pages` (1000 pages = 100,000 items)

The source default is `min_overlap_items=50`. Setting it to 500 in `run_history_log.py` caused >10-minute hangs.

**Rule:**
1. Use source default (50) for `min_overlap_items` unless there is explicit evidence that new items appear sparsely across 5+ pages.
2. Add a Dagster `op_tags={"dagster/max_runtime": N}` to history_log asset as a hard ceiling.
3. When a source has a "double request" pattern like above, the bug is invisible from metrics — only manifest as 2× slower runs.

---

### L58 — Backup pre-flight disk check must exclude backup destination from source size

**Symptom:** Backup job fails every night with "Backup ABORTED: insufficient disk space — Source: 107 GB, Free: 35 GB". But actual per-run backup is only ~19 GB and disk is not actually full.

**Root cause:** `backup.sh` pre-flight falls back to `du -sk $DATA_ROOT` when the native `app_data/` path doesn't exist. `DATA_ROOT=/app/var` is the **parent** of all volume mounts including `/app/var/backups`. So the measurement includes every existing backup in "source size":

```
/app/var/
├── data_lake/        ~19 GB  ← real source
├── dagster_home/     ~0.5 GB ← real source
├── input_source/     ~0.5 GB ← real source
└── backups/          ~95 GB  ← backup DESTINATION, wrongly measured as source
```

`du -sk /app/var` = 115 GB → pre-flight says "need 116 GB" → aborts → rotation trap removes oldest backup → next night same thing (7 backups → 6, disk shrinks ~19 GB, but 6 × 19 GB still >> 44 GB free).

**Why it wasn't caught earlier:** The first backup ever ran before enough backups accumulated to trip the threshold. Once 5+ backups existed (~95 GB), every subsequent run aborted at pre-flight, leaving previous backups intact. The rotation DID fire (removed the oldest) but freed only ~19 GB — not enough to overcome the phantom 95 GB circular estimate.

**Fix:** Measure only the directories actually being copied:
```bash
_precheck_need_kb() {
    local total=0
    if [ -d "${PROJECT_ROOT}/app_data" ]; then
        total=$(du -sk "${PROJECT_ROOT}/app_data" 2>/dev/null | awk '{print $1}')
    else
        local dr="${DATA_ROOT:-/app/var}"
        for vol in data_lake dagster_home input_source; do
            local d="${dr}/${vol}"
            [ -d "$d" ] || continue
            local sz; sz=$(du -sk "$d" 2>/dev/null | awk '{print $1}')
            total=$((total + sz))
        done
    fi
    echo "$total"
}
NEED_KB=$(_precheck_need_kb)
```

**Rule:**
1. Any pre-flight size check: list explicitly what is being measured. Never measure a parent dir that contains the destination.
2. When a backup script has both source and destination under the same mount, the pre-flight MUST enumerate source subdirs individually.
3. If backups silently stop succeeding but old ones remain (rotation running but no new success), suspect circular size estimate — compare `du -sk <source_dirs>` vs `du -sk <parent>`.

---

## Config Snapshot Ingestion (Google Sheets, static reference data)

### L59 — Config snapshot tables: dùng fixed path, KHÔNG phân vùng theo year/month

**Incident (2026-05-01):** `gsheet_team_config.py` dùng `year/month` partitioning cho bảng `teams_raw` và `team_members_raw`. Lúc 03:01 ICT ngày 1/5, nightly batch tạo partition `month=5` mới — trong khi `month=4` vẫn còn. DuckDB glob `ingest_method=*/**/*.parquet` đọc cả hai → team CS xuất hiện 2 lần trong `stg_teams` → `fact_orders` SCD2 join nhân đôi mỗi order có seller thuộc team đó → **1419 duplicate order_id → dbt fail → 102 job failures + hàng trăm alert**.

**Root cause:** `year/month` partitioning phù hợp cho time-series (orders, events) — KHÔNG phù hợp cho config snapshot (teams, members) vì config là "trạng thái hiện tại", không phải "lịch sử theo thời gian".

**Fix pattern — Fixed snapshot path:**

```python
# BAD: mỗi tháng tạo partition mới, cộng dồn duplicate
output_dir = .../ingest_method=google_sheet/year=2026/month=5/
file_path  = .../teams.parquet  # tháng sau: month=6, tháng sau nữa: month=7

# GOOD: luôn overwrite cùng file, không cộng dồn
output_dir = .../ingest_method=google_sheet/snapshot/
file_path  = .../teams.parquet  # overwrite mỗi lần chạy
```

Dùng `snapshot/` làm subdir cố định vì glob pattern của `sources.yml` là `ingest_method=*/**/*.parquet` — cần ít nhất 1 level subdirectory sau `ingest_method=*`.

**Cleanup legacy partitions tự động khi chạy:**

```python
def _save_to_parquet(df, table_name):
    import shutil
    base_dir = .../ingest_method=google_sheet
    # Xóa legacy year=* dirs từ design cũ
    if os.path.exists(base_dir):
        for entry in os.listdir(base_dir):
            entry_path = os.path.join(base_dir, entry)
            if os.path.isdir(entry_path) and entry.startswith("year="):
                shutil.rmtree(entry_path)
    # Ghi vào fixed path
    snapshot_dir = os.path.join(base_dir, "snapshot")
    os.makedirs(snapshot_dir, exist_ok=True)
    df.to_parquet(os.path.join(snapshot_dir, f"{table_name.replace('_raw','')}.parquet"), index=False)
```

**Safety net ở staging SQL (QUALIFY dedup):**

```sql
-- stg_teams.sql — dedup by team_code, giữ snapshot mới nhất
FROM cleaned
QUALIFY ROW_NUMBER() OVER (PARTITION BY team_code ORDER BY year DESC, month DESC) = 1

-- stg_team_members.sql — dedup by SCD2 key, giữ snapshot mới nhất
FROM cleaned
QUALIFY ROW_NUMBER() OVER (PARTITION BY staff_email, team_code, effective_from ORDER BY year DESC, month DESC) = 1
```

**Rules:**
1. **Config/reference tables** (teams, team_members, targets, marketing_spend): dùng fixed path overwrite — KHÔNG year/month partition.
2. **Time-series tables** (orders, events, history_log): dùng year/month partition — đây là nguồn gốc của pattern này.
3. **Staging SQL cho config tables**: luôn thêm `QUALIFY ROW_NUMBER() ... = 1` làm safety net phòng re-introduced partitioning.
4. **Cảnh báo cascade**: Config table duplicate → dim/fact downstream đọc SCD2 nhân đôi → hàng nghìn duplicate rows → toàn bộ dbt graph fail.

---

## Stuck Run — Zombie Subprocess Cascade (post-mortem 2026-05-05)

### L60 — `finally: watchdog.cancel()` orphans dbt subprocess khi run bị kill ngoài

**Symptom:** `pipeline_sapov2_realtime_job` stuck **liên tục** (Runtime: 10 min, Inactive: 9 min, auto-terminated). Pattern lặp lại mỗi 3-13 phút mà không dừng dù đã có watchdog timer và stuck_run_alerter.

**Root cause:** Chuỗi nguyên nhân đa tầng:

1. dbt subprocess hang ở DuckDB WAL checkpoint
2. `stuck_run_alerter` kill Dagster run lúc T=10 min (MIN_RUNTIME đạt ngưỡng, inactivity 9 min)
3. Dagster cancel run → Python garbage-collect generator `sapo_dbt_assets` → `GeneratorExit` → **`finally: watchdog.cancel()` fires, disarming watchdog**
4. dbt subprocess hiện **orphan** — không có watchdog, không có SIGKILL
5. `_terminate_subprocess_tree(run_id)` tìm process bằng `run_id[:12]` trong cmdline/env của dbt → **không tìm thấy** (dbt không inject run_id vào environment của nó)
6. Zombie dbt process tiếp tục chạy, giữ DuckDB WAL lock
7. Run mới bắt đầu 3 min sau → dbt ngay lập tức hang ở WAL lock do zombie → repeat từ bước 1

**Evidence:** "Runtime: 10 min, Inactive: 9 min" = 1 min webhook chạy OK, rồi dbt hang ngay khi start. Perfect match với "zombie từ run trước giữ WAL lock".

**Fix: Kill subprocess trong `finally` block bất kể exit path nào**

```python
# orchestration/assets/dbt.py
watchdog = threading.Timer(DBT_TIMEOUT_SEC, _kill_on_timeout)
watchdog.daemon = True
watchdog.start()
try:
    yield from invocation.stream()
finally:
    watchdog.cancel()
    # Kill subprocess on ANY exit path (normal, timeout, OR external cancellation).
    # Without this: external cancellation cancels the watchdog but leaves dbt alive.
    try:
        if invocation.process.poll() is None:
            invocation.process.kill()
    except Exception:
        pass
```

**Rules:**
1. **`finally` block phải đảm bảo cleanup** — không chỉ cancel watchdog. Bất kỳ exit path nào (exception, GeneratorExit, cancellation) đều phải kill subprocess.
2. **Watchdog + finally kill = defense in depth**: watchdog fires nếu run hoàn tất bình thường nhưng dbt quá chậm; finally kill fires khi run bị cancel externally.
3. **`_terminate_subprocess_tree` tìm theo run_id là không đủ** — subprocesses spawn bởi Dagster assets thường không có run_id trong cmdline hay env của chúng.
4. **Zombie cascade dấu hiệu**: job cứ stuck đều đặn với cùng timing (Inactive ≈ 1 min ít hơn MIN_RUNTIME) là dấu hiệu zombie từ run trước đang giữ lock.

**Reference:** `orchestration/assets/dbt.py` → `finally` block; `orchestration/sensors/stuck_run_alerter.py` → `_terminate_subprocess_tree`.

---

### L61 — QUEUE_STUCK_THRESHOLD phải sizing dựa vào topology schedule thực tế

**Symptom:** `pipeline_sapov2_incremental_job` stuck NOT_STARTED 120 min (đúng bằng QUEUE_STUCK_THRESHOLD=2h). Runs liên tục bị miss, dữ liệu stale.

**Root cause:** Hai vấn đề kết hợp:
1. Zombie dbt processes (L60) tích lũy → CPU + file descriptor pressure → `QueuedRunCoordinator` daemon bị slow/freeze → không poll queue để dequeue incremental run
2. QUEUE_STUCK_THRESHOLD = 2h quá rộng — phải chờ đủ 2h mới phát hiện và cancel

**Tại sao 2h là sai với topology hiện tại:**

```
Incremental schedule: */10 0-2,4-23 * * *   ← skip toàn bộ hour 3
Nightly schedule:     0 3 * * *              ← chạy lúc 3 AM
```

Hour 3 bị skip hoàn toàn → incremental KHÔNG BAO GIỜ xếp hàng trong khi nightly đang chạy → 2h threshold không phục vụ case "chờ nightly xong" vì case đó không xảy ra.

Legitimate wait time thực tế = thời gian chạy của 1 job `dbt_rw` khác = 7-10 min (realtime) hoặc tối đa 60 min (nightly nếu overruns). 90 min bao phủ tất cả edge cases.

**Fix:**

```python
# orchestration/sensors/stuck_run_alerter.py

# Trước: QUEUE_STUCK_THRESHOLD = timedelta(hours=2)
# Sau:
QUEUE_STUCK_THRESHOLD = timedelta(minutes=90)
# Rationale: incremental schedule skips hour 3 entirely — it can never legitimately
# queue behind the nightly job. Max legitimate wait = 1 dbt_rw job duration (~60 min
# worst case nightly overrun). 90 min covers this with margin.
```

**Quy trình sizing QUEUE_STUCK_THRESHOLD cho bất kỳ pipeline nào:**

1. Liệt kê tất cả jobs dùng cùng concurrency tag (e.g., `dbt_rw=1`)
2. Xác định job nào chạy lâu nhất (nightly: ~60 min)
3. Xem schedule của victim job (job bị kẹt) có skip giờ mà job dài chạy không → nếu skip, job dài không thể là nguyên nhân
4. Threshold = `max_legitimate_wait + safety_margin` (không phải "thật to cho an toàn")

**Rules:**
1. **Threshold phải phản ánh topology thực tế** — không set 2h chỉ vì "an toàn". Threshold càng lớn, zombie càng tồn tại lâu, cascade càng nhiều.
2. **Kiểm tra schedule skip hour** — xem từng schedule để hiểu actual dependency. "Incremental skip hour 3" là thông tin quan trọng nhưng không hiển thị rõ ràng trong UI.
3. **L60 fix phòng ngừa zombie** → L61 fix giảm detection latency. Cả hai cần nhau: L60 ngăn zombie tích lũy, L61 đảm bảo nếu zombie vẫn xảy ra thì bị phát hiện nhanh hơn.

**Reference:** `orchestration/sensors/stuck_run_alerter.py` → `QUEUE_STUCK_THRESHOLD`; `orchestration/definitions.py` → `pipeline_sapov2_incremental_schedule` cron.

---

## Health DB Lock — Windows dllhost.exe (post-mortem 2026-05-05)

### L62 — Windows dllhost.exe (COM Surrogate / Defender) locks DuckDB files trên bind-mounted Windows paths

**Symptom:** `ingestion_health.duckdb` bị lock liên tục — `record_run failed: IO Error: Could not set lock on file ... Conflicting lock is held in PID 0`. Health monitoring gián đoạn 3 ngày 21 giờ. Lock **vẫn còn** sau khi restart Docker container.

**Root cause:** DuckDB file nằm trên Windows host (bind mount). Windows Defender real-time scanning (hoặc Windows Explorer shell extension / COM surrogate) mở file khi phát hiện file thay đổi (sau mỗi write từ asset). Process holder là `dllhost.exe` — host process của Windows COM components, thường được Defender dùng để scan file trong background.

Khi Docker container bị restart, OS-level advisory locks từ Linux processes được release — nhưng `dllhost.exe` là Windows-level process, chạy bên ngoài WSL2 container. Lock của nó KHÔNG được release khi restart container. Từ phía Linux container, lock holder PID = 0 (không identify được vì là Windows process).

**Thời gian xảy ra:** Thường sau khi có nhiều write operations liên tiếp vào file (Defender queue scan cao), hoặc sau khi user mở folder chứa file trong Windows Explorer (thumbnail shell extension).

**Detection:**
```python
# Thử mở từ Windows-native Python (KHÔNG phải Docker):
python -c "
import duckdb
path = r'D:\...\monitoring\ingestion_health.duckdb'
try:
    conn = duckdb.connect(path)
    conn.close()
    print('OK')
except Exception as e:
    print(f'FAIL: {e}')
"
# Nếu output có "File is already open in ... dllhost.exe (PID XXXX)"
# → đó là thủ phạm
```

**Fix:**
```powershell
# 1. Tìm PID từ error message của Windows Python test
# 2. Kill process (PowerShell):
taskkill /PID <dllhost_pid> /F

# 3. Mở từ Windows Python để checkpoint (clean state):
python -c "
import duckdb
conn = duckdb.connect(r'D:\...\monitoring\ingestion_health.duckdb')
conn.execute('CHECKPOINT')
conn.close()
print('Checkpointed OK')
"

# 4. Restart Docker Desktop (nếu WSL2 mount cần refresh):
# Right-click Docker tray icon → Restart
docker compose up -d data_platform
```

**Prevention:**
```powershell
# Admin PowerShell — thêm Defender exclusion cho monitoring dir:
Add-MpPreference -ExclusionPath "D:\...\app_data\data_lake\monitoring"
```
Cần admin privileges. Nếu không có admin: chấp nhận rủi ro xảy ra định kỳ, dựa vào watchdog sensor để alert sớm.

**Code defense — `_connect()` tăng retry window và log rõ ràng:**
```python
_LOCK_RETRIES = 8        # từ 5 → 8
_LOCK_BACKOFF_S = 1.0    # từ 0.5 → 1.0 (total ~4 min retry window)

# Khi gặp "PID 0" hoặc "being used by another process":
if "PID 0" in err_str or "being used by another process" in err_str:
    logger.warning("ingestion_health: stale lock — Fix: taskkill /F /IM dllhost.exe ...")
```

**Rules:**
1. **DuckDB files trên Windows bind mount có thể bị Defender lock bất cứ lúc nào** — đặc biệt sau khi file được modified.
2. **Restart Docker container KHÔNG release Windows-level lock** — phải kill process giữ lock trên Windows host.
3. **`PID 0` error từ DuckDB** = lock holder là process không identify được từ Linux side (thường là Windows-side process qua bind mount). Thử mở từ Windows Python để confirm.
4. **Không restore backup** khi gặp vấn đề này — backup cũng dùng cùng path, lock là OS-level không phải trong file.
5. **Defender exclusion** là fix tốt nhất; nếu không có admin — tăng retry window trong `_connect()` để absorb scan ngắn hạn.

**Monitoring alert:** `health_db_watchdog_sensor` đã detect và alert đúng. Nếu alert "🚨 Health DB bị KHÓA" → chạy Windows Python test để confirm `dllhost.exe`, rồi `taskkill`.

**Reference:** `orchestration/ops/ingestion_health.py` → `_connect()`; `orchestration/sensors/health_db_watchdog_sensor.py`.

---

### L63 — Purge job bị stuck-run alerter kill do VACUUM chạy im lặng quá 5 phút

**Symptom:** `maintain_purge_runs_job` bị auto-terminate mỗi lần chạy — Runtime: ~17 min, Inactive: 5 min. Alerter log: `"Auto-terminating stuck run ... no activity for 5:00"`.

**Root cause:** `_vacuum_index_db()` emit 1 dòng log `"Starting VACUUM on index.db (X MB)..."` rồi im hoàn toàn trong suốt quá trình VACUUM. SQLite VACUUM là blocking operation rewrite toàn bộ database file — trên `index.db` lớn (vài trăm MB sau bulk delete) có thể mất 5–15+ phút không có output nào. `stuck_run_alerter` dùng `INACTIVITY_THRESHOLD = 5 min` — nếu run không emit log event trong 5 min liên tiếp thì bị kill.

Các phase khác cũng có thể silent:
- `SELECT DISTINCT run_id FROM event_logs` (full scan trên bảng lớn, có thể 30–90s)
- `DELETE FROM asset_check_executions WHERE run_id NOT IN (...)` (cross-db DELETE lớn)

**Fix:** Chạy VACUUM trong background thread, main thread loop `_done.wait(timeout=30)` và emit heartbeat log mỗi 30 giây:

```python
import threading

_errors: list[Exception] = []
_done = threading.Event()

def _do_vacuum():
    try:
        conn = sqlite3.connect(index_path, timeout=30.0)
        conn.execute('VACUUM')
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        conn.close()
    except Exception as e:
        _errors.append(e)
    finally:
        _done.set()

t = threading.Thread(target=_do_vacuum, daemon=True)
t.start()

elapsed = 0
while not _done.wait(timeout=30):
    elapsed += 30
    log.info(f"VACUUM in progress... ({elapsed}s elapsed, {size_before:.1f} MB)")
```

Ngoài ra thêm log trước các silent phases:
- Trước `SELECT DISTINCT run_id FROM event_logs`: `log.info("Scanning event_logs for orphaned run_ids...")`
- Trước cross-db DELETE: `log.info("Cleaning orphaned asset_check_executions rows (cross-db DELETE)...")`

**Rule:** Bất kỳ operation nào có thể chạy >2 min mà không emit log đều có nguy cơ bị stuck-run alerter kill. Dùng background thread + heartbeat loop để giữ activity signal khi không thể break operation thành chunks nhỏ hơn.

**Không nên:** Whitelist maintenance jobs khỏi alerter — alerter vẫn cần catch genuine stuck scenarios. Fix đúng là làm job emit progress, không phải tắt monitoring.

**Reference:** `orchestration/ops/purge_runs.py` → `_vacuum_index_db()`; `orchestration/sensors/stuck_run_alerter.py` → `INACTIVITY_THRESHOLD`.

---

### L64 — Ingestion NOT_STARTED 90 min: schedule tạo run khi dbt_rw slot bị chiếm bởi nightly batch

**Symptom:** `pipeline_sapov2_realtime_job` và `pipeline_sapov2_incremental_job` lặp lại NOT_STARTED ~90 min rồi bị auto-canceled ("daemon never dequeued"). Xảy ra sau khi L63 fix làm purge chạy thành công lần đầu → backup trigger lần đầu.

**Root cause:** Nightly batch (`pipeline_batch_nightly_job`, 60-90+ min) chiếm `dbt_rw=1` concurrency slot. Khi nightly đang chạy:

1. Realtime tick ở ~03:03 ICT: không có active realtime run → tạo `NOT_STARTED` run mới
2. Coordinator: `dbt_rw=1` bị nightly chiếm → không dequeue realtime → run ở `NOT_STARTED`
3. Realtime ticks tiếp theo (03:06, 03:09, ...): `_has_active_run` thấy `NOT_STARTED` là "active" → `SkipReason`
4. Incremental tại 04:00 (sau giờ skip 03:xx): tương tự, tạo `NOT_STARTED` bị block
5. 90 min sau: `QUEUE_STUCK_THRESHOLD` → auto-cancel cả hai

**Kết nối với backup (L63):** Trước L63 fix, purge bị kill → backup không bao giờ chạy → không có gì mới. Sau fix, backup chạy lần đầu. Backup bản thân không phải nguyên nhân trực tiếp (chỉ chạy max 10 phút, không hold `dbt_rw`), nhưng hệ thống lần đầu chạy đủ các maintenance jobs đồng thời → edge case bị trigger.

**Mechanism trap:** `_ACTIVE_STATUSES` includes `NOT_STARTED` → một run `NOT_STARTED` bị kẹt chặn tất cả ticks tiếp theo qua self-overlap check. Hệ quả: 1 run stuck → 30 ticks bị skip → run bị cancel → cycle lại.

**Fix:**

```python
# Định nghĩa trong definitions.py:
_LONG_DPT_RW_JOBS = ["pipeline_batch_nightly_job", "pipeline_batch_fullrefresh_job"]
_RUNNING_STATUSES = [DagsterRunStatus.QUEUED, DagsterRunStatus.STARTING, DagsterRunStatus.STARTED]

def _long_dbt_rw_holder(context) -> str | None:
    for job_name in _LONG_DPT_RW_JOBS:
        runs = context.instance.get_runs(
            filters=RunsFilter(job_name=job_name, statuses=_RUNNING_STATUSES), limit=1
        )
        if runs:
            return job_name
    return None

# Trong mỗi schedule ngắn (realtime, incremental):
holder = _long_dbt_rw_holder(context)
if holder:
    return SkipReason(f"realtime: yielding to {holder} (dbt_rw occupied)")
```

Lý do dùng `_RUNNING_STATUSES` (QUEUED/STARTING/STARTED) thay vì `_ACTIVE_STATUSES` (includes NOT_STARTED): nếu nightly chính nó đang NOT_STARTED, nó chưa hold slot → không nên block realtime/incremental.

**Bonus fix:** `trigger_backup_after_purge` sensor thêm check `_has_active_ingestion` trước khi fire — tránh backup DuckDB files khi chúng đang được ghi (torn WAL state risk) và giảm I/O contention.

**Rules:**
1. **Schedules không nên tạo RunRequest khi biết run sẽ bị blocked** — creates NOT_STARTED zombie, chặn ticks, bị cancel sau 90 min. Skip tick và retry là tốt hơn.
2. **_has_active_run(self) chỉ check self** — không biết về concurrent jobs khác đang giữ concurrency slot. Phải tự check cross-job khi cần.
3. **QUEUE_STUCK_THRESHOLD = 90 min là catch-all, không phải expected behavior** — nếu nó trigger thường xuyên = có pattern tạo NOT_STARTED runs không cần thiết.
4. **Backup snapshot không nên chạy khi DuckDB đang được ghi** — cp của live WAL = torn state risk.

**Reference:** `orchestration/definitions.py` → `_long_dbt_rw_holder()`, `pipeline_sapov2_realtime_schedule`, `pipeline_sapov2_incremental_schedule`, `trigger_backup_after_purge`; `orchestration/sensors/stuck_run_alerter.py` → `QUEUE_STUCK_THRESHOLD`.

---

## Dagster Job Executor & Type Safety

### L65 — Lightweight read-only jobs must use `in_process_executor` to prevent OOM

**Symptom:** `health_checks_asset_job` and `health_recon_daily_job` crash with `ChildProcessCrashException`. Jobs appear to start then immediately fail with no useful error beyond the crash.

**Root cause:** Dagster's default multiprocess executor spawns a separate subprocess per step. Each subprocess re-imports the full Python environment (dlt, dbt, duckdb, all orchestration modules). For lightweight read-only DuckDB queries this spawns a ~200-400 MB process just to execute a few SQL statements — OOM kills the child before it can run.

**Fix:**

```python
from dagster import in_process_executor

health_checks_asset_job = define_asset_job(
    name="health_checks_asset_job",
    selection=...,
    executor_def=in_process_executor,  # runs steps in same process as daemon
)
```

**Rules:**
1. Any job whose assets are lightweight read-only operations (DuckDB queries, file reads, API calls returning small payloads) should use `in_process_executor`.
2. Only use the default multiprocess executor when steps need isolation (e.g., dbt subprocess, heavy transforms that may OOM and must be killed without killing daemon).
3. `ChildProcessCrashException` on small jobs = suspect OOM from per-step subprocess overhead.

**Reference:** `orchestration/definitions.py` → `health_checks_asset_job`, `health_recon_daily_job`.

---

### L66 — `MetadataValue.float()` rejects Python int — `or 0` fallback is a trap

**Symptom:** `health_kpi_closure_job` fails intermittently (2 FAIL / 3 SUCCESS pattern) with `Param value is not a float`. Error only occurs when revenue values are exactly zero or None.

**Root cause:** `MetadataValue.float()` strictly requires a Python `float`. The pattern `value or 0` returns Python `int(0)` when `value` is `None` or `0.0` (both falsy) — `0` is `int`, not `float`. When the value is non-zero, it stays a `float` from the SQL query → no error. When exactly zero → `or 0` → `int` → type error.

```python
# BAD — `or 0` returns int when value is None/0.0
MetadataValue.float(source_revenue or 0)       # int(0) when source_revenue = 0.0

# GOOD — explicit float literal
MetadataValue.float(source_revenue or 0.0)     # float(0.0) always
```

**Pattern applies to:** any code using `x or 0` as a numeric default where the consuming API is type-strict. Common in metadata emission, JSON serialization, and typed function signatures.

**Rules:**
1. Default numeric literals must match the expected type: `0.0` for float, `0` for int.
2. `or 0` is a correctness trap when `0` is a valid value — use `if x is None else x` if zero has meaning.
3. Intermittent type errors (succeed when non-zero, fail when zero) = suspect `or 0` with type-strict consumer.

**Reference:** `orchestration/assets/kpi_closure.py`; commit `4be752b`.

---

## File-Drop Sensor Behavior

### L67 — File-drop sensor cold-start skip silently ignores files already in drop zone

**Symptom:** Shopee/MISA income files placed in drop zone before sensor deploys (or after sensor cursor reset) are never processed. Sensor ticks every 5 min but always returns `SkipReason("Cold start — recorded baseline mtime=...")` then `SkipReason("No new/modified files")` on subsequent ticks.

**Root cause:** Original file-drop sensor logic detected `prev_mtime == 0.0` (no cursor) and treated it as "cold start" — it saved the current `mtime` as baseline and returned without firing. This means any files present at the moment of first tick are silently baselined, never triggering a run. If someone drops a file before deploying or during cursor reset, it's lost.

**Fix:** Remove cold-start special case — fire whenever `current_mtime > prev_mtime`:

```python
# BAD — files present at deploy are silently ignored
if prev_mtime == 0.0:
    context.update_cursor(json.dumps({"mtime": current_mtime}))
    return SkipReason(f"Cold start — recorded baseline mtime={current_mtime:.0f}")

# GOOD — prev_mtime=0.0 means never seen any file; any file > 0 triggers
if current_mtime <= prev_mtime:
    return SkipReason("No new/modified files")
# falls through to fire RunRequest
```

`prev_mtime = 0.0` (epoch) is always < any real file mtime → first tick with files fires correctly.

**Rules:**
1. File-drop sensors should fire on first tick if files are present — "cold start skip" is a footgun when files pre-exist.
2. After cursor reset or sensor redeploy, check drop zone immediately for unprocessed files.
3. Sensor `run_key` based on mtime ensures idempotency — firing on cold start is safe.

**Reference:** `orchestration/sensors/file_drop_sensors.py`; commit `0d1e671`.

---

## Backup Script Edge Cases

### L68 — `cp -a` returns non-zero when SQLite WAL/SHM files disappear mid-copy

**Symptom:** Backup job logs `WARNING: failed to copy dagster_home` and skips `prune_dagster_history`. All essential data (`schedules/`, `storage/`, `dagster.yaml`) is actually copied correctly. Downstream: backup never gets history pruned → backup size stays large.

**Root cause:** Dagster daemon's WAL checkpoint can delete `.db-wal` and `.db-shm` files between `cp -a` starting and completing. `cp -a` exits non-zero when a source file disappears mid-copy. With `set -euo pipefail` and `if cp -a ...; then` guard, this non-zero is treated as failure and the entire volume backup is marked failed.

**Fix:** Ignore `cp` exit code, check destination is non-empty instead:

```bash
cp -a "$src" "$dst" 2>/dev/null || true   # WAL disappearance is expected
if [ -d "$dst" ] && [ "$(ls -A "$dst" 2>/dev/null)" ]; then
    BACKUP_DATA_OK=true
    prune_dagster_history "$dst"
    log "dagster_home backed up: $(du -sh "$dst" | cut -f1)"
else
    log "WARNING: failed to copy dagster_home (destination empty)"
fi
```

**Rules:**
1. `cp -a` on live SQLite databases is inherently racy — WAL files can disappear. Never treat non-zero exit as "backup failed" without checking the destination.
2. Verify backup success by checking destination exists and is non-empty, not by `cp` exit code.
3. This applies to any `cp -a` of a live Dagster home directory.

**Reference:** `scripts/backup/backup.sh`; commit `7d61491`.

---

### L69 — `run_key=date` deduplicates against previously FAILED runs — prevents retry

**Symptom:** Backup failed on day D (e.g., purge took too long, fallback triggered but backup encountered an error). On day D+1 (same calendar date, early morning), fallback schedule skips with no `SkipReason` — backup never retries. Monitoring shows no backup for 2 days.

**Root cause:** Dagster deduplicates `RunRequest` by `run_key`. If a run with the same `run_key` already exists — regardless of its status (SUCCESS, FAILURE, CANCELED) — Dagster silently discards the new `RunRequest`. Using `run_key=date` means a failed backup on day D blocks any retry attempt on day D since the key already exists.

```python
# BAD — FAILED run with same date key blocks all retries on that day
return RunRequest(run_key=date_key)

# GOOD — run_key=None + manual success check allows retries after failure
records = context.instance.get_run_records(
    filters=RunsFilter(job_name=job_name, statuses=[DagsterRunStatus.SUCCESS]),
    limit=5,
)
for rec in records:
    if datetime.fromtimestamp(rec.create_timestamp, tz=_ICT).date() == today:
        return SkipReason("backup: already succeeded today")
return RunRequest(run_key=None)  # no dedup against prior failures
```

**Rules:**
1. `run_key` deduplication is global across ALL terminal statuses — a failed run with the same key permanently blocks retries until the key changes.
2. Use `run_key=None` + manual query for "skip if already succeeded today" semantics when retries on failure are needed.
3. `run_key` remains appropriate where exactly-once semantics are required (sensor-triggered backup — don't run twice on same purge success event).

**Reference:** `orchestration/definitions.py` → `maintain_backup_fallback_schedule`; commit `2ee4b80`.

## Windows DuckDB Bind-Mount & Sensor Issues (post-mortems 2026-05-06/07)

### L70 — Windows `dllhost.exe` locks bind-mounted DuckDB file, silently breaks monitoring for days

**Symptom:** Health dashboard shows 0/N assets healthy, all "X ngày chưa cập nhật". Logs show `record_run failed: IO Error: Conflicting lock held in PID 0` on every write. Actual pipeline data (parquet files) is current — only monitoring DB is affected.

**Root cause:** Windows COM surrogate (`dllhost.exe`) acquires a filesystem handle on files it scans (Windows Defender / thumbnail indexer). DuckDB inside the Docker container cannot acquire write lock while host process holds it. Lock persists until dllhost releases or is killed. PID reported as 0 because the lock owner is on the host, not visible inside container.

**Fix:**
1. Kill `dllhost.exe` on Windows host: `taskkill /F /IM dllhost.exe`
2. Add Windows Defender exclusion for the monitoring directory (admin terminal):
   ```powershell
   Add-MpPreference -ExclusionPath "D:\Vantt\app\data-integration\app_data\data_lake\monitoring"
   ```
3. If bind mount breaks after kill (IO Error on `ls`), restart Docker Desktop fully (kill WSL + Docker processes, then relaunch)

**Rules:**
1. Defender exclusion path must match the **Windows host path** of the bind mount (`app_data\data_lake\monitoring`), not the container path or a non-existent path.
2. Killing `dllhost.exe` while Docker VM is running can corrupt the bind mount — expect Docker container restart to fail with `mkdir /run/desktop/mnt/host/d: file exists`. Full Docker Desktop restart (including WSL shutdown) is required.
3. Always verify the fix inside the container: `python3 -c "import duckdb; con=duckdb.connect('/app/var/data_lake/monitoring/ingestion_health.duckdb'); con.close(); print('OK')"`.

**Reference:** `app_data/data_lake/monitoring/ingestion_health.duckdb`; incident May 6 2026; commit `4e93d23`.

### L71 — Dagster sensor registered via `ManagedGrpcPythonEnv` origin never ticks when daemon serves `GrpcServer` origin

**Symptom:** Sensor shows `RUNNING` in Dagster UI but has zero ticks ever (`last_tick_start_timestamp = null`). Daemon logs show the sensor is never checked. The sensor was added after the main codebase was already running.

**Root cause:** Dagster stores the sensor's repository location origin in `schedules/schedules.db`. If a sensor is registered while Dagster runs in `dagster dev` / module-import mode (`ManagedGrpcPythonEnvRepositoryLocationOrigin`), but the production daemon serves via file-based gRPC (`GrpcServerRepositoryLocationOrigin`), the daemon cannot find the sensor in its current code server context — it dispatches only sensors whose `job_origin_id` matches the active gRPC server.

**Fix:**
1. Identify stale entry: `SELECT id, job_body FROM jobs WHERE job_body LIKE '%<sensor_name>%'` — confirm `__class__` is `ManagedGrpcPythonEnvRepositoryLocationOrigin`
2. Delete stale entries from both `jobs` and `instigators` tables by `id`
3. Go to Dagster UI → Automation → Sensors → enable the sensor (it will re-register with correct `GrpcServer` origin)

**Rules:**
1. Never register sensors interactively via `dagster dev` in a production environment that runs via `GrpcServer` — the origin mismatch silently orphans the sensor.
2. After any container rebuild or Dagster config change, cross-check sensors in `schedules.db` for origin type: all active sensors should use `GrpcServerRepositoryLocationOrigin`.
3. `health_db_watchdog_sensor` is the primary early-warning for DuckDB lock incidents — verify it ticks within 10 minutes of container start.

**Reference:** `orchestration/sensors/health_db_watchdog_sensor.py`; `app_data/dagster_home/schedules/schedules.db`; incident May 6 2026.

---

### L72 — Defender exclusion must cover ENTIRE `data_lake`, not just `monitoring/` subdirectory

**Symptom:** `pipeline_sapov2_realtime_job` keeps getting stuck (Runtime: 25 min, Inactive: 24 min, auto-killed by stuck_run_alerter). Occurs intermittently — some runs succeed, others hang. `sapo_warehouse.duckdb` accessible between runs but dbt step goes silent immediately.

**Root cause:** The L70 fix added Defender exclusion only for `app_data\data_lake\monitoring` (the monitoring DB path). `dllhost.exe` could still scan `sapo_warehouse.duckdb` (the dbt working DB at `app_data\data_lake\sapo_warehouse.duckdb`). When dllhost.exe holds a lock on `sapo_warehouse.duckdb`, the next dbt subprocess enters D-state (uninterruptible I/O sleep waiting for the file lock). In D-state, even `SIGKILL` is deferred — the watchdog fires but the subprocess doesn't die. No dbt output → 24 min of inactivity → stuck_run_alerter kills the Dagster run via DB state update, but zombie subprocess may persist and block the next run.

**Pattern:** Only some runs get stuck (not every run) because dllhost.exe's scan timing is intermittent — it only locks the file for a brief window immediately after each dbt write. If the next run's dbt starts during that window, it hangs.

**Fix:**
1. Kill `dllhost.exe`: `taskkill /F /IM dllhost.exe`
2. Widen exclusion to cover the entire data_lake (Admin PowerShell):
   ```powershell
   Remove-MpPreference -ExclusionPath "D:\Vantt\app\data-integration\app_data\data_lake\monitoring"
   Add-MpPreference -ExclusionPath "D:\Vantt\app\data-integration\app_data\data_lake"
   ```
3. Optionally disable Windows Search indexing for the directory:
   ```cmd
   attrib +i "D:\Vantt\app\data-integration\app_data\data_lake" /s /d
   ```
4. Kill `dllhost.exe` once more after exclusion is in place — the next spawn will not scan excluded paths.
5. Verify both DBs accessible:
   ```bash
   docker exec data_platform python3 -c "
   import duckdb
   for p in ['/app/var/data_lake/monitoring/ingestion_health.duckdb', '/app/var/data_lake/sapo_warehouse.duckdb']:
       try: c = duckdb.connect(p); c.close(); print(f'OK: {p.split(\"/\")[-1]}')
       except Exception as e: print(f'LOCKED: {p.split(\"/\")[-1]}')
   "
   ```

**Rules:**
1. Defender exclusion must cover ALL DuckDB files used by the pipeline — not just the monitoring DB. Any DuckDB file on a bind-mounted path is vulnerable.
2. Two `taskkill` calls may be needed: first to release the immediate lock, second after exclusion propagates (dllhost.exe respawns immediately after kill; the second spawn respects the exclusion).
3. D-state dbt subprocess cannot be killed by `SIGKILL` — the watchdog in `dbt.py` is ineffective when the process waits on a Windows-held file lock. Only releasing the file lock on the host unblocks it.
4. `sapo_warehouse.duckdb` lock causes 24 min stuck runs (ingestion stalls + silent dbt). `ingestion_health.duckdb` lock causes ~2 min delay per run but does NOT prevent run completion (exception caught in `finally` block).

**Reference:** `transformation/profiles.yml` (sapo_warehouse path); `app_data/data_lake/sapo_warehouse.duckdb`; incident May 6 2026 (second occurrence).

---

### L73 — Bind-mounted DuckDB file on Windows NTFS is permanently vulnerable to host-side locks

**Symptom:** `ingestion_health.duckdb` repeatedly locked by PID 0 (Windows dllhost/Defender) even after Defender exclusion was added for the full `data_lake` path. Lock recurs across restarts.

**Root cause:** Any Docker bind mount from Windows NTFS exposes files to the entire Windows filesystem stack — Defender, Search indexer, Explorer shell extensions, COM/dllhost. Defender exclusions are effective but fragile (can be reset by Windows Update or policy). Named volumes live inside the Docker Desktop Linux VM and are never accessible to Windows host processes.

**Fix:** Move the DuckDB file off the bind mount entirely — mount it via a Docker named volume that overlays the bind mount path:
```yaml
# docker-compose.yml
volumes:
  monitoring_db:  # stored in Docker VM, not NTFS

services:
  data_platform:
    volumes:
      - ./app_data/data_lake:/app/var/data_lake
      - monitoring_db:/app/var/data_lake/monitoring  # overlays bind mount for this subdir
```
Migrate existing data once:
```bash
docker run --rm \
  -v "D:/path/to/data_lake/monitoring:/source:ro" \
  -v "monitoring_db:/dest" \
  alpine sh -c "cp -a /source/. /dest/"
```
Backup coverage unchanged: backup script runs inside container and sees named volume as part of `data_lake` directory tree.

**Rules:**
1. Any DuckDB file that must never be locked by Windows → store in a named Docker volume, not a bind mount.
2. Named volume overlay on a bind-mount subpath works correctly in Docker: the more-specific mount takes precedence.
3. **NEVER recommend "restart Docker Desktop from tray" to fix a DuckDB lock** — this freezes WSL2 (`wsl.exe -l -v` times out), which requires a full Windows restart to recover.
4. The correct recovery path without named volumes: `scripts/fix-duckdb-lock.ps1` (kill dllhost + CHECKPOINT inside container, no Docker Desktop restart).

**Reference:** `docker-compose.yml` (monitoring_db volume); `scripts/fix-duckdb-lock.ps1`; incident May 6 2026 (third occurrence, resolved structurally).


## SQLite Lock Storm — Dagster Metadata DB (post-mortems 2026-05-07/08)

---

### L74 — Dagster jobs get stuck when `maintain_purge_runs_job` holds SQLite exclusive lock during VACUUM

**Symptom:** `pipeline_sapov2_realtime_job` and other short jobs complete all their work but are auto-killed as "stuck" (Inactive 9/10 min). Compute logs show `sqlite3.OperationalError: database is locked` in the step that writes Dagster completion events. Separately, `maintain_purge_runs_job` itself is killed after 15 min runtime / 5 min inactive.

**Root cause:** Two compounding issues in `maintain_purge_runs_job`:
1. **VACUUM on compact index.db**: SQLite VACUUM holds an exclusive lock for its entire duration. `index.db` was 860 MB but 0% fragmented (no free pages) — VACUUM ran for minutes, gained nothing, and blocked every other Dagster process writing to `index.db` during that window.
2. **`SELECT DISTINCT run_id FROM event_logs` with no heartbeat**: 205K-row full scan ran in the main thread for 2–5 min with no `context.log.info()` calls → Dagster inactivity watchdog fired after 5 min of silence and killed the purge job.

**Fix (`orchestration/ops/purge_runs.py`):**
```python
# 1. Skip VACUUM when freelist < 5% of pages (already compact)
free_pct = freelist_count / max(page_count, 1) * 100
if free_pct < 5.0:
    log.info(f"VACUUM skipped: {free_pct:.1f}% free pages — already compact")
    return size_before, size_before

# 2. Run DISTINCT scan in background thread with 30s heartbeats (same pattern as VACUUM)
_SCAN_TIMEOUT = 300  # skip if too slow
while not _done.wait(timeout=30):
    elapsed += 30
    log.info(f"event_logs DISTINCT scan in progress... ({elapsed}s elapsed)")
    if elapsed >= _SCAN_TIMEOUT:
        return 0
```

**Rules:**
1. SQLite `VACUUM` takes an **exclusive lock** for its entire run — never run it on a file shared with active Dagster processes unless the database is actually fragmented (freelist > 5–10%).
2. Check fragmentation before VACUUM: `PRAGMA freelist_count` / `PRAGMA page_count`. If free% < 5, VACUUM costs minutes of lock time and shrinks nothing.
3. Any blocking operation (SQL scan, subprocess, API call) that may take >3 min inside a Dagster op **must** emit `context.log.info()` at least every 4 min, or the inactivity watchdog will kill the run. Use a background thread + heartbeat loop for unbounded operations.
4. The inactivity watchdog threshold is **5 min** of log silence (see `sensors/stuck_run_alerter.py`). Budget heartbeats at ≤30s intervals for safety.
5. When diagnosing "stuck" runs, check the `.err` compute log — `sqlite3.OperationalError: database is locked` with a SQLAlchemy stack trace means another process holds an exclusive SQLite lock, not that the job's own code is hung.

**Reference:** `orchestration/ops/purge_runs.py` (`_vacuum_index_db`, `_cleanup_orphan_event_entries`); incident May 7 2026.

---

### L75 — Dagster ops that call external helpers without `context.log` are invisible to the inactivity watchdog

**Symptom:** Jobs that contain slow helper functions (DuckDB window queries, API calls, metadata scans) get killed by the stuck-run watchdog even though they are actively working. No heartbeat appears in the Dagster event log during the slow phase.

**Root cause:** Python `logging.getLogger(__name__)` writes to stderr/stdout but does **not** create Dagster log events. The stuck-run alerter tracks the last Dagster log event timestamp, not the process's stdout. Helper functions that use only `logger.info()` (module-level) are completely invisible to the watchdog.

**Examples found (fixed May 7 2026):**
- `morning_digest._fetch_stats()`: 4 blocking DuckDB queries (window functions + median), used `logger` not `context.log` — no Dagster events for up to 5 min.
- `reconciliation.recon_sapo_orders_daily()`: called `count_orders()` (external Sapo API) with log only **after** the call returned.

**Fix pattern:**
```python
# Bad: helper uses module logger, invisible to watchdog
def _fetch_stats(db_path):
    rows = conn.execute(BIG_QUERY).fetchall()  # silent for 3+ min

# Good: pass log callable through, emit before blocking call
def _fetch_stats(db_path, log=None):
    def _hb(msg):
        (log or logger.info)(msg)
    _hb("running main stats query...")
    rows = conn.execute(BIG_QUERY).fetchall()
    _hb(f"done ({len(rows)} rows)")

# In the @op:
def my_op(context):
    _fetch_stats(db_path, log=context.log.info)
```

**Rules:**
1. Every `@op` / `@asset` that calls helpers taking >30s must pass `context.log.info` (or equivalent) into those helpers.
2. Add a `context.log.info(...)` **before** every external call (API, subprocess, DuckDB query) that has no internal logging.
3. `logger = logging.getLogger(__name__)` output is NOT visible to the Dagster inactivity watchdog — only `context.log.*` calls create Dagster events.
4. For unbounded operations in helpers (cannot know duration in advance), use the background-thread + heartbeat-loop pattern from `_vacuum_index_db` in `purge_runs.py`.

**Reference:** `orchestration/ops/morning_digest.py` (`_fetch_stats`, `build_digest_rows`, `compose_and_send_digest`); `orchestration/assets/reconciliation.py` (all 4 recon assets); incident May 7 2026.

---

### L77 — Single-shot cross-DB DELETE on index.db holds exclusive lock for ~81s, causing zombie NOT_STARTED runs

**Symptom:** `pipeline_sapov2_realtime_job` and `pipeline_sapov2_incremental_job` appear as NOT_STARTED for 90 min then get auto-canceled. `maintain_purge_runs_job` runs normally but `SchedulerDaemon` logs `sqlite3.OperationalError: database is locked` at `store_event()` during the purge window. `QueuedRunCoordinator` goes silent for ~95 min after the lock clears.

**Root cause:** `_cleanup_orphan_asset_check_executions` ran a single `DELETE FROM asset_check_executions WHERE run_id NOT IN (SELECT run_id FROM runsdb.runs)` with `runs.db` ATTACHed to `index.db`. With 68,604 rows to delete, SQLite held an **exclusive write lock on `index.db` for ~81 seconds**. During this window, `SchedulerDaemon`'s `create_run()` wrote the run record to `runs.db` but failed on the `store_event()` write to `index.db` → half-baked NOT_STARTED run (record exists, no events). `QueuedRunCoordinator` then entered a long backoff (~95 min) after hitting the same locked DB.

This was a sibling bug to L74 (VACUUM lock) — same class, different function. L74/L75 were fixed May 7 but `_cleanup_orphan_asset_check_executions` was overlooked.

**Fix:** Two-phase approach:
1. **Phase 1 (shared read):** ATTACH SELECT to find orphan run_ids — brief read lock only.
2. **Phase 2 (batched write):** DELETE in batches of 50 run_ids with 0.1s sleep between batches — each batch holds exclusive lock <1s, other writers get windows between batches. Runs in background thread with 30s heartbeats.

```python
# Phase 1: shared read — find orphan run_ids
conn.execute(f"ATTACH DATABASE '{runs_path}' AS runsdb")
orphan_ids = [row[0] for row in conn.execute(
    "SELECT DISTINCT run_id FROM asset_check_executions "
    "WHERE run_id NOT IN (SELECT run_id FROM runsdb.runs)"
).fetchall()]
conn.execute("DETACH DATABASE runsdb")

# Phase 2: batched delete — each batch holds exclusive lock < 1s
for i in range(0, len(orphan_ids), 50):
    batch = orphan_ids[i:i+50]
    conn.execute(f"DELETE FROM asset_check_executions WHERE run_id IN ({','.join('?'*len(batch))})", batch)
    conn.commit()
    time.sleep(0.1)  # yield lock window between batches
```

**Rules:**
1. Any SQLite DELETE that touches >1K rows on a shared database (`index.db`, `runs.db`) **must be batched** — never one-shot. Each batch should hold the exclusive lock <1s.
2. When fixing a class of bugs (e.g., "long exclusive SQLite locks"), audit ALL callers that open `index.db` for writes, not just the one that triggered the alert. `_cleanup_orphan_asset_check_executions` had the same pattern as the VACUUM that was fixed in L74 but was missed.
3. A zombie NOT_STARTED run (run_id in `runs.db`, no events in `index.db`) is the signature of a failed `create_run()` mid-write. The run will block the schedule's self-overlap check until it times out (QUEUE_STUCK_THRESHOLD).
4. `QueuedRunCoordinator` entering a long backoff (>10 min silence) after a lock storm indicates it hit repeated errors during the lock window. The coordinator recovers on its own once the lock clears — no manual intervention needed, but it will take 10–95 min depending on backoff state.

**Reference:** `orchestration/ops/purge_runs.py` (`_cleanup_orphan_asset_check_executions`); incident May 8 2026.

---

### L78 — QUEUE_STUCK_THRESHOLD at 90 min was masking the real fix deadline

**Symptom:** Queue-zombie runs (NOT_STARTED, daemon never dequeued) sat for 90 min before auto-cancel. This made the root-cause window (the ~81s lock storm) seem less severe than it was — the system looked "recovered" after 90 min even though the real problem repeated every day.

**Root cause:** `QUEUE_STUCK_THRESHOLD = timedelta(minutes=90)` was sized for the worst-case legitimate wait (nightly job ~60 min) before `_long_dbt_rw_holder` was added. After `_long_dbt_rw_holder` began skipping ticks while nightly was running, the maximum legitimate NOT_STARTED wait dropped to ~10 min (one realtime/incremental job ahead in the `dbt_rw=1` queue). The 90 min threshold was never updated.

**Fix:** Reduce to 20 min — covers max legitimate wait (~10 min) with a 10 min buffer. Zombie runs from future lock storms now get cleaned up in 20 min instead of 90.

**Rules:**
1. After adding a mechanism that reduces legitimate queue wait time (like `_long_dbt_rw_holder`), always re-evaluate `QUEUE_STUCK_THRESHOLD` — it should be `max_legitimate_wait + buffer`, not an old worst-case.
2. A 90 min cleanup window for a 81s root cause means the symptom (stuck jobs, missed ticks) persists for 90 min after the actual problem is gone. Tighter thresholds give faster self-healing.
3. When `_long_dbt_rw_holder` is the mechanism preventing NOT_STARTED accumulation during nightly runs, the threshold can safely be `nightly_skips_ticks → max_wait = max(realtime_runtime, incremental_runtime) + buffer`.

**Reference:** `orchestration/sensors/stuck_run_alerter.py` (`QUEUE_STUCK_THRESHOLD`); `orchestration/definitions.py` (`_long_dbt_rw_holder`); incident May 8 2026.


## Sapo API Quirks

---

### L76 — Sapo orders API silently ignores `created_on_min/max` filter, returns all historical orders

**Symptom:** KPI closure revenue check reports Sapo source revenue ~19× higher than warehouse (e.g. 739M vs 39M, −94.69% drift). Warehouse figure matches real daily volume (verified via webhook order count × avg order value).

**Root cause:** The Sapo `/admin/orders.json` endpoint **ignores `created_on_min` / `created_on_max` query params** — only `modified_on_min/max` is reliably supported (confirmed in `plans/archive/260415-1749-ingestion-trust-engineering/research/sapo-page-metadata-verification.md`). When `sum_revenue_orders()` sends `created_on_min/max`, the API returns **all historical orders** (no date filter applied), paginating up to 200 pages × 250 = 50 000 orders. The function sums the entire history, not just the target day.

The 19× ratio equals `total_historical_orders / daily_orders` — consistent with a small business with ~500 total orders and ~27 new orders/day.

**Fix:** Replace live API call with a raw DuckDB query against `raw__sapo.order`, filtering on `$.created_on` cast as TIMESTAMPTZ. Same approach used by `_sapo_dest_count_customers` in `reconciliation.py`.

```python
# WRONG — API ignores created_on filter
params = {
    "created_on_min": window_start.strftime("%Y-%m-%dT%H:%M:%S"),
    "created_on_max": window_end.strftime("%Y-%m-%dT%H:%M:%S"),
    "limit": 250, "page": 1,
}
# returns ALL orders → sums entire history

# CORRECT — query raw DB directly
conn.execute("""
    SELECT COALESCE(SUM(CAST(json_extract_string(payload, '$.total') AS DOUBLE)), 0)
    FROM raw__sapo.order
    WHERE TRY_CAST(json_extract_string(payload, '$.created_on') AS TIMESTAMPTZ) >= ?
      AND TRY_CAST(json_extract_string(payload, '$.created_on') AS TIMESTAMPTZ) < ?
      AND LOWER(json_extract_string(payload, '$.status')) NOT IN ('cancelled', 'voided')
""", [window_start, window_end])
```

**Corollary — confirmed supported filters for Sapo API:**
| Entity | Working filter | NOT working |
|---|---|---|
| Orders | `modified_on_min/max` | `created_on_min/max` (silently ignored) |
| Customers | `created_on_min/max` | `modified_on_min/max` (no reliable support) |

**Side effect — naive timestamp timezone bug (separate −1% recon drift issue):**
`count_orders` / `count_customers` both format UTC datetimes with `strftime("%Y-%m-%dT%H:%M:%S")` (no `+00:00` marker). Sapo likely interprets these as ICT (UTC+7), shifting the window by 7 hours. This causes the API to count ~1 extra order per 100 at the boundary → consistent −1.0% drift in both `recon_sapo_orders_daily` and `recon_sapo_customers_daily`. Small, accepted for now; fix by appending `+07:00` to the formatted string if Sapo definitely reads ICT.

**Rules:**
1. Verify every Sapo API filter param against the research doc before trusting it — Sapo APIs have inconsistent filter support across entities.
2. For revenue/count verification, prefer reading the raw DuckDB (`raw__sapo.order`) over the live Sapo API — raw DB avoids rate limits, is always available, and gives the exact same data that flows to the warehouse.
3. A KPI drift of >50% always means a windowing/filter bug, not real data divergence — investigate the query first, not the data.
4. When a live API call is replaced by a raw DB query in a KPI check, it no longer tests ingestion completeness — document this scope change clearly.

**Reference:** `orchestration/assets/kpi_closure.py` — fixed 2026-05-07

---

### L79 — `raw/raw.duckdb` không tồn tại; raw Sapo data nằm ở `sapo_raw/order/` dưới dạng Delta Lake parquet

**Symptom:** `_fetch_sapo_revenue` log `WARNING: raw DB not found at /app/var/data_lake/raw/raw.duckdb` mỗi ngày → KPI check trả về `None` → `partial_source` status bật liên tục, morning digest mất revenue signal.

**Root cause:** Commit L76 fix thay thế live Sapo API bằng raw DuckDB query nhưng giả định path `raw/raw.duckdb` (theo schema `raw__sapo.order`). Trong môi trường thực tế, ingestion pipeline **không tạo `raw.duckdb`** — Sapo orders được lưu dưới dạng Delta Lake parquet tại `sapo_raw/order/ingest_method=*/date_key=*/**/*.parquet`. `raw.duckdb` chưa bao giờ tồn tại trong project này.

**Fix:** Dùng `duckdb.connect()` (in-memory) + `read_parquet()` với glob pattern, deduplicate `entity_id` bằng `ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY event_timestamp DESC)` để tránh double-count orders xuất hiện ở nhiều `ingest_method`.

```python
# WRONG — raw.duckdb không tồn tại trong env này
_RAW_DB_PATH = os.path.join(_DATA_LAKE, "raw", "raw.duckdb")
conn = duckdb.connect(_RAW_DB_PATH, read_only=True)
conn.execute("SELECT ... FROM raw__sapo.order WHERE ...")

# CORRECT — đọc parquet trực tiếp, dedup theo entity_id
_SAPO_ORDER_PATH = os.path.join(_DATA_LAKE, "sapo_raw", "order")
parquet_glob = _SAPO_ORDER_PATH.replace("\\", "/") + "/ingest_method=*/**/*.parquet"
conn = duckdb.connect()  # in-memory
conn.execute(f"""
    WITH deduped AS (
        SELECT payload, ROW_NUMBER() OVER (
            PARTITION BY json_extract_string(payload, '$.id')
            ORDER BY event_timestamp DESC
        ) AS rn
        FROM read_parquet('{parquet_glob}', hive_partitioning=false)
    )
    SELECT COALESCE(SUM(CAST(json_extract_string(payload, '$.total') AS DOUBLE)), 0)
    FROM deduped
    WHERE rn = 1
      AND TRY_CAST(json_extract_string(payload, '$.created_on') AS TIMESTAMPTZ) >= ?
      AND TRY_CAST(json_extract_string(payload, '$.created_on') AS TIMESTAMPTZ) < ?
      AND LOWER(json_extract_string(payload, '$.status')) NOT IN (...)
""", [window_start, window_end])
```

**Rules:**
1. Trước khi hardcode bất kỳ DB path nào, verify bằng `os.path.exists()` **và** log warning rõ ràng khi không tồn tại — đừng silently skip với `return None`.
2. Raw Sapo data trong project này nằm ở `sapo_raw/<entity>/` dạng Delta Lake parquet, **không** có `raw.duckdb`. Xem `docs/architecture/data-flow.md` cho storage layout chính xác.
3. Khi dữ liệu raw được lưu ở nhiều `ingest_method` partition (webhook + incremental + historical), **luôn dedup theo `entity_id`** trước khi aggregate — một order có thể xuất hiện ở 2-3 partition khác nhau.
4. Dùng `duckdb.connect()` in-memory + `read_parquet()` khi không cần persistent connection — tránh tạo file `.duckdb` thừa.

**Reference:** `orchestration/assets/kpi_closure.py` (`_fetch_sapo_revenue`) — fixed 2026-05-08

---

## SQLite Lock Storm — False-Positive Stuck Kills (post-mortem 2026-05-09)

---

### L80 — Khi `last_event_time = None` do SQLite lock, stuck alerter không được fallback về `start_dt`

**Symptom:** Ingestion jobs bị kill lúc ~1:20 AM mỗi đêm trong khi thực sự đang chạy bình thường. `stuck_run_alerter` log `killing run <id> — inactive since <start_dt>` dù job không thực sự inactive. Pattern lặp lại sau khi đã fix L74 (VACUUM lock) và L77 (batched DELETE lock).

**Root cause:** `purge_runs` VACUUM giữ exclusive lock trên `index.db` ~15-20 phút. Trong window này, `stuck_run_alerter._get_last_event_time(run_id)` gọi `DagsterEventLogStorage.get_logs_for_run()` → SQLite read fail → trả về `None`. Code cũ xử lý `None` bằng cách **fallback về `start_dt`**:

```python
# CODE CŨ — NGUY HIỂM
last_event_time = _get_last_event_time(run_id) or run.start_time
if now - last_event_time > INACTIVITY_THRESHOLD:
    kill(run_id)  # ← kills healthy job đang chạy bình thường
```

Khi `start_dt` của job > `INACTIVITY_THRESHOLD` trước hiện tại (job đã chạy lâu), alerter kết luận job "inactive" và kill. Jobs bắt đầu ~23:00, bị kill lúc ~1:20 AM (90 phút sau) — đúng bằng `QUEUE_STUCK_THRESHOLD` cũ.

Đây là hệ quả thứ 3 của cùng một root cause "SQLite exclusive lock → caller nhận `None`/exception" — L74 (VACUUM), L77 (batched DELETE) fix phía gây lock; L80 fix phía đọc lock.

**Fix:**
```python
# CORRECT — skip check khi log unreadable, không fallback
last_event_time = _get_last_event_time(run_id)
if last_event_time is None:
    context.log.warning("run %s: event log unreadable (DB locked?), skipping inactivity check", run_id)
    continue  # ← không kill, không fallback

if now - last_event_time > INACTIVITY_THRESHOLD:
    kill(run_id)
```

Ngoài ra: `realtime_schedule` và `incremental_schedule` được cấu hình `yield_to` cho `maintain_purge_runs_job`, ngăn schedule tạo run mới trong ~15-20 phút purge window — tránh NOT_STARTED accumulation.

**Rules:**
1. Khi một monitoring/alerter system nhận `None` từ storage read, đó là signal "cannot determine state" — **không được suy diễn state từ fallback**. Skip the check là đúng; giả định worst-case (= inactive) là sai.
2. `None` từ `get_logs_for_run()` = DB locked **hoặc** run chưa có event — cả hai đều không phải "inactive". Phân biệt 2 case nếu cần: check `run.status` trước.
3. Khi fix một class bug (SQLite exclusive lock), audit tất cả callers nhận `None`/exception từ storage, không chỉ callers gây lock. L74+L77 fix phía write; L80 fix phía read.
4. False-positive kill pattern: nếu job bị kill đúng sau `INACTIVITY_THRESHOLD` kể từ `start_dt` (không phải kể từ last event), nguyên nhân gần như chắc chắn là fallback-to-start_dt bug.

**Reference:** `orchestration/sensors/stuck_run_alerter.py`; `orchestration/definitions.py` (`yield_to` config) — fixed 2026-05-09

---

## Docker Compose & Infrastructure

---

### L81 — Docker Compose interpolates `$` trong `env_file` values — bcrypt hash phải escape `$` thành `$$`

**Symptom:** Caddy fileserver trả về HTTP 401 cho tất cả requests kể cả khi dùng đúng password. Không có error log từ Caddy. `{$FILESERVER_PASSWORD_HASH}` trong Caddyfile nhận được string rỗng hoặc truncated hash.

**Root cause:** Bcrypt hashes có dạng `$2a$14$<salt><hash>` — chứa nhiều ký tự `$`. Docker Compose **interpolate `env_file` values** theo cùng cơ chế với `environment:` block: `$VAR` hoặc `${VAR}` bị thay thế bằng giá trị env var tương ứng (hoặc chuỗi rỗng nếu không tồn tại). Kết quả: hash bị cắt nát trước khi truyền vào container.

Ví dụ: `$2a$14$abc` → Docker Compose đọc `$2a` (expand thành ``) và `$14` (expand thành ``) → container nhận `abc` thay vì full hash.

**Fix:** Escape mọi `$` thành `$$` khi paste bcrypt hash vào `.env` file:

```bash
# Raw hash từ: docker run --rm caddy:alpine caddy hash-password --plaintext 'mypassword'
# Output: $2a$14$abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMN

# WRONG — Docker Compose sẽ interpolate $2a, $14, ...
FILESERVER_PASSWORD_HASH=$2a$14$abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMN

# CORRECT — escape mọi $ thành $$
FILESERVER_PASSWORD_HASH=$$2a$$14$$abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMN
```

Trong Caddyfile dùng `{$FILESERVER_PASSWORD_HASH}` (Caddy env var syntax) — Caddy đọc env var **sau khi** Docker Compose đã inject giá trị vào container, nên Caddyfile không cần escape.

**Rules:**
1. Bất kỳ secret nào chứa `$` (bcrypt, argon2, scrypt hash; regex patterns; connection strings) khi đặt trong `env_file` của Docker Compose **phải escape `$` → `$$`**.
2. Rule này áp dụng cho cả `env_file:` và inline `environment:` trong `docker-compose.yml`. Chỉ không áp dụng khi dùng `$$` trong Compose file (escape cho Compose interpolation).
3. Quick test: `docker compose config` in ra config đã interpolate — dùng để verify hash không bị truncate trước khi restart container.
4. Caddyfile syntax `{$VAR_NAME}` là Caddy-native env var expansion, hoạt động độc lập với Docker Compose interpolation. Không cần escape trong Caddyfile.

**Reference:** `caddy/Caddyfile`; `.env.docker.example` (FILESERVER_PASSWORD_HASH comment) — added 2026-05-09

---

### L82 — Orphaned POSIX record lock (PID 0) trên named volume sau container restart

**Symptom:** `ingestion_health.duckdb` bị lock với "Conflicting lock is held in PID 0, stale 22.1 giờ". Khác với L62 (dllhost): `flock()` thành công, `/proc/locks` trống, không có process nào giữ file — nhưng `fcntl(F_GETLK)` trả về `l_pid=0, l_type=F_WRLCK`. Named volume (ext4, `/dev/sdf`) đã được mount đúng — dllhost không phải nguyên nhân.

**Root cause:** POSIX record lock (fcntl `F_SETLK`) được ghi vào kernel gắn với block device (`/dev/sdf`). Khi một Dagster worker process mở DB và bị kill không sạch (OOM, SIGKILL từ Docker), lock bị "orphan" — process chết nhưng lock vẫn tồn tại trong kernel state của block device. Container restart không clear lock này vì named volume block device được tái sử dụng. Trong PID namespace mới, kernel không tìm được owner → báo `PID 0`.

**Tại sao L73 (named volume) không đủ:** Named volume giải quyết lock do Windows-side (dllhost, Defender). Nhưng POSIX record lock orphan trên named volume là vấn đề khác — xảy ra khi process bên trong container bị kill mà không cleanup.

**Fix:** Copy file sang inode mới. POSIX record lock gắn với inode cụ thể, không theo path. Copy tạo inode mới không có lock; swap nguyên tử bằng `mv`.

```bash
docker exec data_platform sh -c "
  cd /app/var/data_lake/monitoring
  cp ingestion_health.duckdb ingestion_health.duckdb.new
  mv ingestion_health.duckdb ingestion_health.duckdb.locked
  mv ingestion_health.duckdb.new ingestion_health.duckdb
"
# Verify
docker exec data_platform python3 -c "
import duckdb; conn = duckdb.connect('/app/var/data_lake/monitoring/ingestion_health.duckdb')
conn.execute('CHECKPOINT'); conn.close(); print('OK')
"
# Cleanup
docker exec data_platform rm /app/var/data_lake/monitoring/ingestion_health.duckdb.locked
```

**Distinguish from L62 (dllhost):**
| | L62 dllhost | L82 POSIX orphan |
|---|---|---|
| flock() | blocked | succeeds |
| /proc/locks | entry exists | empty |
| fcntl F_GETLK | PID of dllhost | PID 0, F_WRLCK |
| Volume type | bind mount (Windows path) | named volume (ext4) |
| Fix | taskkill dllhost | cp → mv (new inode) |

**Prevention:** Ensure Dagster workers/ops use `try/finally` to close DuckDB connections. `ingestion_health._connect()` already has context manager — ensure callers use `with` pattern. Catastrophic kills (OOM) still cause orphan; script `scripts/fix-duckdb-orphan-lock.sh` recommended.

**Rules:**
1. "PID 0, stale N hours" + flock OK + /proc/locks empty = POSIX orphan lock. Fix: copy to new inode.
2. Named volumes prevent Windows host locks, but NOT Linux kernel orphan locks.
3. POSIX record locks outlive processes if the block device persists (named volumes, mounted filesystems).
4. Always test lock type with `fcntl(F_GETLK)` before assuming dllhost — the fix depends on the lock type.

**Reference:** `app_data/data_lake/monitoring/` (named volume); incident 2026-05-10; L62 for comparison.

---

### L83 — KPI và recon window phải dùng ICT midnight, không phải UTC midnight

**Symptom:** Morning report báo lệch doanh thu ~15%: Sapo source 6.7M ₫ vs Warehouse 5.7M ₫. Xảy ra mỗi ngày, không phải random.

**Root cause:** `_yesterday_window_utc()` tính "hôm qua" từ đồng hồ UTC. Asset KPI chạy lúc 04:45 ICT = 21:45 UTC — lúc này UTC **vẫn còn ngày hôm trước**:

```
04:45 ICT ngày 13/05  →  21:45 UTC ngày 12/05
_yesterday_window_utc() trả về:
  window_start = 2026-05-11 00:00 UTC  (!) ← UTC "hôm qua" = 11/05
  date_key     = 20260511 (UTC)
```

Nhưng `fact_orders.date_key` được tính bằng `strftime(created_at, '%Y%m%d')` với DuckDB `TimeZone=Asia/Ho_Chi_Minh` (khai báo trong `transformation/profiles.yml`) — đây là **ngày ICT**, không phải ngày UTC.

Kết quả: source đếm đơn trong window UTC ngày 11/05 (= ICT 07:00 ngày 11 → 07:00 ngày 12), nhưng warehouse `date_key = 20260511` chứa đơn ICT ngày 11/05 (= ICT 00:00 → 23:59 ngày 11). Hai window lệch nhau 7 tiếng — đơn tạo lúc 00:00–07:00 ICT không cùng chiều.

**Fix:** Dùng ICT midnight làm ranh giới ngày trong mọi "yesterday window":

```python
_ICT = timezone(timedelta(hours=7))

def _yesterday_window_ict() -> tuple[datetime, datetime]:
    now_ict = datetime.now(_ICT)
    today_ict = now_ict.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_ict = today_ict - timedelta(days=1)
    return yesterday_ict, today_ict  # ICT-aware datetimes (+07:00)
```

ICT-aware datetime hoạt động đúng với cả hai use case:
- **Sapo API:** `dt.strftime("%Y-%m-%dT%H:%M:%S")` strip timezone → gửi ICT local string "2026-05-12T00:00:00" (Sapo interpret đúng)
- **Raw DB TIMESTAMPTZ:** DuckDB so sánh `2026-05-12T00:00:00+07:00` vs `"2026-05-11T17:00:00Z"` — khớp vì cùng point in time

**Files đã fix:** `orchestration/assets/kpi_closure.py`, `orchestration/assets/reconciliation.py`

**Rules:**
1. Bất kỳ "yesterday window" nào so sánh với `fact_orders.date_key` PHẢI dùng ICT midnight boundary.
2. `fact_orders.date_key` = ICT date (vì `profiles.yml` set `TimeZone: 'Asia/Ho_Chi_Minh'`). Đây là intentional — phục vụ business day Việt Nam.
3. Sapo timestamps có suffix `Z` (UTC) — pipeline lưu đúng dạng UTC. ICT chỉ cần khi cắt boundary ngày.
4. Symptom đặc trưng: drift ổn định ~15% (không random) = timezone mismatch, không phải ingestion gap.

**Reference:** `orchestration/assets/kpi_closure.py`; `transformation/profiles.yml:16`; incident 2026-05-12

---

### L84 — UTC storage + ICT display là architecture chuẩn cho pipeline Việt Nam

**Pattern:**

```
External API (Sapo)  →  "2026-05-01T01:28:14Z"  (UTC, có 'Z')
         ↓
Pipeline storage     →  TIMESTAMPTZ              (UTC-aware, lưu nguyên)
         ↓
dbt transformation   →  strftime với TimeZone=Asia/Ho_Chi_Minh
         ↓
fact_orders.date_key →  20260501                 (ngày ICT, dùng cho báo cáo VN)
```

**Verification mẫu:**

```python
# "2026-05-01T01:28:14Z" = 01:28 UTC = 08:28 ICT
raw_string   = "2026-05-01T01:28:14Z"
stored_utc   = 2026-05-01 01:28:14+00:00   # lưu trong parquet
display_ict  = 2026-05-01 08:28:14+07:00   # khi query với session timezone ICT
date_key     = 20260501                     # ngày ICT = ngày biz VN
```

**Tại sao UTC storage?**
- UTC không bao giờ có daylight saving time (DST) hay offset thay đổi
- Unambiguous trên mọi hệ thống — không cần biết "timezone của server là gì"
- Dễ tích hợp với hệ thống khác (S3, BigQuery, Kafka đều dùng UTC)
- Khi business mở rộng timezone khác: data cũ vẫn đúng, chỉ cần đổi display layer

**Tại sao ICT display ở serving layer?**
- Business users tại Việt Nam nhìn báo cáo theo giờ Việt Nam
- `date_key = 20260501` nghĩa là "ngày 1/5 theo lịch Việt Nam", không phải lịch UTC

**Quy tắc cho code mới:**
1. Luôn dùng `TIMESTAMPTZ` (không phải `TIMESTAMP`) cho timestamps — naive TIMESTAMP mất timezone context
2. Luôn lưu UTC; chỉ convert sang ICT ở serving/display layer
3. Khi so sánh window với warehouse: dùng ICT boundary (xem L83)
4. `strftime` trên `TIMESTAMPTZ` phụ thuộc DuckDB session `TimeZone` — luôn verify setting trước khi dùng

**Reference:** `transformation/profiles.yml`; `orchestration/assets/kpi_closure.py`; memory `feedback_timestamp_timezone`

---

## Metabase Blueprint Authoring (SERVE)

### L93 — Metabase text card at row 0 wins position conflict over question widget at same row

**Symptom:** A section-heading text card appears as the first widget on a tab, ahead of a date-display question card that was also placed at `row: 0`.

**Root cause:** When two dashcards share the same `row`/`col`, Metabase gives priority to text cards over question cards during layout resolution. The intended order (date display first, section heading second) was lost because both had `"row": 0`.

**Fix:** Move the section heading text card to `row: 2` (the first free row after the 2-row-tall date card), then cascade all downstream widget rows +1.

**Rules:**
1. No two dashcards may share the same `row` + `col` origin in a blueprint — check for conflicts before deploying.
2. A text card and a question card at the same row will not coexist cleanly; text card wins.
3. When inserting a new row above existing content, increment every widget below it by the height of the inserted item.

---

### L94 — `fact_sales` queries referencing `o.channel_key` without joining `fact_orders` cause query errors on all product widgets

**Symptom:** All widgets on the Sản phẩm tab error out with an "unknown column" or "table not found" error for alias `o`.

**Root cause:** Blueprint queries were copied from `fact_orders`-based templates and kept the `o.channel_key` filter, but the Sản phẩm queries only join `fact_sales s`, `dim_products p`, `dim_customers c` — no `fact_orders o` alias exists.

**Fix:** Add `JOIN fact_orders o ON s.order_id = o.order_id` to each affected query. Also change `dim_customers c ON s.customer_key` → `c ON o.customer_key` since `fact_sales` does not carry `customer_key` directly.

**Rules:**
1. When filtering by `channel_key` in a `fact_sales`-primary query, always join `fact_orders` first — `fact_sales` has `order_id` but not `channel_key`.
2. After copying a query template, verify every alias referenced in WHERE/JOIN clauses exists in the FROM clause.
3. `c.customer_type` filter must join through `fact_orders.customer_key`, not `fact_sales.customer_key` (which may not exist).

---

## Seed Data Quality & Mapping (MODEL)

### L85 — Trailing comma trong CSV seed phá vỡ LIKE mapping, silently misclassifies toàn bộ channel

**Symptom:** Dashboard hiển thị `Shopee (Unspecified)` cho đơn hàng Shopee - Fine Japan Vietnam. 256 đơn (~100% FJV orders) bị misclassify trong nhiều tháng. Không có lỗi build, không có test failure.

**Root cause:** Seed `ref_order_sources.csv` có dòng:
```
3988158_1,...,"Shopee_Fine Japan Vietnam,",...
```
CSV parser giữ nguyên trailing comma → `mapping_tag = 'Shopee_Fine Japan Vietnam,'` (có dấu phẩy cuối). `stg_sapo_orders.sql` dùng:
```sql
o.tags LIKE '%' || mt.mapping_tag || '%'
-- becomes: o.tags LIKE '%Shopee_Fine Japan Vietnam,%'
```
Tags JSON thực tế: `["Shopee","Shopee_Fine Japan Vietnam"]` — sau `Vietnam` luôn là `"` rồi `]`, **không bao giờ có bare comma**. LIKE không bao giờ match → fallback về generic `source_id=3988158` → `dim_channels` gán suffix `(Unspecified)`.

**Fix:** Bỏ trailing comma trong CSV seed:
```
# Before
"Shopee_Fine Japan Vietnam,"
# After
Shopee_Fine Japan Vietnam
```
Sau đó `dbt seed --select ref_order_sources` + `dbt run --full-refresh --select src_sapo_orders+` (full-refresh vì `src_sapo_orders` là incremental — đơn cũ đã lưu với wrong `final_source_id`, incremental run không reprocess chúng).

**Rules:**
1. Mapping_tag trong CSV seed dùng LIKE match — **không được có ký tự đặc biệt ở đầu/cuối** (space, comma, quote). Luôn `trim()` khi kiểm tra thủ công.
2. CSV field chứa dấu phẩy → dùng double-quote wrapping → **dễ nhầm lẫn**: `"value,"` trong CSV là value có trailing comma, không phải separator artifact.
3. Silent misclassification không raise error — cần data test: `assert count(channel_name = 'Shopee (Unspecified)') < threshold` hoặc `assert count(channel_name LIKE 'Shopee - %') / count(source_id = '3988158') > 0.95`.
4. Sau `dbt seed` thay đổi reference data: luôn full-refresh incremental models downstream nếu reference data ảnh hưởng đến staging join.

**Reference:** `transformation/seeds/ref_order_sources.csv:31`; `transformation/models/staging/stg_sapo_orders.sql:26-34`


### L86 — Metabase progress.goal là số tĩnh — không thể dùng query column làm goal động

**Symptom:** Widget "MTD Revenue vs Target" hiển thị goal = 4,000,000,000 (hardcoded) mặc dù pipeline đã ingest target từ Google Sheets vào `fact_targets`. Progress bar misleading vì goal không khớp thực tế.

**Root cause:** Hai bugs chồng nhau:
1. `monthly_target` CTE trong SQL được tính đúng từ `fact_targets` nhưng **không được JOIN hoặc SELECT** — bị discard hoàn toàn. `progress.goal: 4000000000` là placeholder tĩnh không liên quan đến data.
2. CTE thiếu `AND metric_code = 'net_revenue'` (hoặc `'gmv'`) — nếu được dùng sẽ SUM tất cả metric targets (gmv + orders + profit), sai semantic.

Thêm vào đó: Metabase `progress` display **không hỗ trợ goal từ query column** — `progress.goal` luôn là số tĩnh trong `visualization_settings`, kể cả khi SQL trả về 2 cột (cột 2 không tự động thành goal).

**Fix:**
- Thêm `metric_code = 'gmv'` filter vào CTE
- Đổi actual metric từ `net_revenue` sang `gross_revenue` để khớp semantic với target GMV
- Set `progress.goal` = giá trị thực từ `fact_targets` (query thủ công rồi hardcode)
- Khi deploy blueprint: query `SELECT SUM(target_val) FROM fact_targets WHERE metric_code='gmv' AND cycle_start_date <= current_date AND cycle_end_date >= current_date` để lấy giá trị mới nhất

**Rules:**
1. Khi viết SQL cho Metabase progress card: luôn kiểm tra CTE có thực sự được SELECT không — unused CTE không raise lỗi.
2. `fact_targets` có nhiều `metric_code` — luôn filter đúng metric khi aggregate target.
3. `progress.goal` trong Metabase là tĩnh. Pipeline ingest target đúng không nghĩa là goal tự động cập nhật — đây là giới hạn Metabase, không phải lỗi pipeline.
4. Khi target đồng đều nhiều tháng (repeat_until), hardcode `progress.goal` là chấp nhận được — chỉ cần redeploy khi giá trị target thực sự thay đổi.

**Reference:** `docs/analytics-handbook/blueprints/ceo_weekly_pulse.md` — Question: MTD Revenue vs Target; `ingestion/src/gsheet_targets.py`; Dashboard 11 card 884, Dashboard 43 card 1250

### L87 — Direct API card patch không tự sync blueprint — blueprint drift silently

**Symptom:** Card 885 (Pace Index, Dashboard 11) hiển thị sai sau khi card 884 và 1250/1251 đã được fix. Blueprint trông đúng nhưng live card vẫn dùng SQL cũ.

**Root cause:** Khi fix card trực tiếp qua Metabase API (`PUT /api/card/:id`), blueprint markdown không tự cập nhật. Ngược lại, khi deploy blueprint (`deploy_from_markdown.js`), chỉ các card được khai báo trong blueprint mới được update — card trên dashboard khác (Dashboard 11 vs Dashboard 43) không bị ảnh hưởng.

**Fix:** Sau mỗi lần patch API trực tiếp, luôn sync blueprint ngay trong cùng commit.

**Rules:**
1. Blueprint là source of truth — mọi thay đổi SQL/viz phải reflect vào blueprint, dù fix qua API hay deploy script.
2. Khi có 2 dashboard song song (Dashboard 11 "CEO Weekly Pulse" + Dashboard 43 "CEO Weekly Pulse [All]"), fix 1 card không tự fix card tương ứng trên dashboard kia — phải patch cả hai.
3. Sau khi patch API trực tiếp: kiểm tra tất cả card cùng tên trên các dashboard khác (`grep` blueprint hoặc query `/api/dashboard/:id`).

**Reference:** Dashboard 11 card 885, Dashboard 43 card 1251; `docs/analytics-handbook/blueprints/ceo_weekly_pulse.md`

### L88 — Scope mismatch: all-channel GMV vs sales-channel target gây progress inflated

**Symptom:** `sales_monthly_review` dashboard hiển thị progress ~1.9B so với goal 600M (~316%) — unrealistic, không phản ánh thực tế business.

**Root cause:** Target trong `fact_targets` (600M/tháng) được set theo scope sales channels (`is_sales_channel = true`). Nhưng progress card query `fact_orders` không có `channel_key IN (... WHERE is_sales_channel)` filter — tính GMV toàn bộ channels bao gồm cả internal/non-sales channels.

Kết quả: numerator (actual) và denominator (target) có scope khác nhau → tỉ lệ vô nghĩa.

**Fix:** Thêm `AND channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)` vào CTE actual của các card so sánh với target. Các card khác trong cùng dashboard (branch breakdown, channel listing) giữ nguyên all-channel scope vì mục đích phân tích khác.

**Rules:**
1. Bất kỳ card nào so sánh actual vs `fact_targets`: scope của actual PHẢI khớp scope của target.
2. `fact_targets` hiện tại được set theo scope `is_sales_channel = true` — mọi target comparison card phải dùng cùng filter này trên `fact_orders`.
3. Không phải tất cả cards trong cùng dashboard cần cùng channel scope — chỉ các cards "actual vs target" mới cần đồng nhất. Cards phân tích (revenue by channel, branch breakdown) có thể giữ all-channel scope.
4. Khi tạo dashboard mới có tab "target vs actual": luôn verify channel scope khớp nhau trước khi publish.

**Reference:** `docs/analytics-handbook/blueprints/sales_monthly_review.md` — Question: Net Revenue vs Target, Question: Variance; Dashboard 31 card 1051

### L89 — Metabase v0.58.11 rejects `date/all-options` for `type:date` variable tags — must use `type:dimension` field filters

**Symptom:** Dashboards with `date/all-options` filter show no data. Direct card query returns HTTP 500: `"date/all-options không hợp lệ cho type:date. Phải là: :category, :date, :date/single"`. Dashboard loads but all cards empty.

**Root cause:** Metabase v0.58.11 (pMBQL) validates parameter types **before** executing SQL. A dashboard-level `date/all-options` parameter can only bind to a `type:dimension` template tag. Template tags defined as `type:date` (old variable style) are rejected at validation — the query never runs.

The CAST/strftime pattern was an attempted fix but irrelevant: the failure happens before SQL execution.

**Fix:** Three-part upgrade for every affected card:

1. **Template tag** — change from `type:date`/`type:text` variable to `type:dimension` field filter:
```json
{
  "type": "dimension",
  "widget-type": "date/all-options",
  "dimension": ["field", {"base-type": "type/DateTime", "effective-type": "type/DateTime", "lib/uuid": "<uuid>"}, 77]
}
```
Field IDs: `77` = `dim_date.date_actual` (DateTime), `179` = `dim_channels.channel_name` (Text/Name)

2. **SQL** — replace CAST/strftime pattern with subquery that hands off the `{{tag}}` to the dimension field:
```sql
-- BROKEN (variable tag — never executes under date/all-options)
[[AND date_key >= CAST(strftime(CAST({{date_range}} AS DATE), '%Y%m%d') AS INTEGER)]]

-- FIXED (dimension field filter)
[[AND date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
[[AND e.date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})]]
[[AND channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
[[AND c.channel_key IN (SELECT channel_key FROM dim_channels WHERE {{channel}})]]
```

3. **Dashcard parameter mappings** — change target from `variable` to `dimension`:
```json
["variable", ["template-tag", "date_range"]]  // BROKEN
["dimension", ["template-tag", "date_range"]]  // FIXED
```

**Scope of fix (2026-05-25):** Applied to 21 deployed cards across:
- Dashboard 35 (Order Profitability) — 9 cards (1130–1138)
- Dashboard 45 (Order Profitability [All]) — 9 cards (1288–1296) [also fixed channel filter]
- Dashboard 37 (Marketing ROI) — 6 cards (1146–1151)
- Blueprints updated: `order_profitability.md`, `marketing_roi.md`

**Rules:**
1. Never use `type:date` or `type:text` variable tags with `date/all-options` or `string/=` dashboard filters — use `type:dimension`.
2. Dimension field filter SQL must use the subquery delegation pattern: `date_key IN (SELECT date_key FROM dim_date WHERE {{date_range}})`.
3. Dashcard `parameter_mappings` target must be `["dimension", ...]` not `["variable", ...]`.
4. All new blueprints MUST use `type:dimension` tags. See `feedback_metabase_field_filter_required.md` in memory.

### L90 — Legacy `!= US` channel filter silently includes internal channels — replace with `is_sales_channel`

**Symptom:** Dashboard scope appears correct ("excludes US") but still includes internal orders: test products, quà tặng, employee benefits, unknown channels. Metrics inflated by non-commercial transactions.

**Root cause:** When `is_sales_channel` was introduced in `dim_channels`, existing dashboards using `channel_key != US` were NOT updated. At the time, US was the only non-sales channel. Later, new internal channels (Gosumo, Quà Tặng, Test Sản Phẩm, Unknown, Ưu đãi Nhân Viên) were added with `is_sales_channel = False` — but the old filter only excludes US, so these new channels leaked through.

**Fix:** Replace exclusion-based filter with inclusion-based:
```sql
-- LEGACY (leaks internal channels added after initial setup)
AND channel_key != (SELECT channel_key FROM dim_channels WHERE channel_name = 'US')

-- CORRECT
AND channel_key IN (SELECT channel_key FROM dim_channels WHERE is_sales_channel)
```

**Scope of fix (2026-05-25):** 17 cards in Dashboard 11 "CEO Weekly Pulse" updated.

**Rules:**
1. Never filter channels by name exclusion (`!= 'US'`, `!= 'Test'`). Always use `is_sales_channel` or explicit inclusion.
2. When adding new non-sales channels to `dim_channels`, audit dashboards for legacy exclusion filters.

---

### L91 — `AssetSelection.key()` does not exist in Dagster 1.13.2 — causes immediate job load failure

**Group:** OPS

**Symptom:** `pipeline_sapov2_realtime_job` failed after a `definitions.py` change. Run lasted 0 seconds, `stepStats` empty, Dagster event log: `"Could not load job definition."` / `"This run has been marked as failed from outside the execution context."` The code change looked syntactically valid; no import error was raised at import time.

**Root cause:** `AssetSelection.key()` (singular) does not exist in Dagster 1.13.2. The method only raised `AttributeError` at runtime when the worker process tried to instantiate the job, not at module import time. The code location _appeared_ loaded (Dagster UI showed `LOADED`) because the error occurs during job execution setup, not during `definitions.py` import.

**Fix:**
```python
# WRONG — AttributeError at runtime, not caught at import
AssetSelection.key(AssetKey(["fact_order_returns"]))

# DEPRECATED but works (Dagster 1.13.2)
AssetSelection.keys(AssetKey(["fact_order_returns"]))

# CORRECT (non-deprecated, works for dbt model assets)
AssetSelection.assets("fact_order_returns")
```

**Rules:**
1. After any `definitions.py` change, always validate in-container: `python3 -c "from orchestration.definitions import defs; print(len(defs.jobs))"` before committing.
2. "Could not load job definition" + `stepStats=[]` + `startTime==endTime` = job instantiation error, not a step failure. Check `EngineEvent` messages in run log.
3. `AssetSelection.assets(str)` accepts plain model name strings for dbt models — no `AssetKey` needed.
4. Code location showing `LOADED` does not guarantee individual job definitions are valid — job validation is lazy (at execution time).

---

### L92 — dbt mart models get 2-component Dagster asset keys `['marts', name]` — bare string selection silently fails

**Group:** OPS

**Symptom:** After adding `AssetSelection.assets("fact_order_returns")` to a job selection, Dagster reported `"Failed to resolve asset job ingest_filedrop_shopee_job"`. No error at module import or at `python3 -c "from orchestration.definitions import defs"` — the failure only appeared in `workspaceOrError.locationOrLoadError` after a code location reload.

**Root cause:** `SapoDbtTranslator.get_asset_key()` falls through to `super()` for model nodes. The default dagster-dbt translator uses the model's `fqn` (fully qualified name) to derive the key. For models in `models/marts/**`, this produces a 2-component key `['marts', 'model_name']`. Models in `models/intermediate/**` get single-component keys. A bare string `"fact_order_returns"` resolves to `AssetKey(['fact_order_returns'])` which doesn't exist in the asset graph → resolution failure.

**Fix:**
```python
# WRONG — wrong key, job fails to resolve silently at runtime
AssetSelection.assets("fact_order_returns")

# CORRECT — use the actual 2-component key for marts/ models
AssetSelection.assets(AssetKey(["marts", "fact_order_returns"]))
```

To discover the actual key for any dbt model:
```python
docker exec data_platform python3 -c "
import json
from orchestration.assets.dbt import SapoDbtTranslator
with open('/app/transformation/target/manifest.json') as f:
    manifest = json.load(f)
translator = SapoDbtTranslator()
for node in manifest['nodes'].values():
    if node.get('resource_type') == 'model' and 'my_model' in node['name']:
        print(node['name'], '->', translator.get_asset_key(node))
"
```

**Rules:**
1. Never assume bare string = valid asset key for dbt models. Always look up the key via translator + manifest first.
2. Key prefix depends on model folder: `marts/` → `['marts', name]`, `intermediate/` → `[name]`, `staging/` → `['staging', name]`.
3. After adding any `AssetSelection.assets(...)` referencing a dbt model by key, verify with `workspaceOrError.locationOrLoadError` — a `RepositoryLocation` (not `PythonError`) confirms success.
4. `python3 -c "from orchestration.definitions import defs"` does NOT catch job resolution errors — always reload the Dagster code location and inspect `locationOrLoadError`.

---

### L93 — `fact_order_economics` không có `order_timestamp` — query filter trên cột này lỗi runtime

**Group:** SERVE

**Symptom:** Các widget Metabase query `fact_order_economics` với filter `AND order_timestamp >= ...` báo lỗi "column not found" khi chạy. Widget hiển thị error thay vì số liệu.

**Root cause:** `fact_order_economics` chỉ kế thừa `date_key` (YYYYMMDD integer, ICT) từ `fact_orders` — không expose `order_timestamp`. Cột này chỉ tồn tại trong `fact_orders`. Các query P&L (Weekly Net Profit, Gross Margin %, Loss-Making Channel Count) được viết nhầm filter trực tiếp trên `fact_order_economics`.

**Fix:**
```sql
-- WRONG — order_timestamp không tồn tại trong fact_order_economics
FROM fact_order_economics
WHERE order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'

-- CORRECT — JOIN fact_orders để lấy order_timestamp
FROM fact_order_economics e
JOIN fact_orders o ON e.order_id = o.order_id
WHERE o.order_timestamp >= date_trunc('week', current_date) - INTERVAL '7 days'
```

**Rules:**
1. `fact_order_economics` columns: `order_id`, `order_code`, `channel_key`, `date_key`, `status`, revenue/cogs/profit fields — KHÔNG có `order_timestamp`.
2. Mọi time-window filter trên `fact_order_economics` phải dùng `JOIN fact_orders ON order_id` hoặc convert sang `date_key` (YYYYMMDD integer, ICT timezone).
3. Khi viết query mới cho bất kỳ mart nào, kiểm tra schema SQL file trước khi dùng column timestamp.

---

### L94 — Blueprint redeploy ghi đè UI manual edits — luôn audit toàn bộ blueprint trước khi deploy

**Group:** SERVE

**Symptom:** Sau khi fix và redeploy blueprint, các widget không liên quan (Cancelled Orders, Return Count) bị "revert" từ scalar về table. User báo "widgets bị biến thành tables".

**Root cause:** Deploy script enforce **toàn bộ** blueprint state xuống Metabase — bao gồm tất cả widget, không chỉ các widget được yêu cầu fix. Những widget đó đã được ai đó sửa thủ công trong Metabase UI thành scalar, nhưng blueprint chưa được cập nhật. Redeploy ghi đè lại state từ blueprint (table).

**Fix:** Trước khi deploy bất kỳ blueprint nào, grep toàn bộ `"display": "table"` trong file để tìm widget nào còn sai:
```bash
grep -n '"display": "table"' docs/analytics-handbook/blueprints/<file>.md
```
Fix hết tất cả widget sai display trong blueprint **trước** khi chạy deploy.

**Rules:**
1. Redeploy = full state sync — không có "partial deploy" cho từng widget.
2. Trước mỗi deploy: scan toàn file blueprint tìm `"display": "table"` — widget có 2 cột (this_week + last_week) thường phải là scalar.
3. Manual Metabase UI edits không được persist qua redeploy — mọi thay đổi muốn giữ phải được ghi vào blueprint.
4. Khi user báo fix N widget → kiểm tra luôn các widget tương tự trong cùng tab/blueprint để tránh missed fixes gây regression.

---

### L95 — Metabase cycle-indicator không nhận filter nếu thiếu `[[AND {{date_range}}]]` trong SQL

**Group:** SERVE

**Symptom:** Cycle-indicator (scalar "Chu kỳ báo cáo") luôn hiển thị cùng một giá trị cố định bất kể user chọn filter Period nào. Card có reload (spinner xuất hiện) nhưng output không đổi.

**Root cause:** Metabase chỉ wire dashboard filter vào card khi card có template tag `{{date_range}}` trong SQL. Nếu cycle-indicator dùng hardcoded `current_date - INTERVAL 'X months'`, Metabase set `parameter_mappings: []` cho dashcard đó — filter không bao giờ được truyền vào query. Card luôn chạy không có filter, trả về hardcoded dates.

**Fix:** Cycle-indicator phải dùng `filter_bounds` CTE với `[[AND {{date_range}}]]`:
```sql
WITH filter_bounds AS (
    SELECT MIN(posting_date) AS p_start, MAX(posting_date) AS p_end
    FROM <table>
    WHERE <base_conditions>
      [[AND {{date_range}}]]      -- bắt buộc để wire filter
      [[AND {{channel}}]]
),
period_adj AS (
    -- detect weekly/monthly/quarterly/yearly từ raw data bounds
    ...
),
prev_calc AS (
    -- n_months từ adjusted boundaries → prev_start luôn là ngày 01
    ...
)
SELECT '📅 Kỳ này: ...' AS "Chu kỳ báo cáo" FROM prev_calc
```

DuckDB gotcha: nếu cột là TIMESTAMP thì phải cast `MIN(col)::DATE` — `TIMESTAMP - TIMESTAMP` trả về INTERVAL, không cast được sang INTEGER để tính duration.

**Rules:**
1. Mọi cycle-indicator/display-label card PHẢI có `[[AND {{date_range}}]]` trong SQL — không có thì Metabase không wire filter.
2. Dùng `filter_bounds` CTE với raw `MIN/MAX(date_col)::DATE` làm nguồn dữ liệu — không dùng `current_date` hardcode.
3. TIMESTAMP columns: `MIN(col)::DATE` hoặc `MIN(col::DATE)` — không dùng `MIN(col)` raw vì arithmetic sau đó sẽ fail.
4. Pattern chuẩn: `filter_bounds` → `period_adj` (heuristic week/month/quarter/year) → `prev_calc` (n_months cho prev_start aligned).
5. Khi audit blueprint: grep `'cycle-indicator\|Chu k\|date_range'` — nếu cycle-indicator không có `{{date_range}}` thì phải fix.

**Reference:** `docs/analytics-handbook/blueprints/channel_profitability_monthly.md` — working implementation.

---

### L96 — Metabase field filter injection fails when the target table has a SQL alias

**Group:** SERVE

**Symptom:** Tất cả cards trả về `Binder Error: Referenced table "main.fact_orders" not found! Candidate tables: "ch"` khi filter được áp dụng. Không có filter → cards chạy bình thường.

**Root cause:** Metabase field filter injection sử dụng fully-qualified table name: `AND "main"."fact_orders"."order_timestamp" >= ?`. DuckDB binder resolve tên này dựa trên table name — KHÔNG phải alias. Khi table được viết là `FROM fact_orders o`, DuckDB chỉ biết alias `o`, không biết `"main"."fact_orders"`, nên binder thất bại.

```sql
-- SAI — fact_orders có alias 'o', injection sẽ fail
FROM fact_orders o
JOIN dim_channels ch ON o.channel_key = ch.channel_key
WHERE ch.channel_name = 'US'
  [[AND {{date_range}}]]  -- injects AND "main"."fact_orders"."order_timestamp" >= ? → ERROR

-- ĐÚNG — không dùng alias, hoặc alias bằng chính tên table
FROM fact_orders
JOIN dim_channels ON fact_orders.channel_key = dim_channels.channel_key
WHERE dim_channels.channel_name = 'US'
  [[AND {{date_range}}]]  -- injects AND "main"."fact_orders"."order_timestamp" >= ? → OK
```

**Rules:**
1. Table được tham chiếu bởi `field_id` của filter **KHÔNG ĐƯỢC** có alias trong FROM clause.
2. Nếu cần alias (ví dụ join nhiều bảng cùng tên), dùng alias bằng chính tên table: `FROM fact_orders fact_orders`.
3. Các table khác (JOIN) vẫn có thể có alias tự do — chỉ table của field_id là bị ảnh hưởng.
4. Đây là extension của L95: L95 nói về table không trong FROM, L96 nói về table trong FROM nhưng có alias.

**Reference:** `docs/analytics-handbook/blueprints/us_crossborder_operations.md`

---

### L97 — Cycle-indicator `period_adj` heuristic misclassifies non-calendar-aligned date ranges

**Group:** SERVE

**Symptom:** Filter "past 7 days" hiển thị cycle-indicator "19/05 – 25/05" (tuần của Mon-Sun chứa ngày đầu) thay vì "23/05 – 29/05" (7 ngày thực tế). Filter "past 3 months" hiển thị "01/03 – 30/06" (quarter boundary) thay vì "01/03 – 30/05". KPI cards có thể show đúng nhưng cycle-indicator sai → user nghĩ filter không hoạt động.

**Root cause:** `period_adj` CTE dùng `raw_dur` (số ngày giữa `p_start` và `p_end`) để đoán loại kỳ:

```sql
CASE WHEN raw_dur <= 6     THEN -- weekly: snap to Mon-Sun
     WHEN raw_dur 35-100   THEN -- quarterly: snap to quarter end
     WHEN raw_dur > 100    THEN -- yearly
     ELSE                       -- monthly: snap to month end
END
```

Vấn đề: heuristic này không phân biệt được "past 7 days" (raw_dur=6) với "thisweek" (raw_dur=0-6), hay "past 3 months" (raw_dur≈90) với "thisquarter" (raw_dur≈89). Kết quả: snap sai boundary → cycle-indicator hiển thị sai kỳ → user mất tin tưởng vào filter.

**Fix:** Bỏ `period_adj` hoàn toàn. Hiển thị raw dates từ `filter_bounds`, dùng same-duration shift cho `prev_period`:

```sql
-- THAY VÌ 3-CTE chain (filter_bounds → period_adj → prev_calc):
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start,
           MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders
    WHERE [[AND {{date_range}}]]
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start, '%d/%m/%Y') || ' – ' || strftime(p_end, '%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime((p_start - (p_end - p_start + 1))::DATE, '%d/%m/%Y') ||
    ' – ' || strftime((p_start - 1)::DATE, '%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM filter_bounds
```

**Tại sao `p_end - p_start + 1` hoạt động đúng:**
- DuckDB: `DATE - DATE = INTEGER` (số ngày)
- `DATE - INTEGER = DATE` (shift back)
- `p_end - p_start + 1` = duration tính inclusive (7 ngày thực = 6 ngày diff + 1)
- Prev_period luôn bằng chính xác độ dài kỳ này → đúng cho mọi filter type

**Rules:**
1. `period_adj` heuristic chỉ đúng với calendar-aligned periods (This Month, This Quarter, This Year). Không dùng nó khi dashboard hỗ trợ arbitrary date ranges.
2. Dùng raw `filter_bounds.p_start/p_end` để hiển thị period — chính xác và trung thực.
3. Dùng `p_start - (p_end - p_start + 1)` làm `prev_start` — works for daily/weekly/monthly/quarterly/yearly uniformly.
4. KPI cards có thể giữ `n_months` approach cho prev_period nếu muốn calendar-aligned comparison (acceptable trade-off cho monthly use case).
5. Khi thêm filter `date_range` cho bất kỳ dashboard nào: kiểm tra cycle-indicator với cả "past 7 days", "past 3 months" lẫn "thismonth", "thisquarter".

**Reference:** `docs/analytics-handbook/blueprints/us_crossborder_operations.md`, `.skills/metabase-automation/references/filter-date-range-pattern.md`

---

### L98 — DuckDB: `DATE - DATE` returns `BIGINT`, not `INTEGER` — `DATE - BIGINT` has no overload

**Group:** SERVE

**Symptom:** Cycle-indicator card trả về lỗi:
```
Binder Error: No function matches the given name and argument types '-(DATE, BIGINT)'.
Candidate functions: -(DATE, INTEGER) -> DATE, -(DATE, DATE) -> BIGINT, ...
```
Card không hiển thị gì, query thất bại hoàn toàn.

**Root cause:** Trong DuckDB, `DATE - DATE` trả về `BIGINT` (số ngày). Nhưng phép trừ `DATE - BIGINT` không được hỗ trợ — chỉ có `DATE - INTEGER`. Khi viết:

```sql
p_start - (p_end - p_start + 1)
```

DuckDB xử lý như sau:
1. `p_end - p_start` = `BIGINT` (overload `-(DATE, DATE) -> BIGINT`)
2. `BIGINT + 1` = `BIGINT` (integer literal `1` được promote lên BIGINT)
3. `p_start - BIGINT` = ❌ NO OVERLOAD — chỉ có `-(DATE, INTEGER) -> DATE`

**Fix:** Cast `(p_end - p_start)` sang `INTEGER` trước khi dùng làm operand:

```sql
-- ❌ SAI — DATE - BIGINT không có overload
p_start - (p_end - p_start + 1)

-- ✅ ĐÚNG — cast BIGINT → INTEGER trước
p_start - (p_end - p_start)::INTEGER - 1
```

Hoặc dùng INTERVAL (an toàn hơn nhưng dài hơn):
```sql
(p_start::TIMESTAMP - ((p_end - p_start)::INTEGER + 1 || ' days')::INTERVAL)::DATE
```

**Rules:**
1. `DATE - DATE` = `BIGINT` trong DuckDB — KHÔNG phải `INTEGER`.
2. `DATE - INTEGER` có overload; `DATE - BIGINT` KHÔNG có overload.
3. Khi muốn `p_start - N_days` mà `N_days` được tính từ `DATE - DATE`: luôn cast `::INTEGER` trước.
4. Integer literals (`1`, `7`, v.v.) được infer là `INTEGER` — `DATE - 1` hoạt động. `DATE - (expression returning BIGINT)` thì không.
5. Rule tương tự áp dụng cho `TIMESTAMP - TIMESTAMP` (trả `INTERVAL`) — không cast được sang `INTEGER`.

**Reference:** `docs/analytics-handbook/blueprints/us_crossborder_operations.md` (card: Chu kỳ báo cáo)

### L99 — DuckDB 1.10: `make_interval()` không tồn tại — dùng string cast thay thế

**Group:** MODEL

**Symptom:** dbt build thất bại với:
```
Catalog Error: Scalar Function with name make_interval does not exist!
Did you mean "make_date"?
```
Model `int_customer_metrics` lỗi ở bước tính `predicted_next_purchase_date`.

**Root cause:** `make_interval(days := n)` chỉ có trong DuckDB >= 1.11 (hoặc chưa có). DuckDB 1.10.1 không có hàm này. Code reviewer cảnh báo rủi ro nhưng không confirm version — `make_interval` được dùng thay cho `INTEGER * INTERVAL '1 day'` (cũng chưa verify).

**Fix:** Dùng string cast để convert số nguyên thành INTERVAL:

```sql
-- ❌ SAI — make_interval không tồn tại trong DuckDB 1.10
CAST(last_order_date AS DATE) + make_interval(days := n)

-- ❌ CHƯA VERIFY — INTEGER * INTERVAL có thể fail
CAST(last_order_date AS DATE) + (n * INTERVAL '1 day')

-- ✅ ĐÚNG — string cast luôn hoạt động
CAST(last_order_date AS DATE) + (n::VARCHAR || ' days')::INTERVAL
```

**Rules:**
1. Không dùng `make_interval()` với DuckDB < 1.11 — hàm không tồn tại.
2. Pattern `(integer::VARCHAR || ' days')::INTERVAL` là cách an toàn nhất để add N days vào DATE/TIMESTAMP bất kể version DuckDB.
3. Khi code reviewer cảnh báo DuckDB compatibility risk: luôn test trực tiếp trên container thay vì tin vào docs. DuckDB version mismatch giữa docs và runtime là phổ biến.
4. Compile (`dbt compile`) không catch runtime Catalog errors — chỉ `dbt build` / `dbt run` mới phát hiện.

**Reference:** `transformation/models/marts/core/intermediate/int_customer_metrics.sql` (column: `predicted_next_purchase_date`)

### L100 — Agent delegation: UI agent implements exactly what the prompt says, not what the intent is

**Group:** SERVE

**Symptom:** User asked for an "Actions tab" on the order detail view. Agent added a banner inside the existing Context tab instead. Required a manual fix to add `OrderTab.ACTIONS`, a new template, tab button, and route mapping.

**Root cause:** The orchestrator prompt included a "simpler" fallback suggestion ("add a small banner in `_context.html`") as an option to reduce scope. The agent followed the simpler path literally — it saw "banner in `_context.html`" and implemented exactly that, ignoring the user's original intent of a proper tab.

**Fix:** Added `OrderTab.ACTIONS` to the enum, wired the route, created `_actions.html` partial, added tab button to `order_detail.html`, removed banner from `_context.html`.

**Rules:**
1. **Never offer a "simpler alternative" in a delegation prompt unless you explicitly want that alternative.** Agents optimize for the path of least resistance; if a simpler path is mentioned, they will take it.
2. When delegating UI feature work to a sub-agent, be prescriptive: name every file to create/modify, every enum value to add, every route to wire. Don't describe the feature conceptually and expect the agent to derive the implementation.
3. For tab-based UIs, the minimum set for a new tab is always: enum value + route mapping + template partial + tab button in the shell template. Any prompt that omits one of these will likely produce an incomplete result.
4. After a UI agent completes, verify the exact output against the spec before marking done — agent summaries describe intent, not actual file contents.

**Reference:** `detailView/app/domain/shared.py` (OrderTab), `detailView/app/adapters/inbound/web/routes.py`, `detailView/app/adapters/inbound/web/templates/order_detail.html`

### L105 — Metabase field filter SQL syntax: `[[AND {{slug}}]]` not `[[AND col = {{slug}}]]`

**Group:** SERVE

**Symptom:** Same as L104 — all widgets crash when filter is active. OR: filters silently double-apply (`col = col = 'value'`), returning 0 rows.

**Root cause:** Two SQL template tag modes inject values differently:

| Tag type | Dashboard param | SQL syntax | What Metabase injects |
|----------|----------------|------------|-----------------------|
| `text` variable | no `field_id` | `[[AND col = {{slug}}]]` | just the raw value string |
| `dimension` field filter | has `field_id` | `[[AND {{slug}}]]` | full clause: `col = 'value'` |

When `field_id` is present on a dashboard param, the deploy script auto-creates a `dimension`-type template tag. A dimension tag replaces `{{slug}}` with the **full WHERE clause** (`col = 'value'`). Writing `AND col = {{slug}}` produces `AND col = col = 'value'` — invalid SQL → query fails.

**Fix:** Change SQL from `[[AND col = {{slug}}]]` → `[[AND {{slug}}]]` whenever `field_id` is on the dashboard parameter:
```sql
-- WRONG (variable syntax with field_id):
WHERE 1=1 [[AND action_type = {{action_type}}]]

-- CORRECT (field filter syntax with field_id):
WHERE 1=1 [[AND {{action_type}}]]
```

**The full working recipe for dropdown filters:**
1. Dashboard param: `{ "slug": "action_type", "type": "string/=", "field_id": 773 }`
2. SQL: `WHERE 1=1 [[AND {{action_type}}]] [[AND {{value_group}}]]`
3. Deploy script auto-creates `dimension` template tags → parameter_mappings = `["dimension", ...]`
4. Metabase renders a searchable dropdown fetching values from field 773

**Rules:**
1. `field_id` present → SQL must use `[[AND {{slug}}]]` (field filter syntax)
2. No `field_id` → SQL must use `[[AND col = {{slug}}]]` (variable syntax)
3. Never mix: `field_id` + `[[AND col = {{slug}}]]` = double-clause crash
4. Check `parameter_mappings[].target[0]`: `"dimension"` confirms field filter mode, `"variable"` confirms plain variable mode
5. This rule also applies to date filters: `[[AND {{date_range}}]]` not `[[AND date_col = {{date_range}}]]`

**Reference:** `docs/analytics-handbook/blueprints/customer_action_queue.md` · See also L104 (mapping type mismatch)

---

### L103 — Metabase click_behavior link templates can reference hidden columns — use for internal IDs in URLs

**Group:** SERVE

**Symptom:** Want to make a display column (e.g. `Mã KH`) clickable to a detail page, but the URL requires an internal ID (`customer_id`) that is not the displayed value. Using `/go/{code}` resolver works but adds an unnecessary redirect hop.

**Root cause:** Metabase `click_behavior.linkTemplate` can reference ANY column returned by the query using `{{column_name}}` — including columns marked `"enabled": false` in `table.columns`. Hidden columns are not visible to the user but are available as template variables.

**Fix:**
1. Add the internal ID to the SQL SELECT: `customer_id AS "customer_id"`
2. Hide it in `table.columns`: `{ "name": "customer_id", "enabled": false }`
3. Reference it in `click_behavior`: `"linkTemplate": "https://detailview.lan.fwg.vn/customers/{{customer_id}}"`

```json
"Mã KH": {
  "click_behavior": {
    "type": "link",
    "linkType": "url",
    "linkTemplate": "https://detailview.lan.fwg.vn/customers/{{customer_id}}"
  }
}
```

**Rules:**
1. When entity type is known (customer/order), link directly to the entity route — do NOT use a resolver (`/go/`) that adds an extra round-trip.
2. Use hidden columns (`"enabled": false`) to carry internal IDs needed in link templates without cluttering the table view.
3. The hidden column name in `linkTemplate` must match the SQL alias exactly (case-sensitive).
4. `/go/{code}` resolver is for cross-entity lookups (e.g. search bar, barcode scanner) where entity type is ambiguous — not for dashboard links where type is guaranteed.

**Reference:** `docs/analytics-handbook/blueprints/customer_action_queue.md` — "Queue — Danh sach outreach" question

---

### L104 — Metabase all-widgets crash when filter active = `field_id` present but SQL uses wrong syntax

**Group:** SERVE

**Symptom:** Dashboard works fine with no filter selected. As soon as any filter value is chosen, ALL widgets error ("There was a problem displaying this chart.").

**Root cause:** `field_id` on a dashboard parameter makes the deploy script create `dimension`-type template tags. A dimension tag replaces `{{slug}}` with the FULL clause `col = 'value'`. If SQL is written as `[[AND col = {{slug}}]]`, Metabase injects `AND col = col = 'value'` — invalid SQL — crashing every card.

**Fix:** Change SQL from variable syntax to field filter syntax. See **L105** for the full recipe.
```sql
-- WRONG (causes crash):
WHERE action_type = 'X' [[AND col = {{value_group}}]]

-- CORRECT:
WHERE action_type = 'X' [[AND {{value_group}}]]
```

**Diagnosis:** Check `parameter_mappings[].target[0]` via API:
- `"dimension"` → field filter mode → SQL must use `[[AND {{slug}}]]`
- `"variable"` → plain variable mode → SQL must use `[[AND col = {{slug}}]]`

**Reference:** See **L105** for the complete working recipe (field_id + `[[AND {{slug}}]]`)

---

### L102 — Metabase `string/=` dropdown requires `field_id` on param + `[[AND {{slug}}]]` in SQL (field filter mode)

**Group:** SERVE

**Summary:** To get a searchable dropdown for a `string/=` dashboard filter, use `field_id` on the parameter AND write SQL in field filter syntax. See **L105** for the complete working recipe.

> **Note:** An earlier version of this entry said `field_id` alone causes crashes — that was incomplete. `field_id` is correct; the crash came from wrong SQL syntax (`[[AND col = {{slug}}]]` instead of `[[AND {{slug}}]]`). L104 documents the crash symptom, L105 documents the fix.

**Group:** SERVE

---

### L101 — HTMX tab partial endpoints cannot be used as full-page deep-links

**Group:** SERVE

**Symptom:** Link `href="/customers/{id}/tab/actions"` from the order Actions tab navigated to a raw HTML fragment (just the tab partial) instead of the full customer detail page with the Actions tab active.

**Root cause:** In an HTMX tab pattern, `GET /entity/{id}/tab/{tab}` is a partial endpoint — it returns only the tab content fragment for HTMX to swap into `#tab-panel`. Linking to it directly from a full-page context (not via HTMX) renders the fragment without the page shell — no nav, no sidebar, no base layout.

Two distinct URL spaces exist:
- `/customers/{id}` → full page (shell + inline first tab)
- `/customers/{id}/tab/{tab}` → HTMX partial only (fragment, no shell)

**Fix:** Added `?tab=` query param to the full-page route. The route resolves the param to `CustomerTab`, passes `initial_tab_template` into context, and `customer_detail.html` uses `{% include initial_tab_template %}` instead of a hardcoded `_overview.html`. Cross-page links use `?tab=actions` to deep-link into a specific tab on first paint.

**Rules:**
1. Never `href` to a `/tab/` partial endpoint from outside that page's HTMX context — it will render a naked HTML fragment.
2. For HTMX tab UIs, deep-linking requires a `?tab=` query param on the full-page route that maps to the correct initial template include.
3. The full-page route must accept the `tab` param, validate it against the enum (with fallback to default), and pass `initial_tab_template` to the template context.
4. The shell template should use `{% include initial_tab_template %}` (variable) not `{% include "partials/..." %}` (hardcoded) so any tab can be the first-paint default.
5. Tab buttons in the shell use `aria-selected` driven by `active_tab.value == "slug"` — this pattern automatically highlights the correct tab when the page renders with a non-default `active_tab`.

**Reference:** `detailView/app/adapters/inbound/web/routes.py` (`customer_detail` handler, `_CUSTOMER_TAB_TEMPLATE`), `detailView/app/adapters/inbound/web/templates/customer_detail.html`

---

### L106 — Sapo selling prices are VAT-inclusive; `$.total_tax` is embedded VAT, not additive

**Group:** MODEL

**Symptom:** `net_revenue`, `gross_profit`, margins, LTV/AOV all overstated. `fact_orders` treated `$.total` as pre-tax net and computed `total_collected = total + tax` — double-counting VAT. Cross-source margin vs MISA COGS was apples-to-oranges (revenue VAT-inclusive, COGS VAT-exclusive).

**Root cause:** Sapo selling prices (giá bán) are **VAT-inclusive**. `$.total` (→ `total_amount`) is the gross amount with VAT already inside; `$.total_tax` (→ `tax_amount`) is the VAT **embedded inside** `$.total`, not added on top. Proven on real data: for taxed orders `tax_amount / net_revenue` clusters at **`0.07407 = 8/108`** (8% items) and **`0.0909 = 10/110`** (10% items) — additive VAT would give exactly `0.08`. ~60% of orders carry `tax=0` (US/export channel ~99.6%, genuinely 0% VAT; plus retail/POS with no VAT recorded).

**Fix (apply at earliest layer where the concept exists):**
```sql
-- fact_orders.sql (the single canonical revenue waterfall):
net_revenue     = total_amount - COALESCE(total_tax_amount, 0)   -- was: total_amount
total_collected = total_amount                                    -- was: total_amount + total_tax_amount (double-count)
-- fact_sales.sql (no per-line tax in Sapo → strip via order ratio):
revenue = line_amount * COALESCE((total_amount - total_tax_amount)/NULLIF(total_amount,0), 1)
```
Downstream (`fact_order_economics` gross_profit/margins, `int_customer_metrics`→`dim_customers` LTV/AOV, `mart_sku_economics_monthly`) auto-corrects since it inherits `net_revenue`. Impact: net −5.97%, total_collected −5.63%.

**Rules:**
1. Treat ALL Sapo price/amount fields (`$.total`, `$.price`, `$.line_amount`) as VAT-inclusive.
2. **Trust Sapo's per-order `$.total_tax`** for the exact embedded VAT — it auto-handles 8% / 10% / 0% (exports). NEVER blanket `/1.08` (breaks exports and 10%-VAT items).
3. `net_revenue = total − tax`; `total_collected = total` (do NOT add tax on top).
4. Line-level revenue has no per-line tax → strip via the order ratio `(total−tax)/total`.
5. Verify any VAT assumption on data first: `tax/net ≈ 8/108` = embedded VAT; `≈ 0.08` = additive (or already net).
6. Refunds (`fact_order_returns.refund_amount`) have no tax field — stay VAT-inclusive; flagged limitation.

**Reference:** `transformation/models/marts/sales/fact_orders.sql`, `fact_sales.sql` · `docs/context/sapo-platform.md` (§ VAT) · `docs/analytics-handbook/guides/revenue_terminology.md` · report `plans/reports/fix-260603-1536-sapo-vat-inclusive-pricing.md`

---

### L107 — Changing mart semantics silently breaks hardcoded UI waterfalls/labels that assumed the old relationship

**Group:** SERVE

**Symptom:** After the VAT fix (L106) flipped `net_revenue` to VAT-exclusive, the detailView Order → Financial tab waterfall stopped reconciling on screen: it showed `Gross revenue − Discount = Net revenue` but `12,000,000 − 4,050,000 = 7,950,000 ≠ 7,361,111` (displayed net). Sidebar "Money headline" hero labeled "Net revenue" but rendered `total_collected` (7,950,000, VAT-inclusive). Values were individually correct (pure pass-through from mart) — the **ordering/labels** were wrong.

**Root cause:** The waterfall row order and the sidebar `effective_revenue` mapping were authored for the PRE-fix model where `net_revenue = gross − discount = total_amount`. Post-fix that identity moved: `gross − discount = total_collected` (incl VAT), and `net_revenue = total_collected − VAT`. The presentation layer hardcoded the old step sequence, so the on-screen arithmetic no longer added up even though every number was right. No test caught it because the app does zero math — it just lays out mart columns in a fixed visual order.

**Fix:** Reorder the waterfall to match new semantics: `gross(incl VAT) −discount = total_collected −VAT = net_revenue(ex-VAT) −COGS = gross_profit −fees = channel_net`. Sidebar hero: domestic shows `net_revenue` (ex-VAT) to match its "Net revenue" label (US keeps `us_revenue_incl_vat`). Also display platform fees as `abs()` (mart stores them negative; minus-operator + negative value = confusing double-negative). detailView templates are baked into the image → `docker compose up -d --build detail_view` to apply.

**Rules:**
1. When you change the meaning/derivation of a mart column (VAT basis, sign, units), grep every downstream presentation layer (templates, hardcoded waterfalls, label↔field mappings, BI tooltips) for the OLD assumed relationship — pass-through UIs break silently.
2. A UI that does no arithmetic is NOT safe from semantic drift: fixed visual ordering encodes an arithmetic identity.
3. Label must match the field it renders (don't label `total_collected` as "Net revenue").
4. Mart stores expense/fee as negative → display `| abs` with an explicit minus operator, don't render the raw negative next to a "−".
5. detailView code/templates are baked into the image (not volume-mounted) — rebuild to apply; verify the live HTML, not just the source.

**Reference:** `detailView/app/adapters/inbound/web/templates/partials/order/_financial.html`, `order_detail.html` · See also L106 (the upstream VAT semantics change) · [[project-detailview-code-baked-in-image]]

---

### L108 — CSS grid `1fr` + `overflow:hidden` clips the last column ("tiền rớt")

**Group:** SERVE

**Symptom:** After adding a 4th column (percent) to the detailView P&L waterfall (`.wf-row` grid `20px 1fr auto auto`), the rightmost amount column visually disappeared / got cut off ("bể tùm lum, percent đẩy tiền rớt"). Values were in the HTML, but not visible.

**Root cause:** A grid `1fr` track is implicitly `minmax(auto, 1fr)` — its MIN size is the column's min-content, so it refuses to shrink below the (wrappable) label's intrinsic width. Adding the extra `auto` column made the row's total tracks exceed the container width; the row overflowed to the right, and the wrapper `.waterfall { overflow: hidden }` clipped the rightmost (amount) cell. Each `.wf-row` is its own `display:grid`, so the overflow happened per-row.

**Fix:** Make the flexible column `minmax(0, 1fr)` so it can shrink to 0 (label wraps) and the fixed columns (pct, amount) always stay on-row and visible. Also tightened `gap` to `--sp-2`. Verified with a headless Playwright screenshot + per-row bounding-box check (amount.right ≤ waterfall.right for all rows).

**Rules:**
1. Any time a grid has a flexible `1fr` next to fixed/`auto` columns AND the container clips overflow, use `minmax(0, 1fr)` (or `minmax(0, …)`) on the flexible track — plain `1fr` won't shrink below min-content and will push siblings out.
2. `overflow: hidden` on a table/waterfall wrapper hides overflow silently — values look "lost" rather than wrapping. Suspect it when content vanishes after adding a column.
3. Verify layout regressions VISUALLY (screenshot + bounding-box math), not just by checking the HTML contains the values — `curl`/urllib can't see clipping. Playwright-py is available on host; target host port 3005.
4. CSS is browser-cached: after a rebuild, hard-refresh (Ctrl+Shift+R) or the old stylesheet masks the fix.

**Reference:** `detailView/app/adapters/inbound/web/static/css/app.css` (`.wf-row`, `.waterfall`) · See also L107 (the change that added the column)

---

### L109 — A cost already embedded in an aggregate must NOT also appear as a sibling deduction (double-count)

**Group:** SERVE

**Symptom:** detailView Financial-tab P&L waterfall double-counted promo on screen: rows visibly summed to `channel_net_profit − promo` but the result row showed the real `channel_net_profit` — off by exactly `promo_goods_cost`. Data was correct; only the display double-counted. (Order 2603035YC1UJNR: net 1,177,290 − cogs 689,840 = gross 487,450; a separate `−Promo goods cost 60,185` row made the visible chain land at 152,927 vs the true 213,112.)

**Root cause:** After the Phase-05 COGS repoint to `int_order_cogs_reconciled` (Sapo-MAC primary), promo SKU rows (line_revenue=0, but with cost) are INSIDE `cogs_goods_primary` → inside `fact_order_economics.cogs_amount`. So `gross_profit = net_revenue − cogs_amount` is ALREADY net of promo, and `channel_net_profit` does not deduct promo separately. The Phase-06 UI (built before the repoint's effect was understood) rendered `promo_goods_cost` as its own `−` waterfall step, deducting it a second time visually. `promo_goods_cost` is an ATTRIBUTION LABEL ("of which promo"), not an independent deduction.

**Fix:** Render `promo_goods_cost` as a non-deducting annotation under the COGS row ("trong đó hàng tặng (promo): …", `wf-row--annotation`), not as a waterfall deduction step. The visible chain then reconciles: `net_revenue − cogs_amount = gross_profit → −fees → channel_net_profit`. Added two dbt guard tests (`assert_promo_account_not_in_keep_pool`, `assert_no_promo_in_overhead_costs`) to lock count-once at the data layer.

**Rules:**
1. Before showing a cost as its own deduction line, ask whether it is already inside a parent aggregate on the same waterfall (COGS, fees, allocated_overhead). If embedded, show it as a non-deducting "of which X" annotation — never a second sibling `−` step.
2. A "_cost"/"_amount" column is not automatically a deduction. Confirm whether the headline result formula (here `channel_net_profit`) actually subtracts it; if not, the UI must not either.
3. When a repoint changes what an aggregate CONTAINS (COGS now includes promo SKUs), re-audit every UI step built against the old composition — the sum can silently stop reconciling even when each row is individually correct. (Sibling of L107.)
4. Verify a waterfall by arithmetic: assert the visible-rows chain == the displayed result value on a real order, not just that each row renders.

**Reference:** `detailView/app/adapters/inbound/web/templates/partials/order/_financial.html` · `transformation/tests/assert_promo_account_not_in_keep_pool.sql`, `assert_no_promo_in_overhead_costs.sql` · See also L107 (mart semantics breaking UI), L106 (VAT-inclusive), and the Phase-05 repoint (`int_order_cogs_reconciled`)

---

### L110 — MISA `invoice_no` resets monthly/quarterly — never a standalone join key

**Group:** TRUST

**Symptom:** Reconciling MISA account-ledger 64214 (promo) to Sapo orders, a single-field join on `invoice_no` produced wildly wrong matches: the same number (e.g. `00000001`, `00000450`) appeared across multiple months/years for unrelated documents, so an `invoice_no`-only anti-join mislabeled ~40M as "no Sapo order / counted zero times". Per-document the real order-less amount was far smaller.

**Root cause:** MISA's `invoice_no` (số hóa đơn) is a counter that **resets each month/quarter**, not a global unique id. Joining MISA→Sapo (or MISA-ledger→MISA-sales-lines) on `invoice_no` alone fans out / mis-pairs records. The earlier "40.4M standalone" figure was a monthly-sum anti-join artifact, not a per-document fact (only ~15.3M was truly order-less).

**Fix:** Join MISA documents with a **3-part key**: `(invoice_no, DATE_TRUNC('month', posting_date), amount)`. With the composite key, 60.3M of the 87.8M invoice-linked 64214 confirmed counted-once via Sapo-MAC COGS; genuine under-count collapsed from "40M" to ~29M (mostly true gifting / MISA-internal vouchers).

**Rules:**
1. Treat MISA `invoice_no` (and any "resetting counter" id) as non-unique — always qualify with period + amount (or the voucher_no) before joining or anti-joining.
2. Never conclude "no match / uncounted" from a monthly-SUM gap (A−B by month). Drill to per-document before claiming a coverage gap — sum gaps hide both matched-but-shifted and key-collision rows.
3. A promo/gift row with a populated `invoice_no` is order-LINKED; only `invoice_no IS NULL` (e.g. voucher XK00155) is genuinely order-less.

**Reference:** `transformation/models/staging/standard/std_misa_account_ledger.sql`, `std_misa_sales_lines.sql` · `docs/architecture/order-pl/promo-count-once-reconciliation.md` · `var/data_lake/misa_raw/account_ledger/**` (raw has `voucher_no`,`invoice_no`,`description`)

---

### L111 — MISA `VCSC*` vs Sapo `VTSC*` SKU codes are the same physical product (alias gap)

**Group:** TRUST

**Symptom:** In `int_order_cogs_reconciled`, ~5.7M (10 promo rows) showed as `misa`-only (no Sapo match) — a spurious reconciliation gap implying uncounted cost, even though the promo units WERE dispatched in Sapo.

**Root cause:** MISA codes the product as `VCSC*` while Sapo dispatches the same physical SKU under `VTSC*`. The COGS reconciliation joins on SKU code, so the prefix difference makes one side look unmatched. Cost is still counted once (Sapo dispatch flows into COGS), but the FULL OUTER JOIN surfaces a false `misa`-only / `sapo`-only split.

**Fix (recommended, not yet applied):** add a `VCSC* ↔ VTSC*` alias mapping via `dim_sku_alias` (already exists in serving) and normalize the SKU key before the COGS reconciliation join, so these rows resolve to `both`. Until then, treat the ~5.7M misa/sapo-only split on these SKUs as cosmetic (does not affect the count-once total).

**Rules:**
1. When a reconciliation joins on a business code (SKU, account, partner) sourced from two systems, check for system-specific prefixing/aliasing before trusting "unmatched" buckets — an alias gap inflates apparent variance without any real money gap.
2. Use `dim_sku_alias` (or an equivalent crosswalk) as the canonical key for cross-system SKU joins; don't join raw vendor codes.

**Reference:** `transformation/models/intermediate/cogs/int_order_cogs_reconciled.sql` · `dim_sku_alias` · `docs/architecture/order-pl/promo-count-once-reconciliation.md`

---

### L112 — Reconciliation dashboards must use `primary_scope: none` — batch scope migrations silently break them

**Group:** TRUST

**Symptom:** `order_listing` dashboard showed fewer orders than Sapo Admin for the same date — CANCELLED orders and non-sales-channel orders were missing from the count and revenue breakdown. The reconciliation checklist explicitly says "bao gồm cả CANCELLED" but the SQL was filtering them out.

**Root cause:** During batch T6 SQL migration (scope standardisation), `AND scope_sales` was applied uniformly to all financial KPI queries. `order_listing` was also tagged `primary_scope: scope_retail` in its frontmatter — but its purpose is full-fidelity Sapo reconciliation, not analytics. `scope_sales` excludes CANCELLED orders and non-sales channels, so order counts and revenue differed from what Sapo shows.

**Fix:** Set `primary_scope: none` and remove all `AND scope_sales` / `AND o.scope_sales` filters. Title changed `[Retail]` → `[All]`. Re-deployed dashboard 26.

**Rules:**
1. Reconciliation/audit dashboards (`order_listing`, `ingestion_health`, anything titled "đối soát" / "reconciliation") must have `primary_scope: none` — they need raw, unfiltered row counts to match the source system.
2. Before applying a batch scope migration, grep for "reconcil", "đối soát", "audit" in dashboard titles/descriptions and exempt those blueprints explicitly.
3. `scope_sales` is an analytics filter (measures real revenue); it is NOT appropriate for operational completeness checks.

**Reference:** `docs/analytics-handbook/blueprints/order_listing.md` · `docs/analytics-handbook/semantic/segments.md#scope_sales`

### L113 — Deploy script false-positive "filter not mapped" warning caused operators to break Today tab

**Group:** SERVE

**Symptom:** Dashboard "Today" tab rendered blank — all 12 cards returned no data. "Yesterday" tab worked fine. "By Date" tab worked when a date was selected.

**Root cause:** Today tab cards use `current_date` (hardcoded) instead of `{{date}}` template variable. The deploy script emitted `⚠️ '...': filter(s) not mapped (no matching {{template_tag}}): date` for every Today tab card on every deployment. An operator read this as "Today tab is broken — the date filter isn't wired", and manually added `{{date}}` to Today tab card SQL. But `{{date}}` requires a `parameter_mappings` entry (wired by deploy script only for By Date tab cards), so Today tab cards ended up with an unresolved variable → blank render.

**Fix:**
1. Replaced `{{date}}` → `current_date` in all 12 Today tab cards via Metabase API.
2. Fixed deploy script: warning now fires only when SQL *contains* a `{{var}}` placeholder that couldn't be wired. Cards with no `{{var}}` (hardcoded predicates) are silently skipped — absence of template tag is intentional, not a misconfiguration.

**Rules:**
1. Multi-tab dashboards with "Today" / "Yesterday" tabs should use hardcoded `current_date` / `current_date - INTERVAL '1 day'` — never `{{date}}` — on those tabs. Only the "By Date" / picker tab should use `{{date}}`.
2. A deploy warning about unmapped filters is only meaningful when the SQL *has* `{{var}}` placeholders. Never add `{{var}}` to suppress a warning unless you also wire a `parameter_mappings` entry.
3. After any Metabase manual edit, re-run the deploy script to restore blueprint-defined state.

**Reference:** `.skills/metabase-automation/scripts/deploy_from_markdown.js` · `docs/analytics-handbook/blueprints/order_listing.md`

### L114 — Multi-tab cycle-indicator cards must have tab-specific SQL — copy-paste leaves wrong dates

**Group:** SERVE

**Symptom:** Dashboard "Chu kỳ báo cáo" (cycle indicator) showed wrong periods: Today tab showed "Theo filter được chọn (không cố định)", Yesterday and By Date tabs both showed "30 ngày gần nhất: …" — none matched the actual tab's time scope.

**Root cause:** When the dashboard was authored, the cycle-indicator SQL was copy-pasted from another dashboard (rolling-30d style) and never updated per tab. Each tab has a distinct time predicate but the same generic/wrong indicator string.

**Fix:** Updated each tab's cycle-indicator SQL:
- Today: `'📅 Hôm nay: ' || strftime(current_date, '%d/%m/%Y')`
- Yesterday: `'📅 Hôm qua: ' || strftime((current_date - INTERVAL '1 day')::DATE, '%d/%m/%Y')`
- By Date: `'📅 Ngày: ' || strftime({{date}}::date, '%d/%m/%Y')`  ← uses `{{date}}` + wired parameter_mappings

**Rules:**
1. Each tab in a multi-tab dashboard needs its own cycle-indicator SQL that reflects the tab's actual time window. Never copy the same SQL across Today / Yesterday / By Date tabs.
2. The "By Date" cycle-indicator must use `{{date}}` (wired to the dashboard filter) so it displays the currently selected date dynamically.
3. When authoring a new tab: write the cycle-indicator SQL last, after confirming the tab's date predicate, to avoid copy-paste drift.

**Reference:** `docs/analytics-handbook/blueprints/order_listing.md` — "Chu kỳ báo cáo" questions, all three tabs

### L115 — Sapo never zeroes cancelled order amounts — revenue KPIs must filter by status

**Group:** TRUST

**Symptom:** Reconciliation dashboard showed non-zero Net Revenue, Total Collected, Gross Revenue for a day with only 3 CANCELLED orders. Expected 0 since no money was collected.

**Root cause:** Sapo stores the original order amounts (`total_amount`, `total_discount_amount`, `total_tax`) on cancelled orders — they are NOT zeroed on cancellation. `fact_orders` inherits these values directly: `total_collected = total_amount`, `net_revenue = total_amount - vat_amount`, `gross_revenue = total_amount + total_discount_amount`. Without a status filter, revenue SUM includes cancelled order face values.

**Fix:** Add `AND status NOT IN ('CANCELLED', 'Voided')` to the WHERE clause of all revenue-aggregate KPI cards (Net Revenue, Total Collected, Gross Revenue, Total Discount). Cannot substitute `scope_sales` — that also filters `is_sales_channel`, breaking all-channel reconciliation.

**Rules:**
1. Any `SUM(revenue_metric)` query must explicitly exclude CANCELLED and Voided unless the intent is to show face-value totals (e.g., order management reports).
2. `COUNT(DISTINCT order_id)` for "Total Orders" reconciliation intentionally counts CANCELLED — do NOT add a status filter there.
3. `scope_sales` ≠ "exclude cancelled": `scope_sales = is_sales_channel AND status NOT IN (CANCELLED, Voided)`. On all-channel dashboards use the explicit status filter only.

**Reference:** `docs/analytics-handbook/blueprints/order_listing.md` — Net Revenue / Total Collected / Gross Revenue / Total Discount SQL · `transformation/models/marts/sales/fact_orders.sql` (revenue field definitions)

### L116 — Orders by Channel SQL: missing newline before GROUP BY causes parse error

**Group:** TRUST

**Symptom:** The "Orders by Channel" bar chart on Order Listing [All] (cards 826/838/850) showed a SQL parse error in Metabase: `"Parser Error: syntax error at or near "BY""`. The chart was completely broken on all 3 tabs.

**Root cause:** Blueprint SQL was authored with the WHERE clause and GROUP BY concatenated without a newline:
```sql
WHERE date(o.ordered_at) = current_dateGROUP BY 1
```
DuckDB tokenizer saw `current_dateGROUP` as an unknown identifier and then could not parse `BY 1` alone.

**Fix:** Add newline between WHERE predicate and GROUP BY. All 3 tabs had the same bug (Today, Yesterday, By Date variants).

**Rules:**
1. SQL GROUP BY, ORDER BY, HAVING, LIMIT — always start on a new line. Never concatenate to the end of a WHERE line.
2. After blueprint edits with find-replace, spot-check the rendered SQL for missing whitespace at clause boundaries.
3. Run `/api/card/<id>/query` via the Metabase API to confirm queries execute before considering a deployment done.

**Reference:** `docs/analytics-handbook/blueprints/order_listing.md` — "Orders by Channel" SQL, Today/Yesterday/By Date tabs

---

### L117 — Metabase `start-of-week` defaults to Sunday — weekly dashboards show Sun-Sat instead of Mon-Sun

**Group:** SERVE

**Symptom:** The weekly review dashboard (dashboard 8) with `past1weeks` filter returned a Sun-Sat window (e.g. 2026-05-25 Mon → actually starting Sun May 25) instead of the expected T2-CN (Mon-Sun) calendar week. The cycle indicator showed the wrong week boundaries, and stakeholders comparing to the calendar saw misaligned numbers.

**Root cause:** Metabase `start-of-week` admin setting defaults to `null`, which resolves to `"sunday"`. All week-based filter shortcuts (`thisweek`, `past1weeks`, `last7days`-week-aligned) use Sunday as the week boundary. The original dashboard also used `past7days` (rolling 7 days, not calendar-week-aligned) which further obscured the issue.

**Fix:**
1. Set Metabase `start-of-week` to `"monday"` via API:
   ```bash
   curl -s -X PUT "$METABASE_URL/api/setting/start-of-week" \
     -H "x-api-key: $METABASE_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"value":"monday"}'
   ```
2. Change dashboard default filter from `past7days` (rolling) to `past1weeks` (previous complete calendar week).
3. Verify cycle indicator SQL uses `MIN(ordered_at)::DATE` / `MAX(ordered_at)::DATE` from `filter_bounds` — not hardcoded `EXTRACT(WEEK FROM current_date)`.

**Rules:**
1. After any Metabase instance setup, immediately set `start-of-week = monday` (VN business weeks are T2-CN).
2. For weekly period dashboards, use `past1weeks` not `past7days`. `past7days` is rolling and never aligns to a calendar week boundary.
3. The `start-of-week` setting is instance-wide — changing it affects ALL dashboards. Verify no dashboard was intentionally Sun-Sat before changing.
4. If the cycle indicator is showing unexpected week numbers, check `start-of-week` first before debugging SQL.

**Reference:** `docs/analytics-handbook/blueprints/sales_ops_weekly_review.md` — default filter `past1weeks`, Chu kỳ báo cáo SQL

### L118 — Packsize COGS overcounted ×N when MISA records in the pack unit, not the base unit

**Group:** MODEL

**Symptom:** `mart_sku_economics_monthly` showed 5 Fine Japan "hộp 10" (H010) SKUs with realized margin −78% to −322% (net_revenue − cogs_amount deeply negative), implying selling far below cost (~809M 2026 revenue, COGS overcounted ~1.7B). `gross_margin_pct` still looked healthy (~65%), masking the error. A downstream assessment wrongly concluded "H010 sold below cost / 440M loss."

**Root cause:** `dim_sku_alias.misa_qty_multiplier` (= `packsize_quantity`, e.g. 10) assumes MISA records COGS in BASE units (chai/bottle). For these SKUs MISA actually records in PACK units (Hộp/box) — the per-bottle "Chai" lines are all `is_promo_line=true` and get filtered out by the model, so `cogs_per_misa_unit` is already cost-per-box. Multiplying by 10 again inflated COGS ×10. `gross_margin_pct` hid it because `misa_revenue_net` is also ×10 in both numerator and denominator (the ratio survives).

**Fix:**
1. Audit (one-off): for each `misa_join_key` with multiplier>1, check whether non-promo `int_misa_sales_lines` are in pack or base unit (compare MISA rev/unit to Sapo pack price). Bug was localized — 5 SKUs; the other ~71 packsize SKUs were correct, so do NOT touch AUTO_PACKSIZE logic.
2. `seed_sku_alias_manual.csv`: set `misa_qty_multiplier=1` for the affected pack SKUs (MANUAL_OVERRIDE wins over AUTO_PACKSIZE). Keep `units_per_pack=10` (physical descriptor; mart only uses the multiplier).
3. Added `realized_gross_profit` / `realized_margin_pct` (Sapo `net_revenue` basis) so commercial margin is explicit and distinct from MISA-book `gross_margin_pct`.

**Rules:**
1. `misa_qty_multiplier` must be 1 when MISA already records in the pack unit; >1 only when MISA records in base units. Verify per SKU before trusting AUTO_PACKSIZE (`= packsize_quantity`).
2. Never trust `gross_margin_pct` alone for a pack SKU — it cancels the multiplier and hides COGS errors. Cross-check `cogs_amount` vs `net_revenue` (`realized_margin_pct`).
3. A realized margin worse than ~−50% is almost always a COGS unit/multiplier artifact, not real below-cost selling — diagnose root cause before "fixing" the metric (don't enshrine the bad number).
4. Two margin columns now exist: `gross_margin_pct` = MISA-book; `realized_margin_pct` = commercial (Sapo price). Use `realized_*` for pricing/dashboards.

**Reference:** `transformation/seeds/seed_sku_alias_manual.csv` ; `transformation/models/marts/sales/mart_sku_economics_monthly.sql` (CAVEAT #7) ; `plans/260604-1125-retail-reactivation/02-understand/product-performance-assessment.md` §3c

### L119 — bootstrap_serving_views blocked by Metabase read-only lock — must stop Metabase first

**Group:** SERVE

**Symptom:** `bootstrap_serving_views.py` failed: `IO Error: Could not set lock on file "olap.duckdb": Conflicting lock is held in PID 0` while Metabase was up — despite the script docstring claiming read_only readers coexist with the writer ("verified 2026-04-08, no stop needed").

**Root cause:** the current DuckDB version makes Metabase's `read_only=true` connection hold a shared lock that conflicts with the script's exclusive WRITE lock. The "PID 0" holder is cross-namespace: the metabase container's `java` process holds an fd on `olap.duckdb`. No `data_platform` / `detail_view` / `rill` process held it. The 2026-04-08 "readers coexist" assumption no longer holds after the DuckDB/Metabase version bump.

**Fix:**
1. `docker compose stop metabase`
2. `docker compose exec -T data_platform python scripts/provisioning/bootstrap_serving_views.py`
3. `docker compose start metabase`
4. Verify: read_only connect to `olap.duckdb`, check `information_schema.columns` for the new column(s).

**Rules:**
1. Stop Metabase before running `bootstrap_serving_views.py` — the writer needs an exclusive lock and a read_only reader still blocks it in the current DuckDB version. (Updated the script docstring accordingly.)
2. "Conflicting lock in PID 0" = holder is in another mount namespace. Find it via other containers' `/proc/*/fd` (grep `olap.duckdb`); do NOT force-unlock (corruption/lock-storm risk).
3. Serving views are `SELECT *` over the rolling parquet glob → corrected DATA flows to Metabase automatically; only NEW or renamed COLUMNS need a bootstrap (CREATE OR REPLACE re-binds the `*`).
4. Don't trust a script docstring over observed lock behaviour after a version bump — verify empirically.

**Reference:** `scripts/provisioning/bootstrap_serving_views.py` docstring ; lesson L18

### L120 — DuckDB Binder Error: ORDER BY references raw column not in GROUP BY

**Group:** SERVE

**Symptom:** Metabase card returns 400 error: `Binder Error: column "X" must appear in the GROUP BY clause or must be part of an aggregate function` — card shows blank/error in dashboard despite blueprint SQL looking correct at a glance.

**Root cause:** DuckDB's strict SQL standard compliance rejects an `ORDER BY` clause that references a raw column (`next_purchase_signal`, `cancel_rate`) when the `GROUP BY` only contains the *derived expression* built on that column (via `COALESCE(...)` or `CASE WHEN ...`). `GROUP BY 1, 2` resolves to the SELECT expressions — not the underlying raw column — so the raw column in `ORDER BY` is unbound.

Two patterns that trigger this:
1. `SELECT COALESCE(col, 'fallback') AS x … GROUP BY 1 ORDER BY CASE col WHEN ...` — `col` alone is unbound; must use `CASE COALESCE(col, 'fallback') WHEN …`
2. `SELECT CASE WHEN col >= N THEN label END … GROUP BY 1 ORDER BY CASE WHEN col >= N THEN sort_int END` — `col` is unbound; must wrap in `MIN(CASE WHEN col >= N THEN sort_int END)` (valid because each band is a mutually exclusive range, so MIN = the single possible value).

**Fix:**
- Pattern 1: replace `CASE raw_col` with `CASE <same-coalesce-expression-as-select>` in ORDER BY.
- Pattern 2: wrap the range-based CASE in `MIN(...)` aggregate in ORDER BY so DuckDB sees it as an aggregate, not a bare column reference.

**Rules:**
1. In DuckDB, any column in `ORDER BY` must either be in `GROUP BY` directly, or wrapped in an aggregate function.
2. `GROUP BY 1, 2` (positional) groups by the SELECT *expressions* — not the raw underlying columns. Do not reference raw columns in `ORDER BY` without re-wrapping or aggregating them.
3. For sort-key CASE expressions derived from a grouped column: if the bands are mutually exclusive (one value per group row), `MIN()` is the correct aggregate wrapper — semantics unchanged, DuckDB satisfied.
4. When blueprint SQL silently inherits this bug, fix the blueprint first and redeploy — never patch Metabase cards directly.

**Reference:** cards 2156 (Next Purchase Signal Breakdown) and 2158 (High Cancel Rate Customers) in dashboard 48 (Customer Operational [Retail])
