# ADR-006: Asset-level locking, priority hierarchy, schedule offset

> **Trạng thái:** Accepted
> **Ngày:** 2026-03-31
> **Tham chiếu:** [`AGENTS.md` §Concurrency](../../AGENTS.md)

## Bối cảnh

Nhiều Dagster jobs chạy song song (Realtime/1m, Incremental/10m, Nightly). DuckDB chỉ cho phép 1 writer. Cần cơ chế coordination mà không serialize toàn bộ pipeline.

## Quyết định

### 1. Asset-level locking (không phải job-level)

```python
op_tags={"dagster/concurrency_key": "duckdb_lock"}  # chỉ trên dbt assets
```

- Chỉ lock bước dbt (write DuckDB), không lock dlt (write Parquet)
- dlt ingestion chạy song song tự do — chỉ ghi Parquet files

### 2. Priority hierarchy (yielding)

```
Realtime (1m)     yields to → Nightly, Manual, Incremental
Incremental (10m) yields to → Nightly, Manual
Nightly           runs with exclusivity
```

Job nhẹ (chạy thường xuyên) nhường job nặng (chạy ít, quan trọng hơn).

### 3. Schedule offset (minute splitting)

```
Incremental: */10 ... (runs at :00, :10, :20, ...)
Realtime:    1-9,11-19,... (explicitly excludes :00, :10)
```

Tránh 2 jobs cùng start tại cùng timestamp → race condition khi check "ai đang chạy?"

## Lý do

- **Asset-level** (không job-level): dlt ghi Parquet song song an toàn, chỉ dbt cần exclusive access DuckDB → serialize toàn bộ job là lãng phí
- **Priority hierarchy**: Realtime chạy mỗi phút, nếu không yield sẽ starve Nightly batch (chạy 1 lần/đêm nhưng quan trọng cho reconciliation)
- **Schedule offset**: Race condition thực tế — 2 jobs start cùng lúc, cả 2 check "không ai active" → cả 2 acquire lock → deadlock hoặc corruption

## Hệ quả

- Dagster Global Concurrency Limits phải được cấu hình (`duckdb_lock`, limit: 1)
- Cron expressions phức tạp hơn (minute splitting)
- Job nhẹ có thể bị delay khi job nặng đang chạy (chấp nhận được)

## Khi nào xem xét lại

- Nếu chuyển sang database hỗ trợ concurrent writes → bỏ locking
- Nếu Dagster cải thiện native priority scheduling → đơn giản hóa cron
