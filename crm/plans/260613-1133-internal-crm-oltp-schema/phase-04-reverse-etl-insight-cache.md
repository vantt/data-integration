# Phase 04 — Reverse-ETL: Warehouse Read-Cache (Insight + Relational)

**Context:** [plan.md](plan.md) · Reports: orders-sales-products, raw-serving-semantic-integration

## Overview
- **Priority:** P0 (giá trị "deep insight" + dữ liệu order/customer/product cho CRM nằm ở đây)
- **Status:** ✅ DONE — Python reverse-ETL (`crm/sync/`: duckdb_reader read-only + pinned cols fail-fast, sqlite_upsert idempotent, orchestrator + `wh_sync_run` + 30d trim, order HWM `>=`), `cache.db` schema (insight + order/customer/product + party_seed), Go seed-consumer (`cmd/syncparties`, 1-writer crm.db) + cache insight read (graceful-empty), 45 test (Go 39 + pytest 6) PASS, code-review fixed. Build+test bằng fixture DuckDB (không có olap.duckdb thật ở máy này — chạy data thật khi deploy).
- `cache.db` = **mọi dữ liệu gốc-warehouse mà CRM cần ĐỌC** (read-only), gồm 2 nhóm:
  - **Nhóm 2 — Insight đã tính:** `wh_*_insight`, `wh_action_queue`.
  - **Nhóm 3 — Quan hệ gốc:** `wh_customer_base`, `wh_product`, `wh_order` (header). Đây KHÔNG phải insight — là master/transactional data Sapo→warehouse.
- CRM **không tính lại, không ghi** nhóm này (nguồn sự thật = Sapo/warehouse). Refresh theo lịch.

## Key Insights
- Warehouse đã có **insight**: `mart_customer_action_queue` (6 action type + `value_at_stake_vnd` + rationale tiếng Việt), `dim_customers`/`int_customer_metrics` (value_group, status, next_purchase_signal, affinity, discount_sensitivity), `mart_product_health` (abc/health/oos_risk/realized_margin_pct).
- Và **quan hệ gốc**: `fact_orders` (order header), `dim_customers` (base attrs), `dim_products` (catalog). Replicate **slim** xuống `cache.db` để CRM "xem đơn của khách / chọn SP gợi ý" + segment theo lịch sử mua.
- **Order line items (`fact_order_items`)**: v1 **KHÔNG replicate** (lớn) — insight đã có last/top SKU; full giỏ hàng để on-demand (đọc `olap.duckdb` kiểu `detailView`) khi cần màn chi tiết sau.
- Read surface: `olap.duckdb` mở `read_only=True`, schema `main_marts` — đúng pattern `detailView`. Fallback: `sapo_export_latest.duckdb`.
- Convention BẮT BUỘC: `date_key` ICT; `net_revenue` (VAT-inclusive); `realized_margin_pct` (KHÔNG `gross_margin_pct` — bug H010); gate margin `has_cogs=true`; `customer_type` B2B & `fact_payments` không tin cậy.
- Link CRM: `cache.wh_*.customer_id` ↔ `crm_party_identity (identity_type='sapo_customer')` — value-link qua file, KHÔNG FK.

## Requirements
- **FR:** job Python đọc DuckDB → upsert `wh_cache`; idempotent theo surrogate key; tạo/khớp `party` cho khách mới (gọi Phase 02 upsert); ghi `sync_run` (rows, status, refreshed_at).
- **NFR:** read-only với DuckDB (memory: tránh write lock file live); upsert COPY-batch; chạy được standalone hoặc như Dagster asset.

## Architecture
> DDL Postgres-style — thực thi **SQLite** ở file riêng **`cache.db`** (Python là writer DUY NHẤT; Go ATTACH read-only). `numeric`→`INTEGER` (VND) / `REAL` (pct); `timestamptz`→`TEXT` UTC; bảng prefix `wh_*`.

