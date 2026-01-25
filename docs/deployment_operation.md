# Deployment & Operations Guide

This document provides guidelines for deploying and operating the Data Warehouse components, including DLT pipelines and the Metabase Serving layer.

---

## 1. DLT Operations

### Configuration

DLT uses a hierarchical configuration system.

- **Secrets (`dlt/.dlt/secrets.toml`)**: Contains sensitive information like database credentials, API keys, and specific destination paths.
  - _Example_: `bucket_url` for filesystem destination, Sapo credentials.
- **Config (`dlt/.dlt/config.toml`)**: Contains non-sensitive, shared configurations.
- **`bucket_url`**: Defines where the Parquet files are stored (Data Lake path).
  - Location: `[destination.filesystem]` in `secrets.toml`.
  - Value: `file:///d:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake`

### State Management

DLT maintains "State" to track what data has been loaded (Incremental Loading).

1.  **Local State (The "Brain")**
    - **Location**: `C:\Users\<User>\.dlt\pipelines\<pipeline_name>`
    - **Effect**: DLT checks this _first_ to determine what data to fetch next.

2.  **Destination State (The Backup)**
    - **Location**: `data_lake/sapo_raw/_dlt_pipeline_state` (or inside the dataset).
    - **Effect**: If Local State is missing, DLT restores state from here to continue loading.

### Troubleshooting

#### Force a Full Refresh (Reset Pipeline)

1.  **Delete Local State**: `rd /s /q C:\Users\<User>\.dlt\pipelines\<pipeline_name>`
2.  **Delete Destination Data**: Remove corresponding folder in `data_lake/sapo_raw/<entity_name>`
3.  **Run Pipeline**: Execute the run script.

#### Common CLI Commands

Run from `dlt/` with `venv` activated.

- `dlt pipeline <pipeline_name> info`: Check status.
- `dlt pipeline <pipeline_name> sync`: Sync state.

---

## 2. Metabase Deployment (Docker)

To serve the OLAP data (Parquet + DuckDB Views), we use Metabase running in a Docker container.

### Prerequisites

- **Docker Desktop** installed on Windows.
- **Git Bash** or PowerShell.

### Directory Structure & Volumes

Critical: We map the local `data_lake` folder to `/data_lake` inside the container.

- **Host Path**: `.\data_lake`
- **Container Path**: `/data_lake`

### Docker Compose Configuration

Create a `docker-compose.yml` file in the project root:

```yaml
version: "3.9"
services:
  metabase:
    image: metabase/metabase:latest
    container_name: metabase_sapo
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      # 1. Mount Data Lake (Read-only recommended for safety, but Read-Write needed if DuckDB writes temp files)
      - ./data_lake:/data_lake

      # 2. Persist Metabase App Data (Users, Dashboards settings)
      - metabase_data:/metabase-data
    environment:
      - MB_DB_FILE=/metabase-data/metabase.db
      - MB_JETTY_PORT=3000

volumes:
  metabase_data:
```

### Setup Steps

1.  **Start Metabase**:

    ```powershell
    docker-compose up -d
    ```

