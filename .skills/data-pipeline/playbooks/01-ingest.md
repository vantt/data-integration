# INGEST Playbook — Thu Thập Dữ Liệu

**Vai trò:** Quản lý toàn bộ quá trình lấy data từ external sources vào data lake (Parquet).
Đầu vào: API / webhook / file-drop / Google Sheets.
Đầu ra: `data_lake/{entity}/ingest_method=*/year=*/month=*/*.parquet`

Sau INGEST, MODEL group đọc Parquet này qua dbt sources.yml.

---

## Bước 0 — Chọn Pattern Ingestion

<!-- VERBATIM từ SKILL.md "Bước 1: Chọn Pattern Ingestion" — KHÔNG paraphrase -->

```
Source đã có trong dlt hub?
(dlthub.com/docs/dlt-ecosystem/verified-sources)
        │
   YES  │  NO
        │
 Pattern B ─── Pattern A (FOCUS)
 (note ngắn)   (custom envelope)
```

### Pattern B — Native dlt source (note ngắn)

```python
from dlt.sources.facebook_ads import facebook_ads_source
pipeline = dlt.pipeline(pipeline_name="...", destination="duckdb", dataset_name="...")
pipeline.run(facebook_ads_source(account_id=..., chunk_size=1000))
```

Reference: `ingestion/run_facebook_ads_batch.py`

### Pattern A — Custom API (full guide)

Theo 6-phase trong `../checklist.md`. Pre-flight checklist bên dưới = Phase 1-2 details.

---

## Pre-flight Checklist (đọc TRƯỚC khi implement)

- [ ] Source authentication: API token / cookie / OAuth strategy đã chọn xong
- [ ] Envelope schema đã định nghĩa: `event_timestamp`, `entity_id`, `modified_on`,
      `ingest_method`, `sync_metadata` có mặt đủ
- [ ] Incremental cursor field xác định — dùng full path:
      `"sync_metadata.event_timestamp"` (không dùng `event_timestamp` bare)
- [ ] `--full-refresh` support: phải reset BOTH `last_value` AND
      `.dlt/pipelines/{name}/` state dir (L33)
- [ ] Partition layout `{table_name}/ingest_method=*/year=*/month=*/{file_id}.parquet`
      declared trong `config.toml` `extra_placeholders` (L35)
- [ ] Health recorder wired: `record_run(asset_key, run_id, ...)` với composite PK
      — UPDATE/DELETE phải filter BOTH `asset_key AND run_id` (L41, L44)
- [ ] Dagster asset wiring: `argv=[]`, `os.chdir(DLT_DIR)`, `load_dlt_configuration()`
      gọi đầu mỗi asset (L8, L9, L10)
- [ ] Concurrency tag: nếu asset write DuckDB →
      `op_tags={"dagster/concurrency_key": "duckdb_lock"}` (L11)
- [ ] Telemetry disabled: `DLT_TELEMETRY_DISABLED=true` set ở process level
      (Lesson 4 dagster-patterns) — tránh zombie thread block job exit

---

## Patterns

### 3-Channel Resilience (Sapo)

Ba kênh bổ sung nhau: **webhook** (realtime, at-least-once) + **history_log**
(backfill gap, truncation risk) + **batch** (full-refresh baseline). Không kênh nào
đứng độc lập. Dedup xảy ra ở MODEL layer (src_ model) dựa trên `ingest_method` priority.

### Pagination & Rate Limiting

- **Early-stop pagination**: Dừng khi page trả về empty / item count < threshold,
  KHÔNG đợi total_count từ API — API hay không trả đúng (L1)
- **Empty page retry**: Retry N lần với backoff trước khi stop — tránh bỏ sót page do
  transient network hiccup (L6)
- **Smart rate limiting**: Track request window; sleep đúng delta, không sleep fixed (L26)

### Authentication

- **Cookie TTL**: `SharedCookieManager` với TTL + 401/403 refresh on-demand (L13, L27)
- **Webhook ACK**: At-least-once delivery — ACK sau khi write thành công, dedup
  trong src_ là safety net (L14)

### Consumer Mode

- **Consumer loop vs one-off**: Webhook consumer có 2 mode — polling loop (realtime
  schedule) và one-off (manual trigger). Switch qua flag, không hardcode (L15)

### Special Ingest Types

- **File-drop sensor**: Cold-start: sensor skip lần đầu (chỉ record cursor), không
  process toàn bộ backlog khi deploy (L67)