### Core DDL (cache.db)
```sql
CREATE TABLE wh_cache.customer_insight (
  customer_key text PRIMARY KEY,        -- MD5 surrogate từ warehouse
  customer_id  bigint,                  -- natural (gọi Sapo / khớp party)
  value_group text, customer_status text,
  next_purchase_signal text, predicted_next_purchase_date date,
  avg_days_between_orders numeric, avg_order_spend numeric,
  discount_sensitivity text, cancel_rate numeric,
  last_purchased_sku text, top_affinity_product text, second_affinity_product text,
  channel_preference text, lifetime_contribution_margin numeric, is_margin_negative boolean,
  refreshed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE wh_cache.product_insight (
  product_key text PRIMARY KEY, sku text,
  abc_class text, health_class text, lifecycle_stage text, velocity_momentum text,
  oos_risk text, realized_margin_pct numeric, discount_dependency text,
  refreshed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE wh_cache.action_queue (
  action_id text PRIMARY KEY,           -- ổn định theo customer_key+action_type+date
  customer_key text, action_type text,  -- CALL_NOW|REORDER_NUDGE|WIN_BACK|...
  rationale_vi text, value_at_stake_vnd numeric, priority int,
  generated_date date, refreshed_at timestamptz NOT NULL DEFAULT now()
);
-- ───── NHÓM 3: quan hệ gốc (read-only replica, KHÔNG insight) ─────
CREATE TABLE wh_cache.customer_base (    -- từ dim_customers (base attrs)
  customer_key text PRIMARY KEY, customer_id bigint,
  customer_code text, display_name text, phone text, email text,
  customer_group text, first_order_date date, refreshed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE wh_cache.product (          -- từ dim_products (catalog nhỏ)
  product_key text PRIMARY KEY, sku text, variant_id bigint,
  product_name text, brand text, unit_price numeric, is_active boolean,
  refreshed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE wh_cache.order_hdr (        -- từ fact_orders, 1 dòng/đơn (slim, KHÔNG dòng đơn)
  order_id text PRIMARY KEY, order_code text, customer_id bigint,
  date_key int,                          -- ICT YYYYMMDD
  net_revenue numeric, status text, channel text, item_count int,
  refreshed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE wh_cache.sync_run (
  run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_table text NOT NULL, row_count int, status text, -- ok|failed
  started_at timestamptz, finished_at timestamptz, error text
);
CREATE INDEX ON wh_cache.customer_insight (customer_id);
CREATE INDEX ON wh_cache.action_queue (customer_key, priority);
CREATE INDEX ON wh_cache.customer_base (customer_id);
CREATE INDEX ON wh_cache.product (sku);
CREATE INDEX ON wh_cache.order_hdr (customer_id, date_key);   -- "đơn của khách X theo thời gian"
```
### Sync job (Python — stdlib sqlite3, KHÔNG cần psycopg)
```
crm/sync/reverse_etl_warehouse_to_crm.py
  1. open olap.duckdb (read_only=True)  [fallback sapo_export_latest]
  2. SELECT từ main_marts:
     - insight: mart_customer_action_queue, dim_customers(+metrics), mart_product_health
     - quan hệ: dim_customers→customer_base, dim_products→product, fact_orders→order_hdr
  3. open cache.db (sqlite3, WAL, busy_timeout) → UPSERT (INSERT ... ON CONFLICT DO UPDATE)
  4. party-link: KHÔNG ghi crm.db trực tiếp (tránh 2 writer). Ghi customer_id mới vào
     cache.wh_party_seed → Go app đọc & tạo crm_party/identity (Phase 02 upsert) khi sync xong
  5. ghi wh_sync_run
```
- **Nguyên tắc 1-writer:** Python CHỈ ghi `cache.db`; việc tạo `crm_party` do Go app làm (đọc seed). Không để Python đụng `crm.db`.
- Lịch: action_queue daily (sau dbt nightly), insight theo nhịp mart. Có thể thành Dagster asset downstream `serving_asset`.

## Related Code Files
- **Tạo:** `crm/sync/cache_schema.sql` (DDL cache.db — Python áp `CREATE TABLE IF NOT EXISTS`, KHÔNG dùng golang-migrate vì đó là của crm.db), `crm/sync/reverse_etl_warehouse_to_crm.py`, `crm/sync/duckdb_reader.py`, `crm/sync/sqlite_upsert.py`, `crm/sync/requirements.txt` (chỉ `duckdb`; sqlite3 là stdlib).
- **Go phía crm.db:** job nhỏ đọc `cache.wh_party_seed` → tạo `crm_party`/`crm_party_identity` (Phase 02).
- **Đọc:** `detailView/adapters/outbound/duckdb/` (mẫu mở olap.duckdb read_only), `scripts/provisioning/bootstrap_serving_views.py`.

## Implementation Steps
1. `cache_schema.sql`: nhóm 2 (`*_insight`, `action_queue`) + nhóm 3 (`customer_base`, `product`, `order_hdr`) + `party_seed`, `sync_run` (IF NOT EXISTS). **KHÔNG bật FK** trong cache.db (bulk-load thứ tự không đảm bảo; toàn vẹn do warehouse lo) — quan hệ qua cột index.
2. `duckdb_reader.py`: read_only connect + select các mart (chỉ cột cần).
3. `sqlite_upsert.py`: `INSERT ... ON CONFLICT DO UPDATE` (idempotent), batch executemany.
4. Pipeline chính: orchestrate insight + quan hệ → cache.db + `wh_party_seed` + `wh_sync_run`. **`order_hdr` incremental** theo `date_key`/`modified_on` (đừng full-reload mỗi lần — đơn nhiều nhất).
5. Go: consume `wh_party_seed` → upsert party/identity (giữ 1-writer cho crm.db).
6. Verify số liệu khớp warehouse (đếm rows, spot-check 1 khách + đơn). (Tuỳ chọn) Dagster asset + lịch.

## Todo
- [ ] `cache_schema.sql` (nhóm 2 + nhóm 3, no-FK)
- [ ] DuckDB read_only reader
- [ ] Upsert idempotent (insight + customer_base/product/order_hdr)
- [ ] `order_hdr` incremental theo date_key
- [ ] Party-seed → Go tạo party
- [ ] sync_run logging + verify khớp warehouse

## Success Criteria
- Chạy job 2 lần → không nhân đôi (idempotent); `customer_insight` khớp `dim_customers`; `order_hdr` khớp `fact_orders` (đếm + tổng `net_revenue`); query "đơn của 1 khách" qua `ATTACH` ra đúng; action_queue hôm nay xuất hiện; mỗi customer_id có party; `refreshed_at` cập nhật.

## Risk Assessment
- **Write lock DuckDB** (memory) → luôn `read_only=True`; nếu file bận → fallback `sapo_export_latest.duckdb`.
- **2 writer cùng file** → tránh hẳn: Python chỉ `cache.db`, Go chỉ `crm.db`. Go ATTACH cache.db read-only — không khoá ghi Python.
- **`order_hdr` phình to** → replicate **slim** (1 dòng/đơn, không dòng đơn) + incremental; dòng đơn để on-demand.
- **Lệch tên cột sau dbt rename** (memory) → pin danh sách cột, fail-fast nếu thiếu.
- **Freshness** → app hiển thị `refreshed_at`; order_hdr theo nhịp sync (không realtime — đơn mới nhất có độ trễ).

## Security
- `cache.db` read-mostly; chỉ Python sync ghi. Go app ATTACH read-only — không sửa.

## Next Steps
→ party_360 (Phase 03) join được insight. → Phase 06 segment/campaign dùng signal từ wh_cache.
