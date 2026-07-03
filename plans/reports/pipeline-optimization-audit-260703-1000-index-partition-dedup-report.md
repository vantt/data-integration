# Pipeline Optimization Audit: Index, Partition & Dedup
**Date:** 2026-07-03 | **Branch:** feature/task-detail-cockpit-backend | **Scope:** Research-only

---

## TL;DR

| Priority | Issue | Effort |
|----------|-------|--------|
| 🔴 CRITICAL | `dim_customers_base` thiếu `unique_key` → duplicate customer_key trên incremental | 30 phút |
| 🔴 CRITICAL | Webhook consumer thiếu idempotent ACK → trùng lặp order update khi retry | 2-3 giờ |
| 🟡 HIGH | 3 SQLite index thiếu trên CRM (party_status, activity_staff, task_party) | 1 giờ |
| 🟡 HIGH | Customer metric lookback quá hẹp: 1 ngày → 3 ngày (clock-skew leakage) | 30 phút |
| 🟡 HIGH | Intermediate models thiếu hive partitioning → DuckDB full-scan | 1 ngày |
| 🟠 MEDIUM | Rolling parquet không có retention policy → disk bloat + query chậm | 1 ngày |
| 🟠 MEDIUM | Order dedup ordering sai: webhook có thể thua history_log trong cùng batch | 1 ngày |
| 🟢 LOW | SCD Type 2 cho order status history (nice-to-have) | 1 tuần |

---

## 1. Parquet Partitioning

### Hiện tại

**Raw layer (dlt output):**
- Sapo sources: `sapo_raw/{entity}/ingest_method={batch_sync|webhook|history_log}/year={Y}/month={M}/`
- MISA, Shopee file-drop: cấu trúc tương tự
- ✅ Year/month hive partitioning đã có

**Mart/Export layer:**
- Pattern: `rolling/{model_name}/{model_name}_{YYYYMMDDHHMMSS}.parquet`
- ❌ Không có time-based partitioning → DuckDB không thể prune partition
- ❌ Mỗi dbt run tạo file mới với timestamp → tích lũy vô hạn

**Intermediate layer:**
- ❌ `int_*` models write single external file, không có partition → full rescan mỗi incremental run

### Gaps

| Gap | Severity | Mô tả |
|-----|----------|--------|
| Intermediate models thiếu date partition | HIGH | `int_shopee_order_fees`, `int_misa_sales_lines` scan toàn bộ khi incremental |
| Mart rolling files tích lũy vô hạn | MEDIUM | Không có retention → disk bloat + DuckDB scan nhiều file cũ |
| Late-arriving data vs partition | LOW | Một số record có `event_timestamp` cũ hơn write partition (history_log reingestion) |

### Recommendations

**Intermediate models — thêm hive partitioning:**
```sql
{{ config(
    materialized='external',
    options={'format': 'parquet', 'partition_by': ["date_trunc('day', event_timestamp)"]}
) }}
```
Áp dụng cho: `int_shopee_order_fees`, `int_misa_sales_lines`, `int_order_promo_goods_cost`

**Rolling retention — giữ 7 phiên bản gần nhất:**
```python
# scripts/provisioning/refresh_rolling.py
RETENTION_DAYS = 7
for pattern in glob.glob(f'{rolling_dir}/*/*.parquet'):
    if os.path.getmtime(pattern) < (datetime.now() - timedelta(days=RETENTION_DAYS)).timestamp():
        os.remove(pattern)
```

---

## 2. dbt Incremental Models

### Inventory

| Model | Strategy | Unique Key | Trạng thái |
|-------|----------|------------|------------|
| src_sapo_v2_orders | delete+insert | order_id | ✅ Tốt |
| src_sapo_v2_inventory_transactions | delete+insert | entity_id (content hash) | ✅ Tốt |
| src_sapo_v2_customers | delete+insert | sapo_customer_id | ⚠️ Thiếu late-arrival buffer |
| **dim_customers_base** | incremental | **THIẾU unique_key** | 🔴 CRITICAL |
| int_customer_metrics | incremental | customer_key | ⚠️ Lookback 1 ngày quá hẹp |
| int_customer_discount_metrics | incremental | customer_key | ⚠️ Watermark trên metric time, không phải data time |

### Critical Fix: dim_customers_base

```sql
{{ config(
    materialized='incremental',
    unique_key=['customer_key'],   -- THÊM NGAY
    on_schema_change='append_new_columns',
    incremental_strategy='delete+insert'
) }}
```

### Customer Metric Lookback

```sql
-- Thay 1 day → 3 days trên tất cả int_customer_* models
WHERE updated_at >= (SELECT MAX(metric_calculated_at) - INTERVAL '3 days' FROM {{ this }})
```

### Order Dedup Event Ordering (Bug Tiềm Ẩn)

Hiện tại webhook có thể thua history_log trong cùng batch nếu webhook arrive sau:
```sql
-- Fix: thêm _dlt_load_id làm tiebreaker
ROW_NUMBER() OVER (
    PARTITION BY order_id
    ORDER BY
        try_cast(modified_on AS TIMESTAMPTZ) DESC NULLS LAST,
        CASE ingest_method 
            WHEN 'webhook' THEN 1 
            WHEN 'history_log' THEN 2 
            ELSE 3 END ASC,
        _dlt_load_id DESC  -- THÊM: newest load wins tiebreak
) = 1
```

---

## 3. Raw Data Deduplication