- **Config snapshot fixed path**: Google Sheets config snapshot dùng fixed path
  (không timestamp suffix) để dlt incremental cursor so sánh được (L59)

### History Log Specifics

- **URI inference**: Sapo history_log URI phải được infer từ entity type, không hardcode (L16)
- **Entity registry pattern**: Central registry cho entity → history_log mapping (L24)

---

## Templates

| Template | Khi nào dùng |
|----------|-------------|
| `../templates/ingest/source-template.py` | DLT source class + resource + envelope builder — Pattern A custom API |
| `../templates/ingest/run-entry-point-template.py` | Entry point script `run_{entity}_{method}.py` — PHẢI `return run_pipeline(...)` (L36) |
| `../templates/ingest/dagster-asset-template.py` | Dagster ingestion asset — includes `argv=[]`, `os.chdir`, `load_dlt_configuration` wiring |

**Quy trình copy template:**
1. Copy template → target path
2. Replace tất cả `{source}`, `{entity}`, `{cursor_field}`, `{biz_key}` placeholders
3. Verify `return run_pipeline(...)` có mặt trong entry point (L36 — silent skip nếu thiếu)

---

## Supporting Scripts

Scripts liên quan INGEST từ `references/supporting-scripts.md`:

| Script | Mục đích |
|--------|---------|
| `scripts/clean_dlt_state.py` | Drop pending dlt packages — recovery khi pipeline crash giữa write |
| `scripts/inspect_customer_parquet.py` | Inspect raw Parquet output — verify schema/content |

**Decision logic đầy đủ:** Xem `references/supporting-scripts.md` mục "Khi Nào Gọi Script
Nào" — bảng tình huống → script chain phù hợp.

**Khi nào gọi `clean_dlt_state.py`:**
- Pipeline crash giữa write → state còn pending packages → lần sau fail
- Sau khi `--full-refresh` bị interrupt
- Pipeline không pick up data mới dù data đã có

---

## Debug Recipes

Xem `references/troubleshooting.md` các sections:

- **dlt — Auth / Session**: 401 loop, 403 sau refresh, cookie TTL
- **dlt — Pipeline State / Incremental**: last_value stale, cursor không update, pending packages
- **dlt — Config / Credentials**: KeyError, MISSING env, Parquet sai chỗ
- **dlt — Parquet / Partition**: partition layout sai, files không tạo
- **Rate Limiting**: smart rate limit implementation

Mục "Debug Recipes" trong `references/troubleshooting.md`:
- Check data lake content (ls + file count)
- Check dlt state (`.dlt/pipelines/{name}/`)
- Full pipeline dry run local (`--limit 1`)

---

## Lessons Cross-Reference

### Ingestion Core (L1-L7)

| ID | Summary | Link |
|----|---------|------|
| L1 | Early-stop pagination — dừng khi empty page, không dùng total_count | `../references/lessons-learned.md#L1` |
| L2 | Incremental cursor path — dùng full dotted path `sync_metadata.event_timestamp` | `../references/lessons-learned.md#L2` |
| L3 | Envelope append-only — bridge tới MODEL dedup strategy | `../references/lessons-learned.md#L3` |
| L6 | Empty page retry — retry N lần với backoff trước khi stop | `../references/lessons-learned.md#L6` |
| L7 | `--full-refresh` support — reset BOTH last_value AND state dir | `../references/lessons-learned.md#L7` |

### Dagster Asset Wiring (L8-L10)

| ID | Summary | Link |
|----|---------|------|
| L8 | `argv=[]` khi gọi dlt run từ Dagster — tránh pick up Dagster sys.argv | `../references/lessons-learned.md#L8` |
| L9 | `os.chdir(DLT_DIR)` trước run — dlt resolve config paths từ CWD | `../references/lessons-learned.md#L9` |
| L10 | `load_dlt_configuration()` phải gọi đầu mỗi asset | `../references/lessons-learned.md#L10` |

### Authentication (L13, L27)

| ID | Summary | Link |
|----|---------|------|
| L13 | Cookie TTL — SharedCookieManager với TTL + 401/403 refresh on-demand | `../references/lessons-learned.md#L13` |
| L27 | Cookie TTL strategy — session invalid detection + re-login flow | `../references/lessons-learned.md#L27` |

### Webhook (L14-L15)

