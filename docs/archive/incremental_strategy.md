# Chiến Lược Incremental Sync & Transformation (DLT + DBT)

Tài liệu này chi tiết hóa cách xử lý **Incremental** từ Ingestion (DLT) đến Transformation (DBT), tận dụng cơ chế partitioning sẵn có và giải quyết bài toán hợp nhất dữ liệu đa nguồn.

## 1. Hiện Trạng Ingestion (DLT)

Hệ thống DLT hiện tại đã được cấu hình tối ưu với cơ chế **Partitioning nhiều cấp**, cho phép quản lý dữ liệu hiệu quả theo nguồn và thời gian.

**Cấu trúc thư mục (Parquet):**

```text
sapo_raw/
  ├── {table_name}/ (e.g., order, customer)
  │   ├── ingest_method={method}/ (e.g., batch_sync, webhook, history_log)
  │   │   ├── year={YYYY}/
  │   │   │   ├── month={MM}/
  │   │   │   │   └── {file_id}.parquet
```

### Bảng Phân Luồng Dữ Liệu (Data Flow Matrix)

Dưới đây là ma trận chi tiết cách dữ liệu chảy từ Sapo về Data Warehouse, được điều chỉnh cho cơ chế Ingestion hiện tại (DLT Partitioning).

| **Entity**    | **Channel**     | **Ingest Method** (Partition) | **Source Endpoint/Topic**              | **Tần Suất** | **Chiến lược Sync**           | **Mục Đích & Đặc Điểm**                                                                                           |
| :------------ | :-------------- | :---------------------------- | :------------------------------------- | :----------- | :---------------------------- | :---------------------------------------------------------------------------------------------------------------- |
| **Orders**    | **Batch API**   | `batch_sync`                  | `GET /admin/orders.json`               | Daily/Hourly | **Incremental (Modified On)** | **Sync nền tảng**. Lấy orders mới tạo hoặc sửa đổi. Sort `modified_on desc`. Dữ liệu đầy đủ nhất nhưng có độ trễ. |
|               | **Webhook**     | `webhook`                     | `orders/create`, `orders/updated`      | Real-time    | **Event Push**                | **Nguồn chính cho Update**. Nhận diện thay đổi tức thì. Payload chứa snapshot tại thời điểm change.               |
|               | **History Log** | `history_log`                 | `GET /admin/settings/get_logs`         | 5-10 mins    | **Incremental (Polling)**     | **Gap Filling & Audit**. Bắt các thay đổi mà Webhook có thể miss. Dùng để trigger fetch lại entity mới nhất.      |
| **Customers** | **Batch API**   | `batch_sync`                  | `GET /admin/customers/doSearch.json`   | Daily        | **Incremental (Created On)**  | **Chỉ lấy khách hàng MỚI**. Do API sort `modified_on` yếu, chỉ tin cậy dùng `created_on` để lấy new customers.    |
|               | **Webhook**     | `webhook`                     | `customers/create`, `customers/update` | Real-time    | **Event Push**                | **Nguồn DUY NHẤT** để lấy update bán tự động (semi-auto).                                                         |
|               | **History Log** | `history_log`                 | `GET /admin/settings/get_logs`         | 5-10 mins    | **Incremental (Polling)**     | **Nguồn Update Dự Phòng**. Cực kỳ quan trọng với Customer vì Batch không lấy được update.                         |
| **Accounts**  | **Batch API**   | `batch_sync`                  | `GET /admin/accounts.json`             | Daily        | **Full Scan**                 | **Full Scan**. Số lượng ít (< 100), quét toàn bộ để đảm bảo danh sách nhân viên luôn đúng.                        |

### Giải Thích Cơ Chế Dòng Chảy

1.  **Ingestion Layer (DLT)**:
    - Không cố gắng merge dữ liệu ngay lập tức.
    - Nhiệm vụ duy nhất là **Capture & Store**.
    - Lưu trữ phân tách (Segregated Storage) vào các folder riêng biệt dựa trên `ingest_method`.
    - Ví dụ: Một khách hàng vừa được tạo (Batch), sau đó sửa địa chỉ (Webhook). Ta sẽ có 2 file Parquet ở 2 thư mục khác nhau:
      - File 1: `.../ingest_method=batch_sync/.../customer_A.parquet` (Created)
      - File 2: `.../ingest_method=webhook/.../customer_A_v2.parquet` (Updated)

2.  **Transformation Layer (DBT)**:
    - Đây là nơi "Điều kỳ diệu" xảy ra (The Magic Happens).
    - Coi toàn bộ các file Parquet ở các partition trên là một **Dòng Sự Kiện (Event Stream)** hỗn hợp.
    - `dbt` sẽ đọc tất cả, sau đó dùng thuật toán **Deduplication** (loại bỏ trùng lặp) dựa trên thời gian để tìm ra trạng thái cuối cùng.
    - **Tại sao cách này tốt hơn cũ?** Cách cũ thường cố gắng update trực tiếp vào database (Upsert) ngay lúc ingest, gây nghẽn cổ chai (bottleneck) và phức tạp khi xử lý conflict. Cách mới dùng năng lực xử lý cực mạnh của DuckDB để tính toán lại state on-the-fly hoặc batch cực nhanh.

