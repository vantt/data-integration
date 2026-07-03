# Phase 2: Intermediate Model Partitioning — Cần Redesign
**Effort:** 3-5 ngày | **Risk:** Trung bình-cao | **Blocker:** Cần macro mới + view update

## Vấn Đề Phát Hiện Sau Audit

### Design Conflict: Rolling vs Partitioned

Tất cả macro hiện tại đều trả về **file path** (ending `.parquet`), không phải directory:

```
get_rolling_location() → {DBT_EXPORT_PATH}/rolling/{name}/{name}_{ts}.parquet
get_versioned_location() → {external_root}/{name}_{batch_id}.parquet
get_parquet_location() → {DBT_EXPORT_PATH}/{name}.parquet
```

DuckDB `COPY ... TO ... (PARTITION_BY ...)` yêu cầu target là **directory**. Thêm `partition_by` vào `options` khi `location` là file path → fail hoặc undefined behavior.

Rolling strategy (N versioned files, GC by refresh_rolling.py) và hive partitioning strategy (1 fixed directory, partitions replace per run) là **hai mô hình đối lập**. Intermediate models hiện đang dùng rolling — chuyển sang partitioned cần thay đổi cả location macro lẫn serving view registration.

---

## Prerequisite: Quyết Định Architecture

Trước khi implement, cần quyết định chiến lược cho intermediate models:

### Option A: Partitioned Directory (recommended cho int_* models)
- Tạo macro mới `get_static_location()` trả về directory path (không có `.parquet`)
- Output: `{DBT_EXPORT_PATH}/intermediate/{name}/` → dbt ghi hive partitions vào đây
- Mỗi run **replace** partition tương ứng (DuckDB COPY TO với PARTITION_BY là replace-mode per partition)
- Không cần rolling GC vì không tích lũy file — partition directory bị overwrite mỗi run
- DuckDB view: `read_parquet('intermediate/int_shopee_order_fees/**/*.parquet', hive_partitioning=true)`

**Tradeoff:** Mất rollback capability (không giữ version cũ). Nhưng intermediate models luôn rebuildable từ raw → không cần rollback.

### Option B: Giữ Rolling, Skip Partitioning
- Không thay đổi gì
- DuckDB glob đọc N file nhỏ thay vì 1 file lớn per partition
- Chấp nhận cost của full-scan vì intermediate models đã đủ nhỏ
- **Khuyến nghị nếu volume không phải vấn đề thực tế**

---

## Implementation (Nếu Chọn Option A)

### Bước 1: Macro mới

Tạo `transformation/macros/get_static_location.sql`:
```sql
{# Returns a fixed directory path for partitioned external materialization.
   Unlike get_rolling_location(), this is NOT timestamped — each dbt run
   overwrites the same directory (partition-level replace semantics). #}
{% macro get_static_location(subdir='intermediate') %}
{{ env_var('DBT_EXPORT_PATH') }}/{{ subdir }}/{{ this.name }}
{% endmacro %}
```

### Bước 2: Xác định date column cho từng model

Trước khi thêm `partition_by`, cần đọc từng model để xác định date column phù hợp:

| Model | Date column cần verify | Partition granularity |
|-------|----------------------|-----------------------|
| int_shopee_order_fees | order_create_time hoặc tương đương | month |
| int_misa_sales_lines | voucher_date | month |

```bash
# Verify column names tồn tại trong output
docker compose exec data_platform dbt show -s int_shopee_order_fees --limit 1
docker compose exec data_platform dbt show -s int_misa_sales_lines --limit 1
```

### Bước 3: Cập nhật model config

```sql
-- int_shopee_order_fees.sql
{{ config(
    tags=['int', 'shopee'],
    options={
        'format': 'parquet',
        'partition_by': "date_trunc('month', order_create_time)"
    },
    location="{{ get_static_location() }}"
) }}
```

### Bước 4: Full-refresh bắt buộc

```bash
docker compose exec data_platform dbt run -s int_shopee_order_fees int_misa_sales_lines --full-refresh
```

Chạy ngoài giờ peak. Kiểm tra row count trước/sau bằng nhau.

### Bước 5: Update bootstrap_serving_views.py

DuckDB view registration cần thêm `hive_partitioning=true` khi đọc partitioned intermediate models. Tìm và update view definitions trong `scripts/provisioning/bootstrap_serving_views.py`.

### Bước 6: Tắt rolling GC cho models đã chuyển

Sau khi chuyển sang static location, `refresh_rolling.py` sẽ không còn thấy các models này trong rolling directory (vì chúng không ghi vào đó nữa). Schema drift detection có thể fire. Cần verify behavior.

---

## Validation

```bash
# 1. Verify partition directories được tạo
ls {DBT_EXPORT_PATH}/intermediate/int_shopee_order_fees/

# 2. Verify DuckDB partition pruning
docker compose exec data_platform duckdb {olap.duckdb} -c "
EXPLAIN SELECT * FROM read_parquet(
    '{DBT_EXPORT_PATH}/intermediate/int_shopee_order_fees/**/*.parquet',
    hive_partitioning=true
) WHERE month = '2026-06-01';"
# Kết quả phải có Partition Pruning

# 3. Row count không đổi so với trước khi migrate
```

---

## Unresolved Questions

1. Downstream dbt models dùng `{{ ref('int_shopee_order_fees') }}` — khi chuyển sang static location, dbt manifest có resolve đúng path không? Cần test.
2. Metabase có query trực tiếp vào rolling path của các models này không? Nếu có, cần update blueprint.
3. refresh_rolling.py schema drift detection sẽ report gì khi model biến khỏi rolling directory?
