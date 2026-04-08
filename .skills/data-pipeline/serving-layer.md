# Serving Layer Mechanism

Cơ chế serving DB cho DuckDB: **rolling snapshots + smart views + zero-downtime swap**.

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
                │ 2. Create/update Smart View in olap.duckdb
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

**Naming quan trọng:** Timestamp ở cuối filename → **lexical sort = chronological sort**. Smart view dùng `max(filename)` để pick latest.

**Mỗi dbt run tạo file mới** — không overwrite. Zero-downtime vì old file vẫn valid cho các query đang chạy.

---

## 2. Smart View Pattern

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

Sau khi smart view được update, script xóa các file cũ (giữ lại file mới nhất):

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

## 4. Best-Effort DB Lock Handling

Nếu `olap.duckdb` đang bị lock (Metabase hoặc process khác đang connect), script **không fail**:

```python
try:
    con = duckdb.connect(SERVING_DB_PATH)
except Exception:
    db_locked = True  # Skip view updates, but vẫn chạy GC

# Later:
if not db_locked and con:
    con.sql("CREATE OR REPLACE VIEW ...")
```

**Lý do an toàn:**
- Smart views đã được tạo từ trước → query vẫn trả về latest file (vì view definition là glob pattern, không phải static file path)
- GC vẫn chạy được vì chỉ cần filesystem access
- Lần chạy sau khi DB free → view definition được update nếu cần

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

**Asset DAG:**
```python
# orchestration/assets/serving.py
@asset(
    deps=[sapo_dbt_assets],    # Chạy SAU khi dbt assets complete
    group_name="serving_layer"
)
def sapo_serving_db(context):
    subprocess.run(
        [PYTHON_EXE, SCRIPT_PATH],   # scripts/provisioning/generate_serving_db.py
        cwd=PROJECT_ROOT,
        check=True
    )
```

**Asset chain (nightly job):**
```
sapo_orders_batch_asset
sapo_customers_batch_asset
sapo_accounts_batch_asset
         │
         ▼
sapo_dbt_assets (build all models + export rolling parquets)
         │
         ▼
sapo_serving_db (Smart Views + GC)
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

# Count rows trong smart view
duckdb data_lake/serving/olap.duckdb -c "SELECT COUNT(*) FROM dim_customers"

# Kiểm tra latest file trong rolling folder
ls -lt data_lake/export/marts/rolling/dim_customers/ | head -5

# Force rerun serving script
python scripts/provisioning/generate_serving_db.py
```
