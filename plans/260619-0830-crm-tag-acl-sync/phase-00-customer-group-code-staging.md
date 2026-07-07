# Phase 00 — Upstream: Parse customer_group JSON tại staging

**Context:** [plan.md](plan.md)

## Overview
- **Priority:** P0 — data contract cho toàn bộ ACL; block phase 01-03
- **Status:** ⬜ TODO
- `customer_group` trong `dim_customers`/`wh_customer_base` hiện là **nguyên JSON blob** của Sapo group object. Phase này parse JSON **một điểm duy nhất ở staging**, expose 3 cột sạch (`customer_group_id`, `customer_group_code`, `customer_group_name`), refactor `customer_type` CASE khỏi LIKE-hack, và propagate xuống cache.db.

## Key Insights (verified 2026-07-06, query trực tiếp cache.db)

- 8 giá trị DISTINCT nhưng chỉ **6 group thực** — cùng id 1812238 (RETAIL) xuất hiện 2 snapshot khác `code` (BANLE 6.451 rows vs TYPE_RETAIL 184 rows, khác `modified_on`), tương tự 1812239 (BANBUON vs TYPE_WHOLESALE). **Kết luận: `code` KHÔNG ổn định (Sapo rename), `id` ổn định → ACL key theo `id`.**
- `dim_customers.customer_type` CASE (dòng ~184-197) match `LIKE '%WHOLESALE%'` xuyên qua JSON — chạy được nhờ substring trùng `"name"` field, nhưng là hack và là điểm parse thứ 2 (DRY violation khi ACL ra đời).
- 1 row giá trị `'Unknown'` (string trần, không phải JSON) → parse phải chịu được non-JSON, trả NULL.

## Related Code Files

- **Sửa:** staging model nơi `customer_group` xuất hiện đầu tiên (trace từ `transformation/models/marts/core/dim_customers.sql` dòng 46 `c.customer_group` ngược lên CTE nguồn — xác định chính xác file staging lúc implement)
- **Sửa:** `transformation/models/marts/core/dim_customers.sql` — expose 3 cột mới + refactor `customer_type` CASE + `is_us_gift_recipient` flag
- **Sửa:** `crm/sync/cache_schema.sql` — `wh_customer_base` thêm 3 cột
- **Sửa:** `crm/sync/duckdb_reader.py` — `_DIM_CUSTOMERS_BASE_COLS` + `fetch_customer_base` SQL
- **Sửa:** `crm/sync/sqlite_upsert.py` — passthrough 3 cột mới (nếu upsert enumerate cột)
- **Sửa:** tests liên quan trong `crm/sync/tests/test_reverse_etl_warehouse_to_crm.py` (fixture schema có `customer_group`)

## Implementation Steps

1. **Staging:** thêm 3 cột derive từ JSON (DuckDB):
   ```sql
   json_extract_string(customer_group, '$.id')   AS customer_group_id,    -- khóa ổn định
   json_extract_string(customer_group, '$.code') AS customer_group_code,  -- display/debug
   json_extract_string(customer_group, '$.name') AS customer_group_name   -- display
   ```
   `json_extract_string` trả NULL với input không phải JSON (`'Unknown'`) — không cần TRY_CAST.
2. **dim_customers:** pass-through 3 cột; giữ `customer_group` raw ("for reference" như comment hiện có). Refactor `customer_type` CASE dùng `customer_group_name`/`customer_group_code` match tường minh thay vì LIKE xuyên JSON (giữ nguyên các nhánh + legacy codes BANBUON/CTN00014); refactor `is_us_gift_recipient` tương tự.
3. **Regression check bắt buộc** (đây là refactor, output phải giữ nguyên): so sánh phân phối `customer_type` trước/sau — kỳ vọng khớp số đã biết: 161 WHOLESALE / 662 CROSSBORDER / 11 PARTNER trên ~7.5k khách.
4. **Cache propagate:** `cache_schema.sql` + `duckdb_reader.fetch_customer_base` + upsert thêm 3 cột. `duckdb_reader._check_columns` sẽ tự bắt lệch cột.
5. Chạy dbt build dim_customers + reverse-ETL end-to-end, verify `wh_customer_base.customer_group_id` có giá trị cho các row có group.

## Todo
- [ ] Trace + sửa staging model (3 cột JSON extract)
- [ ] dim_customers: pass-through + refactor customer_type CASE + is_us_gift_recipient
- [ ] Regression check phân phối customer_type (161/662/11)
- [ ] cache_schema.sql + duckdb_reader.py + sqlite_upsert.py + tests
- [ ] dbt full-refresh dim_customers, reverse-ETL end-to-end verify

## Success Criteria
- `dim_customers.customer_group_id` non-NULL cho mọi row có `customer_group` JSON hợp lệ; NULL cho `'Unknown'`
- Phân phối `customer_type` không đổi so với trước refactor
- `wh_customer_base` có 3 cột mới, populated sau reverse-ETL

## Risks & Deploy notes
- **dim_customers là incremental** — thêm cột chỉ backfill rows thay đổi → phải chạy `dbt --full-refresh` trực tiếp trong container (Dagster asset không có full_refresh flag; dùng lock-retry).
- Nếu tạo dbt node MỚI (thay vì sửa model có sẵn) → restart `data_platform` (manifest pre-parsed lúc startup, không hot-reload).
- Cột mới trên mart → nếu serving view enumerate cột: dừng Metabase, chạy `bootstrap_serving_views.py`.
- `crm/sync` code baked trong image crm → sau khi sửa duckdb_reader/cache_schema: `docker compose up -d --build crm`.
- `wh_customer_base` schema evolve: kiểm tra cách cache.db xử lý cột mới (CREATE IF NOT EXISTS không tự ALTER) — có thể cần ALTER TABLE hoặc drop/recreate bảng cache (dữ liệu cache tái tạo được từ warehouse, an toàn).