2.  **Access UI**:
    Open [http://localhost:3000](http://localhost:3000)

3.  **Add Data Source**:
    - **Database Type**: DuckDB (You may need to install the DuckDB driver plugin for Metabase if not included, or use the official Metabase image if it supports it. _Note: Standard Metabase might not have DuckDB driver by default. If so, use a custom image or mount the driver jar._)
    - **Display Name**: `Sapo OLAP`
    - **Database File Path**: `/data_lake/serving/olap.duckdb`

    > **Important**: The path MUST be `/data_lake/...` (Docker path), NOT `D:\...`.

---

## 3. Serving Layer Operations

### Updating the Serving View (`olap.duckdb`)

After `dlt` and `dbt` have run, the `olap.duckdb` file needs to have its Views created/updated to point to the new Parquet files.

**Script**: `scripts/update_serving_views.py` (Example)

```python
import duckdb

# Connect to the serving DB file
con = duckdb.connect('data_lake/serving/olap.duckdb')

# Create View pointing to Docker path
con.sql("CREATE OR REPLACE VIEW dim_customers AS SELECT * FROM '/data_lake/export/marts/dim_customers/*.parquet'")
con.sql("CREATE OR REPLACE VIEW fact_orders AS SELECT * FROM '/data_lake/export/marts/fact_orders/*.parquet'")

con.close()
```

---

---

# Hướng Dẫn Vận Hành Hệ Thống Data Pipeline (Operator Guide)

Tài liệu này hướng dẫn chi tiết cách vận hành, giám sát và xử lý sự cố cho hệ thống tích hợp dữ liệu (Data Integration Pipeline).

## 1. Tổng Quan Hệ Kiến Trúc

Hệ thống được chia thành 3 tầng chính:

1.  **Ingestion (DLT)**: Kéo dữ liệu từ nguồn (Sapo API, Webhook) về Data Lake (Parquet).
2.  **Transformation (DBT)**: Làm sạch và mô hình hóa dữ liệu (Staging -> Marts).
3.  **Serving (DuckDB/Metabase)**: Tạo database OLAP tối ưu cho báo cáo và deploy lên Metabase.

Toàn bộ quy trình được điều phối tự động bởi **Dagster**.

---

## 2. Vận Hành Tự Động (Dagster)

Hệ thống mặc định chạy tự động. Người vận hành giám sát qua **Dagster UI**.

- **Truy cập**: `http://localhost:3000` (hoặc IP server triển khai).
- **Cách chạy**:
  ```powershell
  # Tại thư mục gốc project
  ./run_dagster.ps1
  ```
- **Các Job Chính**:
  - `sapo_realtime_sync_job` (1 phút/lần): Ingestion Webhook + Transformation (Staging). Đảm bảo đơn mới lên báo cáo ngay lập tức.
  - `sapo_incremental_sync_job` (10 phút/lần): Ingestion History Log + Transformation (Staging). Bắt các thay đổi bị miss bởi webhook.
  - `sapo_nightly_reconciliation_job` (Hàng ngày - 4:00 AM): Ingestion Full Batch (Orders/Customers/Accounts) + Full Transformation (All Layers). Đồng bộ lại toàn bộ dữ liệu chuẩn.

### Kiểm tra trạng thái

Trong tab **Runs** của Dagster UI:

- ✅ **Success**: Hệ thống bình thường.
- ❌ **Failure**: Click vào Job ID để xem log chi tiết lỗi.

---

## 3. Vận Hành Thủ Công (Manual Operations)

Trong trường hợp cần chạy gấp hoặc fix lỗi, có thể chạy thủ công bằng dòng lệnh (CLI).

### 3.1. Chạy Ingestion (DLT)

Sử dụng môi trường ảo Python của DLT:

```powershell
# Kích hoạt venv (nếu chưa)
.\dlt\venv\Scripts\activate

# Chạy kéo Orders (giới hạn 100 trang test)
python dlt/run_orders_batch.py --limit 100

# Chạy Webhook Consumer (chế độ chạy 1 lần rồi thoát)
python dlt/run_webhook_consumer.py --once

# Chạy Webhook Consumer (chế độ lặp vô tận - service)
python dlt/run_webhook_consumer.py --loop
```

### 3.2. Chạy Transformation (DBT)

Sử dụng script wrapper đã chuẩn hóa:

```powershell
# Chạy toàn bộ các model Mart
python transformation/scripts/run_dbt.py --select +tag:mart

# Chạy full-refresh (xóa bảng làm lại từ đầu)
python transformation/scripts/run_dbt.py --full-refresh
```

### 3.3. Chạy Full Deployment (Pipeline Khẩn Cấp)

Nếu muốn chạy lại quy trình deploy (DBT + Update Serving DB) thủ công:

```powershell
# Script này sẽ tự tìm dbt/python trong venv để chạy
./scripts/run_pipeline.ps1
```

---

## 4. Xử Lý Sự Cố Thường Gặp

### Lỗi: "Metabase bị lock database"

Nếu `generate_serving_db.py` báo lỗi không thể ghi đè file `olap.duckdb` do đang được sử dụng.

- **Giải pháp**: Pipeline tự động có cơ chế stop/start container Metabase. Nếu vẫn lỗi, hãy chạy thủ công:
  ```powershell
  docker restart metabase
  ./scripts/run_pipeline.ps1
  ```

### Lỗi: "DLT thiếu dữ liệu"

Nếu thấy báo cáo thiếu đơn hàng mới.

1.  Kiểm tra `sapo_history_log_job` trong Dagster xem có lỗi không.
2.  Chạy thủ công `sapo_orders_batch_job` (nút **Materialize** trong Dagster) để kéo lại toàn bộ dữ liệu.

### Lỗi: "Schema Mismatch"

Nếu API Sapo thay đổi cấu trúc dữ liệu làm DLT lỗi.

1.  Cập nhật code DLT trong `dlt/src/sapo/`.
2.  Chạy pipeline với cờ `--full-refresh` (hoặc drop state trong Dagster) để tái tạo schema.