---

## 2. Chiến Lược Transformation & Serving (Zero-Downtime Architecture)

Để đảm bảo khả năng phục vụ dữ liệu liên tục (High Availability) trên môi trường Windows (nơi file locking là vấn đề nghiêm trọng) và hỗ trợ cập nhật tần suất cao (1 phút/lần), chúng ta áp dụng chiến lược **"Rolling Snapshots"**.

### A. Vấn Đề Của Chiến Lược Cũ (Folder Swapping)

Chiến lược cũ tạo folder `v_YYYYMMDD_HHMMSS` mới cho mỗi lần chạy và switch symlink/view:

1.  **Downtime**: Để switch file `.duckdb` đang được Metabase lock, phải Stop Container -> Swap -> Start Container. Gây gián đoạn dịch vụ mỗi phút.
2.  **Locking**: Trên Windows, không thể ghi đè (overwrite) lên file Parquet nếu Metabase đang query nó.
3.  **Missing Data**: Các model `incremental` chỉ update state nội bộ của DuckDB mà không tự động export ra folder version mới, dẫn đến serving layer bị thiếu dữ liệu.

### B. Chiến Lược Mới: Rolling Snapshots (Immutable Append)

Thay vì cố gắng ghi đè hay tráo đổi folder, chúng ta coi Storage là một **Log** các bản Snapshots.

#### 1. Nguyên Lý Hoạt Động

- **Stable Storage**: Sử dụng một thư mục cố định `data_lake/export/marts/rolling/`.
- **Immutable Writes**: Mỗi lần pipeline chạy, tạo một file Parquet **MỚI** với timestamp (VD: `dim_customers_20240127_1001.parquet`). Không bao giờ ghi đè file cũ.
- **Smart Views**: DuckDB Serving Layer sử dụng View động để luôn đọc file mới nhất:
  ```sql
  CREATE VIEW dim_customers AS
  WITH source AS (
      SELECT *, filename FROM read_parquet('.../dim_customers/*.parquet', filename=True)
  )
  SELECT * EXCLUDE (filename)
  FROM source
  WHERE filename = (SELECT MAX(filename) FROM source)
  ```
- **Lazy Cleanup**: Sau khi update View, hệ thống sẽ thử xóa các file cũ.
  - Nếu file cũ đang được Metabase đọc (Locked) -> **Bỏ qua**, để lại cho lần chạy sau xóa.
  - Nếu file rảnh -> **Xóa ngay**.
  - Kết quả: Hệ thống luôn duy trì 1-3 file mới nhất, không bao giờ crash do lock.

### C. Áp Dụng Chi Tiết

#### 1. Dimensions (VD: `dim_customers`)

- **Dữ liệu**: Nhỏ (< 1GB), thay đổi chậm hoặc vừa.
- **Cách Export**: **Full Rolling Snapshot**.
- **Cơ chế**:
  - DBT chạy `incremental` để update bảng nội bộ `sapo_warehouse.duckdb` (Merge logic).
  - `post-hook` thực hiện `COPY ... TO ...` để dump toàn bộ bảng ra file Parquet mới.
- **Ưu điểm**: Đơn giản, đảm bảo tính nhất quán (Consistency).

#### 2. Facts (VD: `fact_orders`)

- **Dữ liệu**: Lớn, tăng trưởng nhanh theo thời gian.
- **Thách thức**: Dump toàn bộ 10GB+ mỗi phút là lãng phí và chậm.
- **Cách Export**: **Hybrid Partitioning (Future Scoping)**
  - **History (Các tháng cũ)**: Lưu tĩnh (Static Files), ví dụ `orders_2023.parquet`. Không bao giờ ghi lại trừ khi backfill.
  - **Current (Tháng hiện tại)**: Áp dụng **Rolling Snapshot**. Chỉ dump dữ liệu tháng này ra file mới (VD: `orders_current_v1001.parquet`).
  - **Serving View**: `SELECT * FROM read_parquet('history/*.parquet') UNION ALL SELECT * FROM read_parquet('current/*.parquet')`.

---

## 3. Tích Hợp Dagster & Pipeline

1.  **DbtAsset**: Cấu hình `DBT_EXPORT_PATH` trỏ tới `.../rolling`.
2.  **Models**:
    - Config `incremental` để giữ hiệu năng tính toán.
    - Sử dụng `post-hook` hoặc `location` config động để ghi file có timestamp.
3.  **Serving Asset**: Chạy script `generate_serving_db.py` với chế độ "Update & GC" (Update View và Garbage Collect file thừa).

---

## 4. Tổng Kết

Chiến lược này giải quyết triệt để bài toán **Zero Downtime** trên Windows bằng cách tuân thủ nguyên tắc "First Principle": **Không bao giờ ghi vào file đang được đọc. Luôn ghi vào file mới.**
