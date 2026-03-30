# Prompt: Fix OOM stg_sapo_orders — Tách src_ extraction layer

## Tình huống

`stg_sapo_orders` liên tục OOM dù đã tối ưu 3 lần trong single model (xem `docs/troubleshooting_duckdb_oom_stg_sapo_orders.md`). Quick fix trong 1 model đã cạn kiệt — vấn đề là 1 dbt model = 1 SQL query = 1 memory budget, không thể giải phóng RAM giữa chừng.

Lỗi mới nhất (fix #3 đã deploy, memory_limit đã giảm xuống 4GB):
```
Out of Memory Error: failed to allocate data of size 16.0 MiB (3.7 GiB/3.7 GiB used)
```

## Giải pháp: Tách thành 2 model (src_ + stg_)

Tách công việc nặng (extract JSON từ parquet) ra model riêng (`src_sapo_orders`). Mỗi model chạy là 1 query riêng, memory giải phóng hoàn toàn giữa 2 model.

**Đọc kỹ trước khi bắt đầu:**
- `docs/troubleshooting_duckdb_oom_stg_sapo_orders.md` — section 3 (kiến trúc 4-layer)
- `transformation/models/staging/src_sapo_orders.sql` — code hiện tại (VIEW, SELECT *, giữ payload)
- `transformation/models/staging/stg_sapo_orders.sql` — code hiện tại (INCREMENTAL, extract + dedup + enrich)
- `transformation/profiles.yml` — memory_limit hiện tại: 4GB

## Bước thực hiện

### Bước 1: Refactor src_sapo_orders → INCREMENTAL extraction

Đổi `src_sapo_orders.sql` từ:
```sql
-- HIỆN TẠI: VIEW, SELECT *, giữ payload, dedup cơ bản
SELECT * EXCLUDE (rn) FROM (SELECT *, ROW_NUMBER() OVER (...) as rn FROM source) WHERE rn = 1
```

Thành INCREMENTAL TABLE:
- `materialized='incremental'`, `unique_key='entity_id'`, `incremental_strategy='delete+insert'`
- Đọc `source('sapo_raw', 'order')`
- Incremental filter: `WHERE event_timestamp > (SELECT MAX(event_timestamp) - INTERVAL 7 DAY FROM {{ this }})`
- Tech dedup by entity_id (ROW_NUMBER với ingest_method priority: webhook=3 > history_log=2 > batch=1)
- Extract TẤT CẢ scalar JSON fields (copy danh sách từ `stg_sapo_orders.sql` hiện tại — 50+ fields)
- Extract 3 nested JSON arrays as text columns:
  - `json_extract_string(payload, '$.order_line_items') as order_line_items_json`
  - `json_extract_string(payload, '$.payments') as payments_json`
  - `json_extract_string(payload, '$.fulfillments') as fulfillments_json`
- **KHÔNG dùng GROUP BY** — dùng ROW_NUMBER() + WHERE rn = 1 (đã dedup rồi nên không có duplicate issue)
- **KHÔNG giữ payload** trong output

Lưu ý OOM-safe pattern cho model này:
- Nó ĐỌC payload nhưng chỉ extract rồi discard. Không aggregate, không sort payload.
- ROW_NUMBER sort trên lightweight keys (entity_id, event_timestamp) — payload KHÔNG tham gia sort.
- Incremental chỉ xử lý data mới (7 ngày) → dataset nhỏ hơn nhiều so với full scan.
- Nếu lần đầu chạy (full refresh), có thể cần tạm tăng memory_limit trong profiles.yml.

### Bước 2: Đơn giản hóa stg_sapo_orders → VIEW

Đổi `stg_sapo_orders.sql`:
- `materialized='view'` (không cần incremental nữa — src_ đã tích lũy)
- Đọc từ `ref('src_sapo_orders')` thay vì `source('sapo_raw', 'order')`
- Biz dedup: `QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY event_timestamp DESC, modified_on DESC) = 1`
- Giữ enrichment joins (ref_order_sources mapping tags, ref_payment_methods, ref_branch_locations)
- **Xóa toàn bộ JSON extraction** — data đã flat từ src_
- **Xóa toàn bộ meta_keys, deduped_keys, winner_keys CTEs** — tech dedup đã xong ở src_

### Bước 3: Cập nhật unnest models

3 model đọc từ `src_sapo_orders` và unnest từ payload. Đổi sang unnest từ extracted JSON columns:

**`stg_sapo_order_items.sql`:**
- Vẫn đọc `ref('src_sapo_orders')`
- Thay `json_extract_string(payload, '$.order_line_items')` bằng cột `order_line_items_json`
- Thay `json_extract_string(payload, '$.id')` bằng cột `order_id` (đã extract sẵn trong src_)
- Fix bug: hiện tại có 2 lần `unnest(from_json(...))` trên cùng SELECT — chỉ giữ 1

**`stg_sapo_payments.sql`:**
- Tương tự, thay payload → `payments_json`
- Fix bug duplicate unnest

**`stg_sapo_fulfillments.sql`:**
- Tương tự, thay payload → `fulfillments_json`
- Fix bug duplicate unnest

### Bước 4: Tăng memory_limit lại (tùy chọn)

Sau khi tách model, src_sapo_orders xử lý ít hơn (chỉ extract, không biz dedup + enrich). Có thể tăng `memory_limit` trong `profiles.yml` từ `4GB` lên `5GB` hoặc `6GB` để cho DuckDB buffer thoải mái hơn. Test từ thấp lên.

### Bước 5: Test

1. `dbt run --select src_sapo_orders` — phải pass không OOM
2. `dbt run --select stg_sapo_orders` — phải pass (đọc từ src_, rất nhẹ)
3. `dbt build --select fqn:*` — full pipeline pass
4. So sánh row count `std_orders` trước vs sau
5. Spot check vài order_id xem data đúng không

## Files cần sửa

1. `transformation/models/staging/src_sapo_orders.sql` — refactor lớn
2. `transformation/models/staging/stg_sapo_orders.sql` — đơn giản hóa lớn
3. `transformation/models/staging/stg_sapo_order_items.sql` — đổi source + fix bug
4. `transformation/models/staging/stg_sapo_payments.sql` — đổi source + fix bug
5. `transformation/models/staging/stg_sapo_fulfillments.sql` — đổi source + fix bug
6. `transformation/profiles.yml` — tùy chọn điều chỉnh memory_limit

## Không sửa

- `std_orders.sql`, `std_order_items.sql`, etc. — giữ nguyên, chúng đọc từ stg_ và stg_ vẫn output cùng schema
- Marts models — không đổi
- `src_sapo_customers.sql`, `src_sapo_accounts.sql` — để cho phase sau