| ID | Summary | Link |
|----|---------|------|
| L14 | Webhook ACK at-least-once — ACK sau write, dedup là safety net | `../references/lessons-learned.md#L14` |
| L15 | Consumer loop vs one-off — flag-based mode switch | `../references/lessons-learned.md#L15` |

### Sapo History Log (L16, L24-L26)

| ID | Summary | Link |
|----|---------|------|
| L16 | History Log URI Inference — infer từ entity type | `../references/lessons-learned.md#L16` |
| L24 | Entity Registry pattern — central registry entity → history_log | `../references/lessons-learned.md#L24` |
| L25 | NEVER `refresh="drop_sources"` — xóa TẤT CẢ tables trong shared dataset | `../references/lessons-learned.md#L25` |
| L26 | Smart rate limiting — track window, sleep delta, không fixed | `../references/lessons-learned.md#L26` |

### Full-Refresh & Config (L33, L35)

| ID | Summary | Link |
|----|---------|------|
| L33 | dlt incremental 2-layer filter — reset BOTH manual check AND state file | `../references/lessons-learned.md#L33` |
| L35 | Config ecosystem — layered defaults, single .env, DLT `__` mapping | `../references/lessons-learned.md#L35` |

### Config Snapshot & API Bugs (L57, L59, L76)

| ID | Summary | Link |
|----|---------|------|
| L57 | history_log double-fetch — `min_overlap_items` reset behavior; KHÔNG raise lên 500 | `../references/lessons-learned.md#L57` |
| L59 | Config snapshot fixed path — Google Sheets dùng fixed path (không timestamp) | `../references/lessons-learned.md#L59` |
| L76 | Sapo orders API `created_on` bug — API silently ignores filter, trả all history | `../references/lessons-learned.md#L76` |

---

## Sapo-Specific Notes

Bốn gotcha thường gặp nhất với Sapo API:

1. **`created_on` filter bị ignore (L76):** Sapo orders API không filter theo `created_on`
   — trả về toàn bộ history bất kể giá trị. Dùng `modified_on` window thay thế.

2. **history_log truncation risk:** Sapo truncates history_log theo thời gian — data 2021-2025
   trong text partition là **irreplaceable**. KHÔNG xóa raw partition này. Xem plan
   `260422-raw-layer-compaction` và memory `project_sapo_history_log_truncation`.

3. **`min_overlap_items` (L57):** Giá trị hiện tại là tuned sau production incident.
   KHÔNG raise lên 500 — gây double-fetch toàn bộ history_log.

4. **NEVER `drop_sources` (L25):** `refresh="drop_sources"` xóa TẤT CẢ tables trong
   `sapo_raw` dataset, kể cả tables không liên quan. Dùng `full_refresh` flag.

---

## Rollback Scenarios

Khi pipeline fail, đọc 4 scenarios trong `../checklist.md` "Rollback Plan":

| Scenario | Action |
|---------|--------|
| 1. dlt state corrupt | `python scripts/clean_dlt_state.py` hoặc `python run_{entity}.py --full-refresh` |
| 2. dbt incremental stuck | `dbt run --full-refresh --select src_{source}_{entity}` |
| 3. Serving view dropped | Fix mart `location` config → rerun dbt → `generate_serving_db.py` |
| 4. Xóa source hoàn toàn | 5-step: xóa ingestion code → dbt models → Dagster asset → config → parquet |

Chi tiết từng step → `../checklist.md` "Rollback Plan" section.

---

## Cross-cutting Refs

| Concern | Link |
|---------|------|
| DuckDB write lock (nếu asset write DuckDB) | `cross-cutting.md#duckdb-locking` |
| Env vars, config layering, DLT `__` mapping | `cross-cutting.md#env-vars-config-resolution` |
| CWD setup và `load_dlt_configuration` | `cross-cutting.md#cwd-and-load_dlt_configuration` |

---

## When INGEST Interacts with Other Groups

| Interaction | Detail |
|------------|--------|
| INGEST → MODEL | Parquet files tại `data_lake/{entity}/ingest_method=*/...` — MODEL đọc qua `sources.yml` Hive glob |
| INGEST → TRUST | `record_run()` phải gọi trong mỗi ingestion asset để TRUST layer có data |
| INGEST → OPS | Dagster asset registration, concurrency tags, schedule assignment |
| L4 (MODEL) cross-ref | `ingest_method` priority trong dbt dedup dùng values từ envelope (`batch_sync` > `history_log` > `webhook`) |
