# Serving Layer Mechanism

Cơ chế serving DB cho DuckDB: **rolling snapshots + Rolling Self-Refresh Views + zero-downtime swap**.

> **Terminology note (2026-04-08):** Trước đây gọi là `Smart View` — tên cũ mơ hồ ("smart" chỗ nào?). Tên mới `Rolling Self-Refresh View`
> nhấn mạnh cơ chế bên trong:
> - **Rolling**: nhiều phiên bản parquet coexist trong `rolling/<table>/`, GC xóa dần cái cũ
> - **Self-Refresh**: view scan glob và tự pick `max(filename)` mỗi query — không cần manual `CREATE OR REPLACE`
> - **View**: DuckDB view object, không phải materialized

---

## Flow tổng quan

```
[dbt mart model]
   │ (materialized=external, location=rolling)
   ▼
data_lake/export/marts/rolling/{model}/
   ├── {model}_20260407120000.parquet   ← oldest
   ├── {model}_20260407130000.parquet
   └── {model}_20260407140000.parquet   ← latest
                │
                │ [generate_serving_db.py]
                │ 1. Scan each table folder
                │ 2. Create/update Rolling Self-Refresh View in olap.duckdb
                │ 3. Garbage collect old parquets
                ▼
data_lake/serving/olap.duckdb
   └── VIEW {model} AS SELECT * FROM latest parquet
                │
                ▼
          [Metabase queries olap.duckdb]
```

---

## 1. Rolling Snapshots từ dbt

**Macro `get_rolling_location()`** (trong `transformation/macros/`):
```sql
{%- macro get_rolling_location() -%}
  {{ env_var('DBT_EXPORT_PATH') | replace('/rolling', '') }}/rolling/
  {{ this.name }}/
  {{ this.name }}_{{ run_started_at.strftime('%Y%m%d%H%M%S') }}.parquet
{%- endmacro -%}
```

**Ouput pattern:**
```
rolling/dim_customers/dim_customers_20260407120000.parquet
rolling/dim_customers/dim_customers_20260407130000.parquet  ← new run
```

**Naming quan trọng:** Timestamp ở cuối filename → **lexical sort = chronological sort**. Rolling Self-Refresh View dùng `max(filename)` để pick latest.

**Mỗi dbt run tạo file mới** — không overwrite. Zero-downtime vì old file vẫn valid cho các query đang chạy.

---

## 2. Rolling Self-Refresh View Pattern

**Core idea:** View tự động trỏ đến file mới nhất trong folder, không cần update view definition mỗi lần dbt chạy lại.

```sql
CREATE OR REPLACE VIEW dim_customers AS
WITH source_files AS (
    SELECT * FROM read_parquet(
        '/app/data_lake/export/marts/rolling/dim_customers/*.parquet',
        filename=true,
        hive_partitioning=0
    )
),
latest AS (
    SELECT max(filename) as max_fn FROM source_files
)
SELECT * EXCLUDE (filename)
FROM source_files
WHERE filename = (SELECT max_fn FROM latest)
```

**Tại sao hoạt động:**
- `read_parquet(glob, filename=true)` → thêm column `filename` vào kết quả
- `max(filename)` — vì timestamp ở cuối filename, max lexical = max chronological
- `WHERE filename = max_fn` → chỉ đọc file mới nhất
- `EXCLUDE (filename)` — hide utility column

**Zero-downtime swap:**
- Query đang chạy trên file cũ → vẫn hoạt động (file chưa bị GC)
- Query mới → pick up file mới ngay lập tức
- Không cần `DROP VIEW` + `CREATE VIEW` giữa chừng

---

## 3. Garbage Collection

Sau khi rolling self-refresh view được update, script xóa các file cũ (giữ lại file mới nhất):

```python
def garbage_collect(folder_path, latest_file):
    files = glob.glob(os.path.join(folder_path, "*.parquet"))
    for f in files:
        if os.path.basename(f) == latest_file:
            continue  # Keep latest
        try:
            os.remove(f)
        except PermissionError:
            # Linux: file có thể đang bị read → skip, retry lần sau
            pass
```

**Linux concurrency note:**
- Linux không có advisory file lock như Windows
- File đang bị read bởi Metabase query → vẫn có thể unlink, nhưng **inode chưa được free** cho đến khi reader close
- Retry once sau 0.5s để handle transient in-flight reads

---

## 4. DuckDB Lock Behavior — KHÔNG phải vấn đề như từng nghĩ

> **Post-mortem update 2026-04-08:** Trước đây phần này mô tả "best-effort lock handling" như defensive cho lock contention. Verified empirically rằng giả định ban đầu **sai**.

**Sự thật về DuckDB locking:**
- DuckDB connection mode `read_only=true` **KHÔNG acquire bất kỳ file lock nào** — chỉ mmap để read
- Khác SQLite (dùng shared lock cho readers)
- Metabase MotherDuck JDBC driver v1.4.4 với `read_only=true` cũng không lock
- **Test thực tế:** Metabase connected + holding session, Python `duckdb.connect(path)` (default RW) succeed trong 15ms. 2 reader + 1 writer cùng file = OK

**Hệ quả:**
- Pipeline writer (`bootstrap_serving_views.py`) + Metabase reader có thể coexist trên cùng `olap.duckdb`
- Script cũ có catch `except Exception: db_locked = True` — defensive code, **rất hiếm khi fire** trong production hiện tại
- Không cần stop Metabase trước khi chạy bootstrap (trừ khi muốn an toàn tuyệt đối)

