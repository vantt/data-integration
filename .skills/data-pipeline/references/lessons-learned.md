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

### L121 — Guardrail added to shared utility must be applied to ALL callers, not just the one in focus

**Group:** INGEST

**Symptom:** `pipeline_batch_fullrefresh_job` would have failed mid-run — orders asset runs fine (fixed to `--reset-cursor`) but customers/accounts/products assets exit 1 with `BLOCKED: --full-refresh requires --force`.

**Root cause:** When adding the `--full-refresh` guardrail to `pipeline_runner.py`, only the asset that motivated the change (`ingest_sapov2_orders_batch_asset`) was updated to use `--reset-cursor`. Three other batch assets in the same file still passed `["--full-refresh"]` when triggered by the `full_refresh=true` run tag — caught before the job actually ran.

**Fix:** Replace all remaining `argv = ["--full-refresh"] if is_full_refresh else []` with `--reset-cursor` in `sapo_assets.py`. All 4 batch assets now consistently use `--reset-cursor` when triggered via the fullrefresh job tag.

**Rules:**
1. When adding a guardrail or changing a flag's semantics in a shared utility, grep all callers in the same session before closing the task.
2. `--reset-cursor` is the safe default for all batch assets triggered by `full_refresh=true` — resets cursor and appends without deleting existing parquet.
3. `--full-refresh --force` is reserved for deliberate destructive reload only — never pass it from Dagster run tags.

**Reference:** `orchestration/assets/sapo_assets.py` lines 54, 105, 155, 206 ; `ingestion/src/utils/pipeline_runner.py` guardrail block

### L122 — BI card re-deriving a pre-computed mart metric → fragile (empty on no-filter); reuse the column

**Group:** SERVE

