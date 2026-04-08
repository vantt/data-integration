# Troubleshooting — Data Pipeline (dlt + dbt + Serving + Dagster)

## dlt — Auth / Session

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| 401 loop — refresh không dừng | `login_selectors` sai, playwright không login được | Test thủ công: `python -c "from sapo.login import do_login; do_login()"` |
| 403 sau khi refresh thành công | IP bị chặn hoặc account bị lock | Kiểm tra admin panel, thử login manual trên browser |
| Cookie hết hạn quá nhanh | TTL default 6h, server invalidate sớm hơn | Giảm `cookie_ttl` trong SharedCookieManager |

## dlt — Pipeline State / Incremental

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| Pipeline không pick up data mới | `last_value` stale trong state | `python run_{entity}.py --full-refresh` hoặc xóa `.dlt/pipelines/{name}/` |
| Incremental cursor không update | Field path sai | Verify: `"sync_metadata.event_timestamp"` match envelope key |
| Pipeline kẹt, state có pending packages | Crash giữa write | `python scripts/clean_dlt_state.py` |
| Full refresh quá chậm | Scan toàn API | Dùng `--limit N` khi test, full run off-peak |

## dlt — Config / Credentials

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| `KeyError: sources.{source}.username` | Credentials không load | Kiểm tra `secrets.toml` có section, hoặc env var `SOURCES__{SOURCE}__USERNAME` |
| `SOURCES__SAPO__DOMAIN is MISSING` (Dagster log) | `load_dlt_configuration()` chưa gọi | Gọi đầu asset; kiểm tra `ingestion/.env.local` tồn tại |
| Parquet lưu sai chỗ | `bucket_url` không set | Set `DESTINATION__FILESYSTEM__BUCKET_URL=file:///path/to/data_lake` |

## dlt — Parquet / Partition

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| Partition layout sai (không có `ingest_method/year/month`) | `extra_placeholders` thiếu | Thêm vào `[destination.filesystem]` trong `config.toml` |
| Parquet files không tạo | Pipeline run OK nhưng không có data mới | Verify `last_value` — nếu up-to-date thì không write gì |

## dbt — OOM / Memory

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| `Out of Memory` khi chạy src_ model | Payload + dedup + enrichment trong 1 query | Tách `src_` (extract+dedup) và `stg_` (enrichment) — xem `dbt-patterns.md` Lesson 2 |
| dbt crash full refresh | Dataset quá lớn, không có 7-day lookback | Tăng `memory_limit` tạm thời trong `profiles.yml`, hoặc chạy incremental từng chunk |
| Multiple models cùng crash OOM | `threads > 1` → concurrent buffers | Set `threads: 1` trong `profiles.yml` |
| Sort spill liên tục | `memory_limit` quá cao (= container limit) | Giảm `memory_limit` xuống **dưới** container limit (e.g., 5GB nếu container 8GB) |

## dbt — Incremental / Late Events

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| Row count thấp hơn expected | Late-arriving events không được re-process | Verify 7-day lookback: `WHERE event_timestamp > MAX - INTERVAL 7 DAY` |
| Duplicate rows trong dbt output | Dedup logic bị sai | Verify two-phase dedup: tech (entity_id) → biz (biz_key) |
| `unique_key` constraint fail | `delete+insert` không xóa hết rows cũ | Kiểm tra `unique_key` match với biz_key dedup partition |

## dbt — Source / Reference

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| `source not found: {source}_raw` | Source chưa đăng ký | Thêm section vào `transformation/models/sources.yml` |
| `read_parquet failed: no files found` | Glob pattern không match | Verify `external_location` pattern + files có tồn tại |
| JSON field bị null | `json_extract_string` path sai | Debug: `SELECT payload FROM src LIMIT 1;` — kiểm tra actual structure |
| Field sometimes nested, sometimes root | API response inconsistent | Dùng `coalesce(json_extract_string(payload, '$.a.b'), json_extract_string(payload, '$.b'))` |

## dbt — Mart / Export

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| **Mart model không xuất hiện trong serving DB** | Thiếu `location="{{ get_rolling_location() }}"` | Thêm vào `{{ config(...) }}` — **rule #1 của transformation layer** |
| `COPY failed: directory does not exist` | Rolling dir chưa tạo | `python scripts/ensure_dbt_directories.py` |
| Circular dependency error | dim → fact → dim | Tách `dim_X_base` (no metrics) + `int_X_metrics` — xem `dbt-patterns.md` Lesson 6 |
| Fact rows bị drop sau join | Missing dimension key | UNION ALL một row "Unknown" vào dim, dùng `COALESCE` fact-side |

