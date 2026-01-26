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

## 2. Chiến Lược Transformation (DBT + DuckDB)

Thách thức chính là làm sao để DBT đọc dữ liệu từ các partitions này một cách **Incremental** và **Hợp nhất (Merge)** chính xác để tạo ra "Golden Record".

### A. Định Nghĩa Source (External Tables)

Trong `sources.yml`, ta định nghĩa source pattern bao phủ tất cả partition nhưng expose các cột partition (`ingest_method`, `year`, `month`) để DuckDB có thể prune (lọc bớt file) khi query.

```yaml
sources:
  - name: sapo
    tables:
      - name: orders_raw
        external:
          # QUAN TRỌNG: Cần enable hive_partitioning=1 để DuckDB nhận diện ingest_method, year, month thành cột
          location: "read_parquet('sapo_raw/order/**/*.parquet', hive_partitioning=1)"
```

### B. Chiến Lược Incremental Model (Staging/Mart)

Chúng ta không thể chỉ đơn giản dùng `timestamp > max(timestamp)` bởi vì dữ liệu đến từ 3 nguồn với đặc tính khác nhau (Customers Batch thiếu updates).

**Mô hình xử lý:** `Deduplication` & `Last-Write-Wins`.

#### Bước 1: Filter đầu vào (Performance Optimization)

```sql
-- models/staging/stg_sapo__customers.sql
{{
  config(
    materialized='incremental',
    unique_key='entity_id',
    incremental_strategy='delete+insert'
  )
}}

WITH raw_data AS (
    SELECT
        *,
        -- Cột này tự động có sẵn nếu dùng hive_partitioning=1
        ingest_method,
        year,
        month
    FROM {{ source('sapo', 'customer_raw') }}

    {% if is_incremental() %}
    -- LOGIC INCREMENTAL THÔNG MINH:
    -- DuckDB sẽ tự động "Prune" (bỏ qua) các thư mục year/month cũ
    -- nếu event_timestamp tương quan chặt với partition time.
    WHERE event_timestamp > (SELECT MAX(event_timestamp) FROM {{ this }})
    {% endif %}
),
```

#### Bước 2: Hợp Nhất Đa Chiều (Deduplication Logic)

Đây là bước quan trọng nhất để xử lý việc `Batch` thiếu update. Ta gộp chung tất cả nguồn, và dùng `window function` để chọn bản ghi mới nhất.

> **Quan Trọng**: Logic này sẽ được thực hiện và **hoàn tất ngay tại tầng Staging**.
>
> - Output của Staging là một tập dữ liệu "Golden Record" (mỗi entity 1 dòng duy nhất và mới nhất).
> - Các tầng sau (Intermediate/Marts) chỉ việc `SELECT * FROM {{ ref('stg_sapo__customers') }}` mà không cần quan tâm đến việc data đến từ Batch hay Webhook, hay phải deduplicate lại.

```sql
deduped AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY
                event_timestamp DESC, -- Ưu tiên bản ghi mới nhất (quan trọng nhất)
                -- Tie-breaker: Nếu cùng timestamp, ưu tiên Webhook > History > Batch
                CASE
                    WHEN ingest_method = 'webhook' THEN 3
                    WHEN ingest_method = 'history_log' THEN 2
                    ELSE 1
                END DESC
        ) AS rn
    FROM raw_data
)
SELECT * EXCLUDE (rn)
FROM deduped
WHERE rn = 1
```

### C. Xử Lý Trường Hợp Đặc Biệt: Backfill & Late Arriving Data

Do partition theo `event_timestamp`, việc "Incremental by timestamp" hoạt động tốt miễn là không có **Late Arriving Data** nằm quá xa trong quá khứ (vào các partition cũ mà DuckDB có thể đã skip nếu ta filter path thủ công, nhưng filter `WHERE` trên cột thì DuckDB vẫn phải check stats).

**Giải pháp:**

- Tin tưởng vào cơ chế `min/max` stats của file Parquet.
- Khi chạy incremental, DuckDB sẽ đọc metadata của các file parquet. Nếu `max(event_timestamp)` của file < `watermark`, file đó sẽ được skip hoàn toàn. Điều này đảm bảo hiệu năng kể cả khi folder data lớn dần.

---

## 3. Tích Hợp Dagster (Orchestration)

Để đảm bảo việc tính toán incremental hoạt động trơn tru trong pipeline tự động hóa, Dagster cần được cấu hình như sau:

### Cơ Chế Trigger

Hiện tại đang có 3 jobs chính (`orchestration/definitions.py`):

1.  **Realtime Job** (Webhook + DBT): Chạy mỗi phút.
2.  **Incremental Job** (History Log + DBT): Chạy mỗi 10 phút.
3.  **Nightly Job** (Batch Sync + DBT): Chạy 04:00 AM.

### Vấn Đề Lock & Concurrency (Quan Trọng)

Do cả 3 jobs đều trigger `dbt build` (ghi vào cùng file DuckDB `.duckdb`), cần kiểm soát concurrency để tránh lỗi `DuckDB Lock Error` (vì DuckDB single-writer).

**Giải pháp hiện tại (Đã kiểm tra):**

