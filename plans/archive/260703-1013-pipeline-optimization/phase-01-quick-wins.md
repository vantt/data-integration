# Phase 1: Quick Wins
**Effort:** 1-2 ngày | **Risk:** Thấp

## 1.1 CRM — Migration 0034: Missing Indexes

**File:** `crm/migrations/0034_missing_indexes.up.sql`

Tất cả 3 indexes dưới đây đều thiếu và được query thường xuyên:

```sql
-- crm_activity_log(staff_user_id, occurred_at DESC)
-- Query pattern: "100 hoạt động gần nhất của nhân viên X" (coaching dashboard)
CREATE INDEX IF NOT EXISTS idx_activity_log_staff_occurred
  ON crm_activity_log (staff_user_id, occurred_at DESC);

-- crm_task(party_id, status)
-- Query pattern: "open tasks của khách X" (action queue lookup)
CREATE INDEX IF NOT EXISTS idx_task_party_status
  ON crm_task (party_id, status);

-- crm_hug_campaign_target(campaign_id, state)
-- Query pattern: "đếm targets theo state mỗi campaign" (campaign admin)
CREATE INDEX IF NOT EXISTS idx_hug_target_campaign_state
  ON crm_hug_campaign_target (campaign_id, state);
```

**Apply:** `docker compose restart crm` (migrations bind-mounted, auto-apply on startup).

**Down migration** (`0034_missing_indexes.down.sql`):
```sql
DROP INDEX IF EXISTS idx_activity_log_staff_occurred;
DROP INDEX IF EXISTS idx_task_party_status;
DROP INDEX IF EXISTS idx_hug_target_campaign_state;
```

---

## 1.2 dbt — int_customer_metrics: Extend Lookback 1 → 3 Days

**File:** `transformation/models/marts/core/intermediate/int_customer_metrics.sql`

**Line 39 hiện tại:**
```sql
WHERE updated_at >= (SELECT MAX(metric_calculated_at) - INTERVAL '1 day' FROM {{ this }})
```

**Sửa thành:**
```sql
WHERE updated_at >= (SELECT MAX(metric_calculated_at) - INTERVAL '3 days' FROM {{ this }})
```

**Lý do:** Sapo API clock skew + dlt batch reordering có thể làm orders với `updated_at` đến muộn 12-24h. Buffer 1 ngày không đủ khi có multiple reordering hops. 3 ngày = 2x safety margin với chi phí incremental tăng không đáng kể (orders trong 3 ngày vs 1 ngày).

**Không cần full-refresh** — chỉ thay interval, không thêm column.

---

## 1.3 dbt — src_sapo_v2_orders: Add _dlt_load_id Tiebreaker

**File:** `transformation/models/staging/src_sapo_v2_orders.sql`

**Vấn đề:** Trong cùng một batch, nếu 2 bản ghi của cùng `entity_id` có `modified_on` giống nhau và cùng `ingest_method`, ROW_NUMBER không deterministic.

**Hiện tại (CTE `deduped`, ~line 57-72):**
```sql
ROW_NUMBER() OVER (
    PARTITION BY entity_id
    ORDER BY
        try_cast(json_extract_string(payload, '$.modified_on') AS TIMESTAMPTZ) DESC NULLS LAST,
        CASE
            WHEN ingest_method = 'webhook' THEN 1
            WHEN ingest_method = 'history_log' THEN 2
            ELSE 3
        END ASC
) AS rn
```

**Sửa thành — thêm `_dlt_load_id DESC` làm tiebreaker cuối:**
```sql
ROW_NUMBER() OVER (
    PARTITION BY entity_id
    ORDER BY
        try_cast(json_extract_string(payload, '$.modified_on') AS TIMESTAMPTZ) DESC NULLS LAST,
        CASE
            WHEN ingest_method = 'webhook' THEN 1
            WHEN ingest_method = 'history_log' THEN 2
            ELSE 3
        END ASC,
        _dlt_load_id DESC  -- newest load wins when modified_on + ingest_method tie
) AS rn
```

**Áp dụng tương tự** cho QUALIFY block (business dedup) nếu cũng có ORDER BY giống nhau.

**Không cần full-refresh** — logic change không ảnh hưởng schema.

---

## Validation

```bash
# 1. Verify CRM indexes applied
docker compose exec crm sqlite3 /data/crm.db ".indexes crm_activity_log"
docker compose exec crm sqlite3 /data/crm.db ".indexes crm_task"

# 2. Spot-check int_customer_metrics: so sánh row count trước/sau lookback change
# (chạy dbt incremental, đếm rows updated vs expected)
docker compose exec data_platform dbt run -s int_customer_metrics --no-full-refresh

# 3. Verify orders dedup: không có duplicate order_id trong src_sapo_v2_orders
docker compose exec data_platform dbt test -s src_sapo_v2_orders
```
