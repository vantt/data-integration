# Design Doc: DLT Ingestion Skill

**Ngày:** 2026-04-06  
**Mục tiêu:** Đóng gói kinh nghiệm ingestion (dlt) thành skill tái sử dụng khi thêm ingestion mới.  
**Location:** `.skills/dlt-ingestion/` (project-level)

---

## 1. Mục đích & Kích hoạt

Skill được kích hoạt khi:
- User nói "thêm ingestion mới", "add new source", "integrate [source_name]"
- User hỏi về pattern dlt pipeline, envelope schema, incremental load
- User gặp lỗi trong ingestion pipeline đang chạy

---

## 2. Hai Pattern Ingestion

Codebase có 2 pattern riêng biệt. **Skill tập trung Pattern A** (phức tạp, nhiều boilerplate, nhiều lesson learned). Pattern B chỉ note ngắn trong SKILL.md.

### Pattern A: Custom API → Envelope Schema → Parquet (FOCUS)
**Dùng cho:** Sapo (orders, customers, accounts, history_log, webhooks)  
**Đặc trưng:** Tự viết toàn bộ — pagination, auth, schema, error handling  
**Output:** Parquet files tại `data_lake/{table_name}/ingest_method={x}/year={y}/month={m}/`

### Pattern B: Native dlt Source → DuckDB (NOTE ONLY)
**Dùng cho:** Facebook Ads, Facebook Messenger (dùng `dlt.sources.facebook_ads`)  
**Đặc trưng:** Source có sẵn trong dlt hub — chỉ cần truyền credentials, không viết pagination/schema  
**Khi nào dùng:** Source đã có trong [dlthub.com/docs/dlt-ecosystem/verified-sources](https://dlthub.com/docs)  
**Note trong SKILL.md:** "Kiểm tra dlt hub trước — nếu có verified source thì dùng Pattern B, không cần envelope"

---

## 3. Cấu trúc Skill

```
.skills/dlt-ingestion/
├── SKILL.md                        # Entry point, kích hoạt, Pattern A vs B decision
├── checklist.md                    # Checklist 5-phase khi thêm ingestion mới
├── lessons-learned.md              # Lessons từ production
├── troubleshooting.md              # Symptom → Cause → Fix
└── templates/
    ├── source-template.py          # Pattern A: Custom API source (incremental)
    ├── run-entry-point-template.py # Entry point wrapper
    ├── src-model-template.sql      # dbt dedup (src layer)
    └── dagster-asset-template.py   # Dagster asset + job wiring
```

*(stg model template bị loại — quá entity-specific, không tái sử dụng được)*

---

## 4. Nội dung Chi tiết

### 4.1 Checklist 5 Phase (Pattern A)

| Phase | Việc cần làm |
|-------|-------------|
| **1. Config** | Thêm section `[sources.{source}]` vào `.dlt/config.toml`; thêm credentials vào `secrets.toml.sample` + `.env.example` |
| **2. Source Code** | Tạo `src/{source}/{entity}.py` (source + resource), `run_{entity}_{method}.py` (entry point) |
| **3. dbt Transformation** | Tạo `transformation/models/staging/src_{entity}.sql` (dedup), cập nhật `sources.yml` |
| **4. Dagster Orchestration** | Thêm asset vào `orchestration/assets/{source}_assets.py`, wire vào đúng job + schedule |
| **5. Verify** | Test thủ công → check parquet output → chạy Dagster asset → check dbt run |

### 4.2 Templates — Nội dung cốt lõi

**`source-template.py`**
```python
# Skeleton Pattern A — điền vào: entity_name, api_endpoint, cursor_field, response_key

@dlt.source
def {source}_{entity}_source(max_pages=1000, page_size=100, min_overlap_items=500):
    return {entity}(max_pages=max_pages, page_size=page_size, min_overlap_items=min_overlap_items)

@dlt.resource(
    primary_key="entity_id",
    write_disposition="append",
    name="{entity}",
    columns={ENVELOPE_COLUMN_SCHEMA}  # template constant
)
def {entity}(max_pages, page_size, min_overlap_items,
             first_timestamp=dlt.sources.incremental("sync_metadata.event_timestamp")):
    # Auth
    client = get_{source}_client()
    session = client.session
    last_value = first_timestamp.last_value

    # Pagination với @retry tenacity + early-stop
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(1, 2, 10),
           retry=retry_if_exception_type(requests.RequestException))
    def fetch_page(page_num, sess): ...  # 401/403 refresh + 429 backoff

    while page <= max_pages:
        data = fetch_page(page, session)
        items = data.get("{response_key}", [])
        new_envelopes = [build_envelope(item) for item in items if item["{cursor_field}"] > last_value]
        old_count = len(items) - len(new_envelopes)
        consecutive_old_items += old_count
        if new_envelopes: yield new_envelopes
        if consecutive_old_items >= min_overlap_items: break  # early-stop
        page += 1

# build_envelope() — chuẩn hóa envelope schema
def build_envelope(raw_item, entity_type, ingest_method, cursor_field):
    dt = datetime.fromisoformat(raw_item[cursor_field].replace("Z", "+00:00"))
    return {
        "entity_id": str(raw_item["id"]),
        "entity_type": entity_type,
        "ingest_method": ingest_method,   # "batch_sync" | "webhook" | "history_log"
        "event_type": "snapshot",
        "event_timestamp": raw_item[cursor_field],
        "payload_hash": md5(json.dumps(raw_item, sort_keys=True)),
        "year": str(dt.year), "month": str(dt.month),
        "payload": raw_item,
        "sync_metadata": {
            "source_system": "{source}",
            "event_timestamp": raw_item[cursor_field],
            "processing_timestamp": datetime.utcnow().isoformat(),
            "original_event_id": None
        }
    }
```

**`src-model-template.sql`**
```sql
-- Two-stage dedup: tech (entity_id) → business (biz_key)
WITH raw_data AS (
    SELECT * FROM {{ source('{source}_raw', '{entity}') }}
    {% if is_incremental() %}
    WHERE event_timestamp > (SELECT MAX(event_timestamp) - INTERVAL 7 DAY FROM {{ this }})
    {% endif %}
),
-- Stage 1: Tech dedup — giữ record mới nhất mỗi entity_id, ưu tiên ingest method
method_ranked AS (
    SELECT *, 
        CASE ingest_method 
            WHEN 'webhook' THEN 3 
            WHEN 'history_log' THEN 2 
            ELSE 1 END AS method_priority,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id 
            ORDER BY event_timestamp DESC, method_priority DESC
        ) AS rn
    FROM raw_data
),
extracted AS (
    SELECT 
        entity_id,
        json_extract_string(payload, '$.id') AS {biz_key},
        -- ... các fields cần extract
        payload, event_timestamp, ingest_method
    FROM method_ranked WHERE rn = 1
)
-- Stage 2: Business dedup — giữ bản ghi mới nhất mỗi biz_key
SELECT * FROM extracted
QUALIFY ROW_NUMBER() OVER (PARTITION BY {biz_key} ORDER BY event_timestamp DESC) = 1
```

**`dagster-asset-template.py`**
```python
@asset(group_name="{source}_ingestion", key_prefix=["{source}"])
def {source}_{entity}_batch_asset(context):
    context.log.info("Starting {entity} Batch Sync...")
    load_dlt_configuration(context.log.info)   # load .env.local + secrets.toml
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        load_info = run_{entity}_batch.run(argv=[])  # argv=[] ignores Dagster's sys.argv
    finally:
        os.chdir(cwd)
    return Output(value="{entity} Sync Completed", metadata={"load_info": str(load_info)})
```

### 4.3 Lessons Learned

| # | Lesson | Chi tiết |
|---|--------|----------|
| 1 | Early-stop pagination | Không dùng `total_count`; đếm `consecutive_old_items` — khi đạt `min_overlap_items` (500) thì dừng, tránh scan toàn bộ lịch sử |
| 2 | DuckDB concurrency lock | Dagster chạy nhiều asset song song → deadlock DuckDB; giải pháp: `op_tags={"dagster/concurrency_key": "duckdb_lock"}` cho mọi write asset |
| 3 | `argv=[]` trong Dagster | Không truyền `argv=None` (sẽ pick up Dagster's `sys.argv`) — luôn dùng `run(argv=[])` |
| 4 | `os.chdir(DLT_DIR)` | dlt tìm `.dlt/config.toml` relative to CWD — phải `chdir` vào thư mục `ingestion/` trước khi run |
| 5 | `load_dlt_configuration()` | Dagster không load `.env.local` tự động — gọi helper này đầu mỗi asset để load credentials |
| 6 | Incremental cursor path | dlt incremental cần path đầy đủ: `dlt.sources.incremental("sync_metadata.event_timestamp")` — không phải root field |
| 7 | 7-day incremental buffer | dbt src model dùng `MAX - INTERVAL 7 DAY` để catch late-arriving events từ nhiều ingest channels |
| 8 | Ingest method priority | Khi dedup: webhook (3) > history_log (2) > batch_sync (1) — webhook có event mới nhất |
| 9 | Envelope append-only | Không UPDATE trong data lake; mọi change đều append → dedup tại transform layer |
| 10 | Partition config trong `config.toml` | `layout` và `extra_placeholders` phải đặt trong `[destination.filesystem]` của `config.toml`, không phải env var |
| 11 | Session-based auth (Sapo) | Sapo không có API token; dùng `SharedCookieManager` + playwright login — cookie TTL 6h |
| 12 | Empty page retry | Retry 1 lần khi page trống trước khi stop — tránh false early-stop do network fluke |
| 13 | Webhook/history log là note | Hai pattern này không cần template riêng — xem notes trong lessons + code hiện tại làm reference |

### 4.4 Storage & Config

**Nơi lưu Parquet:**
```
data_lake/{table_name}/ingest_method={x}/year={y}/month={m}/{file_id}.parquet
```
- Path gốc: `DESTINATION__FILESYSTEM__BUCKET_URL=file:///app/data_lake`
- Layout config: `.dlt/config.toml` → `[destination.filesystem]`
- Trong container Docker: `/app/data_lake`; local dev: set via `.env.local`

**DuckDB (dbt transformation):**
- Path: `DBT_DATA_LAKE_PATH` env var (default `/app/data_lake`)
- dbt đọc Parquet files từ cùng `data_lake/` folder
- Export marts: `DBT_EXPORT_PATH=/app/data_lake/export/marts`

**Config resolution chain (priority thấp → cao):**
```
secrets.toml.sample  (template, commit vào git)
    ↓
.dlt/secrets.toml    (gitignored, local/server override)
    ↓
.env.local           (gitignored, loaded bởi load_dlt_configuration())
    ↓
Environment variables (docker-compose, CI/CD)
```

**Thêm source mới — các chỗ cần update:**
1. `.dlt/config.toml` → thêm `[sources.{source}]`
2. `ingestion/.dlt/secrets.toml.sample` → thêm credentials template
3. `.env.example` → thêm env vars tương ứng (format: `SOURCES__{SOURCE}__{KEY}`)

### 4.5 Troubleshooting

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| 401 loop không dừng | Cookie refresh bị loop | Kiểm tra `login_selectors` trong config, test playwright login thủ công |
| Pipeline không pick up data mới | `last_value` stale trong state | Xóa `.dlt/pipelines/{name}/` hoặc chạy `--full-refresh` |
| `database is locked` | Concurrent DuckDB write | Thêm `op_tags={"dagster/concurrency_key": "duckdb_lock"}` |
| Parquet partition sai layout | `extra_placeholders` thiếu trong config.toml | Kiểm tra `[destination.filesystem]` có đủ `extra_placeholders` |
| Incremental cursor không update | Field path sai | Verify path match với key trong envelope: `"sync_metadata.event_timestamp"` |
| dbt src model OOM | Full scan data lake lớn | Thêm `{% if is_incremental() %} WHERE event_timestamp > MAX - INTERVAL 7 DAY {% endif %}` |
| Dagster asset nhận Dagster args | `argv=None` thay vì `argv=[]` | Sửa thành `run(argv=[])` trong tất cả Dagster asset calls |
| Credentials không load trong Dagster | `load_dlt_configuration()` chưa gọi | Gọi đầu mỗi asset, trước `os.chdir()` |

---

## 5. Câu hỏi đã giải quyết

| # | Câu hỏi | Quyết định |
|---|---------|------------|
| 1 | Scope Pattern B? | Note ngắn trong SKILL.md: "kiểm tra dlt hub trước" |
| 2 | Location? | `.skills/dlt-ingestion/` (project-level) |
| 3 | Webhook template? | Notes trong lessons-learned, không cần template riêng |
| 4 | History log template? | Notes trong lessons-learned, không cần template riêng |
| 5 | stg layer template? | Bỏ khỏi skill — quá entity-specific |