**Pattern hiện tại (sau Pattern C split):**
1. `refresh_rolling.py` — chạy mỗi pipeline run, **không** mở DuckDB. Chỉ GC parquet files + detect schema drift.
2. `bootstrap_serving_views.py` — chạy thủ công khi schema drift. Mở DB rw, `CREATE OR REPLACE VIEW` cho từng table.

→ Runtime path không touch DB → kể cả nếu lock contention thực sự xảy ra (giả sử driver tương lai thay đổi behavior), pipeline vẫn không bị ảnh hưởng.

**Reference:** `lessons-learned.md` L18 cho chi tiết verification + `plans/260408-1611-fix-serving-db-hang-metabase-lock/plan.md` post-mortem section.

---

## 5. Empty Folder → Drop View

Khi mart model thiếu `location=get_rolling_location()`:
- dbt vẫn chạy thành công nhưng không ghi vào `rolling/{model}/`
- `generate_serving_db.py` thấy folder trống → log `[!] Empty folder: dim_xyz`
- Drop view `dim_xyz` trong serving DB
- **Metabase dashboard trỏ tới view này sẽ lỗi**

**Prevention:** Luôn có `location` trong mọi mart model. Xem Lesson 5 trong `dbt-patterns.md`.

---

## 6. Pre-Create Rolling Directories

dbt `COPY TO '...'` fail nếu parent directory không tồn tại. Script `scripts/ensure_dbt_directories.py` scan `models/marts/**/*.sql` và pre-create:

```
rolling/dim_customers/
rolling/dim_products/
rolling/fact_orders/
...
```

**Chạy khi nào:**
- Sau khi thêm mart model mới
- Trước mỗi dbt build (idempotent, safe to call multiple times)
- Tích hợp trong `run_dbt.py` wrapper

---

## 7. Dagster Integration

**Pattern C — Split runtime vs bootstrap:**

| Script | Khi nào chạy | Mở DuckDB? |
|---|---|---|
| `scripts/provisioning/refresh_rolling.py` | Mỗi pipeline run (Dagster asset) | ❌ KHÔNG |
| `scripts/provisioning/bootstrap_serving_views.py` | Thủ công khi schema drift | ✅ Có |

**Asset code:**
```python
# orchestration/assets/serving.py
@asset(deps=[sapo_dbt_assets], group_name="serving_layer")
def build_serving_db(context: AssetExecutionContext):
    # Streaming subprocess — see lessons-learned.md L17
    proc = subprocess.Popen(
        [PYTHON_EXE, "scripts/provisioning/refresh_rolling.py"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    output_lines = []
    for line in proc.stdout:
        output_lines.append(line.rstrip())
        context.log.info(line.rstrip())
    proc.wait(timeout=int(os.environ.get("SERVING_TIMEOUT_SEC", "1800")))
    if proc.returncode != 0:
        raise Exception(f"refresh_rolling exit {proc.returncode}")

    # Schema drift → raise to fire run_failure_sensor → Lark alert
    if any("[!] SCHEMA_DRIFT" in line for line in output_lines):
        raise Exception("Schema drift — run bootstrap_serving_views.py")
```

**Schema drift detection:**
- `refresh_rolling.py` ghi `.known_tables.json` marker file mỗi run
- Nếu phát hiện table folder mới so với marker → emit `[!] SCHEMA_DRIFT: <table>`
- Asset raise → `run_failure_sensor` (Lark) alert → operator chạy bootstrap thủ công

**Bootstrap workflow:**
```bash
# Stop Metabase (optional với DuckDB read_only — xem mục 4)
docker compose stop metabase
docker compose exec data_platform python scripts/provisioning/bootstrap_serving_views.py
docker compose start metabase
```

**Asset chain (nightly job):**
```
ingest_sapov2_orders_batch_asset
ingest_sapov2_customers_batch_asset
ingest_sapov2_accounts_batch_asset
         │
         ▼
sapo_dbt_assets (build all models + export rolling parquets)
         │
         ▼
build_serving_db (refresh_rolling.py — GC + drift detect)
         │
         ▼
[Metabase refreshes dashboards]
```

---

## Checklist khi thêm mart model mới

- [ ] Thêm `location="{{ get_rolling_location() }}"` vào config
- [ ] Chạy `python scripts/ensure_dbt_directories.py` để tạo rolling dir
- [ ] `dbt run --select dim_new_model` → verify parquet được ghi ra rolling/
- [ ] `python scripts/provisioning/generate_serving_db.py` → verify view được tạo
- [ ] Test view: `duckdb data_lake/serving/olap.duckdb -c "SELECT * FROM dim_new_model LIMIT 5"`
- [ ] Chạy lại dbt lần 2 → verify old parquet bị GC, view vẫn trả data mới

---

## Debug Commands

```bash
# Liệt kê tất cả views trong serving DB
duckdb data_lake/serving/olap.duckdb -c "SELECT name FROM sqlite_master WHERE type='view'"

# Xem view definition
python transformation/check_view.py   # hard-coded: dim_channels, fact_sales

# Count rows trong rolling self-refresh view
duckdb data_lake/serving/olap.duckdb -c "SELECT COUNT(*) FROM dim_customers"

# Kiểm tra latest file trong rolling folder
ls -lt data_lake/export/marts/rolling/dim_customers/ | head -5

# Force rerun serving script
python scripts/provisioning/generate_serving_db.py
```
