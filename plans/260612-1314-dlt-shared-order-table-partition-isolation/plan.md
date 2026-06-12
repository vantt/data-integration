# Plan: dlt Shared Order Table — Partition Isolation Fix

**Status:** PENDING  
**Priority:** High — bất kỳ `--full-refresh --force` nào cũng có thể xóa toàn bộ data  
**Trigger:** Incident 2026-06-12 — `refresh="drop_pipeline_state"` xóa toàn bộ `order/` directory

---

## Problem

4 pipeline khác nhau cùng ghi vào **1 dlt table name `order`** trong dataset `sapo_raw`:

| Pipeline | `pipeline_name` | `ingest_method` |
|---|---|---|
| `run_orders_batch.py` | `sapo_orders_batch` | `batch_sync` |
| `run_history_log.py` | `sapo_history_log_pipeline` | `history_log` |
| `webhook_consumer.py` | (webhook pipeline) | `webhook` |
| text parser (one-time) | — | `text` |

dlt filesystem destination coi `sapo_raw/order/` là **1 logical table duy nhất**. `ingest_method=` chỉ là file layout placeholder — dlt không hiểu đây là ranh giới ownership giữa các pipeline.

**Hậu quả:** Bất kỳ lệnh nào yêu cầu dlt DROP TABLE `order` (dù từ pipeline nào) sẽ xóa **toàn bộ** 4 partition:
```
dlt.run(refresh="drop_sources" | "drop_pipeline_state")
  → rm -rf sapo_raw/order/
        ingest_method=batch_sync/
        ingest_method=history_log/   ← bị vạ lây
        ingest_method=webhook/       ← bị vạ lây
        ingest_method=text/          ← bị vạ lây (irreplaceable)
```

---

## Current State (sau fix cbba8bb)

| Path | Status | Rủi ro còn lại |
|---|---|---|
| `--reset-cursor` | ✅ An toàn | Không |
| `--full-refresh --force` | ⚠️ Vẫn dùng `refresh="drop_sources"` | DROP TABLE toàn bộ |
| Schema migration của 1 pipeline | ⚠️ Chưa kiểm tra | Schema conflict cross-pipeline |
| Future dlt version upgrade | ⚠️ Behavior có thể thay đổi | Unpredictable |

---

## Root Cause

`sapo_raw/order/` là shared directory nhưng dlt không có concept "partial table ownership". Khi dlt cần DROP TABLE, nó xóa directory — không có cơ chế whitelist/protect partition.

---

## Options

### Option A — Tách table name (Recommended)

Mỗi pipeline dùng tên table riêng:

```
sapo_raw/
├── order_batch/          ← sapo_orders_batch
├── order_history_log/    ← sapo_history_log_pipeline
├── order_webhook/        ← webhook pipeline
└── order_text/           ← text (historical, read-only)
```

dbt `src_sapo_orders_v2` đọc từ `read_parquet('sapo_raw/order_*/**/*.parquet')` thay vì `order/**`.

**Pros:**
- DROP TABLE trên 1 pipeline không ảnh hưởng pipeline khác
- Isolation hoàn toàn — dlt quản lý schema riêng từng table
- `--full-refresh --force` an toàn

**Cons:**
- Migration data lake: rename directories
- Cập nhật dbt source path
- Cập nhật `ingest_method` column value (vẫn giữ để downstream biết nguồn)

**Files cần thay đổi:**
- `ingestion/src/sapo/orders.py` — dlt resource name: `"order"` → `"order_batch"`
- `ingestion/src/sapo/history_log.py` — resource name: `"order"` → `"order_history_log"`
- `ingestion/src/sapo/webhook_consumer.py` — `table_name = 'order'` → `'order_webhook'`
- `transformation/models/staging/src_sapo_orders_v2.sql` — glob pattern
- `transformation/sources.yml` — source table definition
- Migration script: rename existing directories + verify row counts

### Option B — Guard `--full-refresh --force` (Minimal fix)

Thay `refresh="drop_sources"` bằng manual deletion (tương tự fix của `--reset-cursor`):

```python
# Thay vì refresh="drop_sources":
# 1. Xóa destination state JSONL files cho pipeline này
# 2. Xóa local state dir
# 3. Xóa CHỈ partition thuộc về pipeline này:
#    sapo_raw/order/ingest_method=batch_sync/
# KHÔNG xóa history_log, webhook, text
```

**Pros:** Ít thay đổi, không cần migrate data lake

**Cons:** Phức tạp để implement đúng (phải biết partition value của từng pipeline), vẫn là workaround không phải fix root cause

### Option C — Separate dataset per pipeline

```
sapo_orders_raw/order/    ← sapo_orders_batch
sapo_history_raw/order/   ← sapo_history_log_pipeline
sapo_webhook_raw/order/   ← webhook pipeline
```

**Pros:** Isolation hoàn toàn ở dataset level  
**Cons:** Phá vỡ cấu trúc hiện tại nhiều hơn Option A, dbt glob phức tạp hơn

---

## Recommendation

**Option A** — tách table name. Đây là fix đúng về kiến trúc, implementation rõ ràng, không phức tạp hơn Option B nhiều nhưng giải quyết root cause thật sự.

---

## Migration Steps (Option A)

1. **Stop tất cả Dagster jobs** liên quan đến order ingestion
2. **Rename directories** trong data lake:
   ```bash
   mv sapo_raw/order/ingest_method=batch_sync     → sapo_raw/order_batch/ingest_method=batch_sync
   mv sapo_raw/order/ingest_method=history_log    → sapo_raw/order_history_log/ingest_method=history_log
   mv sapo_raw/order/ingest_method=webhook        → sapo_raw/order_webhook/ingest_method=webhook
   mv sapo_raw/order/ingest_method=text           → sapo_raw/order_text/ingest_method=text
   ```
3. **Cập nhật dlt resource names** trong source code
4. **Xóa dlt state files** cũ (schema mismatch sau rename)
5. **Cập nhật dbt** glob path trong `src_sapo_orders_v2.sql`
6. **Chạy dbt full-refresh** `src_sapo_orders_v2+`
7. **Chạy bootstrap_serving_views.py** (stop Metabase trước)
8. **Verify** row counts khớp trước/sau migration

---

## Risk Assessment

| Rủi ro | Khả năng | Impact | Mitigation |
|---|---|---|---|
| dbt glob không bắt đủ file | Medium | High | Test với `read_parquet` trước khi deploy |
| dlt schema conflict sau rename | Medium | Medium | Xóa state files + chạy với `--reset-cursor` |
| Downtime ingestion | Low | Low | Dagster tự retry sau resume |
| `order_text` là irreplaceable | — | — | Rename chứ không xóa |

---

## Related

- Incident report: `plans/260612-1042-orders-batch-reingestion/`
- Fix commit: `cbba8bb` (`--reset-cursor` safe path)
- Lesson learned: L124 (lessons-learned.md)
- Memory: `project_sapo_history_log_truncation.md`
