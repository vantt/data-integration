# Supporting Scripts

Các script hỗ trợ cho data pipeline — không thuộc core ingestion/transform nhưng cần thiết để vận hành.

---

## Provisioning

### `scripts/provisioning/generate_serving_db.py`

**Mục đích:** Tạo/update Rolling Self-Refresh Views trong `olap.duckdb` từ rolling parquets + garbage collect file cũ.

**Input:**
- `DBT_DATA_LAKE_PATH` env (default `/app/data_lake`)
- `DBT_EXPORT_PATH` env (default `{data_lake}/export/marts`)

**Output:**
- Views tại `{data_lake}/serving/olap.duckdb`
- Xóa file parquet cũ, giữ lại file mới nhất trong mỗi `rolling/{model}/`

**Gọi khi:**
- Sau khi dbt build complete (Dagster asset `build_serving_db` với `deps=[sapo_dbt_assets]`)
- Thủ công sau khi debug dbt mart model

**Usage:**
```bash
python scripts/provisioning/generate_serving_db.py
```

**Behavior:**
- Best-effort DB lock handling (skip view updates nếu DB locked, vẫn chạy GC)
- Table name allowlist: `^[a-zA-Z_][a-zA-Z0-9_]*$` → bảo vệ SQL injection
- Retry 0.5s khi xóa file bị lock (Linux transient reads)

**Chi tiết cơ chế:** xem `serving-layer.md`.

---

### `scripts/provisioning/metabase_provisioner.py`

**Mục đích:** Provision Metabase dashboards, databases, collections.

**Usage:** Xem chính script để hiểu workflow Metabase provisioning.

---

## Ingestion Support

### `scripts/clean_dlt_state.py`

**Mục đích:** Drop pending packages từ dlt pipeline state — recovery khi pipeline bị kẹt giữa chừng.

**Usage:**
```bash
cd ingestion
python ../scripts/clean_dlt_state.py
```

**Khi dùng:**
- Pipeline crash giữa lúc write → state còn pending packages → pipeline fail lần sau
- Sau khi `--full-refresh` bị ngắt giữa chừng
- Debug pipeline không pick up data mới

**Behavior:**
- Attach vào pipelines: `sapo_orders_batch`, `sapo_customers_batch`, `sapo_accounts_batch`, `sapo_history_log_pipeline`
- Gọi `p.drop_pending_packages()`
- Không exit code 1 kể cả khi fail (để không crash runner)

**Sửa khi thêm pipeline mới:** Thêm tên pipeline vào list `pipelines_to_clean`.

---

### `scripts/inspect_customer_parquet.py`

**Mục đích:** Quick inspect parquet files trong data lake để verify schema/content.

Thường dùng khi debug dbt src_ model để xem raw data structure.

---

## dbt Support

### `scripts/ensure_dbt_directories.py`

**Mục đích:** Pre-create `rolling/{model}/` directories cho mỗi mart model trong `models/marts/`.

**Tại sao cần:** dbt `COPY TO '{location}/{file}.parquet'` fail nếu parent directory không tồn tại. `get_rolling_location()` tạo path nhưng không tạo dir.

**Usage:**
```bash
python scripts/ensure_dbt_directories.py
```

**Chạy khi nào:**
- Trước mỗi `dbt build` / `dbt run` (idempotent, safe to call multiple times)
- Sau khi thêm mart model mới
- Tích hợp trong `transformation/scripts/run_dbt.py` wrapper

**Input:** `DBT_EXPORT_PATH`, `DBT_PROJECT_DIR` env vars  
**Behavior:** Scan `models/marts/**/*.sql`, tạo `{export_path}/rolling/{model_name}/` cho mỗi file.

---

### `transformation/scripts/run_dbt.py`

**Mục đích:** Wrapper cho `dbt build` với auto directory creation.

**Usage:**
```bash
# Chạy tất cả mart models (default)
python transformation/scripts/run_dbt.py

# Chạy model cụ thể
python transformation/scripts/run_dbt.py --select src_sapo_orders+

# Full refresh
python transformation/scripts/run_dbt.py --full-refresh --select src_sapo_orders

# Multi-select
python transformation/scripts/run_dbt.py --select "tag:mart" "+dim_customers"
```

**Features:**
- Auto-resolve dbt executable (venv → PATH fallback)
- Auto pre-create `rolling/{model}/` directories (scan `models/marts/`)
- Set CWD đúng `transformation/` (dbt yêu cầu)
- Load `.env` via python-dotenv
- Default select: `+tag:mart` (build tất cả mart models + upstream)

---

### `transformation/check_view.py`

**Mục đích:** Debug script — inspect view definitions trong serving DB.

**Usage:**
```bash
python transformation/check_view.py
```

**Hard-coded views:** `dim_channels`, `fact_sales` — sửa list trong script nếu cần check view khác.

---

## Maintenance

### `scripts/debug_duckdb.py`

**Mục đích:** Quick REPL vào DuckDB để kiểm tra tables, run queries.

### `scripts/maintenance/` (folder)

Các script maintenance như: backup DuckDB, cleanup logs, rotate snapshots.

### `scripts/backup/` (folder)

Backup scripts cho data lake & DuckDB files.

---

## Pipeline Runner (PowerShell)

### `scripts/run_pipeline.ps1`

**Mục đích:** Windows-only PowerShell wrapper — chạy ingestion + dbt + serving trong 1 command. Dùng khi dev local trên Windows không dùng Dagster.

---

## Khi Nào Gọi Script Nào

| Tình huống | Script |
|-----------|--------|
| Thêm mart model mới, muốn test | `ensure_dbt_directories.py` → `run_dbt.py --select {model}` → `generate_serving_db.py` |
| Pipeline kẹt, không pick up data mới | `clean_dlt_state.py` |
| Mart model thiếu data | `generate_serving_db.py` (check output "Empty folder") |
| Debug view content | `check_view.py` hoặc `debug_duckdb.py` |
| Full pipeline test local (Windows) | `run_pipeline.ps1` |
| Full pipeline test local (Linux) | `run_dbt.py` + `generate_serving_db.py` hoặc dùng Dagster UI |

---

## Integration trong Dagster

```python
# orchestration/assets/serving.py
@asset(deps=[sapo_dbt_assets], group_name="serving_layer")
def build_serving_db(context):
    subprocess.run(
        [PYTHON_EXE, "scripts/provisioning/generate_serving_db.py"],
        cwd=PROJECT_ROOT,
        check=True
    )
```

**Key insight:** Scripts được wrap trong Dagster asset qua subprocess thay vì rewrite thành native Python asset — giữ script standalone (chạy được ngoài Dagster) và asset thin (chỉ orchestrate).

Xem `templates/dagster-serving-asset-template.py` để tạo asset mới cho custom supporting script.