## Serving Layer

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| `[!] Empty folder: dim_xyz` trong log | Mart model chưa chạy hoặc thiếu `location` | 1. Kiểm tra `rolling/{model}/` có parquet. 2. Nếu không → fix `location` trong model config và re-run dbt |
| View bị drop sau serving script | Folder trống → script tự drop view | Giống trên — fix source của vấn đề trong dbt model |
| Metabase query fail `view does not exist` | View bị drop do empty folder | Re-run `generate_serving_db.py` sau khi fix dbt model |
| `[GC] SKIP Locked file` | Linux reader đang đọc file cũ | Bình thường — next run sẽ retry. Không phải lỗi |
| `WARNING: Could not connect to DuckDB` | `olap.duckdb` đang bị lock bởi reader | Bình thường (best-effort mode) — smart views đã có sẵn, query vẫn work |
| Smart view trả data cũ | Latest file mới chưa được viết xong khi view query | Race condition hiếm — retry query sau vài giây |
| Rolling folder có nhiều file cũ | GC fail liên tục | Kiểm tra quyền folder, hoặc chạy manual `generate_serving_db.py` |

## Dagster — Asset / Job

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| `unrecognized arguments: --dagster-...` | `argv=None` thay vì `argv=[]` | Sửa: `run_{entity}.run(argv=[])` |
| `database is locked` trong logs | Concurrent DuckDB writes | Thêm `op_tags={"dagster/concurrency_key": "duckdb_lock"}` |
| Asset fail với `ModuleNotFoundError` | `DLT_DIR` chưa trong `sys.path` | Kiểm tra `orchestration/assets/utils.py` → `DLT_DIR` đúng |
| Asset không tạo parquet | `os.chdir(DLT_DIR)` thiếu | dlt resolve `.dlt/` từ CWD — phải `chdir` vào `ingestion/` |
| Credentials không load | `load_dlt_configuration()` chưa gọi | Gọi đầu asset trước `os.chdir()` |
| Serving asset chạy trước dbt xong | Thiếu `deps` | Thêm `deps=[sapo_dbt_assets]` trong `@asset` |
| Asset `sapo_serving_db` fail silently | Script báo warning nhưng exit 0 | Kiểm tra logs output — script check `"error"` và `"[!]"` markers |
| **Job exit quá chậm / timeout** | dlt hoặc dbt telemetry threads giữ process sống | Set `DLT_TELEMETRY_DISABLED=true` + `DBT_SEND_ANONYMOUS_USAGE_STATS=false` ở docker-compose hoặc shell wrapper (không đặt trong Python code) |
| **dbt start trước khi ingestion xong** (stale data) | Job chứa nhiều ingestion methods, dbt source chỉ map tới 1 upstream | Inject explicit upstream keys trong `DagsterDbtTranslator.get_upstream_asset_keys()` — xem `dagster-patterns.md` Lesson 1 |
| 2 schedule cùng trigger gây deadlock | Start-time race — cả hai check "other running?" cùng lúc | Offset cron minute marks (e.g., realtime: `1,4,7...`; incremental: `*/10 0-3,5-23`) — xem `dagster-patterns.md` Lesson 2 |
| Schedule không skip khi job trước đó đang chạy | Thiếu check `NOT_STARTED` status | Include `DagsterRunStatus.NOT_STARTED` trong `statuses` filter của `get_runs()` |
| dbt mart COPY fail với "directory not found" lần đầu | Rolling subfolder chưa tồn tại | Pre-create dirs trong `@dbt_assets` function (idempotent `os.makedirs(exist_ok=True)`) — không chỉ dựa vào standalone script |

## Rate Limiting

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| 429 Too Many Requests thường xuyên | `request_delay` quá thấp | Tăng `request_delay` trong `config.toml` |
| Pipeline dừng sau 429 | Tenacity retry hết | 429 handler đợi `Retry-After` header — default 60s nếu thiếu |

---

## Debug Recipes

### Check data lake content
```bash
ls -la data_lake/{entity}/ingest_method=*/year=*/month=*/
duckdb -c "SELECT COUNT(*) FROM read_parquet('data_lake/{entity}/**/*.parquet', hive_partitioning=1)"
```

### Check dlt state
```bash
ls ingestion/.dlt/pipelines/
cat ingestion/.dlt/pipelines/{pipeline_name}/state.json | jq .sources
```

### Check dbt incremental state
```bash
duckdb data_lake/sapo_warehouse.duckdb -c \
  "SELECT MAX(event_timestamp), COUNT(*) FROM staging.src_sapo_orders"
```

### Check rolling snapshot latest
```bash
ls -lt data_lake/export/marts/rolling/dim_customers/ | head -5
```

### Check serving view
```bash
duckdb data_lake/serving/olap.duckdb -c \
  "SELECT name FROM sqlite_master WHERE type='view'"
duckdb data_lake/serving/olap.duckdb -c \
  "SELECT COUNT(*) FROM dim_customers"
```

### Full pipeline dry run (local)
```bash
# 1. Ingestion
cd ingestion && python run_orders_batch.py --limit 5

# 2. Transformation
cd ../transformation && python scripts/run_dbt.py --select src_sapo_orders+

# 3. Serving
cd .. && python scripts/ensure_dbt_directories.py
python scripts/provisioning/generate_serving_db.py

# 4. Verify
duckdb data_lake/serving/olap.duckdb -c "SELECT * FROM dim_customers LIMIT 5"
```