**Symptom:** Metabase card "COGS Variance Alert Table" (#108) returns 0 rows / looks broken — even though COGS variance data exists. Debugger shows it executes (columns present) but 0 rows regardless of threshold.

**Root cause:** The card RE-DERIVED COGS variance inside the SQL by comparing a "current window" vs a "prior window" computed from `int_misa_sales_lines` via a `filter_bounds` CTE. With NO date filter applied (default), `filter_bounds` = full data range (MIN..MAX), so the "prior window" (before MIN date) is EMPTY → `JOIN avg_3m USING(product_code)` yields 0 rows ALWAYS. Compounded: a hard `WHERE variance > 10%` filter — current COGS is stable (<1% after the H010 packsize fix), so even a correct alert table would be empty.

**Fix:** Use the PRE-COMPUTED `cogs_variance_pct` column already on `mart_sku_economics_monthly` (latest month) instead of re-deriving. Show TOP movers `ORDER BY ABS(cogs_variance_pct) DESC LIMIT N` (no hard threshold) so the table is never empty — when COGS is stable it still surfaces the largest movers. Card now returns 15 rows.

**Rules:**
1. If a mart already computes a metric (here `cogs_variance_pct`, `cogs_per_unit_3m_avg`), BI cards must reuse the column — do NOT re-derive with ad-hoc window CTEs (fragile + diverges from the canonical definition).
2. "Prior/trailing window" CTEs that key off the filtered range break when the filter is absent (prior window collapses to empty). Avoid in BI SQL; push such logic into the mart.
3. Alert/threshold tables go empty in healthy states and read as "broken" — prefer "top-N movers" (always populated) over a hard threshold filter, or add a graceful empty-state.

**Reference:** `docs/analytics-handbook/blueprints/product_profitability_cost.md` (COGS Variance Alert Table card) ; `mart_sku_economics_monthly.cogs_variance_pct`

### L123 — Metabase date/field filter (field_id) breaks inside aliased/joined native SQL → 500

**Group:** SERVE

**Symptom:** Multiple cards on a dashboard return HTTP 500 on load when a `date/all-options` filter (default `past30days`) is applied. Two stages: (a) without field_id → "Text 'past30days' could not be parsed"; (b) after adding field_id → "Binder Error: Referenced table main.fact_orders not found! Candidate tables: o".

**Root cause:** A `{{date_range}}` field filter (date/all-options with relative values) requires a `field_id` binding to resolve relative dates — without it, the raw value `past30days` is substituted as a literal and fails to parse. WITH a field_id (fact_orders.ordered_at = 848), Metabase generates a fully-qualified `"main"."fact_orders"."ordered_at"` reference — but the card SQL aliases the table (`FROM fact_orders o ... [[AND {{date_range}}]]`), so the generated qualified name doesn't match alias `o`. Field filters do NOT work inside native SQL that aliases or joins the underlying table.

**Fix:** For cards with aliased/joined FROM clauses, do NOT use a date field filter. Either (a) hardcode the intended relative window in SQL (`AND o.ordered_at >= current_date - INTERVAL '30 days'`) and drop the dashboard date filter — best for fixed-cadence boards (rolling-30d), or (b) if interactivity is required, the card's FROM must reference the bare table (no alias) so the field-filter's qualified column resolves.

**Rules:**
1. `date/all-options` filters need a `field_id` in the blueprint (see [[feedback_metabase_field_filter_required]]) — but field_id alone is insufficient when the SQL aliases the table.
2. Field filters (`{{x}}` dimension) only resolve cleanly in simple single-table native SQL without alias. With CTEs/joins/aliases, prefer a hardcoded window or a non-field (raw) param.
3. A board named "rolling-30d / [cadence]" should hardcode its window — an interactive date picker adds fragility for little value.

**Reference:** `docs/analytics-handbook/blueprints/product_performance_velocity.md` ; fact_orders.ordered_at field_id=848

### L124 — `refresh="drop_pipeline_state"` trong dlt xóa toàn bộ parquet của table, không chỉ state

**Group:** INGEST

**Symptom:** Sau khi chạy re-ingest với `--reset-cursor`, directory `ingest_method=history_log/` và `ingest_method=text/` rỗng hoàn toàn. Log dlt có dòng: `"Client for filesystem will drop tables {'order'}"` và `"Table order has seen data for the first time"`. Tất cả parquet của 3 partition (`batch_sync`, `history_log`, `text`) bị xóa.

**Root cause:** `refresh="drop_pipeline_state"` trong dlt filesystem destination KHÔNG chỉ xóa state — nó trigger **DROP TABLE** trên toàn bộ directory `order/`, bao gồm cả các partition `ingest_method=history_log/` và `ingest_method=text/` không liên quan đến pipeline đang chạy. Sau khi DROP TABLE, schema bị clear → dlt ghi lại từ đầu ("Table order has seen data for the first time") → chỉ còn 1 parquet file mới từ batch này.

Root cause sâu hơn: `refresh="drop_pipeline_state"` trong dlt v0.5+ cũng clear schema hash. Khi schema hash mismatch (do schema version tăng), dlt coi table là "mới" → trigger `_init_dataset_and_update_schema` → gọi `drop_table('order')` trước khi load.

**Fix đúng cho `--reset-cursor`:**
```python
# KHÔNG dùng refresh="drop_pipeline_state" — DELETE toàn bộ table data
# ĐÚNG: xóa thủ công destination state JSONL files trước khi tạo pipeline object

# 1. Clear local state dir
shutil.rmtree(os.path.join(get_dlt_pipelines_dir(), pipeline_name))

# 2. Xóa destination state files (pattern: _dlt_pipeline_state/{name}__*.jsonl)
data_lake = os.environ.get("DESTINATION__FILESYSTEM__BUCKET_URL", "").replace("file://", "")
for sf in glob.glob(os.path.join(data_lake, "_dlt_pipeline_state", f"{pipeline_name}__*.jsonl")):
    os.remove(sf)

# 3. source_args["full_refresh"] = True  ← tắt cursor filter ở source layer
# KHÔNG truyền refresh= gì vào pipeline.run()
```

**Rules:**
1. `refresh="drop_pipeline_state"` trong dlt filesystem destination = DROP TABLE trên toàn bộ directory table. Đây là destructive operation, không chỉ xóa state.
2. Khi table có nhiều `ingest_method` partition (batch_sync / history_log / text), DROP TABLE xóa TẤT CẢ — kể cả data từ pipeline khác (`sapo_history_log_pipeline`) và data không thể re-fetch (text).
3. Để reset cursor an toàn: xóa thủ công `_dlt_pipeline_state/{pipeline_name}__*.jsonl` ở destination + xóa local state dir. KHÔNG dùng `refresh=`.
4. State dlt được lưu ở CẢ HAI nơi: local `{pipelines_dir}/{name}/` VÀ destination `_dlt_pipeline_state/`. Chỉ xóa local là KHÔNG ĐỦ — dlt restore từ destination khi khởi tạo pipeline.
5. Dấu hiệu nhận biết: log `"start_value: 2026-XX-XX..."` sau khi đã xóa local state = dlt đã restore từ destination.

**Reference:** `ingestion/src/utils/pipeline_runner.py` (comment block trong `--reset-cursor` handler) ; commit `cbba8bb` (correct fix) ; commit `08ae296` (wrong fix, superceded)

### L125 — mart_sku_economics_monthly.gross_margin_pct is UNCORRECTED (no H010 fix); use realized_margin_pct

**Group:** TRUST

**Symptom:** Product margin cards show ~2× too-low margin for the 5 H010 packsize SKU (Hyaluron & Collagen Plus shows 35.6% vs true 59.8%; Cordyceps Plus 65.6% vs 72.2%).

**Root cause:** The H010 packsize COGS-overcount fix (L118, seed `misa_qty_multiplier=1`) is applied ONLY to the corrected columns `realized_gross_profit` / `realized_margin_pct` in `mart_sku_economics_monthly`. The mart's `gross_margin_pct` / `gross_profit` columns AND the upstream `int_misa_sales_lines.gross_profit` remain UNCORRECTED (10× COGS for the 5 H010 SKU). BI cards that compute `SUM(gross_profit)/SUM(revenue)` from int_misa_sales_lines — or read `gross_margin_pct` — understate those SKU.

**Fix:** For any SKU margin/profit metric, use `realized_margin_pct` / `realized_gross_profit` (+ `net_revenue`) from `mart_sku_economics_monthly`. Never re-derive margin from `int_misa_sales_lines` and never use the mart's `gross_margin_pct`.

**Rules:**
1. Canonical SKU margin = `realized_margin_pct`. `gross_margin_pct` is pre-H010-fix — do not surface it.
2. No corrected COGS exists at channel/voucher grain (int_misa & fact_order_economics use uncorrected `sapo_mac`); channel-level SKU margin can only be approximated via the mart's `top_channel_name`.
3. Same anti-pattern as [[L122]] (reuse pre-computed mart column, don't re-derive) — applied to margin specifically.

**Reference:** `mart_sku_economics_monthly` (realized_margin_pct vs gross_margin_pct) ; L118 (H010 packsize fix) ; `docs/analytics-handbook/blueprints/product_profitability_cost.md`

### L126 — Metabase bubble scatter config: X in graph.dimensions, Y in graph.metrics, size in scatter.bubble

**Group:** SERVE

**Symptom:** A "scatter" card (SKU Margin vs Revenue) rendered with a confusing extra RIGHT y-axis — "Số đơn" (order count) plotted as a second axis series instead of being the bubble size. Bottom=revenue, left=margin, right=order-count (unwanted).

**Root cause:** Blueprint viz had `graph.dimensions: ["Doanh thu", "Gross Margin %"]` (TWO fields) + `graph.metrics: ["So don"]`. Metabase scatter treats the first dimension as X and any extra dimension + the metric as plotted series on dual axes → margin and order-count became left/right axes; the intended bubble encoding was lost.

**Fix:** For a bubble scatter, put exactly ONE field in each slot: `graph.dimensions: ["<X>"]`, `graph.metrics: ["<Y>"]`, `scatter.bubble: "<size>"`. Here: dimensions=["Doanh thu"], metrics=["Gross Margin %"], scatter.bubble="So don". No phantom right axis.

**Rules:**
1. Bubble scatter viz = 1 X dimension + 1 Y metric + 1 bubble field. Never put both axes in `graph.dimensions`.
2. A scatter showing a left AND right y-axis is almost always this misconfiguration — check graph.dimensions has a single entry.

**Reference:** `docs/analytics-handbook/blueprints/product_profitability_cost.md` (SKU Margin vs Revenue Scatter card)

---

### L127 — Metabase field filter on DuckDB: unqualified FROM clause → Binder Error when filter active

**Group:** SERVE

**Symptom:** Dashboard cards show data normally with no filters applied, but return a blank/error when any field filter (`string/=` with `field_id`) is activated. Error in Metabase logs: `Binder Error: Referenced table "main_marts.mart_cohort_retention" not found! Candidate tables: "main.mart_cohort_retention"`. Vietnamese shorthand: *"không dùng filter thì show, có filter thì không ok"*.

**Root cause:** When a Metabase field filter is applied to a native SQL card, Metabase injects a schema-qualified WHERE condition using the table's registered schema: `AND ("main_marts"."mart_cohort_retention"."cohort_dimension" = 'entry_product')`. DuckDB then resolves this 3-part reference as `schema=main_marts, table=mart_cohort_retention` and looks for that exact table alias in the FROM clause. If the FROM clause uses the unqualified name `FROM mart_cohort_retention`, DuckDB resolves it to `main.mart_cohort_retention` (default search path), which does NOT match `main_marts.mart_cohort_retention` in the WHERE — hence Binder Error.

olap.duckdb has two schemas: `main` (primary view) and `main_marts` (alias, where all other mart views live). Metabase syncs field metadata from `main_marts` because all other marts are registered there → field_id carries `main_marts` schema → field filter generates `main_marts`-qualified column reference.

**Fix:** In every native SQL card that uses a field filter (`field_id` in blueprint filter definition), use the **schema-qualified table name** in the FROM clause to match what Metabase will inject in the WHERE:

```sql
-- WRONG (breaks when filter active)
FROM mart_cohort_retention

-- CORRECT
FROM main_marts.mart_cohort_retention
```

Apply to all mart tables in olap.duckdb blueprints that use field filters.

**Rules:**
1. Any blueprint card with `"field_id"` in its filter definition → FROM clause must use `main_marts.<table>`.
2. "Works without filter, fails with filter" = schema mismatch between FROM (unqualified → `main`) and WHERE (field filter → `main_marts`).
3. After deploying a blueprint, test with a filter value applied — not just the no-filter state.

**Reference:** `docs/analytics-handbook/blueprints/cohort_explorer.md` (Cohort Retention Matrix / Cohort Value Summary / Cohort Data Table)

---

### L128 — Pre-pivoted CASE WHEN cards silently show all-NULL rows when window produces non-integer period_n

**Group:** SERVE

**Symptom:** Cohort heatmap cards (Retention Matrix, Value Summary) show the correct number of rows but all metric columns (M0–M12) are NULL when `window_type=calendar` filter is applied. With `window_type=relative` or no filter the cards display correctly.

**Root cause:** The pivot SQL uses `MAX(CASE WHEN period_n = '0' THEN ... END) AS "M0"` etc. for integers 0–12. For `window_type='relative'`, `period_n` is stored as `'0'`, `'1'`... so CASE WHEN matches. For `window_type='calendar'`, `period_n` is `'2023-03'`, `'2024-01'`... — no integer matches → all CASE WHEN branches are FALSE → every metric column returns NULL. The `GROUP BY cohort_value` still produces one row per cohort (with all-NULL metrics), so the result looks like "data present but empty" rather than "0 rows".

Pre-pivoted cards are window-type-aware by design: they only make sense for the window whose `period_n` format they pivot on.

**Fix:** Hardcode `AND window_type = 'relative'` in the SQL of any pre-pivoted card (instead of `[[AND {{window_type}}]]`). Remove the `window_type` parameter mapping from those dashcards so the dashboard filter does not inject a conflicting condition. Provide a separate long-format table card (no pivot) that keeps the dynamic `[[AND {{window_type}}]]` filter for calendar drill-down.

**Rules:**
1. Any card using `CASE WHEN period_n = '<integer>'` is implicitly scoped to `window_type='relative'` — make it explicit in SQL.
2. "Rows exist but all metrics are NULL" from a pivot card = wrong period_n format for the active window filter.
3. The `window_type` dashboard filter should only be wired to cards that handle both formats (long-format table). Pivot/heatmap cards must be decoupled from it.
4. When designing multi-window cohort dashboards: pivot cards = relative only; time-series/long-format cards = both.

**Reference:** `docs/analytics-handbook/blueprints/cohort_explorer.md` (Cohort Value Summary / Cohort Retention Matrix — hardcoded relative; Cohort Data Table — dynamic)

---

### L129 — Dashboard filter that only changes a secondary card feels broken to users

**Group:** SERVE

**Symptom:** After fixing pivot cards to hardcode `window_type='relative'`, the `window_type` dashboard filter still existed but only affected the Data Table card at the bottom. Users reported: "chọn calendar thì hiển thị đâu khác gì relative" (selecting calendar looks identical to relative). Filter appeared broken even though technically correct.

**Root cause:** A dashboard filter that doesn't visibly change the dominant/primary cards creates a broken UX signal. Users interact primarily with the top-of-page pivot/heatmap cards — if those don't respond to the filter, the filter feels non-functional regardless of whether it changes a secondary table below the fold.

**Fix:** Remove filters that only affect secondary or below-the-fold cards. Either: (a) wire the filter to ALL prominent cards (fix the cards to handle the filter), or (b) remove the filter from the dashboard entirely and let the secondary card show all values (users can sort within the table). Don't leave orphan filters.

**Rules:**
1. Every dashboard filter must visibly change at least one prominent (above-the-fold, full-width) card.
2. A filter wired to only a secondary table/detail card = remove it.
3. Test filter behaviour from a user's perspective: change the filter → does anything obviously change in the first 2 cards the user sees?

**Reference:** `docs/analytics-handbook/blueprints/cohort_explorer.md` (`window_type` filter removed; Data Table now shows both windows unsorted)

---

### L130 — Evidence.dev: bare `<` in markdown text is parsed as Svelte tag → "Expected valid tag name"

**Group:** SERVE

**Symptom:** Evidence dev server logs `(invalid-tag-name) Expected valid tag name: Line NNN, column MMM` for a page that renders fine in plain Markdown. The error line in the log refers to the compiled Svelte/Vite output — not the `.md` source line — making it hard to locate.

**Root cause:** Evidence compiles pages via mdsvex (Markdown → Svelte). Any literal `<` outside a SQL code-fence block is treated as an HTML/Svelte tag opening. Threshold annotations like `<40%`, `<10%`, `<0.8` trigger `Expected valid tag name` because `40`, `10`, `0` are not valid HTML tag names. Inside ` ```sql ``` ` fences the `<` is safe (not parsed by Svelte).

**Fix:** Use Svelte inline expression syntax `{'<'}` — mdsvex decodes `&lt;` back to `<` before Svelte parses it, so `&lt;` does NOT help:
- `<40% = Low retention` → `{'<'}40% = Low retention`
- `<10% Normal` → `{'<'}10% Normal`
- `<0.8 = Behind` → `{'<'}0.8 = Behind`

`>` (greater-than) in prose does not need escaping.

**Rules:**
1. Any `<` not followed by a valid HTML/Svelte tag name must use `{'<'}` (not `&lt;` — mdsvex decodes entities before Svelte compile).
2. SQL code-fences are exempt — the Svelte compiler ignores their content.
3. `docker compose restart` preserves the container's writable layer (`.evidence/template/` is NOT cleared). Always use `docker compose up -d --force-recreate` to pick up page content edits.
4. On Windows + Docker WSL2, inotify events for volume-mounted pages may not propagate → hot-reload unreliable; `--force-recreate` is the reliable path.
5. DuckDB connector scans ALL tables in the database by default — add `schemas: [main_marts]` to `connection.yaml` to limit to serving layer only (prevents crawling hundreds of raw tables at startup).

**Reference:** `evidence/pages/ceo-weekly-pulse/` (customers.md line 73/160, index.md line 89 — fixed 2026-06-13)

### L131 — CRM reverse-ETL: `crm_party_identity.identity_value` stores numeric customer_id, not MD5 customer_key

**Group:** SERVE

**Symptom:** SQL JOIN between `cache.wh_action_queue.customer_key` (MD5 hash like `33b8f275...`) and `crm_party_identity.identity_value` returns 0 matches, so `party_id` is always NULL and UI links fall back to search instead of the customer profile.

**Root cause:** Two different representations of the same customer exist in the pipeline:
- `wh_action_queue.customer_key` — 32-char MD5 surrogate key used by the warehouse dimension model
- `crm_party_identity.identity_value` — the raw **numeric** Sapo customer ID (e.g. `100035814`) stored when `syncparties` runs `FindByIdentity(ctx, "sapo_customer", ...)`

Directly joining `pi.identity_value = a.customer_key` compares a numeric string to an MD5 — will never match.

**Fix:** Bridge via `cache.wh_party_seed` which holds both columns:
```sql
LEFT JOIN cache.wh_party_seed ps ON ps.customer_key = a.customer_key
LEFT JOIN crm_party_identity pi
       ON pi.identity_type = 'sapo_customer'
      AND pi.identity_value = CAST(ps.customer_id AS TEXT)
```
`wh_party_seed.customer_id` is the integer Sapo ID; `CAST(... AS TEXT)` makes it match the TEXT column in `crm_party_identity`.

**Rules:**
1. When joining warehouse cache tables to CRM identity tables, always check which identifier format each side uses — MD5 vs numeric are NOT interchangeable.
2. `wh_party_seed` is the canonical bridge: `customer_key (MD5) ↔ customer_id (INTEGER)`.
3. `crm_party_identity` stores `identity_value` as TEXT even for numeric IDs — always `CAST(integer_col AS TEXT)` on the join side.
4. Before assuming a JOIN works, verify with `COUNT(*)` on the live DB and inspect a few sample values from each side.

**Reference:** `crm/app/internal/adapters/outbound/sqlite/cache_repo.go:ListAllActionQueue` (fixed 2026-06-15, commit e3cfed3)

---

### L132 — CRM filter logic: hardcoded thresholds out of sync with domain constants → filter always returns empty

**Group:** SERVE

**Symptom:** Clicking "Khẩn" (urgent) or "Cao" (high) filter on S01 worklist always shows an empty list, even when urgent/high-priority tasks exist in the database.

**Root cause:** Filter thresholds in `screen_worklist.py` used magic numbers (`>= 4` for urgent, `>= 3` for high) that never matched actual task priorities. The domain constants defined in `task.py` are `TASK_PRIORITY_NORMAL=0`, `TASK_PRIORITY_HIGH=1`, `TASK_PRIORITY_URGENT=2`. The Jinja KPI counter in `worklist_fragment.html` had the same stale magic number (`ge 4`).

**Fix:** Replace hardcoded thresholds with values matching domain constants:
```python
# screen_worklist.py
if filter_priority == "urgent":
    all_tasks = [t for t in all_tasks if t.priority >= 2]  # TASK_PRIORITY_URGENT
elif filter_priority == "high":
    all_tasks = [t for t in all_tasks if t.priority >= 1]  # TASK_PRIORITY_HIGH
```
```jinja
{# worklist_fragment.html #}
{% set p1_count = tasks | selectattr('priority', 'ge', 2) | list | length %}
```

**Rules:**
1. Never hardcode numeric thresholds for domain enum/constant comparisons — always reference the named constant or add a comment citing the constant name and file.
2. When domain constants change (e.g. priority scale is rescaled), grep for every numeric comparison that depends on them — in-memory Python filters and Jinja templates are silent blind spots, unlike DB CHECK constraints.
3. In-memory filters that return zero results are indistinguishable from "no data" to the user — always test edge cases with known data when adding filters.

**Reference:** `crm/src/domain/entities/task.py` (constants), `crm/src/adapters/inbound/web/screen_worklist.py` (filter), `crm/src/adapters/inbound/web/templates/fragments/worklist_fragment.html` (KPI). Fixed 2026-06-19, commit f430c9e.

---

### L133 — CRM S01: filter applied to only one list in a multi-source view → UI appears frozen

**Group:** SERVE

**Symptom:** Clicking "Tất cả", "Cao", "Khẩn" filter buttons on S01 worklist shows zero visible change. All rows stay the same regardless of which filter is selected.

**Root cause:** The page renders two independent lists: `all_actions` (ActionQueueItem from warehouse) and `all_tasks` (manual Tasks from SQLite). The priority filter in `_load_worklist_data` only filtered `all_tasks` — the smaller, less visible list. `all_actions` was never touched, so the dominant content remained unchanged and the UI appeared frozen.

Secondary issue: `prio_label` template mapping used thresholds `>= 4 / == 3 / == 2` (copied from stale magic-number pattern) against a domain where max priority is 2, so the P1 badge never rendered.

**Fix:**
```python
# screen_worklist.py — filter BOTH lists
if filter_priority == "urgent":
    all_tasks   = [t for t in all_tasks   if t.priority >= 2]
    all_actions = [a for a in all_actions if a.priority >= 2]
elif filter_priority == "high":
    all_tasks   = [t for t in all_tasks   if t.priority >= 1]
    all_actions = [a for a in all_actions if a.priority >= 1]
```
```jinja
{# worklist_fragment.html — correct prio_label mapping #}
{% if t.priority >= 2 %}{% set prio_label = 'P1' %}
{% elif t.priority == 1 %}{% set prio_label = 'P2' %}
{% else %}{% set prio_label = 'P3' %}{% endif %}
```

**Rules:**
1. When a screen renders multiple independent data collections (e.g. tasks + action queue items), every filter must be applied to ALL collections — missing one makes the filter appear broken even when it technically works on the filtered subset.
2. Before shipping a filter, enumerate every loop in the template and confirm the filter touches the data source for each one.
3. See also [[L132]] — magic number thresholds out of sync with domain constants compound this: even after fixing partial filtering, wrong thresholds would still cause empty results.

**Reference:** `crm/src/adapters/inbound/web/screen_worklist.py`, `worklist_fragment.html`. Fixed 2026-06-19, commit 2dede55.

---

### L134 — New dbt source over an empty parquet glob reds the whole shared dbt run (cascades to unrelated jobs)

**Group:** INGEST

**Symptom:** After adding new dbt source/staging models for a brand-new data source (Hug: `src_hug_scan`, `src_hug_optin_event`), Dagster runs went "tùm lum": `ERROR creating sql incremental model ... src_hug_optin_event` AND `KeyError: 'model.sapo_warehouse.src_hug_optin_event'` — and the failures landed on the **Sapo** realtime/incremental jobs, which had nothing to do with the new models.

**Root cause:** Two compounding issues.
1. The new sources read `read_parquet('.../hug_raw/{name}/.../*.parquet', ...)`. The ingest had never run, so the glob matched **zero files** → DuckDB raises "No files found". Because `sapo_dbt_assets` builds the **entire dbt project** in one run, one broken source reds the shared run and every job that triggers it — including Sapo.
2. Dagster pre-parses the dbt manifest at container startup; adding nodes without restarting `data_platform` → the new node is missing from the in-memory manifest → `KeyError` on the dbt step.

**Fix:** Mirror the existing `ensure_shopee_safety_placeholder.py` pattern: a `scripts/ensure_hug_safety_placeholder.py` writes a sentinel parquet (`entity_id='_safety_placeholder'`) into each `hug_raw/{table}/ingest_method=placeholder/` path so the glob is never empty; wire it into the `data_platform` startup command (before `dbt parse`); filter the sentinel out in each `src_` model (`WHERE entity_id <> '_safety_placeholder'`). Then `docker compose up -d data_platform` (recreate) to re-parse the manifest. Verified: post-restart `pipeline_sapo_v2_incremental` RUN_SUCCESS, hug models build, clean.

**Rules:**
1. A new dbt source backed by a parquet glob MUST ship with a safety-placeholder so the glob is non-empty on day one — otherwise the shared project run breaks for *everyone*, not just the new domain. Reuse `ensure_*_safety_placeholder.py`.
2. Adding any dbt node requires recreating `data_platform` (manifest is pre-parsed at startup, not hot-reloaded) or it KeyErrors.
3. Because one project-wide `dbt_assets` builds all models together, a failure in a brand-new, low-traffic source has blast radius = every job. Treat new sources as production-critical from the first commit.
4. A passing unit test that mocks the upstream contract can hide a real integration bug — when an edge enqueues `entity_type` *inside* the payload wrapper (not as a top-level column), the consumer must parse the wrapper; fixtures must mirror the real row shape exactly.

**Reference:** `scripts/ensure_hug_safety_placeholder.py`, `transformation/models/staging/src_hug_*.sql`, `transformation/models/sources.yml` (hug_raw), `docker-compose.yml` (data_platform command). Fixed 2026-06-20, commits 1f1171a + 9e1a1a6.

---

### L135 — A router factory missing `return router` disabled an entire shared-try mount block

**Group:** SERVE

**Symptom:** After rebuilding the CRM container, startup logged `WARNING hug stations unavailable ('NoneType' object has no attribute 'routes') — /hug/claim and /hug/mint disabled`. All three Hug screens (claim, mint, review) were down — not just the newly added one.

**Root cause:** `make_hug_review_router()` defined its routes but was missing the final `return router`, so it returned `None`. `app.include_router(None)` raises `'NoneType' object has no attribute 'routes'`. In `composition.py` all three hug routers are mounted inside ONE `try/except`, so the new router's failure aborted the block and the warning made claim+mint look disabled too. The task's unit tests passed because they exercised the FastAPI-free `_data`/`_html` helper modules directly and never called the router factory (the factory contract — "returns an APIRouter" — was untested).

**Fix:** Add `return router` at the end of the factory. Verified: `hug stations mounted at /hug/claim, /hug/mint, /hug/review`, `GET /hug/review` → 200.

**Rules:**
1. A `make_*_router()` factory MUST end with `return router` — grep new factories for it; a silent `None` return surfaces only at runtime mount.
2. Mounting several routers in a single `try/except` means one bad factory takes down ALL of them. Mount independent surfaces in their own try/except (or assert each factory returns a non-None APIRouter before include) so blast radius = the broken one only.
3. Splitting rendering into framework-free helpers is great for testability but leaves the thin FastAPI adapter (the factory + route wiring) untested — add at least one smoke test that the app builds and the route returns 200, or the integration seam is a blind spot.

**Reference:** `crm/src/adapters/inbound/web/screen_hug_review.py`, `crm/src/composition.py` (hug stations block). Fixed 2026-06-20, commit 8a8073e.

---

### L136 — A new mart a CRM job reads is absent from the serving DB until its first data row (serving builder skips empty marts)

**Group:** SERVE

**Symptom:** Every `/admin/refresh` logged `hug_resolve` ERROR: `Catalog Error: Table with name mart_hug_optin does not exist!`, even though the dbt model `mart_hug_optin` builds fine and its tests pass on every Dagster run.

**Root cause:** Two different DuckDB files. dbt builds the mart in the warehouse DB, but the CRM resolver reads the **serving** DB (`olap.duckdb`, schema `main_marts`). The serving-DB builder **skips creating a table for a mart whose source folder is empty** — and `mart_hug_optin` has zero rows until the first real opt-in is ingested. So the table is simply missing from the serving DB, and `fetch_new_optins` blew up querying it on every refresh.

**Fix:** Make the consumer tolerate the not-yet-materialized mart — catch `duckdb.CatalogException` and return `[]` (nothing to resolve yet) instead of reding the job. Verified live: `hug_resolve: processed 0 opt-in rows`, refresh ok. The table appears on its own once real data flows (or run `bootstrap_serving_views.py` to create the empty shell).

**Rules:**
1. A brand-new mart that a CRM/serving consumer queries does NOT exist in `olap.duckdb` until it has ≥1 row OR `bootstrap_serving_views.py` is run — the serving builder skips empty-folder marts. New CRM-consumed marts need either the bootstrap step (see [[feedback_new_mart_crm_serving_integration]]) or a consumer that tolerates absence.
2. "dbt model builds + tests pass" ≠ "the table is queryable from the serving DB" — they are different DuckDB files. Always verify the read path the consumer actually uses.
3. Day-zero (no data yet) is a first-class state for any new pipeline branch — every reader must handle the empty/absent case without erroring, or it spams ERROR logs on every scheduled run.

**Reference:** `crm/src/hug/identity_resolver_io.py` (fetch_new_optins), `transformation/models/marts/customer/mart_hug_optin.sql`. Fixed 2026-06-20, commit a01dcd2.

---

### L137 — fact_orders exposes customer_key (surrogate), NOT raw customer_id — join dim_customers to get it

**Group:** SERVE

**Symptom:** A new local job querying the serving DB failed at runtime: `Binder Error: Referenced column "customer_id" not found in FROM clause!` on `SELECT customer_id ... FROM main_marts.fact_orders`. Its unit tests passed (they injected rows via a seam, never hitting the real schema).

**Root cause:** `fact_orders` only carries `customer_key` (a `generate_surrogate_key` hash). The raw Sapo `customer_id` is used INSIDE the model's JOINs (`orders.customer_id` → surrogate) but is NOT in the final SELECT. Code that needs the natural Sapo customer_id (e.g. to join a CRM table keyed on it, like `crm_hug_voucher.customer_id`) cannot read it from fact_orders.

**Fix:** Join `main_marts.dim_customers` (which exposes BOTH `customer_key` and raw `customer_id`) on `customer_key`: `FROM main_marts.fact_orders f JOIN main_marts.dim_customers d ON f.customer_key = d.customer_key` → use `d.customer_id`. No mart change / serving rebuild needed (dim_customers already serves both).

**Rules:**
1. Fact tables in this warehouse key customers by the surrogate `customer_key`, not the raw `customer_id`. To bridge to anything keyed on the natural Sapo customer_id, go through `dim_customers` (has both). Don't assume a fact table re-exposes a natural key just because it's used in its joins.
2. Seam/mock unit tests that inject already-shaped rows do NOT validate the SQL against the real serving schema — pair them with at least one live run (or a `dbt`/DuckDB bind check) before declaring a mart-reader done. (Same failure mode as [[L134]] rule 4 and L136.)

**Reference:** `crm/src/hug/voucher_redeem_matcher.py`, `transformation/models/marts/sales/fact_orders.sql`, `transformation/models/marts/core/dim_customers.sql`. Fixed 2026-06-20, commit 6da9cee.

---

### L138 — Safety-placeholder parquet must match the real DLT output's Hive-partition DEPTH, or the shared dbt run reds once real data lands

**Group:** INGEST

**Symptom:** `src_hug_scan` (and by cascade the whole `pipeline_sapo_v2_realtime_job` / `_incremental_job`) started failing on EVERY run with `Binder Error: Hive partition mismatch between file ".../ingest_method=placeholder/hug_scan_safety_placeholder.parquet" and ".../ingest_method=webhook/year=2026/month=6/part-*.parquet"`. The dbt model and its `sources.yml` were unchanged; the failure began the moment the first real scan event was ingested. A zero-data placeholder had worked for months.

**Root cause:** `sources.yml` reads `read_parquet('.../hug_raw/{name}/ingest_method=*/**/*.parquet', hive_partitioning=1, union_by_name=true)`. DuckDB's `hive_partitioning=1` derives the partition KEY SET from each file's path DEPTH. The placeholder was one level deep (`ingest_method=placeholder/` → keys `{ingest_method}`) while real DLT output is three (`ingest_method=webhook/year=YYYY/month=M/` → `{ingest_method, year, month}`). While only the placeholder existed the glob saw one consistent depth and bound fine; once real 3-level data coexisted, DuckDB rejected the mixed depths. `union_by_name=true` reconciles differing FILE COLUMNS only — NOT differing PATH partition keys.

**Fix:** Write the placeholder at the SAME 3-level depth as real output (`ingest_method=placeholder/year=1970/month=1/...`) — mirroring the already-correct Shopee placeholder — and delete the stale shallow file on startup (idempotent). Applied to both `scan` and `optin_event`. Verified: live Dagster run `RUN_SUCCESS`, all 4 `src_hug_scan` tests pass, glob binds placeholder + real partitions together.

**Rules:**
1. A Hive-partitioned safety/seed placeholder MUST replicate the real producer's FULL partition key path (same depth + key names), not just the first level. A shallower placeholder is a time-bomb: it passes at day-zero and reds the shared run the instant real data lands. Copy the depth from a sibling that already works.
2. `hive_partitioning=1` + `union_by_name=true` does NOT save you from path-level partition mismatches — `union_by_name` is file-columns only. Partition-key consistency across a glob is a separate hard invariant.
3. Day-zero-vs-has-data is a distinct failure axis (cf. [[L134]], L136): a placeholder/glob that works empty can break when populated. When adding a placeholder for a new DLT table, diff its path against the real output layout before the first real row arrives.

**Reference:** `scripts/ensure_hug_safety_placeholder.py`, `transformation/models/staging/sources.yml`, `transformation/models/staging/src_hug_scan.sql`. Fixed 2026-06-23, commit d4593d3.

---

### L139 — A naive `;`-splitting SQL migration runner breaks on a semicolon inside an inline `-- comment`

**Group:** OPS

**Symptom:** Every CRM test that applies migrations to a FRESH sqlite db errored at setup with `sqlite3.OperationalError: incomplete input` on migration `0002_party_identity_golden_record.up.sql` — yet production CRM ran fine and the `.sql` file is valid SQLite. Manifested as ~25 errors across `test_hug_identity_resolver`, `test_hug_review_queue`, etc.

**Root cause:** The migration runner (`crm/src/adapters/outbound/sqlite/migrations.py`) splits each `.up.sql` on `;` and `conn.execute()`s the pieces (so per-statement idempotency like "duplicate column" can be caught). Its splitter tracked BEGIN...END trigger depth but did NOT account for a `;` inside a trailing line comment: `undone_at TEXT  -- set when UndoMerge is applied; prevents double-undo`. That comment `;` was treated as a terminator → the `CREATE TABLE crm_party_merge_log` was cut mid-definition ("incomplete input"), and the leftover `);` became its own `near ")": syntax error`. Production was immune only because `0002` was already recorded in `schema_migrations` and never re-parsed — the bug bites only fresh DBs (tests, new deploys, disaster recovery).

**Fix:** Before scanning a line for the `;` terminator, strip the trailing `-- comment` (`line.split("--", 1)[0]`). BEGIN...END handling unchanged. Added a regression test (`test_migrations_split.py`) covering comment-`;`, trigger body, and real terminators. Full CRM suite went 1 failed + 25 errors → 419 passed / 0 errors.

**Rules:**
1. A hand-rolled SQL statement splitter must ignore `;` inside both BEGIN...END bodies AND `-- line comments` (and, if strings can contain `;`, string literals). Prefer `conn.executescript()` for whole-file DDL unless per-statement error handling forces a manual split — and if you must split, comment-strip first.
2. A migration bug that only triggers on a FRESH database is invisible in production (already-applied migrations are skipped) but reds every test setup and would bite a clean redeploy / DR rebuild. "Works in prod" ≠ "applies cleanly from zero" — exercise migrations against an empty DB in CI.
3. Don't put a `;` in a migration inline comment if your runner is fragile — but better, make the runner robust (rule 1) so SQL stays freely commentable.

**Reference:** `crm/src/adapters/outbound/sqlite/migrations.py` (`_split_statements`), `crm/migrations/0002_party_identity_golden_record.up.sql`, `crm/src/tests/test_migrations_split.py`. Fixed 2026-06-23, commit 0c4dbda.

### L140 — Worklist rendered empty despite healthy data: stale uvicorn process (new template shape + un-reloaded Python) + a swallowed TypeError

**Group:** OPS

**Symptom:** After deploying the S01 worklist redesign, `/worklist` showed the empty state ("Hôm nay không có task nào") with all KPIs 0 — even though `wh_action_queue` held 531 fresh rows (generated that day) and a direct repo+`rank_worklist` call in-container returned 527 correctly-banded actions. No traceback on the page; logs showed only a swallowed `list tasks` error.

**Root cause:** Two compounding issues.
1. The CRM container mounts `./crm/src` (so Jinja TEMPLATES are read live per request) but runs uvicorn WITHOUT `--reload` outside dev mode, so edited PYTHON modules are not reloaded on save. The running process kept executing the OLD `_load_worklist_data`, which returned the old context keys (`actions`/`tasks`); the NEW `worklist_fragment.html` reads `bands`/`counts`/`value_total` (each `| default(...)`), so every new key resolved empty → empty-state branch + KPI 0. Data and logic were both correct; only the in-memory code was stale.
2. Separately/pre-existing: `task_service.list_tasks` called the SQLite repo with wrong kwargs (`assignee_user_id=`/`status=`) vs the repo signature `(assignee_id, statuses: list, limit)`. The `TypeError` was swallowed by the worklist's broad `except Exception: return []`, so the task band was silently always empty.

**Fix:** `docker compose restart crm` to load the new Python (primary fix). Corrected the call to positional `(assignee_id or "", [status] if status else [], limit)`. Verified live endpoint: 527 actions + 4 tasks, banded, no empty state, clean logs.

**Rules:**
1. In this CRM, editing server-rendered TEMPLATES is live (mounted, re-read per request) but editing PYTHON requires `docker compose restart crm` — `--reload` is only enabled in dev mode. A changed template-context contract + un-reloaded view = silent EMPTY render (new keys default-empty), not an error.
2. Diagnose "UI empty but data exists" bottom-up: query the DB → call the repo/logic directly in-container → hit the HTTP endpoint. If DB + logic are fine but the endpoint is empty, suspect a stale process or context-shape mismatch — do NOT re-run the data pipeline on a render bug.
3. A broad `except Exception: return []` in an adapter hides signature/kwarg mismatches as a silent empty list (looks identical to "no data"). Keep the call-site `log.error` (this one had it → grep logs) and prefer narrow excepts.
4. When a template's context contract changes, the producing view and the template must deploy together; a half-reloaded process serves new templates against old data shapes.

**Reference:** `crm/src/adapters/inbound/web/screen_worklist.py` (`_load_worklist_data`), `crm/src/adapters/inbound/web/templates/fragments/worklist_fragment.html`, `crm/src/application/task_service.py` (`list_tasks`), `crm/entrypoint.sh` (`--reload` only in dev). Fixed 2026-06-23, commit 15b57c6.

### L141 — CRM web screens crash on first hit: routes call service methods that don't exist / wrong call shape (kwargs vs dict)

**Group:** OPS

**Symptom:** Whole-stack audit found `POST /campaigns`, `POST /campaigns/{id}/targets/{pid}/convert`, `PATCH /campaigns/{id}/targets/{pid}/status` (and `POST /segments`) would raise `AttributeError`/`TypeError` on the first real request — `screen_management.py` called `campaigns_svc.record_conversion()`, `.update_target_status()`, `.get_target()` (none existed on `CampaignService`) and `create_campaign(name=..., ...)` / `create_segment(name=..., ...)` with kwargs while the services take a single `dict`. Never caught because no request had exercised those routes yet.

**Root cause:** Interface-contract drift between the inbound web adapter and the application service. The screen was written/edited against an assumed service surface that diverged from the actual one. Same family as L140 #2 (worklist called the task repo with wrong kwargs). No static type-check gate (mypy) and broad `except` patterns let signature mismatches survive until runtime. Also a hexagonal breach: `segment_service.py` / `campaign_service.py` imported `sqlite3` and ran raw SQL directly in the application layer instead of going through an outbound port/adapter — so the "service surface" itself was ill-defined.

**Fix:** Realigned screen→service calls (dict args, real method names), added the missing `get_campaign`/`get_target`/`update_target_status`/`record_conversion` to `CampaignService`, moved SQL out of the application services into `campaign_repository`/`segment_repository` behind the port. Verified: 514 crm/src tests pass.

**Rules:**
1. In this hexagonal CRM, the inbound web screen and the application service it calls form a contract — they must be reviewed/edited together. A screen calling a non-existent method or wrong arg shape is invisible until that exact route is hit, so untested mutation routes are latent crashes.
2. Application services must NOT import `sqlite3`/`duckdb`/`fastapi` — SQL belongs in `adapters/outbound/sqlite/` behind a port. A service that runs raw SQL has no stable surface, which is what lets call-site drift go unnoticed.
3. Prefer a contract test (or mypy) over trusting a green run: existing tests passed while three routes were dead. When adding/auditing a screen route, grep the service for the method + check the call shape (dict vs kwargs) before assuming it works.
4. Broad `except Exception` in adapters/screens hides these `TypeError`/`AttributeError` as empty/200 responses — keep call-site logging and narrow excepts (see L140).

**Reference:** `crm/src/adapters/inbound/web/screen_management.py`, `crm/src/application/campaign_service.py`, `crm/src/application/segment_service.py`, `crm/src/adapters/outbound/sqlite/{campaign,segment}_repository.py`. Found in full-stack audit 2026-06-23, commit adbd7b1.

### L142 — Sapo order payload stores payments under `$.prepayments`, not `$.payments` — whole payment pipeline silently empty

**Group:** MODEL

**Symptom:** `stg_sapo_v2_payments` = 0 rows → `std_payments` = 0 → `fact_payments` empty (1 placeholder) → `dim_customers.payment_behavior` uniformly `PAYMENT_PREPAID`/NULL, no `PAYMENT_COD`. No error anywhere; everything "ran green". An earlier audit misattributed the uniform PREPAID to a hardcoded `'CASH'` in std_payments — but the real cause was zero input rows.

**Root cause:** Payments are NOT a separate ingestion entity — they're embedded in the Sapo order payload. `src_sapo_v2_orders.sql` extracted `json_extract_string(payload, '$.payments') as payments_json`, but the Sapo API stores payment records under **`$.prepayments`**. `$.payments` does not exist in ANY order payload (verified across batch_sync + history_log). So `payments_json` was NULL for all 15.5K orders, and `stg_sapo_v2_payments` (which filters out NULL/`[]`) produced nothing. Verified on raw parquet: 0 orders have non-empty `$.payments`, ~57% have non-empty `$.prepayments` (each item: `id, payment_method_id, amount, paid_on, source` e.g. `cod_transfer`; `payment_method_id=1958911` = COD per `ref_payment_methods` seed).

**Fix:** `src_sapo_v2_orders.sql:175` `$.payments` → `$.prepayments`. Because `src_sapo_v2_orders` is an INCREMENTAL table, existing rows keep NULL `payments_json` — a one-time `dbt build --full-refresh -s src_sapo_v2_orders+` is required to backfill (a normal incremental run won't reprocess old orders). Downstream incrementals `int_customer_metrics` + `dim_customers` also need full-refresh for `payment_behavior` to recompute historically (see [[feedback_dim_customers_incremental_full_refresh]]).

**Rules:**
1. Verify JSON extraction PATHS against a real raw payload sample, not the assumed key name. A wrong `$.path` yields silent NULLs, not an error — downstream "0 rows" looks identical to "no data exists". When a staging model is unexpectedly empty, sample the RAW parquet payload (read one file, not all — OOM) and confirm the key actually exists.
2. "Empty mart" ≠ "missing data" — trace the path key-by-key from raw payload → src extraction → stg filter. Here the data was present all along under a different key.
3. An extraction-path fix on an INCREMENTAL src table only affects NEW rows; historical backfill needs `--full-refresh` on the src AND any downstream incremental that derives from the changed column.
4. Don't trust an audit's stated impact mechanism without checking input cardinality first — "hardcoded CASH corrupts behavior" was moot when the table had 0 rows.

**Reference:** `transformation/models/staging/src_sapo_v2_orders.sql:175`, `stg_sapo_v2_payments.sql`, `ref_payment_methods.csv` (id 1958911 = COD). Raw: `sapo_v2_raw/order/...parquet` `$.prepayments`. Found via full-stack audit verification 2026-06-24, commit 8624772.

### L143 — Making a widely-consumed mart column NULL silently breaks BI cards that SUM/AVG it without a gate

**Group:** MODEL

**Symptom:** A dbt fix made `fact_order_economics.gross_profit`/`gross_margin_pct` NULL when `has_cogs=FALSE` (don't show profit when cost unknown). Parse-clean, "looks done". But a Metabase audit found **31 cards** referencing those columns; **20 had no `has_cogs` gate** → after the change they drop the ~10% no-cogs orders from aggregates (15532 total, 13917 has_cogs → 1615 no-cogs). Two cards used `COALESCE(SUM(gross_profit),0)` — SUM ignores NULL so they **silently understate** margin with NO visible error, on CEO/Finance dashboards.

**Root cause:** A mart column is a public contract consumed by many BI cards. Flipping its values to NULL changes every downstream `SUM`/`AVG`/`FILTER` that doesn't explicitly handle the new NULL. `SUM` skips NULL (understates), `AVG` skips NULL (shifts), `COALESCE(SUM,...)` masks the drop entirely. None of these error — they just produce wrong numbers.

**Fix:** Decision was to KEEP the NULL behavior + gate the consumers: add `has_cogs` to each affected card's WHERE/FILTER so margin is computed over cogs-known orders consistently (8 cards needed it; 12 already had a gate). Done via blueprint edits + `deploy_from_markdown.js` redeploy (NEVER manual API/UI — blueprints are source of truth), each verified via `POST /api/card/:id/query`. Alternative considered: switch consumers to `realized_*` (changes meaning) or revert the NULL change (restores cards but shows uncorrected gross).

**Rules:**
1. Before changing a mart column's value distribution (esp. introducing NULLs, or renaming), AUDIT consumers first: grep blueprints + query Metabase cards for the column. A green dbt parse says nothing about 31 downstream cards.
2. `SUM`/`AVG` over a newly-NULLable column silently changes the number; `COALESCE(SUM(x),0)` HIDES the drop. Gate the no-cogs rows explicitly (`WHERE has_cogs`) rather than relying on NULL propagation.
3. Fix BI cards only via blueprints + deploy script (analytics-as-code source of truth), never manual API/UI ([[feedback_metabase_redeploy_use_skill]]). Verify each card with a live query run after deploy.
4. When a mart column has a "corrected" sibling, prefer steering consumers to it ([[reference_realized_vs_gross_margin_pct]]) over mutating the original's semantics, which has wider blast radius.
5. **Don't batch-apply a gate uniformly across cards of different KINDS.** A `has_cogs` gate is right for an aggregation/KPI card (keeps SUM/AVG consistent) but WRONG for a row-level diagnostic/exception card whose job is to surface broken rows — there the gate HIDES the very anomalies it should show. (Card 1520 "Shopee Orders Missing Fee Data" got the gate in the batch sweep and hid order SON06338 = no-fees + no-cogs, the worst case. A NULL `gross_profit` cell is harmless in a table card; remove the gate, label the no-cogs rows instead.) Classify card intent (aggregate vs exception-list) before applying a uniform fix.

**Reference:** `transformation/models/marts/sales/fact_order_economics.sql` (has_cogs/gross_profit), `docs/analytics-handbook/blueprints/metabase/{ceo_monthly_scorecard,marketing_roi,finance_accounting_recon,...}.md`. Audits `plans/reports/from-metabase-auditor-gross-profit-null-impact-260624-0840-report.md` + `from-metabase-verifier-card-1520-recon-semantics-260624-1036-report.md`. Fixed 2026-06-24, commits bfcaace (8 cards) + 418f240 (card 1520 gate removal).

---

### L144 — A UTF-8 BOM in a YAML config silently breaks strict PyYAML; the error points at the wrong line

**Group:** OPS

**Symptom:** Loading `orchestration/config/ingestion_sla.yaml` raised `yaml.parser.ParserError: expected '<document start>', but found '<block mapping start>'` pointing at **line 5** (`defaults:`) — the first non-comment line. The file *looked* perfectly valid; lines 1-4 are comments. Production (container PyYAML) parsed it fine for months; only surfaced on a dev box with a stricter PyYAML. This in turn broke `orchestration/asset_checks._build_asset_def_map()` load on that environment.

**Root cause:** The file started with a UTF-8 BOM (bytes `EF BB BF`) at offset 0. Some PyYAML builds treat the BOM as stray content before the document, so the first real mapping is read as a second/invalid document — and the reported line is the first mapping (line 5), NOT the BOM (byte 0). The misleading line number sends you hunting in the wrong place. Editors on Windows can re-introduce a BOM on save.

**Fix:** Re-saved the file as UTF-8 **without** BOM (content byte-identical otherwise). Verify: `open(path,'rb').read(3)` must NOT be `b'\xef\xbb\xbf'`; then `yaml.safe_load(open(path,encoding='utf-8'))` succeeds.

**Rules:**
1. When a YAML/JSON `ParserError` points at the first non-comment line and the syntax looks correct, check byte 0 for a BOM: `python -c "print(open(F,'rb').read(3))"`. The reported line is often a red herring.
2. Config files consumed by parsers (YAML/TOML/JSON) must be saved UTF-8 **no BOM**. On Windows, never trust the displayed text — check the raw bytes.
3. "Works in prod" ≠ "valid": library-version differences in BOM tolerance mean a file can load in the container but fail in dev (or vice-versa). Normalize encoding so it parses everywhere.

**Reference:** `orchestration/config/ingestion_sla.yaml`. Found during the `sapo_assets`→`sapo_v2_assets` rename import-validation, fixed 2026-06-24 commit f6355ab.

---

### L145 — A zombie STARTED/QUEUED run blocks the self-overlap guard forever; run_monitoring OFF + an activity-only stuck-sensor both miss it

**Group:** OPS

**Symptom:** Sapo webhook ingestion silently stalled ~7h. The realtime schedule logged every tick: `pipeline_sapo_v2_realtime_schedule skipped: previous run still active (35c42d4d)`. Meanwhile `health_alert_stuckrun_sensor` logged `No stuck runs detected` the entire time. Run `35c42d4d` had been `STARTED` since 09:45 (its process long dead); two more were stuck `QUEUED`.

**Root cause (3 compounding):** (1) The schedule's self-overlap guard `_has_active_run()` treats STARTED/STARTING/QUEUED/NOT_STARTED as "active" (correct by design) → it skips while ANY such run exists. (2) Dagster `run_monitoring` was **disabled** in `dagster.yaml`, so dead run-workers were never auto-failed — a zombie sits `STARTED` indefinitely. (3) The stuck-sensor decided staleness from event-log activity only; when `last_event_time` came back `None` (no events / transient SQLite lock) it did an unconditional `continue` (skip), so a run with a dead process AND no events was never flagged. A container `--force-recreate` also orphans in-flight runs without failing them. Net: nothing ever cleared the zombie, and the guard skipped forever.

**Fix:** (a) Recover now — mark zombies failed: `DagsterInstance.get().report_run_failed(run, "...")` (CLI has no `dagster run terminate` in 1.13). (b) Enable `run_monitoring` in `dagster.yaml` (`enabled: true`, generous `max_runtime_seconds` coarse backstop — set ABOVE the longest legit job, e.g. 14400s, so it never false-kills nightly/full-refresh). (c) Harden the stuck-sensor with a per-job absolute max-runtime backstop so a STARTED/QUEUED run past its ceiling is terminated even when `last_event_time is None`. Apply via container recreate; confirm `MonitoringDaemon` appears in the daemon list.

**Rules:**
1. A self-overlap "skip if previous still active" guard is only safe if SOMETHING reliably terminates dead runs. Pair it with `run_monitoring` enabled, OR a sensor that kills on absolute max-runtime — never rely on activity/heartbeat alone (a dead process emits no events → looks "not stuck").
2. `run_monitoring.max_runtime_seconds` is a BLUNT global kill — set it generously above the longest legit job; do precise per-job kills in the sensor. A too-tight global silently murders the nightly.
3. After any container `--force-recreate`/restart, in-flight runs become zombies. With `run_monitoring` on they self-heal; without it they block schedules forever. Always check `non-terminal runs == 0` after a recreate.
4. Recovery: `instance.report_run_failed(run)` (or `report_run_canceled`) flips a zombie to terminal so the guard stops skipping. `dagster run` has no `terminate` subcommand in 1.13.
5. Diagnose a stalled schedule by reading the scheduler log for `skipped: previous run still active (<id>)` then checking that run's status + age in `dagster_home/history/runs.db`. Builds on [[L48]] (zombie NOT_STARTED) + dagster-Lesson-13 — new angle: STARTED/QUEUED zombie + sensor blind spot.

**Reference:** `app_data/dagster_home/dagster.yaml` (run_monitoring), `orchestration/sensors/stuck_run_alerter.py` (per-job max-runtime), `orchestration/definitions.py` (`_has_active_run`/`_ACTIVE_STATUSES`). Incident + fix 2026-06-24. Report: `plans/reports/from-reliability-agent-*-260624-1656-report.md`.

---

### L146 — Critical runtime config living ONLY in a gitignored volume is silently lost on a fresh deploy

**Group:** OPS

**Symptom:** `dagster.yaml` — holding the DuckDB single-writer concurrency lock (the one AGENTS.md says "DO NOT REMOVE"), `run_monitoring`, freshness-off, and retention — existed ONLY in `app_data/dagster_home/` (gitignored volume). No tracked template, no copy mechanism. It worked on the live box, but a fresh `app_data` (new machine, wiped volume, disaster recovery) would silently come up with DEFAULT Dagster config: no concurrency lock → parallel DuckDB writers → lock storms; no zombie auto-fail; FreshnessDaemon re-enabled → SQLite contention. All the hard-won fixes, gone, with zero error at deploy time.

**Root cause:** runtime state dirs (DAGSTER_HOME, data lakes) are correctly gitignored, but a *config* file that happens to live inside one was never separated out into version control. "It's in the volume and the volume persists" hides the gap until the volume doesn't persist.

**Fix:** Track the config as source (`orchestration/dagster.yaml`) and seed DAGSTER_HOME at container boot with **copy-if-absent**: `mkdir -p $DH && { [ -f $DH/dagster.yaml ] || cp /app/orchestration/dagster.yaml $DH/dagster.yaml; }` prepended to the compose `command`. Copy-if-absent (NOT unconditional cp) so a live-tuned volume copy is never clobbered; the tracked file only seeds a fresh instance. Verified boot stays clean (webserver + MonitoringDaemon).

**Rules:**
1. Audit what lives in gitignored volumes: anything that is *config/behavior* (not pure data/state) must have a version-controlled source. "Persisted in a Docker volume" is NOT "version-controlled" — it dies with the volume.
2. Seed config into runtime dirs with **copy-if-absent** at boot, never unconditional copy (which would overwrite live hand-tuning) and never rely on a volume mount of a gitignored file.
3. Trigger to apply this lesson: any time you edit a file under a gitignored path (`git ls-files --error-unmatch <path>` errors), stop and ask "is this config that must survive a fresh deploy?" If yes, track a source + seed it.

**Reference:** `orchestration/dagster.yaml` (tracked source), `docker-compose.yml` (data_platform `command` copy-if-absent), `.gitignore` (`app_data/` ignored). Fixed 2026-06-24 commit d4e098a.

---

### L148 — Windows git autocrlf=true injects CRLF into shell scripts, silently breaking Linux containers at exec time

**Symptom:** Docker container built successfully (`chmod +x entrypoint.sh` ran in layer) but crashed immediately with `exec /app/entrypoint.sh: no such file or directory`. The file was physically present; the error is the kernel failing to find the interpreter `/bin/bash\r` (shebang `#!/bin/bash\r` with a carriage return).

**Group:** OPS

**Root cause:** `git config core.autocrlf=true` on the Windows dev machine converts LF→CRLF when checking out files. Shell scripts committed with LF are stored on disk with CRLF. `docker build` COPY transfers the CRLF file into the Linux image. The Linux kernel's `exec()` sees `#!/bin/bash\r` as a literal interpreter path — `/bin/bash\r` doesn't exist — and returns "no such file or directory". The container build layer (`chmod +x`) succeeds; the runtime exec fails. Previous builds masked the bug by reusing a cached layer built on a machine (or at a time) where the file was LF.

**Fix:** Add `RUN sed -i 's/\r//' /app/entrypoint.sh /app/refresh.sh` in Dockerfile immediately after COPY, before `chmod +x`. This strips CRLF in the image regardless of what the host injected. Alternatively, add `.gitattributes`: `*.sh text eol=lf` to enforce LF in the repo and prevent checkout conversion.

**Rules:**
1. Any `exec /app/foo.sh: no such file or directory` where the file exists → suspect CRLF shebang first.
2. Shell scripts in repos used on Windows hosts MUST be guarded: either `.gitattributes eol=lf` or `sed -i 's/\r//'` in Dockerfile.
3. A clean Docker build does NOT prove runtime works — `chmod +x` succeeds even on CRLF files; the failure only surfaces at container startup.
4. Never rely on Docker layer cache to hide a host-environment dependency (CRLF/LF, path separators, UID). A fresh build on a different machine will break.

**Reference:** `Dockerfile.crm` line `RUN sed -i 's/\r//' /app/entrypoint.sh /app/refresh.sh`. Fixed 2026-06-25 commit c95e318.

### L147 — A verification probe that swallows its own failure path is VACUOUS — it passes without testing anything

**Symptom:** A restore-verify drill claimed a "write→read→delete round-trip" proved the restored CRM was writable. It POSTed to `/api/tags` — an endpoint that **does not exist** (real routes were `/api/parties/{id}/tags`, `/settings/tags`). The 404 landed in a broad `except Exception: print("write-probe skipped — read-path verified"); return`. So the write test **never ran**; the drill reported PASS having verified nothing about writes. Invisible in testing because the happy path AND the 4 negative-tamper tests only exercised the *read/integrity* gate.

**Group:** TRUST

**Root cause:** Two compounding test anti-patterns: (1) a probe whose failure is caught and downgraded to a soft "skipped" — so the assertion can never fail; (2) the negative/tamper suite didn't cover the write path, so the vacuous probe was never caught by "does a known-bad input make this fail?". A check that cannot fail proves nothing.

**Fix:** Replace the endpoint-guessing soft-skip with a REAL, deterministic write that can actually fail: `docker exec <container> python3 -c "open restored crm.db; CREATE TEMP-ish table; INSERT; DELETE; DROP; commit; print('WRITABLE')"` and assert `WRITABLE` in stdout (else FAIL). No broad except, no fallback that masks failure.

**Rules:**
1. Every verification/probe must have a reachable FAILURE path. If the only outcomes are "pass" and "skipped", it's vacuous — delete it or make it assert.
2. NEVER `except: ... return`/"skip" around the thing you're trying to prove. Catching the failure of an assertion turns the assertion off.
3. The negative-test suite must tamper EVERY dimension the check claims to cover (here: a write-path tamper, not only read/integrity tampers). If a deliberately-broken input still PASSes, the check for that dimension is vacuous — this is how you catch a dead probe. (See also L143 rule on non-vacuous gates.)
4. Prefer a deterministic low-level assertion (direct SQLite write) over guessing a high-level API shape — fewer false "skips", and it fails loudly when wrong.

**Reference:** `crm/ops/restore_verify_crm.py` `_assert_writable` (was `_write_delete_roundtrip`). Found by `code-reviewer` (report `plans/260624-2010-crm-backup-checkpoint-restore-verify/reports/from-code-reviewer-backup-restore-260624-2243-report.md`). Fixed 2026-06-24 commit 41ad75a.

### L149 — Revenue and margin in one model must share the same VAT base; mixing VAT-inclusive revenue with VAT-excluded margin distorts margin %

**Symptom:** `mart_hug_attribution` emitted `redemption_revenue_vnd = fact_orders.total_collected` (VAT-INCLUDED cash) next to `redemption_margin_vnd = fact_order_economics.channel_net_profit` (VAT-EXCLUDED: net_revenue − COGS − fees). Revenue was inflated ~8–10% vs the margin base, so the effective margin % (margin/revenue) read artificially low. Surfaced while repointing phantom columns: a fact_orders refactor had dropped the old `total_price_vnd` / `contribution_margin_vnd` columns, blocking the build.

**Group:** MODEL

**Root cause:** Under build-fix pressure the forced repoint of the dropped financial columns picked `total_collected` for revenue without matching the margin column's VAT treatment. Sapo prices are VAT-inclusive (`total_collected = net_revenue + VAT`); VAT is a pass-through liability, not earnings.

**Fix:** Revenue → `fact_orders.net_revenue` (after discount, VAT removed) — same VAT-excluded base as `channel_net_profit`. Documented both columns in the `mart_hug_attribution` semantic contract in `marts/schema.yml`.

**Rules:**
1. Any revenue + margin (or any ratio) emitted by one model MUST share a single VAT base. Never pair VAT-inclusive (`total_collected`, `gross_revenue`) with VAT-excluded (`net_revenue`, `channel_net_profit`).
2. VAT is pass-through, not revenue — default to VAT-excluded (`net_revenue`) for profitability / ROI / attribution marts; reserve `total_collected` for cashflow / AR questions.
3. When a refactor drops columns and you must repoint, the replacement is a SEMANTIC choice, not just "a column that compiles": verify the definition against the paired columns and warehouse canon (e.g. `dim_customers.lifetime_contribution_margin = SUM(channel_net_profit)`).

**Reference:** `transformation/models/marts/core/mart_hug_attribution.sql` + `marts/schema.yml` (mart_hug_attribution contract). Fixed 2026-06-26 commit 3e983c2.

### L150 — A drill running inside a socket-mounted sidecar can't reach a sibling's host-published port via `localhost`; join the shared network and address by name

**Symptom:** The CRM restore-verify drill, moved from the host into the `crm_drill_runner` sidecar (which holds the Docker socket), booted the ephemeral CRM with `docker run -p 18090:8090` then polled `http://localhost:18090/healthz`. Gate B failed with "ephemeral CRM never became healthy" — even though the ephemeral's own container logs showed `Application startup complete` + its internal healthcheck returning 200. The app was fine; the drill just couldn't see it.

**Group:** INFRA / DOCKER

**Root cause:** `docker run -p` publishes the port on the **host**, not on the calling container. When the drill runs on the host, `localhost:18090` reaches the published port. When it runs inside the sidecar, `localhost` is the sidecar's own loopback — the sibling's host-published port is not there. (Same family as the named-volume rule: a socket-mounted container orchestrates containers on the HOST daemon, so host-relative addressing — published ports, bind-mount paths — does not translate to the caller's namespace.)

**Fix:** In sidecar mode, attach the ephemeral to the shared user network (`--network caddy_net`, no `-p`) and address it by container name (`http://crm-restore-verify:8090`). No Caddy label → Caddy never routes to it, so isolation holds. Host/dev mode keeps the `-p` + `localhost:<port>` path. Branch on whether the drill itself is running in-container.

**Rules:**
1. Anything reached over the network from inside a socket-mounted orchestrator must be addressed by container name on a shared network, NOT `localhost:<published-port>` — published ports live on the host, not the caller.
2. The sibling-container translation rule covers BOTH ends: bind-mount paths (use named volumes) AND port reachability (use a shared network + DNS name). Audit both when moving a host-run tool into a sidecar.
3. A passing internal Docker HEALTHCHECK in the sibling's logs does NOT mean the orchestrator can reach it — they resolve `localhost` in different namespaces. Verify reachability from the actual caller.

**Reference:** `crm/ops/restore_verify_crm.py` (`gate_b_functional`, SIDECAR branch) + `Dockerfile.drillrunner` + `crm_drill_runner` service. Found + fixed during Phase 6 live verification 2026-06-26.

### L151 — A Protocol interface wired to the wrong layer (repo vs service) silently passes Python's structural typing but fails at runtime with a type error the UI swallows as 500

**Symptom:** The "Gán phụ trách" (M04) modal submitted but never saved. The form closed visually on some browsers; on others the modal just stayed open. No UI error message. Server log showed an SQLite `InterfaceError` on the `owner_user_id` field.

**Group:** SERVE / CRM-WEB

**Root cause:** `screen_modals.py` declared an `OwnerAssigner` Protocol with `upsert_profile(self, profile: CustomerProfile)` — matching the **repository** layer signature (`SQLiteProfileRepository.upsert_profile`). The composition root wired `owner_assigner = profile_svc` (a `ProfileService`), whose actual signature is `upsert_profile(self, party_id: str, **kwargs)`. Python's structural (duck-type) Protocol checking raises no error at wire-time. At request time, `post_assign_owner` passed a `CustomerProfile` object as the first positional arg; the service received it as `party_id`, passed it straight to SQLite as a bind parameter, and SQLite threw `InterfaceError: unsupported type`. The exception was caught and re-raised as HTTP 500. HTMX on a 500 does not swap the target, so the modal stayed open and the save silently failed.

**Fix:** Update the `OwnerAssigner` Protocol signature to `upsert_profile(self, party_id: str, **kwargs) -> object` (matching the service layer) and call it as `upsert_profile(party_id, owner_user_id=owner_user_id)`. Remove the intermediate `CustomerProfile` construction and the now-unused import.

**Rules:**
1. When writing a Protocol for a service dependency, copy the signature from the **service** layer, NOT the repository layer — they differ and Python won't catch the mismatch.
2. Inspect server logs on "silent" UI failures before assuming the frontend is broken — a 4xx/5xx from the backend is often invisible to the user when HTMX's `hx-swap` is skipped on error.
3. After adding a new route that POSTs and is expected to redirect, smoke-test it once in a real browser and confirm the redirect actually fires (not just that the form submits without JS errors).

**Reference:** `crm/src/adapters/inbound/web/screen_modals.py` (`post_assign_owner`, `OwnerAssigner`). Fixed 2026-06-26.

### L152 — Middleware-injected user context is invisible to service calls unless handlers explicitly thread it through; every mutation handler must pull `request.state.current_user`

**Symptom:** All activity-log entries (`crm_activity`) and notes (`crm_note`) created via the web UI had `staff_user_id=NULL` and `author_user_id=NULL` respectively, even after CF Access authentication was working and the correct user appeared in the navbar. Additionally, logging an activity from the Inbox screen always returned HTTP 500 silently.

**Group:** SERVE / CRM-WEB

**Root cause:** Three independent failures sharing the same root pattern:
1. `CFAccessMiddleware` injects `request.state.current_user` on every request — but injection ≠ propagation. `handle_log_activity` and `handle_add_note` in `screen_customer_360.py` both had `request: Request` available but never read `request.state.current_user`, so `staff_user_id` and `author_user_id` were never passed to the service layer.
2. `screen_inbox.py`'s `ActivityLogger` Protocol declared `log_activity(party_id, activity_type, body, channel)` but `ActivityService.log_activity` takes `(activity_data: dict)` — a Protocol-layer mismatch (same class as L151). The handler called it with 4 positional args; the service received the `party_id` string as `activity_data`, then `activity_data.get("party_id")` raised `AttributeError`, caught as HTTP 500.
3. `post_assign_owner` had no `request: Request` parameter at all, making `current_user` unreachable. Assignment changes wrote to the profile column but left zero audit trail in `crm_activity`.

**Fix:** (a) Read `current_user = getattr(request.state, "current_user", None)` at the top of each mutation handler; pass `actor_id = current_user.user_id if current_user else None` to service calls. (b) Fix inbox Protocol to `log_activity(activity_data: dict)` and rebuild the call as a dict. (c) Add `request: Request` to `post_assign_owner`; add `ActivityLogger` to `WebDeps`/`_ModalDeps`; log the assignment as an activity record.

**Rules:**
1. Every mutation handler (POST/PATCH/DELETE) that touches a domain record MUST read `request.state.current_user` and pass `user_id` to the service — even if the feature doesn't display it yet, the DB column accepts it and audit history is irreversible to recover.
2. Middleware injecting context into `request.state` does nothing for service calls — it's the handler's job to thread it down. No amount of middleware sophistication compensates for a handler that ignores it.
3. When adding a new operation that changes ownership, assignment, or status of any entity, always check: is there an audit log call? If not, add it. The question "who did this, when?" will be asked in production.
4. Protocol signatures must be verified against the concrete service signature at wire-time, not assumed from memory. L151+L152 both caused silent runtime failures from this gap.

**Reference:** `screen_customer_360.py` (`handle_log_activity`, `handle_add_note`), `screen_inbox.py` (`ActivityLogger`, `handle_log_activity_on_conv`), `screen_modals.py` (`post_assign_owner`, `WebDeps`), `composition.py` (`_ModalDeps`). Fixed 2026-06-26.