### Hiện tại

Pipeline dùng 2-level dedup trong `src_*` models:
1. **Technical dedup**: `ROW_NUMBER() PARTITION BY entity_id` (dlt envelope ID)
2. **Business dedup**: `QUALIFY ROW_NUMBER() PARTITION BY order_id` với ingest_method priority (webhook > history_log > batch)

Đây là thiết kế đúng. Tuy nhiên có 2 lỗ hổng:

### Critical: Webhook ACK không idempotent

Nếu consumer crash giữa write-to-parquet và ACK → webhook re-process → payload xuất hiện 2 lần trong raw. Dedup business-level giảm thiểu nhưng không loại bỏ hoàn toàn nếu 2 payload có khác nhau (timestamp drift).

**Fix:**
```python
# Ghi với unique constraint trên external_message_id
try:
    for msg in messages:
        write_to_parquet_idempotent(msg, unique_key='external_message_id')
    ack_batch([m.id for m in messages if write_succeeded(m)])
except Exception:
    raise  # Message tự release sau lock TTL
```

### Order Items Thiếu Dedup

`src_sapo_v2_order_items` không có unique_key check → nếu order JSON chứa duplicate line items, cả 2 đều persist.

```sql
-- Thêm vào stg_sapo_v2_order_items
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY order_id, line_number
    ORDER BY _dlt_load_id DESC
) = 1
```

### Thời gian Consolidation Raw Data

Câu hỏi từ user: **có nên consolidate/compact raw parquet sau một thời gian?**

**Khuyến nghị:** CÓ, nhưng cẩn thận:
- Sau 90 ngày, gom các file theo tháng thành 1 file `year={Y}/month={M}/consolidated.parquet`
- Chỉ compact sau khi verify dedup hoàn chỉnh ở staging layer
- Giữ raw gốc ít nhất 30 ngày sau compact trước khi xóa (audit safety)
- **Không compact data &lt; 30 ngày** — incremental pipeline còn cần re-read

---

## 4. SQLite Indexes (CRM)

### Đã có (✅)
- `idx_party_phone` — crm_party(primary_phone)
- `idx_activity_party_occurred` — crm_activity(party_id, occurred_at DESC)
- `idx_task_assignee_status_due` — crm_task(assignee_user_id, status, due_at)
- ~15 indexes khác

### Thiếu (cần tạo)

```sql
-- Migration mới: 0034_missing_indexes.up.sql

-- Customer search by status + date (dashboard queries)
CREATE INDEX IF NOT EXISTS idx_party_status_created
  ON crm_party (status, created_at DESC);

-- Staff activity coaching (high frequency)
CREATE INDEX IF NOT EXISTS idx_activity_staff_occurred
  ON crm_activity (staff_user_id, occurred_at DESC);

-- Task lookup per customer (action queue)
CREATE INDEX IF NOT EXISTS idx_task_party_status
  ON crm_task (party_id, status);

-- Campaign progress tracking
CREATE INDEX IF NOT EXISTS idx_hug_target_campaign_state
  ON crm_hug_campaign_target (campaign_id, state);

-- Identity resolution
CREATE INDEX IF NOT EXISTS idx_identity_link_party
  ON crm_identity_link (party_id);
```

**Expected impact:** 20-30% speedup trên customer coaching + action queue queries.

---

## 5. DuckDB Serving Layer

DuckDB không có persistent index (in-memory only) — đây là by design. Tối ưu tập trung vào:

| Gap | Fix |
|-----|-----|
| Rolling files không có cleanup | Implement retention 7 versions |
| Fact tables không sorted/clustered | Re-write với `ORDER BY date_key` sau dbt run |
| Hive raw: DuckDB mở 100s files | Consolidation job monthly super-parquets |

**Thêm PRAGMA optimize sau write:**
```python
con = duckdb.connect('data_lake/serving/olap.duckdb', read_only=False)
con.execute("PRAGMA optimize")
con.close()
```

---

## 6. Unresolved Questions

1. Tổng size `sapo_raw/` hiện tại? → quyết định urgency của consolidation strategy
2. Webhook consumer có bao giờ crash giữa write và ACK chưa? → mức độ urgent của idempotent fix
3. % late-arriving orders &gt;24h là bao nhiêu? → validate lookback buffer 3 ngày có đủ không
4. P95 query latency cho "orders last 7 days" trên Metabase? → baseline trước khi cluster
5. `dlt state` có bao giờ reset manual không? → ảnh hưởng đến watermark strategy

---

## Action Plan (Ưu tiên)

### Tuần 1 — Critical + Quick Wins
1. [ ] Thêm `unique_key=['customer_key']` vào `dim_customers_base`
2. [ ] Tạo CRM migration `0034_missing_indexes.up.sql` với 5 indexes trên
3. [ ] Extend customer metric lookback: 1 ngày → 3 ngày
4. [ ] Fix order dedup tiebreaker: thêm `_dlt_load_id DESC`

### Tuần 2 — Medium Priority
5. [ ] Thêm hive partitioning cho 3 intermediate models
6. [ ] Implement rolling parquet retention policy (7 versions)
7. [ ] Thêm dedup cho `stg_sapo_v2_order_items`

### Tuần 3+ — Architecture
8. [ ] Idempotent ACK cho webhook consumer
9. [ ] Raw data consolidation job (90-day+ data)
10. [ ] SCD Type 2 cho order status history (if analytics cần)
