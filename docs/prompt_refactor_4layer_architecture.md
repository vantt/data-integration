# Prompt: Refactor dbt staging → 4-layer architecture (src_ → stg_ → std_ → marts)

> **Trạng thái: ⏳ ĐANG THỰC HIỆN (cập nhật 2026-03-30)**
>
> - Bước 1-3: ✅ DONE (orders pipeline refactored, biz dedup gom vào src_)
> - Bước 4-7: ⏳ TODO (customers, accounts chưa refactor)
> - Bước 8: ⏳ TODO (std_ inconsistencies: fact_payments, dim_staff)
> - Bước 9: ✅ DONE (memory_limit: 5GB)
> - Bước 10: ✅ DONE (109/109 PASS)

## Bối cảnh

Đọc tài liệu kiến trúc tại:
- `docs/troubleshooting_duckdb_oom_stg_sapo_orders.md` — section 3 (kế hoạch dài hạn)
- `transformation/AGENTS.md` — quy tắc dbt hiện tại

## Vấn đề cần giải quyết

1. **OOM:** `stg_sapo_orders` crash vì 1 model làm quá nhiều (extract JSON + dedup + enrich) trong 1 query. 1 dbt model = 1 SQL query = 1 memory budget. Cần tách thành nhiều model để memory peak = max() thay vì sum().

2. **Kiến trúc lộn xộn:** `src_` và `stg_` đọc cùng source độc lập, `src_` là VIEW giữ payload (re-scan mỗi lần query), một số marts bỏ qua `std_` layer.

## Kiến trúc mục tiêu: 4 layers

```
source() → src_ (INCREMENTAL: extract + tech dedup + tích lũy)
    → stg_ (VIEW: biz dedup + enrich)
        → std_ (VIEW: normalize + status mapping, standard interface cho marts)
            → marts (dim_/fact_)
```

**Vai trò mỗi layer:**
- `src_` = Materialized extraction point. Đọc parquet, extract ALL JSON fields (scalar + nested arrays), tech dedup by entity_id, ghi incremental table. Payload KHÔNG có trong output. Source chỉ scan data mới.
- `stg_` = Business preparation. Đọc từ src_ (nhẹ). Business dedup, enrichment joins (ref tables). Unnest models (order_items, payments, fulfillments) cũng ở layer này.
- `std_` = Standard interface. Normalize, status mapping, canonical schema. Tất cả marts PHẢI đọc từ std_.
- `marts` = Dimensional models. Giữ nguyên.

## Các bước thực hiện

### Bước 1: Refactor src_sapo_orders (INCREMENTAL extraction)

Đổi `src_sapo_orders` từ VIEW (SELECT * + dedup, giữ payload) thành INCREMENTAL TABLE:
- Đọc `source('sapo_raw', 'order')`
- Tech dedup by entity_id (ROW_NUMBER with ingest_method priority: webhook > history_log > batch)
- Extract ALL scalar JSON fields (50+ fields từ `stg_sapo_orders` hiện tại)
- Extract nested JSON arrays as text columns: `order_line_items_json`, `payments_json`, `fulfillments_json`
- Incremental: `WHERE event_timestamp > (SELECT MAX(event_timestamp) - INTERVAL 7 DAY FROM {{ this }})`
- KHÔNG có GROUP BY — dùng streaming scan + ROW_NUMBER (xem fix #3 trong troubleshooting doc)
- Output: flat columns, KHÔNG CÒN payload

### Bước 2: Đơn giản hóa stg_sapo_orders (VIEW)

Đổi `stg_sapo_orders` từ INCREMENTAL (extract + dedup + enrich) thành VIEW:
- Đọc từ `ref('src_sapo_orders')` (không phải source!)
- Business dedup by order_id: `QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY event_timestamp DESC, modified_on DESC) = 1`
- Enrichment joins: ref_order_sources (mapping tags), ref_payment_methods, ref_branch_locations
- KHÔNG extract JSON — data đã flat từ src_

### Bước 3: Đổi source cho unnest models

Các model unnest hiện đọc từ `src_sapo_orders` (có payload) và extract từ `payload`:
- `stg_sapo_order_items`: đổi sang đọc từ `ref('src_sapo_orders')`, unnest từ cột `order_line_items_json` thay vì `json_extract_string(payload, '$.order_line_items')`
- `stg_sapo_payments`: tương tự, unnest từ `payments_json`
- `stg_sapo_fulfillments`: tương tự, unnest từ `fulfillments_json`

Lưu ý: các model này có bug duplicate unnest (2 lần `unnest(from_json(...))` trên cùng 1 dòng SELECT). Cần fix khi refactor.

### Bước 4: Refactor src_sapo_customers (INCREMENTAL extraction)

Đổi từ VIEW thành INCREMENTAL TABLE:
- Extract ALL JSON fields (hiện tại logic extract nằm trong `stg_sapo_customers`)
- Tech dedup by entity_id
- Bỏ `payload` khỏi output (hiện tại `stg_sapo_customers` vẫn output payload)
- Incremental strategy

### Bước 5: Đơn giản hóa stg_sapo_customers (VIEW)

- Đọc từ `ref('src_sapo_customers')`
- Cleaning, formatting (phone, email, dates)
- Không extract JSON

### Bước 6: Refactor src_sapo_accounts (INCREMENTAL extraction)

Tương tự src_sapo_customers.

### Bước 7: Đơn giản hóa stg_sapo_accounts (VIEW)

- Đọc từ `ref('src_sapo_accounts')`
- Cleaning (staff name coalescing, etc.)

### Bước 8: Fix inconsistencies ở std_ layer

1. Tạo `std_accounts` (MỚI) — normalize account/staff data
2. Đổi `dim_staff` đọc từ `std_accounts` thay vì `stg_sapo_accounts`
3. Đổi `fact_payments` đọc từ `std_payments` thay vì `stg_sapo_payments`

### Bước 9: Cập nhật profiles.yml

- Giữ `memory_limit: '4GB'` (đã thay đổi trong fix #3)
- Có thể tăng lại lên `5GB` hoặc `6GB` sau khi src_ materialized extraction giải quyết OOM

### Bước 10: Verify & Test

- Chạy `dbt build` — tất cả models pass
- So sánh output `std_orders` trước vs sau refactor (row count, spot check values)
- Verify OOM không còn xảy ra
- Chạy dbt tests (unique, not_null, accepted_values, relationships)

## Lưu ý quan trọng

- **KHÔNG đổi tên `std_` models** — giữ nguyên `std_orders`, `std_order_items`, etc. Marts đang ref chúng.
- **Thứ tự thực hiện quan trọng:** src_ trước (vì stg_ sẽ depend vào src_), rồi stg_, rồi fix std_ inconsistencies.
- **Mỗi bước nên commit riêng** để dễ rollback nếu cần.
- **Tham khảo code hiện tại** trước khi sửa — đọc file gốc để hiểu logic, đừng viết từ đầu.
- **`src_sapo_customers` và `src_sapo_accounts` sẽ được dùng** để extract thông tin customer/staff mà orders không có. Không phải dead code.