- Các job đã được gắn tag `concurrency_group: dbt_rw`.
- Điều này đảm bảo tại một thời điểm chỉ có 1 tiến trình được phép ghi vào DB. (Cần đảm bảo file `dagster.yaml` của instance có cấu hình limit cho tag này, hoặc dùng `run_queue` configuration).

### Chiến Lược Retry

- Đối với **Realtime/Incremental Job**: Nên set `max_retries: 0` hoặc thấp (1). Vì nếu fail do lock, job sau sẽ chạy ngay lập tức (1-10 phút sau). Retry liên tục sẽ làm tắc nghẽn hàng đợi.
- Đối với **Nightly Job**: Có thể cho phép retry 1-2 lần vì đây là job quan trọng chạy 1 lần/ngày.

### Deployment Note

Kịch bản chạy lý tưởng:

1.  **DLT Step**: Capture dữ liệu mới vào Parquet (Append-only, rất nhanh, không lock).
2.  **DBT Step**:
    - Dagster check lock `dbt_rw`.
    - Thực thi `dbt build --select tag:otp`.
    - DBT đọc Parquet mới -> Update Staging -> Update Marts -> Release Lock.

---

## 4. Quản Lý Thực Thi Pipeline (Script Runner)

Hiện tại, việc chạy DLT được quản lý tốt bởi framework (pipeline wrapper). Đối với DBT, ta cần đảm bảo tính nhất quán tương tự.

### Đánh giá Script `run_dbt.py`

Hiện tại đang có script `transformation/scripts/run_dbt.py`.

- **Ưu điểm**:
  - Tự động tìm kiếm `dbt executable` trong môi trường ảo (venv) của DLT. Điều này rất tốt để đảm bảo không phụ thuộc vào global python.
  - Set đúng `cwd` (current working directory) để chạy dbt.
- **Điểm cần cải thiện**:
  - **Environment Variables**: Chưa thấy logic load `.env` (ví dụ: `DBT_DATA_LAKE_PATH`, `DBT_EXPORT_PATH`). Nếu chạy thủ công mà quên load env, dbt sẽ lỗi path.
  - **Logging**: Basic print. Cần log rõ ràng hơn nếu tích hợp vào hệ thống lớn.

### Đề xuất Cải Tiến

Cần nâng cấp `run_dbt.py` để trở thành một "Generic Runner" mạnh mẽ hơn hoặc dùng wrapper của DLT nếu có thể, cụ thể:

1.  **Auto-load .env**: Sử dụng `python-dotenv` để load file `.env` từ root project trước khi chạy dbt command. Điều này cực kỳ quan trọng cho DuckDB path.
2.  **Error Handling**: Capture stderr/stdout tốt hơn để debug khi pipeline fail trong Dagster (mặc dù Dagster asset đã handle, nhưng script độc lập cũng cần).

---

## 5. Đánh Giá Kỹ Thuật & Dự Trù Rủi Ro

Sau khi scan codebase hiện tại (`models/sources.yml`, `profiles.yml`), đây là các đánh giá kỹ thuật cho việc triển khai:

### A. Khả Thi & Thuận Lợi

1.  **DuckDB Adapter**: Đã được cấu hình (`profiles.yml`). DuckDB xử lý file Parquet cực tốt, đặc biệt là các thao tác Window Function và Filter Pushdown cần thiết cho chiến lược này.
2.  **Codebase DLT**: Đã có cấu trúc partition chuẩn (`ingest_method/year/month`). Đây là tiền đề bắt buộc để DBT hoạt động hiệu quả.

### B. Rủi Ro & Điều Chỉnh Cần Thiết

1.  **Cấu hình Source (`sources.yml`)**:
    - Hiện tại: `read_parquet('.../**/*.parquet')` (chưa rõ options).
    - **Vấn đề**: DuckDB có thể không tự động nhận diện các cột partition (`ingest_method`, `year`, `month`) từ đường dẫn file nếu không bật `hive_partitioning`.
    - **Khắc phục**: Cần sửa lại `sources.yml` để thêm option `hive_partitioning=1`.
    - Ví dụ: `read_parquet('.../**/*.parquet', hive_partitioning=1)`
2.  **Performance khi lượng file lớn**:
    - Pattern `**/*.parquet` có thể khiến DuckDB phải list toàn bộ file system mỗi lần chạy, gây chậm.
    - **Khắc phục**: Nếu sau này chậm, có thể chuyển sang dùng biến môi trường DBT để chỉ định cụ thể partition cần đọc (ví dụ: chỉ đọc `year=2024`). Nhưng hiện tại với volume < 1GB/ngày thì chưa đáng lo.
3.  **Schema Evolution**:
    - Vì đọc "Schema-on-read" từ Parquet, nếu các file Parquet cũ và mới có schema lệch nhau (thêm/bớt cột), DuckDB có thể cần option `union_by_name=True`.
    - **Dự trù**: Cần theo dõi log DBT, nếu lỗi schema thì thêm option này vào `read_parquet`.

### C. Kết Luận

Chiến lược hoàn toàn khả thi trên nền tảng code hiện tại. Chỉ cần một điều chỉnh nhỏ trong `sources.yml` để kích hoạt tính năng partition của DuckDB.
