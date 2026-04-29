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
def ingest_sapo_realtime_schedule(context):
    active = _has_active_run(context, "ingest_sapo_realtime_job")
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
        | AssetSelection.assets(serving.sapo_serving_db)  # refresh parquet rolling
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
transform_batch_nightly_job = define_asset_job(
    name="transform_batch_nightly_job",
    selection=...,
    # KHÔNG có full_refresh tag — chạy incremental bình thường
    tags={"concurrency_group": "dbt_rw"},
)

# Job 2: Manual full-refresh — launch thủ công khi cần reload lại toàn bộ
transform_batch_fullrefresh_job = define_asset_job(
    name="transform_batch_fullrefresh_job",
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
def sapo_orders_batch_asset(context):
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

**Khi nào dùng `transform_batch_fullrefresh_job`:**
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
        "ingest_sapo_realtime_job", "ingest_sapo_incremental_job",
        "transform_batch_nightly_job", "ingest_sheets_sync_job",
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

**Symptom:** `ingest_sapo_realtime_job` stuck 14+ min with 14 min inactive. Multiple runs stuck in single day. Jobs auto-terminated by stuck alerter but pattern keeps recurring.

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
- Nightly batch (`transform_batch_nightly_job`) holds `dbt_rw=1` for ~30-60 min. Realtime ticks queued behind it sit in `NOT_STARTED` legitimately.
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
| `transform_batch_nightly_schedule` | `0 3 * * *` ICT | Default nightly batch |
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
